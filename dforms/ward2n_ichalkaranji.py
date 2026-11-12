"""Ichalkaranji Mahanagarpalika (ichalkaranjimnp.in): its 4 divisional (zone) offices A-D and their email ids. One page,
/official-email-ids/ (WordPress, Marathi; in archive.s1d.me, saved 2026-11-11; the page shows "Last Update"), one table
"अ.क्र. | विभागाचे नाव | ई – मेल आयडी" of 34 departments; rows "विभागीय कार्यालय ए / बी / सी / डी" are the zone offices. The site
names no zone officer and no wards per zone. Records: the zone offices (post "Divisional Office", the email), level "zone",
area "Divisional Office A". Record ids: dept:ward2n_ichalkaranji:zone-<letter>:office.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_ichalkaranji"
BODY, LGD, STATE, DISTRICT = "Ichalkaranji Mahanagarpalika", "251619", "MH", "Kolhapur"
URL = "https://ichalkaranjimnp.in/official-email-ids/"
LETTERS = {"ए": "A", "बी": "B", "सी": "C", "डी": "D", "ई": "E"}


def items(get=None):
    return [{"key": f"{MODULE}-email-ids", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    m = re.search(r"Last Update\s*:\s*([^@<]+)", soup.get_text(" "))
    last = _esw.clean(m.group(1)) if m else None
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "विभागाचे नाव", soup=soup)[:1]:
        for r in rows:
            dept = _ward.col(r, "विभागाचे नाव")
            z = re.search(r"विभागीय\s*कार्यालय\s*(ए|बी|सी|डी|ई)(?![\u0900-\u097f])", dept)
            if not z:
                continue
            letter = LETTERS[z.group(1)]
            area = f"Divisional Office {letter}"
            recs.append(_ward.record(MODULE, f"zone-{letter.lower()}:office", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=area, area_regional=dept, zone=area,
                                     post="Divisional Office", post_regional=dept, email=_ward.col(r, "मेल"),
                                     wing="administration", last_updated=last, source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "email-ids", r.content)], "" if recs else "no zone office rows"
