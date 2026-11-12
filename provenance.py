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
"""
import gzip
import hashlib
import os
import socket
import subprocess
import threading
import time

MAX_COPY = 200 * 1024 * 1024        # one body larger than this is noted (sha256, size) but not copied
MAX_HELD = 400 * 1024 * 1024        # bodies held for one item before its end; beyond this they are noted, not copied
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
        by_url = {}
        for s in self.sources:
            by_url.setdefault(s["url"], s)
            by_url.setdefault(s["final_url"], s)
        ctypes = {s["content_type"].split(";")[0].strip().lower() for s in self.sources if s["bytes"]}
        for _, data in recs:
            if not isinstance(data, dict):
                continue
            data.setdefault("trail", tid)
            src = by_url.get(data.get("src_url") or "") or single
            if src and "src" not in data:
                data["src"] = {"sha256": src["sha256"], "url": src["final_url"]}
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
