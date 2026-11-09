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
    return {"key": row["domain"], "payload": {"url": row["url"], "name": row["name"], "kind": row["kind"],
                                              "state": row["state_code"], "jurisdiction": row["jurisdiction"]}}


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

PROBES = []    # many hosts per project: no single health check would mean anything
