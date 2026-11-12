"""Coimbatore City Municipal Corporation (ccmc.gov.in): the officers of each of the 5 zones and of each of the 100 wards.
One page per zone, ccmc.gov.in/index.php/<zone>-zone/<zone>-zone-officers-details (Joomla; answers from Germany and India; saved
in archive.s1d.me 2026-11-08). Each page has two tables:
  1. zone officers: Sl. No. | Name | Designation | Phone No (Assistant Commissioner, Executive Engineer, Assistant Executive
     Engineer, Assistant Town Planning Officer, Administrative Officer, Assistant Revenue Officer, Zonal Sanitary Officer);
  2. ward officers: Ward No | AE/JE | MOBILE NO | WATER SUPPLY AE/JE | MOBILE NO | SANITARY INSPECTOR | MOBILE NO | BC's NAME |
     MOBILE NO (BC = bill collector, the property tax collector of the ward).
Records: zone officers at level "zone" (wards = every ward of the zone's ward table: the ward-to-zone mapping); ward officers at
level "ward", one record per officer and post with the wards that officer covers. One queue item = one zone page.
Record ids: dept:ward_coimbatore:<zone>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_coimbatore"
BODY, LGD, STATE, DISTRICT = "Coimbatore City Municipal Corporation", "252653", "TN", "Coimbatore"
ZONES = ("central", "east", "north", "south", "west")
URL = "https://ccmc.gov.in/index.php/{z}-zone/{z}-zone-officers-details"
# ward table heading -> (post, wing)
WARD_POSTS = (
    (r"water", "Assistant / Junior Engineer (Water Supply)", "water"),
    (r"sanitary", "Sanitary Inspector", "sanitation"),
    (r"\bbc|bill", "Bill Collector (Property Tax)", "revenue"),
    (r"ae\s*/\s*je", "Assistant / Junior Engineer", "engineering"),
)


def items(get=None):
    return [{"key": f"{MODULE}-{z}", "payload": {"reader": MODULE, "url": URL.format(z=z), "state": STATE, "zone": z}} for z in ZONES]


def _tables(html):
    soup = _esw.soup(html)
    return [_esw.grid(t) for t in soup.find_all("table")]


def parse(html, p):
    zone = p.get("zone") or re.search(r"/(\w+)-zone/", p["url"]).group(1)
    zname = f"{zone.title()} Zone"
    officers, wardrows, head = [], [], None
    for rows in _tables(html):
        if not rows:
            continue
        h = [c.lower() for c in rows[0]]
        if any("designation" in c for c in h) and any("name" in c for c in h):
            ni = next(i for i, c in enumerate(h) if "name" in c)
            di = next(i for i, c in enumerate(h) if "designation" in c)
            pi = next((i for i, c in enumerate(h) if "phone" in c or "mobile" in c), None)
            officers += [(r[ni], r[di], r[pi] if pi is not None and pi < len(r) else "") for r in rows[1:] if len(r) > di]
        elif h and "ward" in h[0]:
            head = h
            wardrows += [r for r in rows[1:] if r and re.match(r"^\d+\s*[A-Za-z]?$", r[0].strip())]
    wards = [str(int(re.match(r"\d+", r[0]).group(0))) for r in wardrows]
    seen, recs = set(), []
    src = p["url"]
    common = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, source=src, zone=zname)
    for name, post, phone in officers:
        post = _esw.clean(post).replace("Assisstant", "Assistant").replace("Adminstrative", "Administrative")
        if not (name or phone):
            continue
        recs.append(_ward.record(MODULE, f"{zone}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, level="zone", area=zname,
                                 post=post, name=name, phone=phone, wards=wards, **common))
    if head:
        # (name column, phone column, post, wing) for each officer column pair of the ward table
        cols = []
        i = 1
        while i < len(head):
            label = head[i]
            if "mobile" in label or "phone" in label:
                i += 1
                continue
            post, wing = next(((pt, w) for rx, pt, w in WARD_POSTS if re.search(rx, label)), (label.title(), None))
            ph = i + 1 if i + 1 < len(head) and ("mobile" in head[i + 1] or "phone" in head[i + 1]) else None
            cols.append((i, ph, post, wing))
            i += 2 if ph else 1
        groups = {}
        for r in wardrows:
            w = str(int(re.match(r"\d+", r[0]).group(0)))
            for ni, pi, post, wing in cols:
                name = _esw.clean(r[ni]) if ni < len(r) else ""
                phone = _esw.clean(r[pi]) if pi is not None and pi < len(r) else ""
                if not name and not phone:
                    continue
                digits = re.sub(r"\D", "", phone)
                # one officer = one phone number (names are spelt two ways: "T.Jeganathan" / "T.Jeganathanr")
                k = (post, digits) if digits else (post, f"vacant-{w}" if name.lower() == "vacant" else name.lower().replace(" ", ""))
                g = groups.setdefault(k, {"post": post, "wing": wing, "name": name, "phone": phone, "wards": []})
                g["wards"].append(w)
        for g in groups.values():
            area = ("Ward " if len(g["wards"]) == 1 else "Wards ") + ", ".join(g["wards"])
            recs.append(_ward.record(MODULE, f"{zone}:{_esw.slug(g['post'])}:{_esw.slug(g['name']) or 'post'}", seen, level="ward",
                                     area=area, post=g["post"], name=g["name"], phone=g["phone"], wards=g["wards"], wing=g["wing"],
                                     **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, p.get("zone") or _esw.slug(p["url"])[-40:], r.content)]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no officer tables"
