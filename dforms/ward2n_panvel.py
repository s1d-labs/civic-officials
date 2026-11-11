"""Panvel Mahanagarpalika (panvelcorporation.maharashtra.gov.in): its 4 ward offices A-D (Kharghar, Kalamboli, Kamothe, Panvel)
with the ward officer, mobile, landline, email and map link. One page, /Zone_Office (English; answers from Germany; live sample
2026-11-11, not in archive.s1d.me; the page shows "Last Updated"). One <section id="zone-N"> per office: "Office: WARD 'A'",
"Ward Officer:", "Address:", "Email:", "Contact:", "Landline:", a Google Maps link, and a table "Election Ward No. | Area in
Ward" (empty on 2026-11-11; read when it has rows). One officer can hold two offices (A and C). Records: level "zone",
area "Ward A". Record ids: dept:ward2n_panvel:ward-<letter>:ward-officer.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_panvel"
BODY, LGD, STATE, DISTRICT = "Panvel Mahanagarpalika", "251492", "MH", "Raigad"
URL = "https://panvelcorporation.maharashtra.gov.in/Zone_Office"


def items(get=None):
    return [{"key": f"{MODULE}-zone-office", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    m = re.search(r"Last Updated:\s*([A-Za-z]{3}\s+\d{1,2},\s*\d{4})", soup.get_text(" "))
    last = m.group(1) if m else None
    seen, recs = set(), []
    for sec in soup.find_all("section", id=re.compile(r"^zone-\d+")):
        kv = {}
        for pp in sec.find_all("p"):
            s = pp.find("strong")
            if s:
                k = _esw.clean(s.get_text()).rstrip(":")
                kv[k] = _esw.clean(pp.get_text(" ").replace(s.get_text(), "", 1))
        office = kv.get("Office", "")
        lm = re.search(r"WARD\s*'?([A-Z])'?", office)
        if not lm:
            continue
        letter = lm.group(1)
        wards = []
        for t in sec.find_all("table"):
            for r in _esw.grid(t)[1:]:
                wards += [w for w in _ward.wards_of(r[0]) if w not in wards]
        link = sec.find("a", href=re.compile(r"maps\.app\.goo\.gl|google\.[a-z.]+/maps|goo\.gl/maps"))
        area = f"Ward {letter}"
        name = kv.get("Ward Officer", "")
        recs.append(_ward.record(MODULE, f"ward-{letter.lower()}:ward-officer", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=area, area_local=kv.get("Address") or None, zone=area,
                                 post="Ward Officer", name=name, phone=_esw.phones(kv.get("Contact", ""), kv.get("Landline", "")),
                                 email=kv.get("Email", ""), address=kv.get("Address"), wards=wards,
                                 map_url=link["href"] if link else None, vacant=None if name else True, wing="administration",
                                 last_updated=last, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "zone-office", r.content)], "" if recs else "no ward office sections"
