"""Source trail (owner, 2026-11-12): for every record, which page or file it came from, the exact bytes that were read, and how.

Every response a reader gets through the pool loop's get() is noted: requested url, final url, method, form data or not, HTTP
status, content type, size, sha256 of the body, fetch time, and where the copy is:
  - live responses: the body is saved ONCE in the project's bucket at sources/<sha[:2]>/<sha256><ext>.gz (gzip of the exact
    bytes; the path is the content hash, so the same bytes always land on the same key) and a record "src:<sha256>" (type
    source_copy) indexes it;
  - archive-first hits: no new copy; the trail names the archive.s1d.me capture (url + capture time).
Per queue item one record "trail:<item key>:<UTC time>" (type trail) lists the reader, the git commit of the family checkout,
the task, project, run, worker, start/end time and every source of the item in fetch order.
Every data record of the item gets:
  "trail": the trail record id,
  "src": {"sha256", "url"} of its source when the reader says which one (data["src_url"]) or when the item read one source only,
  "method": what the reader did ("html table", "pdf text", "ocr", "json api", ...): the reader's own value, else the module's
           METHOD constant, else a default from the content type;
and keeps any position the reader gives in "src_pos" ({"page", "line", "row", "cells"} as the reader knows them).
How a record names its source, most exact first:
  1. data["src_sha256"] (from at(r)): the exact bytes; needed when one url gave several answers (POST paging, ASP.NET postbacks);
  2. data["src_url"]: the url the reader passed to get() (or the final url); used only when that url gave one answer in the item;
  3. the item read one source only;
  4. the record's own url field ("url", "source", "page", "pdf_url", "file_url") when it is a url the item read and that url gave
     one answer: src then carries "via": "record url" (the reader did not say it in so many words).
A reader that reads a copy saved in the bucket earlier sets data["src"] = {"sha256", "url", "file"} itself; it is kept.
"""
import gzip
import hashlib
import json
import os
import socket
import subprocess
import threading
import time

MAX_COPY = 200 * 1024 * 1024        # one body larger than this is noted (sha256, size) but not copied
MAX_HELD = 400 * 1024 * 1024
MAX_FORM = 8 * 1024             # form data kept in full up to this size (ASP.NET view state is often larger: then its hash)        # bodies held for one item before its end; beyond this they are noted, not copied
EXT = (("pdf", ".pdf"), ("html", ".html"), ("json", ".json"), ("xml", ".xml"), ("csv", ".csv"), ("zip", ".zip"),
       ("spreadsheet", ".xlsx"), ("excel", ".xls"), ("image/png", ".png"), ("image/jp", ".jpg"), ("text/plain", ".txt"))
_commit = None


def commit():
    """The git commit of the family checkout this process runs (GitHub runner: GITHUB_SHA when it is this repo's)."""
    global _commit
    if _commit is None:
        here = os.path.dirname(os.path.abspath(__file__))
        try:
            _commit = subprocess.run(["git", "-C", here, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            _commit = ""
        _commit = _commit or os.environ.get("CIVIC_COMMIT", "")
    return _commit


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ext_of(ctype, url):
    c = (ctype or "").lower()
    for k, e in EXT:
        if k in c:
            return e
    tail = (url or "").split("?")[0].rsplit("/", 1)[-1]
    if "." in tail and len(tail.rsplit(".", 1)[1]) <= 5:
        return "." + tail.rsplit(".", 1)[1].lower()
    return ".bin"


def at(r, url=None):
    """What a record says about its source response r: {"src_url": the url asked (else r.url), "src_sha256": hash of the bytes}.
    The hash is worked out once per response. Use as data.update(provenance.at(r, url)) or {**provenance.at(r, url), ...}."""
    if r is None:
        return {}
    sha = getattr(r, "_src_sha256", None)
    if sha is None:
        try:
            sha = hashlib.sha256(r.content or b"").hexdigest()
        except Exception:
            sha = ""
        try:
            r._src_sha256 = sha
        except AttributeError:
            pass
    out = {"src_url": url or getattr(r, "url", "") or ""}
    if sha:
        out["src_sha256"] = sha
    return out


def file_src(body, url, file):
    """src for data read from a copy saved in the bucket earlier: {"sha256" of the bytes read, "url" of the original, "file" key}."""
    return {"sha256": hashlib.sha256(body or b"").hexdigest(), "url": url or "", "file": file}


def hook(trail):
    """A requests response hook that notes every 200 answer of a reader's own session in the trail (forms/*.py readers that
    keep a session of their own for ASP.NET postbacks): session.hooks["response"].append(provenance.hook(trail))."""
    def _note(r, *a, **kw):
        try:
            if getattr(r, "status_code", None) != 200 or getattr(r, "is_redirect", False):
                return r
            req = getattr(r, "request", None)
            method = getattr(req, "method", "GET") or "GET"
            body = getattr(req, "body", None) if method.upper() != "GET" else None
            trail.note(r, getattr(req, "url", "") or r.url, method, body)
        except Exception:
            pass
        return r
    return _note


def default_method(ctype):
    c = (ctype or "").lower()
    if "pdf" in c:
        return "pdf"
    if "json" in c:
        return "json api"
    if "html" in c:
        return "html page"
    return c.split(";")[0] or "unknown"


class Trail:
    """One per worker thread. begin(item) -> the loop's get() calls note(...) for each response -> finish(recs, files)."""

    def __init__(self, task, project, run_id=""):
        self.task, self.project, self.run_id = task, project, str(run_id or "")
        self.worker = os.environ.get("SCRAPE_RUN_ID") or socket.gethostname()
        self.stored = set()          # sha256 copied by this process already
        self.lock = threading.Lock()
        self.item = None
        self.sources, self.bodies, self.held = [], {}, 0

    def begin(self, item, reader=""):
        self.item, self.reader = item, reader
        self.started = now()
        self.sources, self.bodies, self.held = [], {}, 0

    def note(self, r, url, method="GET", data=None):
        """A response the reader got (status 200, or any status the loop hands on). Never raises."""
        if self.item is None or r is None:
            return
        try:
            body = r.content or b""
        except Exception:      # a stream that cannot be read again: note what we know
            body = b""
        sha = hashlib.sha256(body).hexdigest()
        ctype = (r.headers.get("Content-Type") or "") if getattr(r, "headers", None) is not None else ""
        e = {"url": url, "final_url": getattr(r, "url", "") or url, "method": method.upper(), "form": data is not None,
             "status": getattr(r, "status_code", None), "content_type": ctype, "bytes": len(body), "sha256": sha,
             "fetched_at": now()}
        if data is not None:                 # what was sent, so the request can be repeated: in full when small, else its hash
            raw = data if isinstance(data, (bytes, str)) else json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
            raw_b = raw.encode("utf-8", "replace") if isinstance(raw, str) else raw
            if len(raw_b) <= MAX_FORM:
                e["form_data"] = raw if isinstance(raw, str) else raw_b.decode("utf-8", "replace")
            else:
                e["form_sha256"], e["form_bytes"] = hashlib.sha256(raw_b).hexdigest(), len(raw_b)
        arch = getattr(r, "from_archive", "")
        if arch:
            e["copy"] = {"archive": url, "captured": arch}
        elif not body:
            e["copy"] = None
        elif len(body) > MAX_COPY or self.held + len(body) > MAX_HELD:
            e["copy"] = None
            e["not_copied"] = "size cap"
        else:
            e["copy"] = {"bucket": f"sources/{sha[:2]}/{sha}{ext_of(ctype, e['final_url'])}.gz"}
            if sha not in self.bodies:
                self.bodies[sha] = body
                self.held += len(body)
        self.sources.append(e)

    def finish(self, recs, files, reader_method=""):
        """Add the copies, the source_copy index records and the trail record to (recs, files); annotate the data records.
        Returns (recs, files). Data records are the ones given; the added records are appended."""
        if self.item is None:
            return recs, files
        key = self.item.get("key", "")
        tid = f"trail:{key}:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        single = self.sources[0] if len({s["sha256"] for s in self.sources if s["bytes"]}) == 1 else None
        by_url, shas_of, by_sha = {}, {}, {}
        for s in self.sources:
            by_sha.setdefault(s["sha256"], s)
            for u in {s["url"], s["final_url"]}:
                by_url.setdefault(u, s)
                shas_of.setdefault(u, set()).add(s["sha256"])

        def one(u):          # the source of a url that gave exactly one answer in this item, else None
            return by_url.get(u) if isinstance(u, str) and u and len(shas_of.get(u, ())) == 1 else None
        ctypes = {s["content_type"].split(";")[0].strip().lower() for s in self.sources if s["bytes"]}
        for _, data in recs:
            if not isinstance(data, dict):
                continue
            data.setdefault("trail", tid)
            sha = data.pop("src_sha256", None)
            src, via = (by_sha.get(sha) if sha else None) or one(data.get("src_url")) or single, ""
            if src is None and sha:          # bytes the trail did not see (read outside get()): the reader's own hash and url
                data.setdefault("src", {"sha256": sha, "url": data.get("src_url") or ""})
            if src is None and "src" not in data and not data.get("src_url"):
                src = next((one(data.get(k)) for k in ("url", "source", "page", "pdf_url", "file_url") if one(data.get(k))), None)
                via = "record url" if src else ""
            if src and "src" not in data:
                data["src"] = {"sha256": src["sha256"], "url": src["final_url"], **({"via": via} if via else {})}
            # the reader's word first; else from this record's source, or from the one content type all sources share
            data.setdefault("method", reader_method or default_method((src or {}).get("content_type", "")
                                                                         or (next(iter(ctypes)) if len(ctypes) == 1 else "")))
        extra_recs, extra_files = [], []
        for s in self.sources:
            c = s.get("copy") or {}
            sha = s["sha256"]
            if "bucket" not in c or sha not in self.bodies:
                continue
            with self.lock:
                if sha in self.stored:
                    continue
                self.stored.add(sha)
            extra_files.append((c["bucket"], gzip.compress(self.bodies[sha], 6), "application/gzip"))
            extra_recs.append((f"src:{sha}", {"type": "source_copy", "sha256": sha, "file": c["bucket"], "url": s["url"],
                                              "final_url": s["final_url"], "content_type": s["content_type"], "bytes": s["bytes"],
                                              "fetched_at": s["fetched_at"]}))
        extra_recs.append((tid, {"type": "trail", "item": key, "project": self.project, "task": self.task, "reader": self.reader,
                                 "payload": self.item.get("payload", {}), "commit": commit(), "run_id": self.run_id,
                                 "worker": self.worker, "started": self.started, "finished": now(), "records": len(recs),
                                 "sources": self.sources}))
        self.item, self.bodies, self.held = None, {}, 0
        return list(recs) + extra_recs, list(files) + extra_files
