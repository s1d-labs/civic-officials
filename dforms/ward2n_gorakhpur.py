"""Gorakhpur Nagar Nigam (gorakhpurnagarnigam.up.gov.in): its zonal offices (Zone 1 & 3 share one office, Zone 2, Zone 4, Zone 5)
with address and telephone. One page, /contact.aspx (saved in archive.s1d.me 2026-11-06): one card per zonal office
(div.zonal-office: badge "Zone 1 & 3", address lines, "Telephone:"). The page names no zonal officers and no wards of each zone
(the officer directory, /Administrativewing.aspx, lists only head-office posts). Records: one per zone, post "Zonal Office",
level "zone"; a shared office gives one record per zone with the same address. Record ids: dept:ward2n_gorakhpur:zone-<n>:office.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_gorakhpur"
BODY, LGD, STATE, DISTRICT = "Gorakhpur Nagar Nigam", "249444", "UP", "Gorakhpur"
URL = "https://gorakhpurnagarnigam.up.gov.in/contact.aspx"


def items(get=None):
    return [{"key": f"{MODULE}-contact", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for card in soup.select("div.zonal-office"):
        badge = card.select_one(".office-badge")
        zones = re.findall(r"\d+", badge.get_text(" ") if badge else "")
        if not zones:
            continue
        info = card.select(".contact-info")
        addr = _esw.clean(" ".join(x.get_text(" ") for x in info[0].find_all("p"))) if info else ""
        tel = " ".join(x.get_text(" ") for x in card.find_all("p") if "Telephone" in x.get_text())
        tel = _esw.clean(re.sub(r"(?i)telephone\s*:", " ", tel))
        title = card.select_one(".card-title")
        for z in zones:
            recs.append(_ward.record(MODULE, f"zone-{z}:office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                     level="zone", area=f"Zone {z}", zone=f"Zone {z}", post="Zonal Office",
                                     office_name=_esw.clean(title.get_text(" ")) if title else None, address=addr, phone=tel,
                                     wing="administration", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contact", r.content)], "" if recs else "no zonal office cards"
