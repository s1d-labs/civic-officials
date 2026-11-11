"""What this family scrapes: the officials listed on Indian government sites (Who's Who, directory and contact pages).

sites.csv holds the sites (from the India Gov Status list of igod.gov.in sites): district administrations, urban local bodies and
police units. One project per kind; one queue item per site. The work runs on GitHub runners (most NIC sites answer from abroad).
Sites that do not answer from abroad go to the `-in` project, which runs through the hub's Indian proxies: list their domains in
retry_in.txt and run Setup again.
"""
import hashlib
import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
FAMILY = json.loads((HERE / "scrape.json").read_text())["family"]

KINDS = {  # sites.csv kind -> project suffix, title
    "District administration": ("districts", "District administration sites: Who's Who and directories"),
    "Urban local body": ("ulbs", "Urban local body sites: officials and contacts"),
    "Police unit": ("police", "Police unit sites: officers and contacts"),
}


def sites():
    with open(HERE / "sites.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def item(row):
    extra = {k: row[k] for k in ("lgd_code", "read_start") if row.get(k)}
    return {"key": row["domain"], "payload": {"url": row["url"], "name": row["name"], "kind": row["kind"],
                                              "state": row["state_code"], "jurisdiction": row["jurisdiction"], **extra}}


def project(suffix, title, rows, **extra):
    return {"name": f"{FAMILY}-{suffix}", "title": title, "task": "whoswho", "target": f"{FAMILY}-{suffix}",
            "env": {}, "probe": None, "unit_label": "site", "record_label": "official or page",
            "items": [item(r) for r in rows], "workers": 8, "threads": 4, "delay_ms": 800, **extra}


ALL = sites()
PROJECTS = [project(suffix, title, [r for r in ALL if r["kind"] == kind]) for kind, (suffix, title) in KINDS.items()]

_retry = HERE / "retry_in.txt"
_in = set(_retry.read_text().split()) if _retry.exists() else set()
PROJECTS.append(project("in", "Sites that answer only from India (through the hub's Indian proxies)",
                        [r for r in ALL if r["domain"] in _in], proxy="IN"))

# Sites that answer only plain HTTP and only from Indian machines (Karnataka's town sites on mrc.gov.in refuse HTTPS, and give 504
# through the proxies): they run on the hub's India pool servers (geo "IN"), from http://.
_geo = HERE / "geo_in.txt"
_g = set(_geo.read_text().split()) if _geo.exists() else set()


def _http(it):
    it["payload"]["url"] = "http://" + it["payload"]["url"].split("://", 1)[-1]
    return it


_p = project("geo", "Sites that answer only over HTTP from Indian machines (India pool servers)", [r for r in ALL if r["domain"] in _g], geo="IN")
_p["items"] = [_http(i) for i in _p["items"]]
PROJECTS.append(_p)

# Town sites on states' shared municipal platforms (seeds/build_platforms.py): mostly India-only, so on the India pool servers.
with open(HERE / "platform_sites.csv", newline="", encoding="utf-8") as f:
    _plat = list(csv.DictReader(f))
PROJECTS.append(project("platforms", "Town sites on state municipal platforms (Kerala, Telangana, Tamil Nadu, Assam, Jharkhand)", _plat, geo="IN"))

# Bodies whose site or officials page the search agents found (seeds/build_found.py): India servers.
with open(HERE / "found_sites.csv", newline="", encoding="utf-8") as f:
    _found = list(csv.DictReader(f))
PROJECTS.append(project("found", "Town sites found by web search (start at the officials page when known)", _found, geo="IN"))

# Officer, ward and councillor pages of India's largest cities (seeds/build_big.py): India servers, start page read.
_bigf = HERE / "big_sites.csv"
if _bigf.exists():
    with open(_bigf, newline="", encoding="utf-8") as f:
        _big = list(csv.DictReader(f))
    PROJECTS.append(project("bigcities", "Officer and councillor pages of India's largest cities", _big, geo="IN"))

# Statewide sources of officials (directory task): APIs, contact pages and PDFs that cover many bodies at once (directories.json).
_dirs = json.loads((HERE / "directories.json").read_text())
PROJECTS.append({"name": f"{FAMILY}-directories", "title": "Statewide officials directories (APIs, contact pages, PDFs)", "task": "directory",
                 "target": f"{FAMILY}-directories", "env": {}, "probe": None, "unit_label": "source", "record_label": "official or page",
                 "items": _dirs, "workers": 6, "threads": 1, "delay_ms": 1500, "geo": "IN"})

# Sources that time out from India but answer from abroad (MCD's portal): GitHub runners (no geo, no proxy).
_farf = HERE / "directories_abroad.json"
if _farf.exists():
    PROJECTS.append({"name": f"{FAMILY}-dir-abroad", "title": "Officials sources that answer only from abroad (GitHub runners)",
                     "task": "directory", "target": f"{FAMILY}-dir-abroad", "env": {}, "probe": None, "unit_label": "source",
                     "record_label": "official or page", "items": json.loads(_farf.read_text()), "workers": 1, "threads": 1, "delay_ms": 2000})

# Booth Level Officers from state CEO lists (blo task; blo_sources.json): India servers and GitHub runners through Indian proxies.
_blof = HERE / "blo_sources.json"
if _blof.exists():
    _blo = json.loads(_blof.read_text())
    _open = {"KL"}     # states whose lists answer from anywhere: plain GitHub runners, no proxy needed
    PROJECTS.append({"name": f"{FAMILY}-blo", "title": "Booth Level Officers from state Chief Electoral Officer lists", "task": "blo",
                     "target": f"{FAMILY}-blo", "env": {}, "probe": None, "unit_label": "file or page", "record_label": "booth part",
                     "items": [i for i in _blo if i["payload"]["state"] not in _open], "workers": 8, "threads": 1, "delay_ms": 1000,
                     "geo": "IN", "proxy": "IN"})
    PROJECTS.append({"name": f"{FAMILY}-blo-kl", "title": "Booth Level Officers: Kerala (one request per booth)", "task": "blo",
                     "target": "www.ceo.kerala.gov.in", "env": {}, "probe": None, "unit_label": "booth", "record_label": "booth",
                     "items": [i for i in _blo if i["payload"]["state"] == "KL"], "workers": 8, "threads": 1, "delay_ms": 1000})

# Elected ward councillors from State Election Commission pages and result files (councillors task; councillor_sources.json):
# India servers only (every SEC site checked refuses foreign IPs).
_cof = HERE / "councillor_sources.json"
if _cof.exists():
    PROJECTS.append({"name": f"{FAMILY}-councillors", "title": "Elected ward councillors (State Election Commissions)", "task": "councillors",
                     "target": f"{FAMILY}-councillors", "env": {}, "probe": None, "unit_label": "body or file", "record_label": "councillor",
                     "items": json.loads(_cof.read_text()) + [i for f in sorted((HERE / "seeds").glob("councillors_*.json"))
                                                              for i in json.loads(f.read_text())],
                     "workers": 4, "threads": 1, "delay_ms": 1000, "geo": "IN"})

# OCR'd results PDFs (Tamil Nadu 2022, Haryana 2026, Delhi MCD 2022, UP/Uttarakhand heads ...): GitHub runners through Indian
# proxies (some sites answer only from India; OCR needs the runners' cores). One item = at most 6 pages of one PDF
# (every seeds/ocr_councillors_*.json).
_ocr = [i for f in sorted((HERE / "seeds").glob("ocr_councillors_*.json")) for i in json.loads(f.read_text())]
# Tamil Nadu: every results PDF is already in the bucket (the first item of each file saved it), so its items read the saved copy
# and need no Indian proxy: any GitHub runner can take them (project -ocr-b, own task name so older checkouts cannot).
_ocr_tn = [{"key": i["key"], "payload": {**i["payload"], "stored": "civic-officials-councillors-ocr/councillors/TN/"
                                         + hashlib.sha1(i["payload"]["url"].encode()).hexdigest()[:12] + ".pdf"}}
           for i in _ocr if i["payload"].get("state") == "TN"]
_ocr = [i for i in _ocr if i["payload"].get("state") != "TN"]
if _ocr:
    PROJECTS.append({"name": f"{FAMILY}-councillors-ocr", "title": "Elected ward councillors read by OCR (scanned results files)",
                     # own task name: workers whose checkout predates the OCR reader do not know it, so they cannot take these items
                     "task": "councillors-ocr", "target": f"{FAMILY}-councillors-ocr", "env": {}, "probe": None,
                     "unit_label": "6 PDF pages", "record_label": "councillor", "items": _ocr, "workers": 8, "threads": 1,
                     "delay_ms": 1000, "proxy": "IN"})
if _ocr_tn:
    PROJECTS.append({"name": f"{FAMILY}-councillors-ocr-b", "title": "Tamil Nadu ward councillors by OCR, from the saved results PDFs",
                     "task": "councillors-ocr-b", "target": f"{FAMILY}-councillors-ocr-b", "env": {}, "probe": None,
                     "unit_label": "6 PDF pages", "record_label": "councillor", "items": _ocr_tn, "workers": 100, "threads": 1,
                     "delay_ms": 0})

# Department offices and officers (depts task, dforms/<module>.py; every seeds/dept_*.json): police stations, power offices,
# EROs, sub-registrars, water offices. Both projects run on the India servers and on GitHub runners through the Indian proxies;
# "india_only" items are kept apart because GitHub runners without a proxy must never get them.
_dept = [i for f in sorted((HERE / "seeds").glob("dept_*.json")) for i in json.loads(f.read_text())]
if _dept:
    PROJECTS.append({"name": f"{FAMILY}-depts", "title": "Department offices: police, power, ERO, sub-registrar, water (all India)",
                     "task": "depts", "target": f"{FAMILY}-depts", "env": {}, "probe": None, "unit_label": "source page",
                     "record_label": "office", "items": [i for i in _dept if not i["payload"].get("india_only")], "workers": 24,
                     # geo + proxy: the India servers (fast, direct) and GitHub runners through the proxies both take these
                     "threads": 1, "delay_ms": 1000, "geo": "IN", "proxy": "IN"})
    PROJECTS.append({"name": f"{FAMILY}-depts-in", "title": "Department offices that answer only from India",
                     "task": "depts", "target": f"{FAMILY}-depts-in", "env": {}, "probe": None, "unit_label": "source page",
                     "record_label": "office", "items": [i for i in _dept if i["payload"].get("india_only")], "workers": 24,
                     "threads": 1, "delay_ms": 1000, "geo": "IN", "proxy": "IN"})
    # geo + proxy: India servers and GitHub runners through the Indian proxies both take these items

PROBES = []    # many hosts per project: no single health check would mean anything

# District portals that no project read before (seeds/directories_missing.json, 2026-11-11): whoswho items in the sites.csv item
# format. "route" abroad = answered from Germany (GitHub runners); india = India servers and the Indian proxies.
_dmf = HERE / "seeds" / "directories_missing.json"
if _dmf.exists():
    _dm = json.loads(_dmf.read_text())
    for _suffix, _route, _extra in (("dm-abroad", "abroad", {}), ("dm-in", "india", {"geo": "IN", "proxy": "IN"})):
        _p = project(_suffix, f"District officers: portals not read before ({_route})", [], **_extra)
        _p["items"] = [i for i in _dm if i["payload"]["route"] == _route]
        PROJECTS.append(_p)
