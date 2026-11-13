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

# BLO lists from district websites and CEO pages (blo2 readers in forms/blo2_*.py; seeds/blo2_*.json); own task name so older
# checkouts cannot take them. Scanned PDFs (kind "pdf") are saved in India for a later OCR task.
_b2 = [i for f in sorted((HERE / "seeds").glob("blo2_*.json")) for i in json.loads(f.read_text())]
if _b2:
    PROJECTS.append({"name": f"{FAMILY}-blo2", "title": "Booth Level Officers: district lists and CEO pages (blo2)", "task": "blo2",
                     "target": f"{FAMILY}-blo2", "env": {}, "probe": None, "unit_label": "file or page", "record_label": "booth part",
                     "items": [i for i in _b2 if i["payload"]["kind"] != "pdf"], "workers": 4, "threads": 1, "delay_ms": 1000})
    PROJECTS.append({"name": f"{FAMILY}-blo2-in", "title": "Booth Level Officers: scanned district PDFs saved once (India)", "task": "blo2",
                     "target": f"{FAMILY}-blo2-in", "env": {}, "probe": None, "unit_label": "file", "record_label": "page",
                     "items": [i for i in _b2 if i["payload"]["kind"] == "pdf"], "workers": 2, "threads": 1, "delay_ms": 1000,
                     "geo": "IN", "proxy": "IN"})

# Scanned BLO lists and lists whose text layer cannot be read (legacy or Type 3 fonts), read by OCR (forms/blo2_ocr.py;
# seeds/blo2ocr.json, made by seeds/build_blo2ocr.py). The items read the PDF saved in the bucket ("stored"), else fetch it
# once from cdn.s3waas.gov.in (answers from abroad) and save it: plain GitHub runners, no proxy. Own task name, so older
# checkouts cannot take them.
_b2o = HERE / "seeds" / "blo2ocr.json"
if _b2o.exists():
    PROJECTS.append({"name": f"{FAMILY}-blo2-ocr", "title": "Booth Level Officers: scanned district lists read by OCR",
                     "task": "blo2-ocr", "target": f"{FAMILY}-blo2-ocr", "env": {}, "probe": None, "unit_label": "file",
                     "record_label": "booth part", "items": json.loads(_b2o.read_text()), "workers": 8, "threads": 1,
                     "delay_ms": 500})

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
# Tamil Nadu again, from the text layer of the same saved PDFs (cforms/tn_text.py: mPDF Tamil glyphs mapped, no OCR; one item = one
# PDF): every ward, where the OCR items found about half. Same project (runners, no proxy, task name known to new checkouts only).
_ocr_tn += [i for f in sorted((HERE / "seeds").glob("stored_councillors_*.json")) for i in json.loads(f.read_text())]
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
                     "record_label": "office", "items": [i for i in _dept if not i["payload"].get("india_only") and not i["payload"].get("open")], "workers": 24,
                     # not India-only: plain GitHub runners, no proxy (2026-11-12, owner: the 10 Indian proxies held it to 5 workers;
                     # an item that fails abroad moves to depts-in)
                     "threads": 1, "delay_ms": 1000})
    PROJECTS.append({"name": f"{FAMILY}-depts-in", "title": "Department offices that answer only from India",
                     "task": "depts", "target": f"{FAMILY}-depts-in", "env": {}, "probe": None, "unit_label": "source page",
                     "record_label": "office", "items": [i for i in _dept if i["payload"].get("india_only")], "workers": 24,
                     "threads": 1, "delay_ms": 1000, "geo": "IN", "proxy": "IN"})
    # geo + proxy: India servers and GitHub runners through the Indian proxies both take these items

# Open sources (public files on GitHub and the like, payload "open": no geoblock): plain GitHub runners, no proxy, no India server
_open = [i for i in _dept if i["payload"].get("open") and not i["payload"].get("india_only")]
if _open:
    PROJECTS.append({"name": f"{FAMILY}-depts-open", "title": "Department offices from open files (no geoblock)", "task": "depts",
                     "target": f"{FAMILY}-depts-open", "env": {}, "probe": None, "unit_label": "file", "record_label": "office",
                     "items": _open, "workers": 8, "threads": 1, "delay_ms": 500})

# Ward map files (GeoPDFs, PDF maps) saved once to the bucket (wardmaps task = depts.py, dforms/wm_geopdf.py; seeds/wm_*.json):
# civic-india wm_geopdf.py converts the saved copies to ward GeoJSON (2026-11-11: Okeskar/Maha_Election_2025, 975 files, 5.7 GB).
# seeds/wm2_*.json (2026-11-11): the SBM-Urban live ward layer per state, Esri India Living Atlas wards, APSAC, Puducherry SEC
# ward PDFs, Rajasthan LSG 2019 maps; their India-only items go to the -wardmaps-in project
_wm = [i for f in sorted((HERE / "seeds").glob("wm*_*.json")) for i in json.loads(f.read_text())]
if _wm:
    PROJECTS.append({"name": f"{FAMILY}-wardmaps", "title": "Ward map files (GeoPDFs, PDF maps) saved once to the bucket",
                     "task": "wardmaps", "target": f"{FAMILY}-wardmaps", "env": {}, "probe": None, "unit_label": "file",
                     "record_label": "file", "items": [i for i in _wm if not i["payload"].get("india_only")],
                     "workers": 4, "threads": 1, "delay_ms": 500})
    PROJECTS.append({"name": f"{FAMILY}-wardmaps-in", "title": "Ward map files and layers that answer only from India",
                     "task": "wardmaps", "target": f"{FAMILY}-wardmaps-in", "env": {}, "probe": None, "unit_label": "file",
                     "record_label": "file", "items": [i for i in _wm if i["payload"].get("india_only")],
                     "workers": 4, "threads": 1, "delay_ms": 1000, "geo": "IN", "proxy": "IN"})

# Tamil Nadu public-service and boundary layers on the TNGIS public GeoServer WFS (seeds/tngis_services.json, built by
# seeds/build_tngis_services.py; dforms/wm2_wfs.py with payload "kind"): police stations and jurisdictions, PDS shops, health
# facilities, schools, anganwadi, CSC, offices, taluk / block / village / town boundaries. One item = one layer saved ONCE to the
# bucket (gis/tngis/33/<layer>.geojson.gz). TNGIS answers from abroad (the ward layers ran on GitHub runners): no proxy, no geo.
# One host for every item: 2 workers. seeds/tngis_all.json (2026-11-13, seeds/build_tngis_all.py): every other non-mirror layer
# of the owner's TNGIS download that the WFS still answers, same project and reader.
_tngis = [i for f in ("tngis_services.json", "tngis_all.json") if (HERE / "seeds" / f).exists()
          for i in json.loads((HERE / "seeds" / f).read_text())]
if _tngis:
    PROJECTS.append({"name": f"{FAMILY}-tngis", "title": "Tamil Nadu TNGIS service and boundary layers saved once to the bucket",
                     "task": "wardmaps", "target": f"{FAMILY}-tngis", "env": {}, "probe": None, "unit_label": "layer",
                     "record_label": "layer", "items": _tngis, "workers": 2, "threads": 1,
                     "delay_ms": 2000})
# seeds/tngis_all_big.json: the 67 large TNGIS layers (about 20 M features; 0.2-2.8 GB of GeoJSON each by estimate), same
# reader and host, own project so they are queued only on purpose; 1 worker (one answer of a few MB at a time).
_tngis_big = HERE / "seeds" / "tngis_all_big.json"
if _tngis_big.exists():
    PROJECTS.append({"name": f"{FAMILY}-tngis-big", "title": "Tamil Nadu TNGIS large layers (parcels, land use, buildings) saved once",
                     "task": "wardmaps", "target": f"{FAMILY}-tngis-big", "env": {}, "probe": None, "unit_label": "layer",
                     "record_label": "layer", "items": json.loads(_tngis_big.read_text()), "workers": 1, "threads": 1,
                     "delay_ms": 2000})

PROBES = []    # many hosts per project: no single health check would mean anything

# District portals that no project read before (seeds/directories_missing.json, 2026-11-11): whoswho items in the sites.csv item
# format. "route" abroad = answered from Germany (GitHub runners); india = India servers and the Indian proxies.
# seeds/directories_missing2.json (block-district, 2026-11-13): S3WaaS portals of districts with no official that sites.csv
# lacks; same item format, keys "dm2:<host>[path]". Route "direct" items (answer only dev-vps-3) belong to the hub project
# civic-officials-whoswho-direct (not in the GitHub pool; queued there by INSERT), so no family project lists them.
_dmf = HERE / "seeds" / "directories_missing.json"
if _dmf.exists():
    _dm = json.loads(_dmf.read_text())
    _dm2f = HERE / "seeds" / "directories_missing2.json"
    if _dm2f.exists():
        _dm += json.loads(_dm2f.read_text())
    for _suffix, _route, _extra in (("dm-abroad", "abroad", {}), ("dm-in", "india", {"geo": "IN", "proxy": "IN"})):
        _p = project(_suffix, f"District officers: portals not read before ({_route})", [], **_extra)
        _p["items"] = [i for i in _dm if i["payload"]["route"] == _route]
        PROJECTS.append(_p)
