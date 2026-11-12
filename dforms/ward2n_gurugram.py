"""Municipal Corporation of Gurugram (mcg.gov.in): its zone offices (Joint Commissioners I-VI and Zonal Taxation Officers I-VI, each
with the wards of the zone) and the head-office officers (Commissioner, Additional Commissioners, Chief / Executive Engineers,
town planners, senior sanitary inspectors I-VI, accounts), from the page "Office Contacts" (/contact/office-contacts). The site is
a single-page app (Vite/React): the data is not on an API but written into the app's script bundle (/assets/index-<hash>.js,
named in the home page), as objects {officeName, name, type, address, phone, email, timings, services}; the address of a zone
office ends with "(Zone-I, Wards- 11,14,15,16,17,18)". Live sample 2026-11-11 (answers from Germany; archive.s1d.me has only the
empty home page; the page shows no date). Two requests per run: the home page, then the bundle. The Joint Commissioner zones and
the Zonal Taxation zones hold different wards (as written). Records: offices that name a zone: level "zone" with wards; the others:
level "body". Ward-wise Contacts (/contact/ward-wise-contacts) lists the nominated ward members: not read here.
Record ids: dept:ward2n_gurugram:<office slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_gurugram"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation of Gurugram", "248576", "HR", "Gurugram"
URL = "https://www.mcg.gov.in/"
OFFICE = re.compile(r'\{officeName:"([^"]*)",name:"([^"]*)",type:"([^"]*)",address:"([^"]*)",phone:"([^"]*)",email:"([^"]*)"')
TYPE_WING = {"engineering": "engineering", "taxation": "revenue", "sanitation": "sanitation", "revenue": "administration"}


def items(get=None):
    return [{"key": f"{MODULE}-office-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def bundle_url(html, base=URL):
    m = re.search(r'<script[^>]+src="(/assets/index-[^"]+\.js)"', html)
    return base.rstrip("/") + m.group(1) if m else None


def parse(js, p, source=None):
    seen, recs = set(), []
    for office, name, typ, address, phone, email in OFFICE.findall(js):
        office = _esw.clean(office)
        post = re.sub(r"\s*Office$", "", office)
        z = re.search(r"\(\s*Zone\s*-\s*([IVX]+)\s*,\s*Wards?\s*-\s*([\d,\s]+)\)", address, re.I)
        addr = _esw.clean(address[:z.start()] if z else address).strip(" ,")
        wing = _ward.wing_of(post)
        if wing in ("other", "administration"):
            wing = TYPE_WING.get(typ.lower(), wing)
        if re.search(r"(?i)town planner", post):
            wing = "planning"
        if re.search(r"(?i)horticulture", post):
            wing = "horticulture"
        kw = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, post=post, name=_esw.clean(name).strip(" ,"),
                  phone=phone.strip() if re.search(r"\d{5}", phone) else "", email=email, address=addr, wing=wing,
                  section=typ or None, source=source or p["url"], page="https://www.mcg.gov.in/contact/office-contacts")
        if z:
            zone = f"Zone-{z.group(1).upper()}"
            recs.append(_ward.record(MODULE, _esw.slug(office), seen, level="zone", area=zone, zone=zone,
                                     wards=_ward.wards_of(z.group(2)), **kw))
        else:
            recs.append(_ward.record(MODULE, _esw.slug(office), seen, level="body", area=BODY, **kw))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (home page)"
    js_url = bundle_url(r.text, p["url"])
    if not js_url:
        return [], [_esw.keep(MODULE, "home", r.content)], "no script bundle in the home page"
    j = get(js_url)
    if j is None:
        return [], [], "no answer (script bundle)"
    recs = parse(j.text, p, source=js_url)
    return recs, [_esw.keep(MODULE, "bundle", j.content, "js")], "" if recs else "no office objects in the bundle"
