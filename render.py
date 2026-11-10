"""Task `render`: for sites that draw their content with JavaScript (Rajasthan's lsg.rajasthan.gov.in/<town>/ platform).
One queue item = one site. Open the start page in headless Chromium as a visitor would, follow up to MAX_PAGES links whose text or
address looks like officials / contacts / members, and read each rendered page with the same parsers as whoswho (tables, public
utility cards, people cards). Saves each rendered page to the bucket. Records match whoswho's.

`python render.py --local https://lsg.rajasthan.gov.in/mcajmer/` runs one site without the hub.
Setup: `pip install playwright` and `playwright install chromium` (the runner drops --with-deps on pool servers).
"""
import gzip
import hashlib
import json
import os
import signal
import sys
import time
from urllib.parse import urlsplit

from officials import (LINK_WORDS, candidate_links, normalise, page_title, pubutility, row_id, tables, text_people)

MAX_PAGES = 12
stop = False


def on_signal(*_):
    global stop
    stop = True


def render_site(page, item, metric=lambda *a: None, delay=1.0):
    p = item["payload"]
    url = p["url"]
    site = (urlsplit(url).netloc + "/" + urlsplit(url).path.strip("/").split("/")[0]).lower()
    meta = {"site_name": p.get("name", ""), **{k: p.get(k, "") for k in ("kind", "state", "jurisdiction")},
            **({"lgd_code": p["lgd_code"]} if p.get("lgd_code") else {})}
    recs, files, n_rows = [], [], 0

    def visit(u):
        t = time.time()
        try:
            resp = page.goto(u, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            metric("http_error")
            return None
        metric("n_http")
        metric("t_http_s", time.time() - t)
        if resp is not None and resp.status != 200:
            metric(f"http_{resp.status}")
        page.wait_for_timeout(6000)          # Angular pages keep connections open: give the lists time to fill in
        time.sleep(delay)
        return page.content()

    home = visit(url)
    if home is None:
        return False, "start page did not render", [], [], 0
    todo = [u for u in candidate_links(home, page.url, urlsplit(page.url).hostname or "", limit=30)
            if urlsplit(u).path.startswith(urlsplit(url).path.rstrip("/"))]
    # Angular menus are often <a> without href: also click-free routes the page shows as text links
    seen, pages = {url.rstrip("/")}, [(url, home)]
    while todo and len(pages) < MAX_PAGES and not stop:
        u = todo.pop(0)
        if u.rstrip("/") in seen:
            continue
        seen.add(u.rstrip("/"))
        html = visit(u)
        if html is not None:
            pages.append((u, html))
    for u, html in pages:
        n = 0
        for t in tables(html) + pubutility(html):
            for cells in t["rows"]:
                recs.append((row_id(site, u, t["caption"], cells), {"type": "row", "site": site, **meta, "page": u, "category": t["caption"],
                                                                     "via": "render", **normalise(cells), "cells": cells}))
                n += 1
        if not n:
            for t in text_people(html):
                for cells in t["rows"]:
                    recs.append((row_id(site, u, "people", cells), {"type": "row", "site": site, **meta, "page": u, "category": "people",
                                                                     "via": "render-text", **normalise(cells), "cells": cells}))
                    n += 1
        h = hashlib.sha1(u.encode()).hexdigest()[:16]
        path = f"pages/{site.replace('/', '_')}/{h}.rendered.html.gz"
        files.append((path, gzip.compress(html.encode("utf-8", "replace")), "application/gzip"))
        recs.append((f"{site}:page:{h}", {"type": "page", "site": site, **meta, "url": u, "final_url": u, "title": page_title(html),
                                          "rows": n, "file": path, "rendered": True,
                                          "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
        n_rows += n
    return True, "", recs, files, n_rows


def browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    b = pw.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(user_agent="Mozilla/5.0 (compatible; s1d-labs public records; +https://labs.s1d.me)", ignore_https_errors=False,
                        **({"proxy": {"server": os.environ["SCRAPE_PROXY"]}} if os.environ.get("SCRAPE_PROXY") else {}))
    return pw, b, ctx.new_page()


def main():
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    pw, b, page = browser()
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
                hub.failure("site", item["key"], "gave up after 3 attempts", url=item["payload"]["url"])
                hub.complete([item["key"]], "done", fetched=0)
                continue
            try:
                ok, why, recs, files, n = render_site(page, item, hub.metric, max(1.0, hub.settings.get("delay_ms", 0) / 1000))
            except Exception as e:
                ok, why, recs, files, n = False, f"{type(e).__name__}: {e}"[:200], [], [], 0
            for i in range(0, len(files), 100):
                hub.upload_many(files[i:i + 100])
            for rid, data in recs:
                hub.record(rid, data)
            if ok:
                hub.complete([item["key"]], "done", fetched=n)
            else:
                hub.failure("site", item["key"], why, url=item["payload"]["url"])
                hub.complete([item["key"]], "failed", error=why)
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise
    finally:
        b.close()
        pw.stop()


def local(url):
    pw, b, page = browser()
    try:
        ok, why, recs, files, n = render_site(page, {"key": url, "payload": {"url": url}})
    finally:
        b.close()
        pw.stop()
    print(json.dumps({"ok": ok, "why": why, "rows": n, "pages": [d["url"] for _, d in recs if d["type"] == "page"]}, indent=1))
    for _, d in [x for x in recs if x[1]["type"] == "row"][:8]:
        print({k: d.get(k) for k in ("category", "name", "designation", "phone", "email")})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        sys.exit(main())
