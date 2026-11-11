"""Ulhasnagar Mahanagarpalika (umc.gov.in): its 4 ward (prabhag samiti) offices with the ward officer, mobile, email, address and
the camp area each office serves (Ulhasnagar-1, -2, -4, -5). One JSON API, /api/api/ward-offices?lang=en (the site's own data
call; answers from Germany; live sample 2026-11-11, not in archive.s1d.me; directories.json lists the same url as a directory
item, but DB civic held no rows from it on 2026-11-11). Fields: ward_name, officer_name, address, email ("umc[dot]ward1[at]gmail[dot]com"),
mobile, landline, areas, map_url, ward_no. The API gives no election ward numbers per office (no "wards" key).
Records: level "zone", area "Ward Office <n>". Record ids: dept:ward2n_ulhasnagar:wo<n>:ward-officer.
"""
import json
import re

from dforms import _esw, _ward

MODULE = "ward2n_ulhasnagar"
BODY, LGD, STATE, DISTRICT = "Ulhasnagar Mahanagarpalika", "251484", "MH", "Thane"
URL = "https://umc.gov.in/api/api/ward-offices?lang=en"


def items(get=None):
    return [{"key": f"{MODULE}-ward-offices", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(data, p):
    seen, recs = set(), []
    for o in data if isinstance(data, list) else []:
        office = _esw.clean(o.get("ward_name"))
        m = re.search(r"\d+", office)
        if not m:
            continue
        n = m.group(0)
        area = f"Ward Office {n}"
        name = _esw.clean(o.get("officer_name"))
        phones = [x for x in (o.get("mobile"), o.get("landline")) if x and re.search(r"\d{6}", str(x))]
        recs.append(_ward.record(MODULE, f"wo{n}:ward-officer", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=area, area_local=_esw.clean(o.get("areas")) or None, zone=area,
                                 post="Ward Officer", name=name, phone=", ".join(str(x) for x in phones),
                                 email=o.get("email") or "", address=o.get("address"),
                                 map_url=o.get("map_url") or None, vacant=None if name else True, wing="administration",
                                 source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    try:
        data = json.loads(r.content)
    except ValueError:
        return [], [_esw.keep(MODULE, "ward-offices", r.content, "txt")], "not json"
    recs = parse(data, p)
    return recs, [_esw.keep(MODULE, "ward-offices", r.content, "json")], "" if recs else "no ward offices"
