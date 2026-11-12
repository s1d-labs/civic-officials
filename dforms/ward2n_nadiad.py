"""Nadiad Municipal Corporation (nadiadnmc.in; corporation since 2025): its 2 zones (West, East) with their Deputy Municipal
Commissioners, and its civic centres (area offices, incl. the merged villages Yoginagar, Peepalg, Dumral, Fatepur, Kamla,
Manjipura, Dabhan, Bilodra, Utarsanda, Tundel). Two pages of the ASP.NET MVC site (answer from Germany; live samples 2026-11-11,
not in archive.s1d.me); their URLs carry a fixed menu key (/Home/ViewMethod/<key>~~, taken from the home page menu):
  OFFICIALS          table Sr No. | Name of the Officer | Designation | Department / Branch; only rows whose branch names a zone
                     ("West Zone", "East Zone") are read here (the other rows are body-wide heads).
  CITY CIVIC CENTERS table Sr. No. | Name | Address; rows that name a civic centre (the fire station row is left out).
The pages give no phones and no ward lists. Records: level "zone". Record ids: dept:ward2n_nadiad:<page>:<slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_nadiad"
BODY, LGD, STATE, DISTRICT = "Nadiad Municipal Corporation", "251187", "GJ", "Kheda"
BASE = "https://nadiadnmc.in/Home/ViewMethod/"
PAGES = {"officials": "XGmqpSvedpqbTYkhfuV14A~~", "civic-centres": "wERIaYNvUeVa7WS4JaTDyw~~"}


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": BASE + v, "state": STATE, "page": k}}
            for k, v in PAGES.items()]


def parse_officials(html, p, seen):
    recs = []
    for head, rows in _ward.header_tables(html, "name of the officer", "designation"):
        for r in rows:
            branch, name, post = _ward.col(r, "department", "branch"), _ward.col(r, "name of the officer"), _ward.col(r, "designation")
            m = re.search(r"(?i)\b(north|south|east|west|central)\s*zone\b", branch)
            if not m or not name:
                continue
            zone = f"{m.group(1).title()} Zone"
            recs.append(_ward.record(MODULE, f"officials:{_esw.slug(zone)}:{_esw.slug(post or 'officer')}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone,
                                     post=post or "Zone Officer", name=name, wing="administration", source=p["url"], src_pos=r.pos))
    return recs


def parse_centres(html, p, seen):
    recs = []
    for head, rows in _ward.header_tables(html, "name", "address"):
        for r in rows:
            name, addr = _ward.col(r, "name"), _ward.col(r, "address")
            if not re.search(r"(?i)civic\s*cent", f"{name} {addr}"):
                continue
            area = re.sub(r"(?i)\s*[–-]?\s*(city\s*)?civic\s*cent(er|re)\s*$", "", name).strip() or name
            recs.append(_ward.record(MODULE, f"civic-centres:{_esw.slug(area)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=f"{area} Civic Centre", post="Civic Centre",
                                     address=addr, wing="administration", source=p["url"], src_pos=r.pos))
    return recs


PARSERS = {"officials": parse_officials, "civic-centres": parse_centres}


def fetch(p, get):
    page = p.get("page") or next((k for k, v in PAGES.items() if v in p["url"]), "")
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = PARSERS[page](r.text, p, set())
    return recs, [_esw.keep(MODULE, page, r.content)], "" if recs else "no rows"
