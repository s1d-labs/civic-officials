"""Rajkot Municipal Corporation (rmc.gov.in): the offices of its 3 zones (East, West, Central), each with the Deputy Municipal
Commissioner's office phone. One page, /ContactUS (ASP.NET MVC; answers from Germany; archive.s1d.me copy saved 2026-11-06, live
check 2026-11-11): "DMC EZ: 0281-2389274", "DMC WZ: ...", "DMC CZ: ..." under the head office address. The page names no officers
and no ward lists (the 18 wards are split over the 3 zones; the hotspot plan only says "East zone, Central zone and west zone area
including all 18 wards"). Not read: the 2026 "Pocket Diary" (/rmcwebsite/docs/HomePage/PocketDiary.pdf, 170 pages, CorelDRAW
curves with no text layer: it needs OCR from the saved copy), the RTI proactive disclosures (postback links).
Records: level "zone", post "Deputy Municipal Commissioner" (the office: name not given). Record ids:
dept:ward2n_rajkot:<zone slug>:dmc.
"""
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_rajkot"
BODY, LGD, STATE, DISTRICT = "Rajkot Municipal Corporation", "251120", "GJ", "Rajkot"
URL = "https://www.rmc.gov.in/ContactUS"
ZONES = {"EZ": "East Zone", "WZ": "West Zone", "CZ": "Central Zone"}


def items(get=None):
    return [{"key": f"{MODULE}-contact", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    seen, recs = set(), []
    for para in _esw.soup(html).find_all("p"):
        t = _esw.clean(para.get_text(" "))
        m = re.match(r"(?i)D\.?\s?M\.?\s?C\.?\s*(EZ|WZ|CZ)\s*:\s*(.+)", t)
        if not m:
            continue
        zone = ZONES[m.group(1).upper()]
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:dmc", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=zone, zone=zone, post="Deputy Municipal Commissioner", phone=m.group(2),
                                 address="Rajkot Municipal Corporation, Dhebarbhai Road, Rajkot", wing="administration",
                                 source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contact", r.content)], "" if recs else "no DMC lines"
