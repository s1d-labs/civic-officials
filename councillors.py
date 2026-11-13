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
from urllib.parse import urljoin, urlsplit

import requests
from scrape_hub_client import HubRejected
from bs4 import BeautifulSoup

import archive_first
import provenance
from certs_trust import trust
from forms.aspnet import LegacyTLS, insecure_retry

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
    for n, tr in enumerate(soup.select("table tr"), 1):
        a = tr.find("a", href=re.compile(r"wyr/view/\d+"))
        tds = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        if a and tds:
            rows.append((urljoin(p["url"], a["href"]), tds, n))
    recs = []
    for url, tds, n in rows:
        if stop:
            break
        m = get(url)
        if m is None:
            continue
        d = kl_member(m.text)
        d.update({"type": "councillor", "state": "KL", "url": url, "list_url": p["url"], "lb_id": p["lb_id"],
                  "row_ml": tds, "election": d.get("election") or "General Election -2025",
                  # the fields come from the member's detail page; row_ml from row n of the body's ward list
                  **provenance.at(m, url), "src_pos": {"selector": "detail page labels", "list_row": n},
                  "method": "html page (labels on the member's detail page)"})
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
             "text": text, "file": files[0][0], **{k: p[k] for k in ("label", "election", "body") if k in p},
             "src_pos": {"page": i}, "method": "pdf text (pypdf, one record per page)"})
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


def https_refused(url, e):
    """An https address whose port 443 refuses the connection (not a timeout): worth one try over http."""
    if not url.startswith("https://") or isinstance(e, requests.exceptions.ConnectTimeout):
        return False
    m = str(e).lower()
    return "refused" in m or "couldn't connect" in m


def reader_of(p):
    """The module that reads this item: dforms.<reader> (depts), cforms.<xx> (form-<xx>), else the built-in kind."""
    if p.get("reader"):
        return "dforms." + p["reader"]
    k = p.get("kind", "")
    if k.startswith("form-"):
        return "cforms." + k.split("-", 1)[1]
    if k == "seed" and p.get("module"):
        return "dforms." + p["module"]
    return "councillors." + k if k else ""


def reader_method(p):
    """The reader module's METHOD constant ("pdf text", "ocr", "html table" ...), when it has one and is loaded."""
    return getattr(sys.modules.get(reader_of(p)), "METHOD", "") or ""


def main(run_fn=None, task="councillors"):
    """The pool loop; depts.py reuses it with its own run_fn and failure kind."""
    run_fn = run_fn or run
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)
    af = archive_first.from_env()        # ARCHIVE_FIRST=1 + read key in the project env: saved copy before the live site
    live_only = [af is None]
    trail = provenance.Trail(task, project, getattr(hub, "run_id", ""))     # source trail: every response read, copied once

    def get(url, method="GET", data=None, headers=None):
        if not live_only[0] and archive_first.plain_get(method, data, headers):
            r = af.lookup(url)
            hub.metric("archive_hit" if r is not None else "archive_miss")
            if r is not None:
                if not r.encoding or r.encoding.lower() == "iso-8859-1":
                    r.encoding = r.apparent_encoding or "utf-8"
                trail.note(r, url, method, data)
                return r
        t = time.time()
        try:
            try:
                r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
            except requests.exceptions.SSLError as e:
                # servers that still need TLS legacy renegotiation (Punjab water, MP PHED): same request, certificate checks stay on
                r = None
                if "renegotiation" in str(e).lower():
                    hub.metric("tls_legacy_retry")
                    s.mount(f"https://{urlsplit(url).hostname}/", LegacyTLS())
                    try:
                        r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
                    except requests.exceptions.SSLError:
                        r = None
                if r is None:
                    # certificate expired / incomplete chain / old ciphers: once more without checks (owner, 2026-11-11);
                    # the records of this item get tls_unverified
                    hub.metric("tls_unverified_retry")
                    r = insecure_retry(s, url, method, data=data, headers=headers, timeout=(20, 90))
            except requests.exceptions.ConnectionError as e:
                # port 443 refused (Karnataka *.mrc.gov.in town sites serve plain http only): the same page over http,
                # as whoswho.py does; the trail notes the http address
                if not https_refused(url, e):
                    raise
                hub.metric("https_refused_http_retry")
                url = "http://" + url[len("https://"):]
                r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
        except requests.RequestException:
            hub.metric("http_error")
            hub.error()
            return None
        hub.metric("n_http")
        hub.metric("t_http_s", time.time() - t)
        time.sleep(max(0.5, hub.settings.get("delay_ms", 0) / 1000))
        if r.status_code != 200 and not (method == "PROPFIND" and r.status_code == 207):    # 207: a WebDAV folder listing
            hub.metric(f"http_{r.status_code}")
            if r.status_code in (403, 429, 503):
                hub.block()
            return None
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        trail.note(r, url, method, data)
        return r
    get.hub = hub      # readers that keep their source files in the bucket (cforms/tn.py) read them back through the hub

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
                hub.failure(task, item["key"], "gave up after 3 attempts", url=url)
                hub.complete([item["key"]], "done", fetched=0)
                continue
            before = set(getattr(s, "unverified_hosts", ()))
            if af:
                af.reset()
            trail.begin(item, reader_of(item["payload"]))
            try:
                recs, files, why = run_fn(item, get)
                if why and not recs and af and af.used:
                    # failed on saved copies (a postback needs a live session, or the copy is a different page): once more live
                    hub.metric("archive_retry_live")
                    live_only[0] = True
                    try:
                        recs, files, why = run_fn(item, get)
                    finally:
                        live_only[0] = False
                    af.reset()
            except ModuleNotFoundError as e:
                if not str(getattr(e, "name", "") or "").startswith(("dforms.", "cforms.", "forms.")):
                    raise
                # a reader pushed after this job checked out the family: give the item back untouched and end the job, so a
                # job with the new checkout takes it (old jobs used to burn all 3 attempts of every new item)
                hub.metric("old_checkout")
                hub.complete([item["key"]], "pending", error=f"old checkout: {e.name}")
                break
            except Exception as e:
                recs, files, why = [], [], f"{type(e).__name__}: {e}"[:200]
            if set(getattr(s, "unverified_hosts", ())) - before or getattr(s, "unverified_hosts", None) and \
                    (urlsplit(url).hostname or "") in s.unverified_hosts:
                for _, data in recs:     # fetched without a certificate check: say so on every record of the item
                    data["tls_unverified"] = True
            if af and af.used:
                for _, data in recs:     # read (partly) from archive.s1d.me copies: the newest capture time used
                    data["archived_at"] = max(af.used)
            n_data = len(recs)
            recs, files = trail.finish(recs, files, reader_method(item["payload"]))
            n_skip = sum((trail.row_counts.get("rows_skipped") or {}).values())
            if n_skip:          # data rows a reader left out (the reasons are on the trail record)
                hub.metric("rows_skipped", n_skip)
            # the hub accepts only plain path characters: a reader's file name with %28, spaces or brackets was refused (422) and
            # the refusal stopped the whole worker (2026-11-14, st_tr_dirs)
            files = [(re.sub(r"[^A-Za-z0-9._/-]+", "-", f[0]), *f[1:]) for f in files]
            for attempt in range(5):
                try:
                    for i in range(0, len(files), 100):      # source copies can make many files: links in chunks
                        hub.upload_many(files[i:i + 100])
                    for rid, data in recs:
                        hub.record(rid, data)
                    if why and not n_data:
                        hub.failure(task, item["key"], why, url=url)
                        hub.complete([item["key"]], "failed", error=why)
                    else:
                        hub.complete([item["key"]], "done", fetched=n_data)
                    break
                except requests.RequestException:  # same item again after a pause; records are keyed, so a repeat is harmless
                    time.sleep(30 * (attempt + 1))
                except HubRejected as e:   # the hub refused this item's data: the item fails, the worker goes on
                    hub.failure(task, item["key"], f"hub refused: {e}"[:200], url=url)
                    hub.complete([item["key"]], "failed", error=f"hub refused: {e}"[:200])
                    break
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(payload, run_fn=None):
    s = requests.Session()
    s.verify = trust()
    s.headers.update(HEADERS)

    def get(url, method="GET", data=None, headers=None):
        try:
            r = s.request(method, url, data=data, headers=headers, timeout=(20, 90))
        except requests.exceptions.ConnectionError as e:
            if not https_refused(url, e):
                raise
            r = s.request(method, "http://" + url[len("https://"):], data=data, headers=headers, timeout=(20, 90))
        time.sleep(1)
        if r.status_code == 200 and (not r.encoding or r.encoding.lower() == "iso-8859-1"):
            r.encoding = r.apparent_encoding or "utf-8"
        return r if r.status_code == 200 else None
    provenance.rows_reset()
    recs, files, why = (run_fn or run)({"key": "local", "payload": json.loads(payload)}, get)
    print(json.dumps({"why": why, "records": len(recs), "files": [f[0] for f in files], **provenance.rows(len(recs))}))
    for rid, d in recs[:3]:
        print(rid, {k: d.get(k) for k in ("name", "position", "party", "ward_no", "ward_name", "ward_code", "phone", "body", "page")})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        local(sys.argv[2])
    else:
        sys.exit(main())
