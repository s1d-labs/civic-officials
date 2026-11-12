"""Amravati Mahanagarpalika (amravaticorporation.in): the zone officers among its administrative officers (the in-charge Assistant
Commissioner of each of the 5 zones, the zone Deputy Engineers, the encroachment squad head of zones 3 and 4). One page,
/administrative-officers/ (WordPress, Marathi; in archive.s1d.me, saved 2026-11-11; the page shows "Last Update"), one table
"Sr.no. | Name | Mobile No. | Designation" of about 56 officers. Only rows whose designation names a zone (झोन क्र.N) are read;
an officer named for two zones ("झोन ३ व ४") gets one record per zone. A second charge after "/" ("झोन क्र.१ / शाखा अभियंता")
goes to "also". The page does not list the wards of each zone (no "wards" key).
Records: level "zone", area "Zone <n>". Record ids: dept:ward2n_amravati:zone<n>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_amravati"
BODY, LGD, STATE, DISTRICT = "Amravati Mahanagarpalika", "251328", "MH", "Amravati"
URL = "https://amravaticorporation.in/administrative-officers/"
POSTS = ((r"सहा\.?\s*आयुक्त", "Assistant Commissioner"), (r"उप\s*अभियंता", "Deputy Engineer"),
         (r"कनि(?:ष्ठ|ष्ट)\s*अभियंता", "Junior Engineer"), (r"अतिक्रमण\s*पथक\s*प्रमुख", "Encroachment Squad Head"),
         (r"स्वच्छता\s*निर[िी]क्षक", "Sanitary Inspector"), (r"कर\s*निर[िी]क्षक", "Tax Inspector"))
ZONE = re.compile(r"झोन\s*(?:क्र\.?)?\s*(\d)(?:\s*(?:व|,)\s*(\d))?")


def joined(s):
    """The page writes a zero-width joiner after a virama ("आयुक्\u200dत"); clean() makes it a space: join the letters again."""
    return re.sub(r"्\s+(?=\S)", "्", s)


def items(get=None):
    return [{"key": f"{MODULE}-administrative-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    m = re.search(r"Last Update\s*:\s*([^@<]+)", soup.get_text(" "))
    last = _esw.clean(m.group(1)) if m else None
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "Name", "Designation", soup=soup)[:1]:
        for r in rows:
            des = joined(_ward.hi_norm(_ward.col(r, "Designation")))
            parts = [_esw.clean(x) for x in des.split("/")]
            zpart = next((x for x in parts if ZONE.search(x)), None)
            if not zpart:
                continue
            z = ZONE.search(zpart)
            zones = [g for g in z.groups() if g]
            en = next((e for rx, e in POSTS if re.search(rx, zpart)), _ward.hi_post(zpart))
            if re.match(r"प्र\s*\.", zpart):
                en += " (in charge)"
            also = "; ".join(x for x in parts if x != zpart) or None
            name = joined(_ward.col(r, "Name"))
            phone = re.sub(r"^[.…\s]+$", "", _ward.col(r, "Mobile"))
            for zn in zones:
                area = f"Zone {zn}"
                recs.append(_ward.record(MODULE, f"zone{zn}:{_esw.slug(en)}", seen, body=BODY, lgd=LGD, state=STATE,
                                         district=DISTRICT, level="zone", area=area, zone=area, post=en, post_regional=des,
                                         name=name, name_regional=name, phone=phone, also=also, last_updated=last,
                                         source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "administrative-officers", r.content)], "" if recs else "no zone officers"
