"""Municipal Corporation Shimla (shimlamc.hp.gov.in, NIC e-Nigam 1.0.1): the contact directory pages /Contact/Index/<n>
(menu "Contacts"; one HTML table each: S.No | Designation | [Name Of Ward] | Name | Office | Epbax no. | Resi No./Mobile No.;
live sample 2026-11-13 from dev-vps-3 (Mumbai); archive.s1d.me has only /contact-us/ (pool vantage, no answer): route unchecked).
  5  SEHB Supervisor List: one garbage-collection supervisor (SEHB Society of the MC) per ward, "Ward No 13 ( Krishna Nagar )"
  7  SEHB Assistant Supervisor List: the same for 8 wards
  8  MC Zonal Office: JEs of the water and sewerage zones (Central, Chotta Shimla, Sanjauli, Ridge, Chaura Maidan, New Shimla),
     the zonal offices (Dhalli, New Shimla, Totu), reservoirs and pump houses: office phones, no names
  4  MC Departments: Commissioner, Joint Commissioner, Health Officer, EE (R&B), Architect Planner, superintendents
Records: rows with a ward -> level "ward" (wards = [the number], area "Ward 13 (Krishna Nagar)"); page 8 rows that name a zone or
zonal office -> level "zone"; the rest -> level "body". The Epbax number is an office extension (kept as "extension").
Record ids: dept:ward3_shimla:<page>:<ward or post slug>:<mobile or name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py)

MODULE = "ward3_shimla"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Shimla", "248248", "HP", "Shimla"
BASE = "https://shimlamc.hp.gov.in/Contact/Index/"
PAGES = {"5": "sehb-supervisors", "7": "sehb-assistant-supervisors", "8": "zonal-offices", "4": "departments"}
WARD = re.compile(r"(?i)ward\s*no\.?\s*(\d{1,3})\s*(?:\(\s*(.*?)\s*\))?")
ZONE = re.compile(r"(?i)\bzon(e|al)\b|\(ws\s*&\s*sd\)|ws\s*&\s*sd")


def items(get=None):
    return [{"key": f"{MODULE}-{slug}", "payload": {"reader": MODULE, "url": BASE + n, "page": n, "state": STATE}}
            for n, slug in PAGES.items()]


def cell(row, *names):
    for n in names:
        for k, v in row.items():
            if k.lower() == n:
                return v
    return ""


def parse(html, p):
    seen, recs = set(), []
    tag = PAGES.get(str(p.get("page")), "contacts")
    for head, rows in _ward.header_tables(html, "s.no", "designation"):
        for r in rows:
            post = cell(r, "designation")
            name = re.sub(r"^-+$", "", cell(r, "name"))
            ward_txt = cell(r, "name of ward")
            office = re.sub(r"^-+$", "", cell(r, "office"))
            ext = re.sub(r"^-+$", "", cell(r, "epbax no."))
            mob = re.sub(r"^-+$", "", cell(r, "resi no./mobile no."))
            if not post or not (name or office or mob):
                continue
            post = re.sub(r"(?i)^supervisior$", "Supervisor", post)
            m = WARD.search(ward_txt)
            if m:
                w = str(int(m.group(1)))
                level, area, wards = "ward", f"Ward {w}" + (f" ({_esw.clean(m.group(2))})" if m.group(2) else ""), [w]
            elif tag == "zonal-offices" and ZONE.search(post):
                level, area, wards = "zone", post, []
            else:
                level, area, wards = "body", BODY, []
            phone = ", ".join(x for x in (mob, office) if x)
            sehb = tag.startswith("sehb")
            key = f"{tag}:{wards[0] if wards else _esw.slug(post)}:{re.sub(r'[^0-9]', '', mob)[:10] or _esw.slug(name) or 'office'}"
            recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=level,
                                     area=area, post=(f"SEHB {post}" if sehb else post), name=name, phone=phone,
                                     wards=wards, extension=ext or None, ward_name=_esw.clean(m.group(2)) if m and m.group(2) else None,
                                     wing="sanitation" if sehb else None,
                                     agency="Shimla Environment Heritage Conservation & Beautification (SEHB) Society, MC Shimla"
                                     if sehb else None,
                                     zone=area if level == "zone" else None, source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, PAGES.get(str(p.get("page")), "contacts"), r.content, "html")]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no contact table"
