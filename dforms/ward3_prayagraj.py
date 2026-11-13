"""Prayagraj Nagar Nigam (prayagrajmc.up.gov.in, the UP e-governance "CitizenHome" portal; allahabadmc.gov.in redirects here): the
8 zones and their staff. Five public pages of the portal (SectionInformation.html?editForm&rowId=N, one HTML table each; live
sample 2026-11-13 from Mumbai, not in archive.s1d.me; the portal sets a JSESSIONID cookie with one redirect first):
  354 "Nagar Nigam Zone Offices"   Sr.No. | Zone | Zone Office Name | Zone Office Address | Zonal Officer Details | Mobile | Lat | Long
  355 "Zonal Employee Details"     Sr.No. | Zone Number | Employee Name | Designation | Mobile Number   (tax, engineering, clerks)
  358 "Jalkal Zone Offices"        Sr.No. | Zone Number | Zone Office Name | Zone Office Address | Zone Officer Details | Mobile
  359 "Jalkal Zonal Employee Details"  same columns as 355 (water works: executive / junior engineers, demand clerks)
  356 "Know Your Zone Ward"        Sr.No. | Zone | Ward ("28-JHULEY LAL NAGAR") | Mohalla: read only for the wards of each zone.
Records: level "zone", area "Zone <n>" (the zone office name in zone_office), wards = the zone's wards from page 356 (100 wards,
2023 delimitation), ward_names = their names. Jal Kal records get wing "water". A mobile "0000000000" is left out. Lat / long of
the zone offices are kept as written (lat_text, lon_text: degree strings, some without the seconds sign).
Record ids: dept:ward3_prayagraj:<nagarnigam|jalkal>:zone<n>:<post slug>:<mobile or row>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_prayagraj"
BODY, LGD, STATE, DISTRICT = "Prayagraj Nagar Nigam", "249369", "UP", "Prayagraj"
BASE = "https://prayagrajmc.up.gov.in/SectionInformation.html?editForm&rowId={}&page="
PAGES = {"zone_offices": 354, "zone_employees": 355, "zone_wards": 356, "jalkal_offices": 358, "jalkal_employees": 359}
URL = BASE.format(PAGES["zone_offices"])


def url(page):
    return BASE.format(PAGES[page])


def items(get=None):
    return [{"key": f"{MODULE}-zones", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def zone_no(s):
    m = re.search(r"(?i)zone\s*-?\s*(\d+)", s or "")
    return m.group(1) if m else None


def zone_wards(html):
    """{zone no: [(ward no, ward name)]} from page 356, in ward number order."""
    out = {}
    for head, rows in _ward.header_tables(html, "Zone", "Ward")[:1]:
        for r in rows:
            z, w = zone_no(_ward.col(r, "Zone")), _ward.col(r, "Ward")
            m = re.match(r"\s*(\d{1,3})\s*-\s*(.*)$", w)
            if not (z and m):
                provenance.skip_row(r, 'skip: not (z and m)')
                continue
            ws = out.setdefault(z, [])
            if m.group(1) not in [x for x, _ in ws]:
                ws.append((str(int(m.group(1))), _esw.clean(m.group(2))))
    return {z: sorted(ws, key=lambda x: int(x[0])) for z, ws in out.items()}


def phone_of(s):
    return "" if re.fullmatch(r"[0\s-]*", s or "") else s


def offices(html, src, wing, zw, seen):
    recs = []
    for head, rows in _ward.header_tables(html, "Zone", "Office Name")[:1]:
        for r in rows:
            z = zone_no(_ward.col(r, "Zone"))
            if not z:
                provenance.skip_row(r, 'skip: not z')
                continue
            area = f"Zone {z}"
            post = "Zonal Officer (Jal Kal)" if wing == "water" else "Zonal Officer"
            ph = phone_of(_ward.col(r, "Mobile"))
            ws = zw.get(z, [])
            recs.append(_ward.record(MODULE, f"{src}:zone{z}:{_esw.slug(post)}:{re.sub(r'\D', '', ph) or len(recs)}", seen,
                                     body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=area, zone=area,
                                     zone_office=_ward.col(r, "Office Name"), post=post, name=_ward.col(r, "Officer"),
                                     phone=ph, address=_ward.col(r, "Address"), wards=[w for w, _ in ws] or None,
                                     ward_names=[f"{w}-{n}" for w, n in ws] or None, wing=wing, role="head",
                                     lat_text=_ward.col(r, "Latitude") or None, lon_text=_ward.col(r, "Longitude") or None,
                                     wards_note=None if ws else "zone not in the zone-ward page", source=url(
                                         "jalkal_offices" if wing == "water" else "zone_offices"), src_pos=r.pos))
    return recs


def employees(html, src, wing, zw, seen):
    recs = []
    for head, rows in _ward.header_tables(html, "Zone", "Employee Name")[:1]:
        for r in rows:
            z = zone_no(_ward.col(r, "Zone"))
            name, post = _ward.col(r, "Employee Name"), _ward.col(r, "Designation")
            if not (z and post and name):
                provenance.skip_row(r, 'skip: not (z and post and name)')
                continue
            area = f"Zone {z}"
            ph = phone_of(_ward.col(r, "Mobile"))
            ws = zw.get(z, [])
            recs.append(_ward.record(MODULE, f"{src}:zone{z}:{_esw.slug(post)}:{re.sub(r'[^0-9]', '', ph) or len(recs)}", seen,
                                     body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=area, zone=area,
                                     post=post, name=name, phone=ph, wards=[w for w, _ in ws] or None,
                                     wards_note=None if ws else "zone not in the zone-ward page",
                                     wing=wing or _ward.wing_of(post),
                                     source=url("jalkal_employees" if wing == "water" else "zone_employees"), src_pos=r.pos))
    return recs


def parse(pages, p=None):
    """pages: {page name: html}. Records of the four office / staff pages, wards from page 356."""
    zw = zone_wards(pages.get("zone_wards") or "")
    seen, recs = set(), []
    out = []
    for name, fn, src, wing in (("zone_offices", offices, "nagarnigam", "administration"),
                                ("zone_employees", employees, "nagarnigam", None),
                                ("jalkal_offices", offices, "jalkal", "water"),
                                ("jalkal_employees", employees, "jalkal", "water")):
        if pages.get(name):
            rs = fn(pages[name], src, wing, zw, seen)
            out.append((name, rs))
            recs += rs
    return recs, out


def fetch(p, get):
    pages, resp, files = {}, {}, []
    for name in PAGES:
        r = get(url(name))
        if r is None or r.status_code != 200:
            continue
        pages[name], resp[name] = r.text, r
        files.append(_esw.keep(MODULE, name, r.content))
    if not pages.get("zone_offices") and not pages.get("zone_employees"):
        return [], files, "no answer"
    recs, out = parse(pages, p)
    for name, rs in out:
        _ward.tag(rs, resp[name], url(name), METHOD)
    return recs, files, "" if recs else "no zone table"
