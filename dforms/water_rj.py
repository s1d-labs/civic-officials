"""Rajasthan: Public Health Engineering Department directory, phedwater.rajasthan.gov.in/.../en/directory0.html (answers only from India).

One server-rendered page (about 225 KB) with five tables: the main directory (about 800 rows: secretariat, chief engineers, ACE regions,
SE circles incl. Jaipur city circles, EE divisions, with name + mobile, designation, place, STD code, office phone, email), a second
list (ACE/SE/EE posts at headquarters, with extension and residence), and the Drilling, WSSO and Chemist wings (designation, place,
district, mobile; no names). "VACANT" and "." mean no officer / no value. The page shows no date. One queue item.
The name cell often repeats the mobile ("SH. KRISHAN KANT GUPTA 9166619700"): the digits go to phone, not to the name.
Level from the post (_water.level_of: E.E. = division, S.E. = circle, ACE = zone, AEN = sub-division), else "state" at Jaipur HQ.
Record ids: dept:water_rj:RJ-PHED-<slug of designation>-<slug of place> (a counter when one office has several such posts).
"""
import re

from dforms import _esw, _water
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_rj"
URL = "https://phedwater.rajasthan.gov.in/content/raj/water/public-health-engineering-department/en/directory0.html"
ORG = "Public Health Engineering Department, Rajasthan"
COLS = {"name": r"name", "mobile": r"mobile", "post": r"designation", "place": r"place", "district": r"district", "std": r"std",
        "tel": r"telephone", "extn": r"extn", "resi": r"resi", "email": r"e-?mail"}


SKIP = re.compile(r"(?i)^(chief minister|chief secretary)$")     # listed at the top of the directory; not PHED offices


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "RJ", "india_only": True}}]


def blank(s):
    s = _esw.clean(s)
    return "" if re.fullmatch(r"[.\-–\s*]*", s) else s


def person(s):
    """'SH. SUBHASH SHARMA 8279101550, 9460924523' -> ('SH. SUBHASH SHARMA', '8279101550, 9460924523'); VACANT -> no name."""
    s = blank(s)
    phones = _esw.phones(s)
    name = _esw.clean(re.sub(r"[\d*,/]+", " ", s)).strip(" .-")
    if not name or re.match(r"(?i)^vacant\b", name):
        m = re.search(r"(?i)(?:additional|addl\.?|add\.?)\s*charges?\s*(?:sh\.?|smt\.?)?\s*([A-Z][A-Z .]+)", name or "")
        return (f"{m.group(1).strip()} (additional charge)" if m else ""), phones
    return name, phones


def columns(head):
    out = {}
    for i, h in enumerate(head):
        h = h.lower()
        for k, rx in COLS.items():
            if k not in out and re.search(rx, h):
                out[k] = i
                break
    if "mobile" not in out and head and not head[-1].strip():    # WSSO table: last column has no heading
        out["mobile"] = len(head) - 1
    return out


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        rows = pgrid(t)
        if not rows:
            continue
        col = columns(rows[0])
        if "post" not in col:
            continue
        for row in rows[1:]:
            c = {k: (row[i] if i < len(row) else "") for k, i in col.items()}
            post = blank(c.get("post"))
            if not post or SKIP.match(post):
                continue
            name, own = person(c.get("name", ""))
            std = re.sub(r"\D", "", c.get("std", ""))
            tel = [x for x in re.split(r"[\s,/]+", blank(c.get("tel", ""))) if re.fullmatch(r"\d{5,8}", x)]
            office = ", ".join(f"0{std.lstrip('0')}-{x}" if std else x for x in tel)
            phone = _esw.phones(own, blank(c.get("mobile")), office, blank(c.get("resi")) if len(re.sub(r"\D", "", c.get("resi", ""))) >= 10 else "")
            email = _esw.emails(blank(c.get("email")))
            if not (phone or email or name):
                continue
            place = _esw.clean(re.sub(r"\d{6,}", "", blank(c.get("place")))) or blank(c.get("district"))
            level = _water.level_of(post, "state")
            area = re.sub(r"(?i)^(?:e\.?\s?e|s\.?\s?e|a\.?\s?en|addl\.?\s*c\.?\s?e|ace)\b\.?[\s.,:-]*", "", post).strip(" ,.-")
            if len(area) < 3 or re.match(r"(?i)^(\(|&|o/o|to\b|ta\b|mon\b)", area):     # a post in an office: the office's place
                area = place.title()
            if level == "state" and blank(c.get("district")):         # wing tables (drilling, WSSO, labs) list district posts
                level = "district"
            if level in ("state", "district") and place:
                area = place.title()
            elif place and place.lower() not in area.lower():
                area = f"{area}, {place.title()}"
            key = _water.unique(f"RJ-PHED-{_esw.slug(post)}-{_esw.slug(place)}", seen)
            recs.append(_esw.record(MODULE, key, dept="water", level=level, area=area, post=post, name=name, phone=phone, email=email,
                                    state="RJ", district=blank(c.get("district")).title() or None,
                                    office_id=f"RJ-PHED-{_esw.slug(post)}-{_esw.slug(place)}", org=ORG, place=place, source=url,
                                    src_pos=row.pos))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "directory0", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
