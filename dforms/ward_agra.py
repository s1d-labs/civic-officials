"""Agra Nagar Nigam (nagarnigamagra.com): its 4 zones (Chatta, Hari Parvat, Loha Mandi, Taj Ganj), each zone office's address and
the wards of each zone. One page, /zones-wards/ (WordPress; answers from Germany; live sample 2026-11-11, not in archive.s1d.me):
one table with a column per zone and rows "Office Address" and "Corporate Wards" ("1-KAJIPADHA | 14-KACHH PURA | ..."). The page
names no officers: records are the zone offices (post "Zone Office", the address, wards = the zone's wards; the ward-to-zone
mapping of the 100 wards). Records: level "zone". Record ids: dept:ward_agra:<zone slug>:zone-office.
"""
import re

from dforms import _esw, _ward

MODULE = "ward_agra"
BODY, LGD, STATE, DISTRICT = "Agra Nagar Nigam", "249062", "UP", "Agra"
URL = "https://nagarnigamagra.com/zones-wards/"


def items(get=None):
    return [{"key": f"{MODULE}-zones-wards", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if len(g) < 3:
            continue
        zones = [_esw.clean(c) for c in g[0]]
        rows = {}
        label = None
        for r in g[1:]:
            if len(set(r)) == 1:
                label = _esw.clean(r[0]).lower()
                continue
            if label:
                rows[label] = r
        addr, wards = rows.get("office address"), rows.get("corporate wards")
        if not wards:
            continue
        for i, z in enumerate(zones):
            ws = []
            for part in re.split(r"\s*\|\s*", wards[i] if i < len(wards) else ""):
                m = re.match(r"\s*(\d{1,3})\s*-", part)
                if m and str(int(m.group(1))) not in ws:
                    ws.append(str(int(m.group(1))))
            address = _esw.clean(addr[i]) if addr and i < len(addr) else ""
            recs.append(_ward.record(MODULE, f"{_esw.slug(z)}:zone-office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                     level="zone", area=f"{z} Zone", zone=f"{z} Zone", post="Zone Office", address=address,
                                     wards=ws, wing="administration", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "zones-wards", r.content)], "" if recs else "no zone table"
