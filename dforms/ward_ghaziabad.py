"""Ghaziabad Nagar Nigam (ghaziabadnagarnigam.in): the officers of its 5 zones (City, Kavi Nagar, Mohan Nagar, Vasundhara, Vijay
Nagar) and the wards of each zone. Answers from Germany (live sample 2026-11-11; not in archive.s1d.me). One queue item reads two
pages:
  /staffList.aspx          "Officer's List": one table क्र.सं. | नाम अधिकारी/कर्मचारी | पदनाम | नंबर | दूरभाष with department rows
                           (स्वास्थ्य विभाग, कर विभाग, निर्माण विभाग, जलकल विभाग, प्रकाश विभाग ...); posts that name a zone
                           ("जोनल प्रभारी-वसुंधरा", "कर अधीक्षक-सिटी जोन", "अधि0अभि0 मोहननगर/वसुंधरा जोन", "एस0एफ0आई0-कविनगर जोन") are
                           the zone officers; only those rows are read.
  /zones-and-wards.aspx    one table per zone (Ward No. | Mohalla Names) under a heading "CITY ZONE", "KAVI NAGAR ZONE" ...:
                           the ward-to-zone mapping (100 wards).
Names and posts are in Hindi: name and name_regional carry the same text; post = English (_ward.hi_post), post_regional = as
written. Records: level "zone", wards = the zone's wards. Record ids: dept:ward_ghaziabad:<zone>:<wing>:<post slug>:<n>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward_ghaziabad"
BODY, LGD, STATE, DISTRICT = "Ghaziabad Nagar Nigam", "248988", "UP", "Ghaziabad"
URL = "https://ghaziabadnagarnigam.in/staffList.aspx"
ZONEPAGE = "https://ghaziabadnagarnigam.in/zones-and-wards.aspx"
# Hindi / English spellings of the zone names -> one name
ZONES = {"City": r"सिटी|city", "Kavi Nagar": r"कवि\s*नगर|kavi", "Mohan Nagar": r"मोहन\s*नगर|mohan",
         "Vasundhara": r"वं?सुं?धरा|vasundhara", "Vijay Nagar": r"विजय\s*नगर|vijay"}
DEPTS = {"स्वास्थ्य": "sanitation", "कर": "revenue", "निर्माण": "engineering", "जलकल": "water", "प्रकाश": "electrical", "उद्यान": "horticulture",
         "पशु": "health"}


def zones_in(text):
    t = _ward.hi_norm(text)
    return [z for z, rx in ZONES.items() if re.search(rx, t, re.I)]


def zone_wards(html):
    """{zone: [ward numbers]} from zones-and-wards.aspx: the zone heading is the nearest text before each table."""
    soup = _esw.soup(html)
    out = {}
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not g or "ward" not in g[0][0].lower():
            continue
        head = []
        for x in t.find_all_previous(string=True, limit=12):
            if x.find_parent("table"):
                break  # the text of the table before: the heading of this one has ended
            if x.strip():
                head.append(x.strip())
        head = " ".join(head[::-1])
        z = zones_in(head)
        if not z:
            continue
        for r in g[1:]:
            w = _ward.wards_of(r[0])
            if w:
                out.setdefault(z[0], [])
                out[z[0]] += [x for x in w if x not in out[z[0]]]
    return out


def parse(html, zw, p):
    soup = _esw.soup(html)
    seen, recs, n = set(), [], {}
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        dept = ""
        for r in g:
            cells = [_esw.clean(c) for c in r]
            if len(set(cells)) == 1:
                dept = cells[0]
                continue
            if len(cells) < 4 or not cells[0].isdigit():
                continue
            name, post, phone, tel = cells[1], cells[2], cells[3], cells[4] if len(cells) > 4 else ""
            zs = zones_in(post)
            if not zs or re.search(r"समस्त", post):
                continue
            wing = next((w for k, w in DEPTS.items() if dept.startswith(k)), None)
            en = _ward.hi_post(post)
            if en == _esw.clean(post) and wing:
                en = {"engineering": "Engineer", "water": "Engineer (Jalkal)", "revenue": "Tax officer"}.get(wing, en)
            for z in zs:
                key = f"{_esw.slug(z)}:{wing or 'dept'}:{_esw.slug(en) or 'post'}"
                n[key] = n.get(key, 0) + 1
                zone = f"{z} Zone"
                recs.append(_ward.record(MODULE, f"{key}:{n[key]}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                         level="zone", area=zone, zone=zone, post=en, post_regional=post, name=name,
                                         name_regional=name, phone=" ".join(x for x in (phone, tel) if x), wards=zw.get(z) or None,
                                         wing=wing, section=dept, source=p["url"]))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}-staff", "payload": {"reader": MODULE, "url": URL, "zone_page": ZONEPAGE, "state": STATE}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "staff-list", r.content)]
    z = get(p.get("zone_page") or ZONEPAGE)
    zw = {}
    if z is not None:
        files.append(_esw.keep(MODULE, "zones-and-wards", z.content))
        zw = zone_wards(z.text)
    recs = parse(r.text, zw, p)
    return recs, files, "" if recs else "no zone officers"
