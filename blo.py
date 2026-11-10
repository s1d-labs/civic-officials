"""Task `blo`: Booth Level Officers from the public lists of state Chief Electoral Officers. One queue item = one file or page.
Payload: {"url", "kind", "state", ...}. Kinds:
- "ka-ac-json": Karnataka ceo.karnataka.gov.in/blo_data/ac/<AC>.json; parts = [part, station, BLO, phone, supervisor, phone,
  AERO, phone, ERO, phone].
- "html-table": any page whose tables list BLOs (Puducherry, Lakshadweep, ...): rows as in whoswho, tagged with the AC in the payload.
- "pdf": the file goes to the bucket, each page's text becomes a record (parsed later on the box).
Records: one per part ("blo:<state>:<ac>:<part>") with state, ac_no, ac_name, district, part_no, station, blo_name, blo_phone and the
supervising officers. Every answer is kept in the bucket under blo/<state>/.
`python blo.py --local '<payload json>'` runs one item without the hub.
"""
import gzip
import hashlib
import io
import json
import os
import signal
import sys
import time

import requests

from certs_trust import trust

from officials import normalise, tables

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; s1d-labs public records; +https://labs.s1d.me)"}
PLAIN_UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"
stop = False


def on_signal(*_):
    global stop
    stop = True


def ka_ac(doc, p):
    out = []
    for row in doc.get("parts") or []:
        row = list(row) + [""] * (10 - len(row))
        part = str(row[0])
        out.append((f"blo:KA:{doc.get('no')}:{part}", {
            "type": "blo", "state": "KA", "ac_no": doc.get("no"), "ac_name": doc.get("name"), "district": doc.get("district"),
            "part_no": part, "station": row[1], "blo_name": row[2], "blo_phone": str(row[3]),
            "supervisor_name": row[4], "supervisor_phone": str(row[5]), "aero_name": row[6], "aero_phone": str(row[7]),
            "ero_name": row[8], "ero_phone": str(row[9]), "version": doc.get("version"), "url": p["url"]}))
    return out


def run(item, get):
    p = item["payload"]
    r = get(p.get("method", "GET"), p["url"], p.get("data"))
    if r is None:
        return [], [], "no answer"
    key = hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16]
    kind, st = p.get("kind", "html-table"), p.get("state", "xx")
    recs = []
    if kind == "pdf":
        files = [(f"blo/{st}/{key}.pdf", r.content, "application/pdf")]
        from pypdf import PdfReader
        try:
            pages = [(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(r.content)).pages]
        except Exception:
            pages = []
        for i, text in enumerate(pages, 1):
            recs.append((f"blo:{st}:{key}:p{i}", {"type": "blo_pdf_page", "state": st, "url": p["url"], "page": i, "text": text,
                                                  "file": files[0][0], **{k: p[k] for k in ("ac_no", "label") if k in p}}))
        return recs, files, ""
    files = [(f"blo/{st}/{key}.{'json' if kind.endswith('json') else 'html'}.gz", gzip.compress(r.content), "application/gzip")]
    if kind == "ka-ac-json":
        try:
            recs = ka_ac(r.json(), p)
        except ValueError:
            return [], files, "not JSON"
    else:
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        text = r.text
        if kind == "json-html":          # Kerala show_blo: {"selectHtml": "<table>...</table>"}
            try:
                text = r.json().get("selectHtml") or ""
            except ValueError:
                return [], files, "not JSON"
        n = 0
        for t in tables(text):
            for cells in t["rows"]:
                f = normalise(cells)
                rid = f"blo:{st}:{p['booth_id']}:{n}" if p.get("booth_id") else f"blo:{st}:{key}:{n}"
                recs.append((rid, {"type": "blo", "state": st, "url": p["url"], "category": t["caption"],
                                                     **{k: p[k] for k in ("ac_no", "ac_name", "district", "part_no", "station", "booth_id") if k in p},
                                                     "blo_name": f.get("name", ""), "blo_phone": f.get("phone", ""), "cells": cells}))
                n += 1
    return recs, files, "" if recs else "no rows"


def main():
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
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
            hub.metric("http_error")
            hub.error()
            return None
        hub.metric("n_http")
        hub.metric("t_http_s", time.time() - t)
        time.sleep(max(0.5, hub.settings.get("delay_ms", 0) / 1000))
        if r.status_code != 200:
            hub.metric(f"http_{r.status_code}")
            if r.status_code in (403, 429, 503):
                hub.block()
            return None
        return r

    try:
        while time.time() < deadline and not stop:
            if hub.settings.get("paused"):
                time.sleep(30)
                continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break
            item = items[0]
            if item.get("attempts", 0) > 3:
                hub.failure("blo", item["key"], "gave up after 3 attempts", url=item["payload"]["url"])
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
            if why and not recs:
                hub.failure("blo", item["key"], why, url=item["payload"]["url"])
                hub.complete([item["key"]], "failed", error=why)
            else:
                hub.complete([item["key"]], "done", fetched=len(recs))
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(payload):
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)
    recs, files, why = run({"key": "local", "payload": json.loads(payload)}, lambda m, u, d: s.request(m, u, data=d, timeout=(20, 120)))
    print(json.dumps({"why": why, "records": len(recs), "files": [f[0] for f in files]}))
    for rid, d in recs[:3]:
        print(rid, {k: d.get(k) for k in ("ac_name", "part_no", "station", "blo_name", "blo_phone")})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        sys.exit(main())
