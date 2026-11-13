"""Cyberabad Municipal Corporation, Telangana (cmc.telangana.gov.in; carved out of GHMC in February 2026): the officers of its zones and circles,
wing by wing. One page, /KeyContacts.aspx, in the GHMC layout (ASP.NET accordion: an <h5> per section over one table with Zone /
Circle columns; parsed by dforms/_ward3_south2.keycontacts, the rules of ward2s_ghmc). Sections seen (live from Mumbai,
2026-11-13): Zonal Commissioner, Deputy Commissioner (one per circle), Property Tax, Town Planning, Urban Bio Diversity,
Health, Sanitation, Engineering, Electrical, Veterinary, Food Safety ... The page shows no ward numbers and no "last updated"
date: records are level "circle" or "zone". Not in archive.s1d.me. Route: answered from India (dev-vps-3) 2026-11-13; GHMC's
own page answers HTTP 403 from Germany, so the item is India-only (route abroad unchecked).
Source trail: src_pos = {"table", "row"} of the row in the saved page.
Record ids: dept:ward3_cyberabad:<section slug>:<zone or circle slug>:<post slug>:<name slug>.
"""
from dforms import _esw, _ward3_south2

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_cyberabad"
BODY, LGD, STATE, DISTRICT = "Cyberabad Municipal Corporation", "305330", "TG", "Medchal Malkajgiri"
URL = "https://cmc.telangana.gov.in/KeyContacts.aspx"


def items(get=None):
    return [{"key": f"{MODULE}-key-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True,
                                                         "route": "direct"}}]


def parse(html, p):
    return _ward3_south2.keycontacts(html, p, module=MODULE, body=BODY, lgd=LGD, state=STATE, district=DISTRICT)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "key-contacts", r.content)], "" if recs else "no zone or circle tables"
