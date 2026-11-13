"""Akola Municipal Corporation (amcakola.in; the older host akolamc.org does not answer, 2026-11-13): the page "Ward Offices"
(/ContactUs/Wardofc), one div.contact-information block per zone office: h5 = office name (EAST / WEST / NORTH / SOUTH ZONE OFFICE
AMC), then the address, the phone and the email as single-contact-info lines. Live sample from dev-vps-3 (Mumbai) 2026-11-13;
not in archive.s1d.me. The page names no officer and no wards: one office record per zone (level "zone", post "Zone Office",
wards_note). Ids: dept:ward3_akola:zone:<zone slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html blocks (div.contact-information)"

MODULE = "ward3_akola"
BODY, LGD, STATE, DISTRICT = "Akola Municipal Corporation", "251312", "MH", "Akola"
URL = "https://amcakola.in/ContactUs/Wardofc"


def items(get=None):
    return [{"key": f"{MODULE}-zone-offices", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, url=URL):
    s = _esw.soup(html)
    seen, recs = set(), []
    for blk in s.select("div.contact-information"):
        h = blk.find("h5")
        if not h:
            continue
        office = _esw.clean(h.get_text(" "))
        lines = [_esw.clean(x.get_text(" ")) for x in blk.select("div.single-contact-info")]
        lines = [x for x in lines if x and x != office]
        phone = " ".join(x for x in lines if re.fullmatch(r"[\d\s/,+-]{8,}", x))
        email = " ".join(x for x in lines if "@" in x)
        address = " ".join(x for x in lines if x not in (phone, email) and not re.fullmatch(r"[\d\s/,+-]{8,}", x) and "@" not in x)
        zone = re.sub(r"(?i)\s*office\s*amc\s*$", "", office).title()
        recs.append(_ward.record(MODULE, f"zone:{_esw.slug(zone)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=zone, zone=zone, post="Zone Office", address=address, phone=phone,
                                 email=email, role="head", wing="administration",
                                 wards_note="the source names the zone office, not its wards or officer", source=url,
                                 src_pos=_ward.nth(blk)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "ward-offices", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no zone office blocks"
