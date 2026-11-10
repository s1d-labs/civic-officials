"""Task `councillors`: elected ward members of urban local bodies, from State Election Commission pages. One queue item = one
body or one file. Payload: {"url", "kind", "state", ...}. Kinds:
- "kl-body": Kerala SEC ward directory, sec.kerala.gov.in/public/wyrw/<body id> (ward table in Malayalam) and one English detail
  page per member, /public/wyr/view/<member id> (name, post, party, front, votes, margin, ward code, phone, email, address).
- "pdf": a results file (Andhra Pradesh, Odisha, Assam ...). The file goes to the bucket, each page's text becomes a record
  (parsed later on the box).
- "seed": {"module": "<xx>"}: runs cforms/<xx>.py items(get) through the hub and stores the queue items it lists as one record
  ("seed_items"); civic-india/hub_register.sh then queues them. Readers that can list their bodies offer items(get).
- "form-<xx>": a state reader in cforms/<xx>.py (Punjab, Rajasthan, Telangana, Himachal ...): fetch(payload, get) with
  get(url, method="GET", data=None, headers=None) on one requests session (cookies kept), returning (records, files, why).
Records: one per member ("councillor:<state>:<ward code or body:ward>"). Every answer is kept in the bucket under councillors/<state>/.
`python councillors.py --local '<payload json>'` runs one item without the hub.
"""
import gzip
import hashlib
import importlib
import io
import json
import os
import re
import signal
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from certs_trust import trust

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; s1d-labs public records; +https://labs.s1d.me)"}
stop = False


def on_signal(*_):
    global stop
    stop = True


def tokens(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "head"]):
        t.decompose()
    return [" ".join(s.split()) for s in soup.stripped_strings]


def after(tok, label, skip=("•",)):
    """The first text after a label on a detail page."""
    for i, t in enumerate(tok):
        if t == label:
            for u in tok[i + 1:i + 4]:
                if u not in skip:
                    return u
    return None


def kl_member(html):
    tok = tokens(html)
    d = {}
    if "Active Representative" in tok:
        i = tok.index("Active Representative")
        d["name"], d["position"] = (tok[i + 1:i + 3] + [None, None])[:2]
    age = next((t for t in tok if t.startswith("Age:")), None)
    if age:
        d["age"] = age.split(":", 1)[1].strip()
        j = tok.index(age)
        d["front"], d["party"] = (tok[j + 1:j + 3] + [None, None])[:2]
    for label, key in (("Votes Secured", "votes"), ("Margin", "margin"), ("Local Body Name", "body"), ("District", "district"),
                       ("Ward Number / Name", "ward"), ("Ward Reservation / Code", "reservation_code"), ("Phone Number", "phone"),
                       ("Email Address", "email"), ("Office / Residential Address", "address"), ("Election Code", "election")):
        v = after(tok, label)
        if v and v != "N/A":
            d[key] = v
    serving = next((t for t in tok if t.startswith("Serving:")), None)
    if serving:
        d["serving_since"] = serving.split(":", 1)[1].strip()
    m = re.match(r"Ward No\.\s*(\S+)\s*\((.*)\)$", d.get("ward") or "")
    if m:
        d["ward_no"], d["ward_name"] = m.group(1), m.group(2)
    m = re.match(r"(.*?)\s*•\s*([A-Z]\d+)$", d.get("reservation_code") or "")
    if m:
        d["reservation"], d["ward_code"] = m.group(1), m.group(2)
    elif re.match(r"^[A-Z]\d{6,}$", d.get("reservation_code") or ""):
        d["ward_code"] = d["reservation_code"]
    return d


def kl_body(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/KL/body-{p['lb_id']}.html.gz", gzip.compress(r.content), "application/gzip")]
    soup = BeautifulSoup(r.text, "lxml")
    rows = []
    for tr in soup.select("table tr"):
        a = tr.find("a", href=re.compile(r"wyr/view/\d+"))
        tds = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        if a and tds:
            rows.append((urljoin(p["url"], a["href"]), tds))
    recs = []
    for url, tds in rows:
        if stop:
            break
        m = get(url)
        if m is None:
            continue
        d = kl_member(m.text)
        d.update({"type": "councillor", "state": "KL", "url": url, "list_url": p["url"], "lb_id": p["lb_id"],
                  "row_ml": tds, "election": d.get("election") or "General Election -2025"})
        key = d.get("ward_code") or f"{p['lb_id']}:{d.get('ward_no') or len(recs)}"
        recs.append((f"councillor:KL:{key}", d))
    return recs, files, "" if recs else ("no members" if not rows else "member pages did not answer")


def pdf(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:16]
    files = [(f"councillors/{p['state']}/{key}.pdf", r.content, "application/pdf")]
    from pypdf import PdfReader
    try:
        pages = [(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(r.content)).pages]
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    recs = [(f"councillor-pdf:{p['state']}:{key}:p{i}", {"type": "councillor_pdf_page", "state": p["state"], "url": p["url"], "page": i,
             "text": text, "file": files[0][0], **{k: p[k] for k in ("label", "election", "body") if k in p}})
            for i, text in enumerate(pages, 1)]
    return recs, files, "" if recs else "empty pdf"


def seed(p, get):
    """List a state's queue items through the hub (no direct requests from a box): cforms/<module>.py items(get) -> one record."""
    mod = importlib.import_module("cforms." + p["module"])
    items = mod.items(get)
    return ([(f"seed:{p['module']}", {"type": "seed_items", "module": p["module"], "items": items, "url": p.get("url", "")})], [],
            "" if items else "no items")


KINDS = {"kl-body": kl_body, "pdf": pdf, "seed": seed}


def run(item, get):
    """Built-in kinds above; "form-<xx>" uses cforms/<xx>.py, whose fetch(payload, get) returns (records, files, why) like kl_body."""
    p = item["payload"]
    if p["kind"].startswith("form-"):
        mod = importlib.import_module("cforms." + p["kind"].split("-", 1)[1])
        return mod.fetch(p, get)
    return KINDS[p["kind"]](p, get)


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

    def get(url, method="GET", data=None, headers=None):
        t = time.time()
        try:
            r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
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
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r

    try:
        while time.time() < deadline and not stop:
            if hub.settings.get("paused"):
                time.sleep(30)
                continue
            try:
                items = hub.claim(1, steal=True, retry_failed=True)
            except requests.RequestException:      # hub slow under load: wait and ask again instead of ending the run
                time.sleep(30)
                continue
            if not items:
                break
            item = items[0]
            url = item["payload"].get("url", "")
            if item.get("attempts", 0) > 3:
                hub.failure("councillors", item["key"], "gave up after 3 attempts", url=url)
                hub.complete([item["key"]], "done", fetched=0)
                continue
            try:
                recs, files, why = run(item, get)
            except Exception as e:
                recs, files, why = [], [], f"{type(e).__name__}: {e}"[:200]
            for attempt in range(5):
                try:
                    if files:
                        hub.upload_many(files)
                    for rid, data in recs:
                        hub.record(rid, data)
                    if why and not recs:
                        hub.failure("councillors", item["key"], why, url=url)
                        hub.complete([item["key"]], "failed", error=why)
                    else:
                        hub.complete([item["key"]], "done", fetched=len(recs))
                    break
                except requests.RequestException:  # same item again after a pause; records are keyed, so a repeat is harmless
                    time.sleep(30 * (attempt + 1))
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(payload):
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)

    def get(url, method="GET", data=None, headers=None):
        r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
        time.sleep(1)
        if r.status_code == 200 and (not r.encoding or r.encoding.lower() == "iso-8859-1"):
            r.encoding = r.apparent_encoding or "utf-8"
        return r if r.status_code == 200 else None
    recs, files, why = run({"key": "local", "payload": json.loads(payload)}, get)
    print(json.dumps({"why": why, "records": len(recs), "files": [f[0] for f in files]}))
    for rid, d in recs[:3]:
        print(rid, {k: d.get(k) for k in ("name", "position", "party", "ward_no", "ward_name", "ward_code", "phone", "body", "page")})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        sys.exit(main())
