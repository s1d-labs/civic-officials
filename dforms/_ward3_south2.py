"""Helpers of the ward3 readers of the South-2 group (Andhra Pradesh, Telangana, Odisha; branch ward-staff-south2).

keycontacts(): the GHMC-style "Key Contacts" page (/KeyContacts.aspx) that the corporations carved out of GHMC in 2026 use too
(Cyberabad: cmc.telangana.gov.in, Malkajgiri: mmc.telangana.gov.in; same layout as www.ghmc.gov.in, read by ward2s_ghmc). Per
section an <h5> heading over one table S.NO | Name | Designation | Zone | Circle | Contact Number | Email ID (column order changes
between sections). Same rules as ward2s_ghmc.parse: rows that name a zone or a circle are kept; head-office rows and the
Commissioner / Additional Commissioner / MLA / MP / MLC / vigilance tables are left out; a row with a circle is level "circle"
(extra key "circles" when the cell names more than one), a row with only a zone is level "zone".
"""
import re

from dforms import _esw, _ward

SECTION_WING = (
    (r"property\s*tax|trade\s*licen|estates", "revenue"), (r"town\s*planning", "planning"),
    (r"bio\s*diversity|urban\s*forestry|horticult", "horticulture"), (r"sanitation", "sanitation"),
    (r"health|entomolog|veterinar|food\s*safety", "health"), (r"electric", "electrical"), (r"engineer", "engineering"),
    (r"zonal|deputy\s*commissioner", "administration"),
)
SKIP = re.compile(r"(?i)mayor|^commissioner$|additional\s*commissioner|mla|\bmps?\b|mlc|corporator|vigilance")
HEAD_OFFICE = re.compile(r"(?i)head\s*office|^-?$")


def _wing(section, post):
    for rx, wing in SECTION_WING:
        if re.search(rx, section, re.I):
            return wing
    return _ward.wing_of(post)


def keycontacts(html, p, *, module, body, lgd, state, district):
    """[(record id, data)] of one Key Contacts page (see the module text)."""
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
        if not any(c.startswith("name") for c in head) or not any("designation" in c for c in head) \
                or not any(c in ("zone", "circle") for c in head):
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
            if not circle and not zone:
                continue
            if not zone and re.search(r"(?i)\bzone\b", circle):
                zone, circle = circle, ""
            zone = re.sub(r"(?i)\s*zone$", "", zone)
            post = post.title() if post.isupper() else post
            name = "" if name == "-" else name
            level = "circle" if circle else "zone"
            area = circle if circle else f"{zone} Zone"
            circles = [c.strip() for c in re.split(r"\s*,\s*", circle) if c.strip()] if circle else None
            key = f"{_esw.slug(section)}:{_esw.slug(area)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}"
            recs.append(_ward.record(module, key, seen, body=body, lgd=lgd, state=state, district=district, level=level,
                                     area=area, zone=f"{zone} Zone" if zone else None, post=post, name=name,
                                     phone=f"{contact} {mail}", email=f"{mail} {contact}", source=p["url"],
                                     wing=_wing(section, post), section=section.title(),
                                     circles=circles if circles and len(circles) > 1 else None, src_pos=rp))
    return recs
