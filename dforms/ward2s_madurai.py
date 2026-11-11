"""Madurai City Municipal Corporation (www.tnurbantree.tn.gov.in/madurai/, the Tamil Nadu urban local body WordPress platform): the
engineers, water supply fitters and sanitary staff of its 4 zones and 100 wards. One page, /madurai/office-staffs/ ("Office Staffs";
the page shows no "last updated" date). India only in practice: from Germany the page timed out on 2026-11-11 (the site's home page
answered); the sample was fetched once from India (vpsin) on 2026-11-11. Not in archive.s1d.me on that date.
The page has three tables (the second also holds broken one-cell copies of its own cells: tables with one column are skipped):
  1. "ENGINEERING SECTION - SE/EE/AEE PHONE NUMBERS": Sl. No. | Name | Zone | Mobile, with heading rows that name the post (City
     Engineer, Executive Engineer, Assistant Executive Engineer, Town Planning Engineers, Street Light AEE / AEs). The Zone cell is
     "Zone 1 ( Ward 1 to 23)" (the zone-to-ward mapping: 1-23, 24-49, 50-74, 75-100), "-Central Office", "All Zone [1 to 100]", or,
     for the town planning rows, the post ("Assistant Executive Engineer (Zone 4)").
  2. "ENGINEERING SECTION - AE/JE PHONE NUMBERS": Sl. No. | Name | Ward Nos | Place of Office | Mobile, heading rows "Zone N",
     "Zone N Fitter" (water supply fitters) and "Central Officers" (the Ward Nos cell then holds the post). The post is written
     after the name ("Mr.R.Kani A.E", "Mr.S.Babu JE").
  3. "SANITARY INSPECTORS DETAILS": the same columns; Sanitary Officers (S.O, wards = the whole zone) and Sanitary Inspectors (S.I).
Records: zone officers and Sanitary Officers at level "zone" (wards = the zone's wards), section engineers, fitters and sanitary
inspectors at level "ward" (their own ward list), central posts at level "body". The place of office goes in "address".
Record ids: dept:ward2s_madurai:<zone or central>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2s_madurai"
BODY, LGD, STATE, DISTRICT = "Madurai City Municipal Corporation", "252889", "TN", "Madurai"
URL = "https://www.tnurbantree.tn.gov.in/madurai/office-staffs/"
ZONE_WARDS = {1: (1, 23), 2: (24, 49), 3: (50, 74), 4: (75, 100)}
SUFFIX = (  # post written after the name -> (English post, wing)
    (r"S\.?\s?O\b\.?(?:\s*I/?C)?", "Sanitary Officer"), (r"S\.?\s?I\b\.?", "Sanitary Inspector"),
    (r"A\.?\s?E\b\.?", "Assistant Engineer"), (r"J\.?\s?E\b\.?(?:\s*\(i/c\))?", "Junior Engineer"),
)


def items(get=None):
    return [{"key": f"{MODULE}-office-staffs", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def zone_wards(n):
    lo, hi = ZONE_WARDS[n]
    return [str(w) for w in range(lo, hi + 1)]


def _zone_no(text):
    m = re.search(r"(?i)\bzone\s*(\d)", text or "")
    return int(m.group(1)) if m and int(m.group(1)) in ZONE_WARDS else None


def split_post(name, default):
    """("Mr.R.Kani A.E", "AE/JE") -> ("Mr.R.Kani", "Assistant Engineer"); a name with no post after it keeps the default post.
    "C.Veeran SI (SO I/C)" -> ("C.Veeran", "Sanitary Inspector (Sanitary Officer in charge)")."""
    n = _esw.clean(name).strip(" ,")
    extra = ""
    m = re.search(r"\(\s*S\.?O\.?\s*I/?C\s*\)\s*$", n, re.I)
    if m:
        n, extra = n[:m.start()].strip(" ,"), " (Sanitary Officer in charge)"
    for rx, post in SUFFIX:
        m = re.search(r"[\s,]+" + rx + r"\s*$", n, re.I)
        if m:
            return n[:m.start()].strip(" ,"), post + extra
    if default == "Sanitary Inspector" and re.search(r"\sI$", n):  # "Mr.Sivasubburamaniyan I": the page drops the S of SI
        return n[:-2].strip(" ,"), default + extra
    return n, default + extra


def tables(html):
    """The page's tables with more than one column, as grids."""
    out = []
    for t in _esw.soup(html).find_all("table"):
        g = _esw.grid(t)
        if g and len(g[0]) > 1:
            out.append(g)
    return out


def _heading(row):
    cells = [c for c in row if c]
    return cells[0] if cells and len(set(cells)) == 1 and not re.fullmatch(r"\d+", cells[0]) else None


def parse(html, p):
    seen, recs = set(), []
    src = p["url"]

    def add(key_area, post, name, phone, level, area, wards, zone=None, address=None, wing=None):
        recs.append(_ward.record(MODULE, f"{_esw.slug(key_area)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=BODY,
                                 lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area, zone=zone, post=post, name=name,
                                 phone=phone, wards=wards, address=address, wing=wing, source=src))

    for g in tables(html):
        head = [c.lower() for c in g[0]]
        if "zone" in head and "mobile" in head:  # table 1: zone / central engineers
            post0 = ""
            for r in g[1:]:
                h = _heading(r)
                if h:
                    post0 = re.sub(r"\s*[–-]\s*", " - ", h)
                    continue
                if len(r) < 4 or not (r[1] or r[3]):
                    continue
                name, where, phone = r[1], r[2], r[3]
                post = post0
                if re.search(r"(?i)town\s*planning", post0):
                    post = re.sub(r"(?i)\s*\(?\s*zone\s*\d\s*\)?", "", where).strip() or "Engineer"
                    post = post if re.search(r"(?i)planning", post) else f"{post} (Town Planning)"
                post = re.sub(r"(?i)engineers$", "Engineer", post)
                z = _zone_no(where)
                if z:
                    add(f"zone-{z}", post, name, phone, "zone", f"Zone {z}", zone_wards(z), zone=f"Zone {z}")
                elif re.search(r"(?i)all\s*zone", where):
                    add("all", post, name, phone, "body", "All zones", _ward.wards_of(re.sub(r"(?i)all\s*zone", "", where)))
                else:
                    add("central", post, name, phone, "body", "Central Office", None)
        elif "ward nos" in head:  # tables 2 and 3: ward engineers, fitters, sanitary staff
            sanitary = any(re.search(r"(?i)\bS\.?\s?[IO]\b", r[1]) for r in g[1:] if len(r) > 1)
            zone, fitter, central = None, False, False
            for r in g[1:]:
                h = _heading(r)
                if h:
                    zone, fitter, central = _zone_no(h), bool(re.search(r"(?i)fitter", h)), bool(re.search(r"(?i)central", h))
                    continue
                if len(r) < 5 or not (r[1] or r[4]):
                    continue
                raw, wards_txt, place, phone = r[1], r[2], r[3], r[4]
                place = "" if place in ("–", "-") else place
                if central:
                    name, _ = split_post(raw, "")
                    add("central", wards_txt or "Engineer", name, phone, "body", "Central Office", None, wing="engineering")
                    continue
                if fitter:
                    name, post, wing = _esw.clean(raw), "Fitter (Water Supply)", "water"
                else:
                    name, post = split_post(raw, "Sanitary Inspector" if sanitary else "Assistant / Junior Engineer")
                    wing = None
                zn = f"Zone {zone}" if zone else None
                wards = [w for w in _ward.wards_of(re.sub(r"\(.*?\)", "", wards_txt))]
                whole = zone and wards == zone_wards(zone)
                if post.startswith("Sanitary Officer") or whole:
                    add(f"zone-{zone}", post, name, phone, "zone", zn, zone_wards(zone), zone=zn, address=place, wing=wing)
                elif wards:
                    add(f"zone-{zone}", post, name, phone, "ward", f"Ward {', '.join(wards)}", wards, zone=zn, address=place,
                        wing=wing)
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "office-staffs", r.content)], "" if recs else "no staff tables"
