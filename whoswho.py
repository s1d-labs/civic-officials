"""Task `whoswho`: one queue item = one government site. Read its home page, find the pages that list officials (Who's Who,
directory, contacts), fetch them, save each page to the bucket, and store every table row as a record. On S3WaaS sites, page
through each Who's Who category with the site's own `ww_pages` call, as the page's "next" button does.

Records: one per page read (type "page") and one per row (type "row": site, page, category, raw cells, and the common fields
name / designation / email / phone / address when the headers say so). Record ids are stable, so a rerun replaces, never doubles.
`python whoswho.py --local https://patna.nic.in/` runs one site without the hub and prints a summary.
"""
import gzip
import hashlib
import json
import os
import signal
import sys
import threading
import time
from urllib.parse import urlsplit

import requests

from certs_trust import trust
from forms.aspnet import LegacyTLS

from officials import (PEOPLE_PATH, ajax_rows, candidate_links, common_links, normalise, page_title, pager_blocks, pubutility,
                       row_id, tables, text_people)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; s1d-labs public records; +https://labs.s1d.me)"}
# Some servers (Jalandhar, Bhiwandi) answer 406 to any "Mozilla/5.0" label that is not a full browser, but serve plain clients.
# On a 406 we ask once more with this plain label, which says only who we are (owner approved, 2026-11-10).
PLAIN_UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"
MAX_PAGES = 25          # pages fetched per site (home page and candidates; AJAX pages are counted apart)
MAX_AJAX = 300          # ww_pages calls per site
# A site that fails from a GitHub runner usually refuses foreign IPs: it goes to the -in project (Indian proxies), which retries.
RETRY = os.environ.get("SCRAPE_POOL_PROJECT", "").endswith(("-in", "-geo", "-platforms", "-found", "-bigcities"))
MAX_ATTEMPTS = 3
stop = False


def on_signal(*_):
    global stop
    stop = True


class Site:
    """Everything about one site visit. `hub` may be None (local run)."""

    def __init__(self, hub, session, item, delay):
        self.hub, self.s, self.item, self.delay = hub, session, item, delay
        p = item["payload"]
        self.url = p["url"]
        self.meta = {"site_name": p.get("name", ""), **{k: p.get(k, "") for k in ("kind", "state", "jurisdiction")},
                     **({"lgd_code": p["lgd_code"]} if p.get("lgd_code") else {})}
        self.read_start = bool(p.get("read_start"))     # the start address is itself an officials page (found by search)
        self.site = (urlsplit(self.url).hostname or "").lower().removeprefix("www.")
        self.records, self.files, self.n_rows = [], [], 0

    def metric(self, *a):
        if self.hub:
            self.hub.metric(*a)

    def get(self, url, method="GET", data=None):
        t = time.time()
        try:
            try:
                r = self.s.request(method, url, data=data, timeout=(15, 45), allow_redirects=True)
            except requests.exceptions.SSLError as e:
                # servers that still need TLS legacy renegotiation (Punjab government sites): same request, certificate checks stay on
                if "renegotiation" not in str(e).lower():
                    raise
                self.metric("tls_legacy_retry")
                self.s.mount(f"https://{urlsplit(url).hostname}/", LegacyTLS())
                r = self.s.request(method, url, data=data, timeout=(15, 45), allow_redirects=True)
            except requests.exceptions.ConnectionError as e:
                # port 443 refused (Karnataka *.mrc.gov.in town sites serve plain http only): ask the same page over http
                if not url.startswith("https://") or isinstance(e, requests.exceptions.ConnectTimeout) or "refused" not in str(e).lower() \
                        and "couldn't connect" not in str(e).lower():
                    raise
                self.metric("https_refused_http_retry")
                url = "http://" + url[len("https://"):]
                r = self.s.request(method, url, data=data, timeout=(15, 45), allow_redirects=True)
            if r.status_code == 406:
                self.metric("http_406_plain_retry")
                r = self.s.request(method, url, data=data, timeout=(15, 45), allow_redirects=True, headers={"User-Agent": PLAIN_UA})
        except requests.RequestException as e:
            self.metric("http_error")
            if self.hub:
                self.hub.error()
            return None, type(e).__name__
        self.metric("n_http")
        self.metric("t_http_s", time.time() - t)
        time.sleep(self.delay)
        if r.status_code != 200:
            self.metric(f"http_{r.status_code}")
            if r.status_code in (403, 429, 503) and self.hub:
                self.hub.block()
            return None, f"http {r.status_code}"
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r, ""

    def keep_page(self, url, final, html, n_rows):
        h = hashlib.sha1(url.encode()).hexdigest()[:16]
        path = f"pages/{self.site}/{h}.html.gz"
        self.files.append((path, gzip.compress(html.encode("utf-8", "replace")), "application/gzip"))
        self.records.append((f"{self.site}:page:{h}", {"type": "page", "site": self.site, **self.meta, "url": url, "final_url": final,
                                                         "title": page_title(html), "rows": n_rows, "file": path,
                                                         "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))

    def add_rows(self, page, caption, rows, via):
        for cells in rows:
            self.records.append((row_id(self.site, page, caption, cells),
                                 {"type": "row", "site": self.site, **self.meta, "page": page, "category": caption, "via": via,
                                  **normalise(cells), "cells": cells}))
        self.n_rows += len(rows)
        return len(rows)

    def ajax(self, page_url, html):
        """Page through each S3WaaS Who's Who or directory category with the site's own call, as its "next" button does."""
        n, calls = 0, 0
        for kind in ("ww", "dir"):
            pg = pager_blocks(html, kind)
            if not pg:
                continue
            for b in pg["blocks"]:
                p = 1
                while p < b["pages"] and calls < MAX_AJAX and not stop:
                    r, _ = self.get(pg["ajaxurl"], "POST", {"action": pg["action"], "paged": p, "tax_slug": b["slug"], "type": "next",
                                                           "profile_image": pg["profile"], "filter": pg["filter"], "security": pg["nonce"]})
                    calls += 1
                    if r is None:
                        break
                    rows = ajax_rows(r.text)
                    if not rows:
                        break
                    n += self.add_rows(page_url, b["name"], rows, f"{pg['action']}:{b['slug']}:{p + 1}")
                    try:
                        if str(json.loads(r.text).get("last")) == "1":
                            break
                    except ValueError:
                        break
                    p += 1
        self.metric("ajax_calls", calls)
        return n

    def run(self):
        home, why = self.get(self.url)
        if home is None and self.url.startswith("https://"):
            home, why = self.get("http://" + self.url[8:])
        if home is None:
            return False, why or "home page did not load"
        base = home.url
        self.site = (urlsplit(base).hostname or self.site).lower().removeprefix("www.")
        todo = candidate_links(home.text, base, self.site)
        for u in common_links(base):
            if u not in todo:
                todo.append(u)
        n0 = 0
        if self.read_start:
            for t in tables(home.text):
                n0 += self.add_rows(base, t["caption"], t["rows"], "table")
            n0 += self.ajax(base, home.text)
        self.keep_page(self.url, base, home.text, n0)    # a home page's tables are mostly tenders and notices: read only when told
        seen, fetched = {base.rstrip("/")}, 0
        while todo and fetched < MAX_PAGES and not stop:
            u = todo.pop(0)
            if u.rstrip("/") in seen:
                continue
            seen.add(u.rstrip("/"))
            r, _ = self.get(u)
            fetched += 1
            if r is None or "html" not in r.headers.get("content-type", "html"):
                continue
            final = r.url
            if final.rstrip("/") != u.rstrip("/"):
                if final.rstrip("/") in seen:
                    continue
                seen.add(final.rstrip("/"))
            n = 0
            for t in tables(r.text):
                n += self.add_rows(final, t["caption"], t["rows"], "table")
            for t in pubutility(r.text):
                n += self.add_rows(final, t["caption"], t["rows"], "card")
            if not n and PEOPLE_PATH.search(urlsplit(final).path):       # people as cards (no table): members / staff pages
                for t in text_people(r.text):
                    n += self.add_rows(final, t["caption"], t["rows"], "text")
            n += self.ajax(final, r.text)
            self.keep_page(u, final, r.text, n)
            if n:      # a page with officials: its own links to more such pages (directory categories) are worth a look
                for v in candidate_links(r.text, final, self.site, limit=10):
                    if v.rstrip("/") not in seen and v not in todo:
                        todo.append(v)
        return True, ""


def main():
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    lock = threading.Lock()

    def worker():
        s = requests.Session()
        s.headers.update(HEADERS)
        while time.time() < deadline and not stop:
            with lock:
                if hub.settings.get("paused"):
                    items = None
                else:
                    items = hub.claim(1, steal=True, retry_failed=RETRY)
            if items is None:
                time.sleep(30)
                continue
            if not items:
                return
            item = items[0]
            if item.get("attempts", 0) > MAX_ATTEMPTS:     # down from India too (checked 2026-11-09): stop spending proxy time on it
                with lock:
                    hub.failure("site", item["key"], f"gave up after {MAX_ATTEMPTS} attempts", url=item["payload"]["url"])
                    hub.complete([item["key"]], "done", fetched=0)
                continue
            site = Site(hub, s, item, max(0.5, hub.settings.get("delay_ms", 0) / 1000))
            try:
                ok, why = site.run()
            except Exception as e:      # one odd site must not stop the worker
                ok, why = False, f"{type(e).__name__}: {e}"[:200]
            for i in range(0, len(site.files), 100):
                hub.upload_many(site.files[i:i + 100])
            for rid, data in site.records:
                hub.record(rid, data)
            with lock:
                if ok:
                    hub.clear_failure("site", item["key"])
                    hub.complete([item["key"]], "done", fetched=site.n_rows)
                else:
                    hub.failure("site", item["key"], why, url=site.url)
                    hub.complete([item["key"]], "failed", error=why[:200])

    try:
        n = max(1, min(int(hub.settings.get("threads", 4)), 8))
        ts = [threading.Thread(target=worker, daemon=True) for _ in range(n)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(url):
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)
    site = Site(None, s, {"key": url, "payload": {"url": url}}, 0.5)
    ok, why = site.run()
    pages = [d for _, d in site.records if d["type"] == "page"]
    rows = [d for _, d in site.records if d["type"] == "row"]
    print(json.dumps({"ok": ok, "why": why, "pages": [(p["final_url"], p["rows"]) for p in pages], "rows": len(rows)}, indent=1, ensure_ascii=False))
    for r in rows[:8]:
        print({k: r.get(k) for k in ("category", "name", "designation", "email", "phone")})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        sys.exit(main())
