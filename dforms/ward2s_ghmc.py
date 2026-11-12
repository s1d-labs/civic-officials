"""Greater Hyderabad Municipal Corporation (www.ghmc.gov.in): the officers of its 6 zones and 30 circles, wing by wing.
One page, /KeyContacts.aspx (ASP.NET; India only: HTTP 403 from Germany on 2026-11-11; read from India the same day; not in
archive.s1d.me). The page is an accordion: per section an <h5 class="panel-title"> heading ("ZONAL COMMISSIONER", "DEPUTY
COMMISSIONER", "PROPERTY TAX WING", "TOWN PLANNING WING", "URBAN BIO DIVERSITY WING", "HEALTH WING", "ELECTRICAL WING",
"ENGINEERING WING", "URBAN COMMUNITY DEVELOPMENT WING", "ENTOMOLOGY", "VETERINARY", "SANITATION", "FOOD SAFETY", ...) over one
table: S.NO | Name | Designation | Zone | Circle | Contact Number | Email ID (the column order changes between sections; the
engineering table has a second heading row of search boxes). The zones are Shamshabad, Golconda, Secunderabad, Rajendranagar,
Charminar and Khairathabad: the GHMC of 2026, after the split into GHMC, Cyberabad and Malkajgiri and the merger of 27 old ULBs
(Badangpet, Jalpally, Shamshabad, Adibatla ... are circles now). The page shows no "last updated" date and no ward numbers.
Records: one per officer and section row that names a zone or a circle (head-office rows, the Mayor / Commissioner / Additional
Commissioner tables and the MLA / MP / MLC tables are left out). A row with a circle is level "circle" (area = the circle cell as
written, "Jubilee Hills, Borabanda" when the officer covers two circles; extra key "circles" = the list); a row with only a zone
is level "zone". Extra keys: section (the heading), wing (from the section). Record ids:
dept:ward2s_ghmc:<section slug>:<zone or circle slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_ghmc"
BODY, LGD, STATE, DISTRICT = "Greater Hyderabad Municipal Corporation", "251664", "TG", "Hyderabad"
URL = "https://www.ghmc.gov.in/KeyContacts.aspx"
SECTION_WING = (
    (r"property\s*tax", "revenue"), (r"town\s*planning", "planning"), (r"bio\s*diversity|urban\s*forestry|horticult", "horticulture"),
    (r"sanitation", "sanitation"), (r"health|entomolog|veterinar|food\s*safety", "health"), (r"electric", "electrical"),
    (r"engineer", "engineering"), (r"zonal|deputy\s*commissioner", "administration"),
)
SKIP = re.compile(r"(?i)mayor|^commissioner$|additional\s*commissioner|mla|mp|mlc|corporator|vigilance")
HEAD_OFFICE = re.compile(r"(?i)head\s*office|^-?$")


def items(get=None):
    return [{"key": f"{MODULE}-key-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def _wing(section, post):
    for rx, wing in SECTION_WING:
        if re.search(rx, section, re.I):
            return wing
    return _ward.wing_of(post)


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for t in soup.find_all("table"):
        h = t.find_previous("h5")
        section = _esw.clean(h.get_text(" ")) if h else ""
        if not section or SKIP.search(section):
            continue
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g:
            continue
        head = [_esw.clean(c).lower() for c in g[0]]
        if not any(c.startswith("name") for c in head) or not any("designation" in c for c in head) or not any(c in ("zone", "circle") for c in head):
            continue
        for r, rp in zip(g[1:], gp[1:]):
            row = dict(zip(head, [_esw.clean(c) for c in r]))
            name, post = _ward.col(row, "name"), _ward.col(row, "designation")
            zone, circle = row.get("zone", ""), row.get("circle", "")
            contact, mail = _ward.col(row, "contact"), _ward.col(row, "email", "emaii")
            if not post or not (name or contact or mail):
                continue
            if HEAD_OFFICE.search(zone) and HEAD_OFFICE.search(circle):
                continue
            circle = "" if HEAD_OFFICE.search(circle) else circle
            zone = "" if HEAD_OFFICE.search(zone) or zone.lower() == "zonal office" else zone
            if not circle and not zone and not re.search(r"(?i)zone", row.get("circle", "")):
                continue
            if not zone and re.search(r"(?i)\bzone\b", circle):      # "Zonal Office" | "Khairathabad Zone"
                zone, circle = circle, ""
            zone = re.sub(r"(?i)\s*zone$", "", zone)
            post = post.title() if post.isupper() else post
            name = "" if name in ("-",) else name
            level = "circle" if circle else "zone"
            area = circle if circle else f"{zone} Zone"
            circles = [c.strip() for c in re.split(r"\s*,\s*", circle) if c.strip()] if circle else None
            key = f"{_esw.slug(section)}:{_esw.slug(area)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}"
            recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area,
                                     zone=f"{zone} Zone" if zone else None, post=post, name=name, phone=f"{contact} {mail}",
                                     email=f"{mail} {contact}", source=p["url"], wing=_wing(section, post), section=section.title(),
                                     circles=circles if circles and len(circles) > 1 else None, src_pos=rp))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "key-contacts", r.content)], "" if recs else "no zone or circle tables"
