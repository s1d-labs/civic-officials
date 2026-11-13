"""Shared engine of the village-worker readers (dforms/vil_*.py): the named front-line workers of a village, ward or centre:
ASHA, ANM / MPW (health sub-centre), anganwadi worker and helper, ICDS sector supervisor, and village police (police patil,
gram rakshak, chowkidar) where a government page lists them by name.

An HTML table is read by the words of its header row. One row can name more than one person (Mizoram district health pages:
"Name of the Sub Center | Name of the ANM | Mobile No. | Village Name | Name of the ASHA | Mobile No."): every person column
gives its own record, and each phone column belongs to the nearest person column on its left. Area columns (village, ward,
centre / sub-centre / PHC, sector, project, block, district) are kept as their own fields; the record's area is the smallest one.
A column whose header names a doctor (MO / CHO / medical officer) is not a village post and is kept only in table_row.
The table's caption is the nearest heading before it, or a full-width title row above the header ("ASHA DETAILS OF FHC ...").

Records (depts.py contract): {"type": "dept_office", "dept" (health / women_child / police), "level" ("village"; a sector
supervisor is "section"), "layer": "village_worker", "post", "name", "phone", "area", "village", "ward_no", "centre", "sector",
"project", "block", "district", "state", "caption", "table_row", "src_url", "src_pos" {table, row, col}, "method"}.
A name cell "Vacant" / "Nil" / "-" gives no record. Nothing is masked: the lists are published as they are.
"""
import re
from urllib.parse import urlparse

from dforms import _esw

# header / caption word -> (post, dept, level)
POSTS = [
    (r"\basha\b|accredited social|sahiya|mitanin|sahyogini", ("ASHA", "health", "village")),
    (r"\banm\b|auxiliary nurse|female\s*h\.?\s*/?\s*w|female health worker|mphw\s*\(?f", ("ANM", "health", "village")),
    (r"\bmpw\b|male\s*h\.?\s*/?\s*w|male health worker|mphw\s*\(?m", ("MPW (Male Health Worker)", "health", "village")),
    (r"helper|\bawh\b|sahayika|sahayak", ("Anganwadi Helper", "women_child", "village")),
    (r"anganwadi worker|anganwadi teacher|\baww\b|sevika|worker", ("Anganwadi Worker", "women_child", "village")),
    (r"supervisor|mukhya sevika", ("ICDS Supervisor", "women_child", "section")),
    (r"police patil|पोलीस पाटील", ("Police Patil", "police", "village")),
    (r"gram rakshak|ग्राम रक्षक|gram rakshi|village police|\bvpo\b", ("Village Police Officer", "police", "village")),
    (r"chowkidar|chaukidar|चौकीदार", ("Gram Chowkidar", "police", "village")),
]
DOCTOR = re.compile(r"(?i)\bm\.?o\.?\b|\bcho\b|medical officer|doctor|\bmoic\b")
PHONE_H = re.compile(r"(?i)mobile|phone|contact|\bcug\b|\bph\.?\b|cell|मोबा|फोन|संपर्क")
NAME_H = re.compile(r"(?i)name|नाम|नाव|പേര്")
SNO_H = re.compile(r"(?i)^(s\.?\s*no\.?|sl\.?\s*no\.?|sr\.?\s*no\.?|serial|no\.?|#|क्र\.?|क्रम)$")
AREA_H = [  # role, header words (first match wins)
    ("ward_no", r"\bward\b"),
    ("village", r"village|gram\b|gaon|ग्राम|गाव|गांव|hamlet|habitation|mohall?a|tola"),
    ("centre", r"sub[\s-]*cent|centre|center|\bawc\b|\bphc\b|\bchc\b|\bfhc\b|\buphc\b|institution|facility|kendra|केंद्र"),
    ("sector", r"sector|circle"),
    ("project", r"project|icds"),
    ("block", r"block|mandal|taluk|tehsil"),
    ("district", r"district|zila|जिला|जिल्हा"),
    ("gp", r"panchayat"),
]
NOT_NAME = re.compile(r"(?i)^(vacant|nil|none|n\.?a\.?|-+|—|to be (filled|appointed)|not (appointed|available)|do|\"|〃)$")
HEAD_TEXT = ("h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "p", "caption")


def post_of(text):
    for rx, v in POSTS:
        if re.search(rx, text or "", re.I):
            return v
    return None


def role_of(h):
    """One header cell -> (role, post info or None). Roles: person, phone, sno, doctor, <area roles>, None."""
    h = _esw.clean(h)
    if not h:
        return None, None
    post = post_of(h)
    if DOCTOR.search(h) and not post:
        return "doctor", None
    if PHONE_H.search(h) and not NAME_H.search(h):
        return "phone", None
    if SNO_H.match(h):
        return "sno", None
    area = next((r for r, rx in AREA_H if re.search(rx, h, re.I)), None)
    if post and not (area and not re.search(r"(?i)worker|helper|sevika|sahayika|asha|\banm\b|\bmpw\b|supervisor|patil|rakshak|chowkidar", h)):
        return "person", post
    if area:
        return area, None
    if NAME_H.search(h):
        return "person", None
    return None, None


def header_index(g):
    """Index of the header row among the first 5 rows: the first row with a person column and at least two roles."""
    for i, row in enumerate(g[:5]):
        roles = [role_of(c)[0] for c in row]
        if "person" in roles and len({r for r in roles if r}) >= 2 and len(set(row)) > 1:
            return i
    return None


def caption_of(table, g, hi):
    """A full-width title row above the header, else the nearest heading-like text before the table."""
    for row in reversed(g[:hi]):
        if len(set(row)) == 1 and row[0]:
            return _esw.clean(row[0])
    prev = table.find_previous(HEAD_TEXT)
    t = _esw.clean(prev.get_text(" ")) if prev else ""
    return t if 3 <= len(t) <= 200 else ""


def table_records(module, g, pos, url, p, caption="", tag="page"):
    """Records of one table grid (rows of cell texts; pos: src_pos per row)."""
    hi = header_index(g)
    if hi is None:
        return []
    head = [_esw.clean(c) for c in g[hi]]
    roles = [role_of(c) for c in head]
    cap_post = post_of(caption)
    default = cap_post or ((post_of(p["post"]) or (p["post"], p.get("dept", "health"), p.get("level", "village")))
                           if p.get("post") else None)
    persons, owner, last = [], {}, None
    for i, (r, info) in enumerate(roles):
        if r == "person":
            persons.append(i)
            last = i
        elif r == "doctor":
            last = None
        elif r == "phone" and last is not None:
            owner.setdefault(last, []).append(i)
    host = urlparse(url).netloc
    out, seen = [], set()
    for row, sp in zip(g[hi + 1:], pos[hi + 1:]):
        cells = [_esw.clean(c) for c in row] + [""] * max(0, len(head) - len(row))
        if [c.lower() for c in cells[:len(head)]] == [h.lower() for h in head]:
            continue        # a repeated header row
        if len(set(c for c in cells if c)) <= 1 and len(head) > 2:
            continue        # a full-width title row inside the table
        areas = {}
        for i, (r, _) in enumerate(roles):
            if r and r not in ("person", "phone", "sno", "doctor") and cells[i] and r not in areas:
                areas[r] = cells[i]
        sno = next((cells[i] for i, (r, _) in enumerate(roles) if r == "sno" and cells[i]), "")
        for pi in persons:
            info = roles[pi][1] or default
            if not info:
                continue
            post, dept, level = info
            raw = cells[pi]
            phone = _esw.phones(*[cells[j] for j in owner.get(pi, [])], raw)
            name = _esw.clean(re.sub(r"(?:\+?91[\s-]*)?\d[\d\s-]{8,}\d", " ", raw)).strip(" ,;:-|")
            name = re.sub(r"(?i)\b(ph|mob|mobile|phone)\.?\s*:?\s*$", "", name).strip(" ,;:-|")
            if NOT_NAME.match(name) or re.fullmatch(r"[\d\s.,/-]*", name):
                name = ""
            if not (name or phone):
                continue
            k = (post, name.lower(), phone, areas.get("village") or areas.get("ward_no") or areas.get("centre"))
            if k in seen:
                continue        # rowspan repeats a person over the rows of the villages they serve
            seen.add(k)
            ward = areas.get("ward_no")
            area = areas.get("village") or (f"Ward {ward}" if ward and re.fullmatch(r"\d{1,3}", ward) else ward) or \
                areas.get("centre") or areas.get("gp") or areas.get("sector") or p.get("area")
            key = f"{host}:{tag}:t{sp.get('table', 0)}-r{sp.get('row', 0)}:{_esw.slug(post)}"
            out.append(_esw.record(
                module, key, dept=dept, level=level, layer="village_worker", post=post, name=name, phone=phone, area=area,
                village=areas.get("village"), ward_no=ward, centre=areas.get("centre"), sector=areas.get("sector"),
                project=areas.get("project") or p.get("project"), block=areas.get("block") or p.get("block"),
                gram_panchayat=areas.get("gp"), district=areas.get("district") or p.get("district"), state=p.get("state"),
                body=p.get("body"), local_body_code=p.get("local_body_code"), serial=sno, caption=caption or None,
                office_id=key, source=url, src_url=url, src_pos=dict(sp, col=pi + 1),
                table_row={h or f"col{i + 1}": c for i, (h, c) in enumerate(zip(head, cells)) if c} or None,
                tls_unverified=True if p.get("tls_unverified") else None))
    return out


def html_records(module, html, url, p, tag="page"):
    """Records of every usable table of an HTML page."""
    soup = _esw.soup(html)
    out = []
    for table in soup.find_all("table"):
        pos = []
        g = _esw.grid(table, pos=pos)
        if len(g) < 2:
            continue
        hi = header_index(g)
        if hi is None:
            continue
        out += table_records(module, g, pos, url, p, caption_of(table, g, hi), tag)
    return out
