"""Task `directory`: one queue item = one statewide source of officials (a web page, a JSON answer, or a PDF).

Payload: {"url", "method" (GET|POST), "data" (form fields), "fmt" (html|json|pdf), "state", "source", "label"}.
- html: every table row becomes a record (as in whoswho).
- json: every object in the answer (or in its first list of objects) becomes a record.
- pdf: the file goes to the bucket under directories/; each page's text becomes a record (parsed later on the box).
Every answer is also kept in the bucket, so it can be parsed again without asking the site.
`python directory.py --local '<payload json>'` runs one item without the hub.
"""
import gzip
import hashlib
import io
import json
import os
import sys
import threading
import time

import requests

from certs_trust import trust

from officials import normalise, pubutility, tables

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; s1d-labs public records; +https://labs.s1d.me)"}
PLAIN_UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"     # one retry on a 406 (see whoswho.py)
stop = threading.Event()     # main() swaps in scrape_hub_client.stop_flag(), set on SIGINT / SIGTERM


def objects(doc):
    """The records in a JSON answer: a dict that looks like one record, or the first list of dicts found."""
    if isinstance(doc, list):
        return [x for x in doc if isinstance(x, dict)]
    if isinstance(doc, dict):
        for k in ("data", "result", "results", "items", "records", "rows"):
            if isinstance(doc.get(k), list):
                return objects(doc[k])
        lists = [v for v in doc.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        return objects(lists[0]) if lists else [doc]
    return []


def pdf_pages(body):
    from pypdf import PdfReader
    try:
        return [(p.extract_text() or "") for p in PdfReader(io.BytesIO(body)).pages]
    except Exception:       # a broken or scanned PDF: kept in the bucket, read later by OCR
        return []


def flat(d):
    return {k: ("" if v is None else (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))) for k, v in d.items()}


def run(item, get):
    """Returns (records, files, why). `get(method, url, data)` -> requests.Response or None."""
    p = item["payload"]
    r = get(p.get("method", "GET"), p["url"], p.get("data"))
    if r is None:
        return [], [], "no answer"
    meta = {k: p.get(k, "") for k in ("state", "source", "label")}
    if p.get("lgd_code"):
        meta["lgd_code"] = p["lgd_code"]      # a source about one body (big-city officer lists): rows tie to it directly
    key = hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16]
    fmt = p.get("fmt", "html")
    recs, files = [], []
    if fmt == "pdf":
        files.append((f"directories/{p.get('state', 'xx')}/{key}.pdf", r.content, "application/pdf"))
        for i, text in enumerate(pdf_pages(r.content), 1):
            recs.append((f"dir:{key}:p{i}", {"type": "pdf_page", **meta, "url": p["url"], "page": i, "text": text, "file": files[0][0]}))
    else:
        files.append((f"directories/{p.get('state', 'xx')}/{key}.{fmt}.gz", gzip.compress(r.content), "application/gzip"))
        if fmt == "json":
            try:
                rows = [flat(o) for o in objects(r.json())]
            except ValueError:
                rows = []
            n = 0
            for cells in rows:
                embedded = [t for v in cells.values() if "<table" in v for t in tables(v)]
                if embedded:     # a CMS answer that carries an HTML table inside a text field (e.g. MCD's showContent)
                    for t in embedded:
                        for c in t["rows"]:
                            recs.append((f"dir:{key}:{n}", {"type": "row", **meta, "url": p["url"], "category": t["caption"] or p.get("label", ""),
                                                            "via": "json-html", **normalise(c), "cells": c}))
                            n += 1
                    continue
                recs.append((f"dir:{key}:{n}", {"type": "row", **meta, "url": p["url"], "category": p.get("label", ""), "via": "json",
                                                **normalise(cells), "cells": cells}))
                n += 1
        else:
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding or "utf-8"
            n = 0
            for t in tables(r.text) + pubutility(r.text):
                for cells in t["rows"]:
                    recs.append((f"dir:{key}:{n}", {"type": "row", **meta, "url": p["url"], "category": t["caption"] or p.get("label", ""),
                                                    "via": "table", **normalise(cells), "cells": cells}))
                    n += 1
    recs.append((f"dir:{key}", {"type": "source", **meta, "url": p["url"], "fmt": fmt, "records": len(recs), "file": files[0][0] if files else ""}))
    return recs, files, ""


def main():
    global stop
    from scrape_hub_client import HubClient, count_request, stop_flag
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    stop = stop_flag()
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)

    def get(method, url, data):
        t = time.time()
        try:
            r = s.request(method, url, data=data, timeout=(20, 120))
            if r.status_code == 406:
                hub.metric("http_406_plain_retry")
                r = s.request(method, url, data=data, timeout=(20, 120), headers={"User-Agent": PLAIN_UA})
        except requests.RequestException:
            count_request(hub, None)                             # http_error
            return None
        count_request(hub, r.status_code, time.time() - t)       # n_http, t_http_s, http_<code>, block on 403/429/503
        time.sleep(max(0.5, hub.settings.get("delay_ms", 0) / 1000))
        if r.status_code != 200:
            return None
        return r

    try:
        while time.time() < deadline and not stop.is_set():
            if hub.settings.get("paused"):
                time.sleep(30)
                continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break
            item = items[0]
            if item.get("attempts", 0) > 3:
                hub.failure("source", item["key"], "gave up after 3 attempts", url=item["payload"]["url"])
                hub.complete([item["key"]], "done", fetched=0)
                continue
            try:
                recs, files, why = run(item, get)
            except Exception as e:
                recs, files, why = [], [], f"{type(e).__name__}: {e}"[:200]
            if files:
                hub.upload_many(files)
            for rid, data in recs:
                hub.record(rid, data)
            if why:
                hub.failure("source", item["key"], why, url=item["payload"]["url"])
                hub.complete([item["key"]], "failed", error=why)
            else:
                hub.complete([item["key"]], "done", fetched=len(recs))
        hub.close("finished" if not stop.is_set() else "failed", "" if not stop.is_set() else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(payload):
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)
    item = {"key": "local", "payload": json.loads(payload)}
    recs, files, why = run(item, lambda m, u, d: s.request(m, u, data=d, timeout=(20, 120)))
    print(json.dumps({"why": why, "records": len(recs), "files": [f[0] for f in files]}))
    for rid, d in recs[:5]:
        print(rid, {k: d.get(k) for k in ("type", "name", "designation", "email", "phone", "page")}, str(d.get("text", ""))[:200])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        sys.exit(main())
