"""Generic police contact tables (shared by the police3_* readers of branch police-sho-w; not a reader itself).

tables(html, url, module, district, state) reads every <table> whose head row names an officer and/or a place and a phone:
  "Police Officer's Name | Police Station | Mobile No | Landline No | Email Address"   (station in-charges)
  "Police Officer's Name | Post | Mobile No | Landline No | Email Address"            (SP, Addl. SP, SDPO ...)
  "Police Officer's Name | Branch | Mobile No | post"                                (branches: LCB, traffic, cyber, control room)
  "Name of Police Station | Name of SHO | Mobile | Landline", "Station | In-charge | CUG" ...
Head words: name (officer / name / in-charge / SHO / incharge name), place (police station / station / branch / unit / office /
thana / PS), post (post / designation / rank), mobile (mobile / cell / CUG / whatsapp), landline (landline / phone / tel / office
no), email. A row of one cell is a section heading (kept as "section"; "Sub-Division X" also as subdivision).
The level comes from the head (place = police station -> police_station) and the words (police_s3waas.level_of): SP / SDPO /
DySP / ACP / circle / branch rows get district / subdivision / circle levels; office_type marks units: women (Bharosa, Damini,
mahila, AHTU), traffic, cyber, control_room, unit (other branches).
A rank written before the name ("PI Shri X", "API Shri Y", "IPS Z") goes to rank; the name keeps the rest.
Every record: area (the place as published), post, rank, name, phone (mobile first, then landline), email, section, district,
state, source, src_url, src_pos {table, row}. Record id dept:<module>:<district slug>:<slug of place or post>.
"""
import re

from bs4 import BeautifulSoup

from dforms import police_s3waas
from dforms._police import clean, email, phones, rec, slug, uniq
import provenance

H = [   # (field, head pattern), first match wins
    ("sno", r"^(s\.?\s*no|sr\.?\s*no|sl\.?\s*no|#|क्र)"),
    ("email", r"e-?\s?mail"),
    ("mobile", r"mobile|cell|cug|whats ?app|मोबाई"),
    ("landline", r"land ?line|phone|tel|office no|contact|दूरध्वनी"),
    ("name", r"officer'?s? name|name of (the )?(officer|sho|in-?charge|ps ?i)|in-?charge|^name$|^sho$|अधिकारी|नाव"),
    ("place", r"police station|^station|branch|unit|^office|thana|^ps$|ps name|name of ps|पोलीस ठाणे|शाखा"),
    ("post", r"^post$|designation|^rank|पद"),
]
RANK = re.compile(r"^((?:Sr\.?\s*)?P\.?I\.?|A\.?P\.?I\.?|P\.?S\.?I\.?|IPS|DYSP|Dy\.?\s?SP|ASP|SP|Insp(?:ector)?\.?|S\.?I\.?)"
                  r"\s+(?=(?:Shri|Smt|Mr|Ms|Mrs|Kum|[A-Z]))", re.I)
WOMEN = re.compile(r"bharosa|damini|mahila|women|\bahtu\b|human trafficking|\bajk\b|ajaak", re.I)


def kind(h):
    h = (clean(h) or "").lower().strip(" :.")
    for k, pat in H:
        if re.search(pat, h, re.I):
            return k
    return None


def unit_type(s):
    s = s or ""
    if WOMEN.search(s):
        return "women"
    if re.search(r"traffic", s, re.I):
        return "traffic"
    if re.search(r"cyber", s, re.I):
        return "cyber"
    if re.search(r"control ?room", s, re.I):
        return "control_room"
    return None


def split_rank(name):
    m = RANK.match(name or "")
    if m:
        return clean(m.group(1)), clean(name[m.end():])
    return None, name


def _cells(tr):
    return [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]


def _v(c, i):
    return c[i] if i is not None and i < len(c) and c[i].strip("-–— ") else None


def tables(html, url, module, district, state):
    soup = BeautifulSoup(html, "lxml")
    d = slug(district)
    out = []
    for ti, t in enumerate(soup.find_all("table")):
        rows = t.find_all("tr")
        if len(rows) < 2:
            continue
        head = [kind(h) for h in _cells(rows[0])]
        col = {}
        for i, k in enumerate(head):
            if k and k not in col:
                col[k] = i
        if not (("name" in col or "place" in col) and ("mobile" in col or "landline" in col)):
            continue
        place_head = (_cells(rows[0])[col["place"]] if "place" in col else "").lower()
        cap = t.find_previous(["h1", "h2", "h3", "h4", "h5", "caption"])
        caption = clean(cap.get_text(" ", strip=True)) if cap else None
        section, sub = None, None
        for ri, tr in enumerate(rows[1:], 1):
            c = _cells(tr)
            if len([x for x in c if x]) == 1 and len(c) <= 2:
                section = c[0] or c[-1]
                m = re.match(r"^sub[- ]?division\s+(.+)$", section, re.I)
                sub = clean(m.group(1)) if m else None
                continue
            rank, name = split_rank(_v(c, col.get("name")))
            place, post = _v(c, col.get("place")), _v(c, col.get("post"))
            if not (name or place or post):
                provenance.skip_row(tr, 'skip: not (name or place or post)')
                continue
            ph = phones(*(re.sub(r"\b(0\d{2,4})\s*/\s*(\d{5,8})\b", r"\1-\2", x)        # '02482/225601': STD code / number
                          for x in (_v(c, col.get("mobile")), _v(c, col.get("landline"))) if x))
            if not ph and not name:
                provenance.skip_row(tr, 'skip: not ph and not name')
                continue
            ut = unit_type(f"{place or ''} {post or ''}")
            if place and re.search(r"police station|thana|^ps|ps name|name of ps|पोलीस ठाणे", place_head) and ut is None:
                level, otype = "police_station", "police station"
            elif place and re.search(r"branch|unit|शाखा", place_head):
                level, otype = "district", ut or "unit"
            else:
                level, otype = police_s3waas.level_of(place or post or "", post or rank or "",
                                                      default="police_station" if place else "district")
                if ut:
                    otype = ut
                    if level == "police_station" and ut in ("traffic", "control_room"):
                        level = "district"
            key = place or post
            if not place and post:
                place = district if level == "district" else clean(re.sub(r"^(?:home\s+)?(?:SDPO|S\.D\.P\.O\.?|DYSP|Dy\.?\s?SP|ACP|CO)\s+",
                                                                          "", post, flags=re.I))
            out.append(rec(module, f"{d}:{slug(key)}", level=level, office_type=otype, area=place, post=post or (
                "SHO" if level == "police_station" else None), rank=rank, name=name, phone=ph,
                email=email(_v(c, col.get("email")) or ""), section=section or caption, subdivision=sub, district=district,
                state=state, source=url, src_url=url, src_pos={"table": ti, "row": ri}))
    return uniq(out)
