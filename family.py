"""What this family scrapes: the officials listed on Indian government sites (Who's Who, directory and contact pages).

sites.csv holds the sites (from the India Gov Status list of igod.gov.in sites): district administrations, urban local bodies and
police units. One project per kind; one queue item per site. The work runs on GitHub runners (most NIC sites answer from abroad).
Sites that do not answer from abroad go to the `-in` project, which runs through the hub's Indian proxies: list their domains in
retry_in.txt and run Setup again.
"""
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

PROBES = []    # many hosts per project: no single health check would mean anything
