"""Puducherry: National Health Mission staff with their place of work (PHCs, UHCs, health and wellness centres, hospitals), from the
NHM Puducherry list www.nhmpuducherry.org.in/WebResources/html_pdf/programme/71.pdf (18 pages, 728 rows; the PDF was made
2026-04-24). Four parts: Pondicherry State Health Society - Puducherry District, District Health Mission - Karaikal District,
Mahe Region, Yanam Region. Columns: S.N, name of the staff, designation, place of working, date of joining. The list gives no
phone numbers. It names the medical officers of the health and wellness centres ("Medical Officer (HWC)", Lingareddipalayam ...),
RBSK and PHC doctors, staff nurses, ANMs, lab technicians, AYUSH physicians, counsellors and office staff. One queue item (one GET).

pypdf layout text: a row is "<S.N>  <name>  <designation>  <place of working>  <date of joining>". Cells are centred, so their
starts move from row to row. A row with more than three cells between S.N and the date (names can hold wide gaps: "Sagayamari
K") is cut at its two widest gaps; a row with fewer cells is placed by the page's usual column starts (the most common starts of
the 3rd and 4th cells of clean five-cell rows). Office posts (PSHS Office, DMS Office, State ... Manager) are kept: level facility with the office as the area.
Records: dept health, level facility, layer health, area = place of working, post = designation, name, district (from the part
heading), joined, facility_type (PHC / UHC / HWC / hospital / office, from the place and post). Record ids:
dept:civic_health_py:PY-<district>-<S.N>.
"""
import re

from dforms import _esw

MODULE = "civic_health_py"
URL = "https://www.nhmpuducherry.org.in/WebResources/html_pdf/programme/71.pdf"
CHUNK = re.compile(r"\S+(?: \S+)*")
ROW = re.compile(r"^\s*(\d{1,4})\s+\S")
DATE = re.compile(r"\s(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{2,4})\s*$")
PART = re.compile(r"(?i)(state health society|district health mission)\s*-\s*(.+?)\s*(district|region)?\s*$")
HOSPITAL = re.compile(r"(?i)\b(gh|ggh|hospital|igggh|rggw|igmc|jipmer|chc|cgp)\b")


def chunks(line):
    return [(m.start(), m.group()) for m in CHUNK.finditer(line)]


def columns(lines):
    """(post x, place x) of one page: the most common starts of the 3rd and 4th cells of clean five-cell rows."""
    xs = {}
    for ln in lines:
        if ROW.match(ln) and DATE.search(ln):
            cs = chunks(ln)
            if len(cs) == 5:
                xs[(cs[2][0], cs[3][0])] = xs.get((cs[2][0], cs[3][0]), 0) + 1
    if not xs:
        return None
    post = max(set(k[0] for k in xs), key=lambda v: sum(n for k, n in xs.items() if abs(k[0] - v) <= 1))
    place = max(set(k[1] for k in xs), key=lambda v: sum(n for k, n in xs.items() if abs(k[1] - v) <= 1))
    return post, place


def split3(cells, cols):
    """(name, post, place) from the cells of one row between S.N and the date."""
    if len(cells) >= 3:
        gaps = sorted(range(1, len(cells)), key=lambda i: cells[i][0] - (cells[i - 1][0] + len(cells[i - 1][1])), reverse=True)
        cut = sorted(gaps[:2])
        parts = [cells[:cut[0]], cells[cut[0]:cut[1]], cells[cut[1]:]]
        return tuple(_esw.clean(" ".join(t for _, t in part)) for part in parts)
    out = {"name": [], "post": [], "place": []}
    for x, t in cells:
        out[col_of(x, cols)].append(t)
    return tuple(_esw.clean(" ".join(out[k])) for k in ("name", "post", "place"))


def col_of(x, cols):
    if not cols:
        return "name"
    return "place" if x + 2 >= cols[1] else "post" if x + 2 >= cols[0] else "name"


def ftype(place, post):
    p = f"{place} {post}"
    if re.search(r"(?i)\bhwc\b|wellness|\baam\b|arogya mandir", p):
        return "HWC"
    if re.search(r"(?i)\buhc\b|\buphc\b", p):
        return "UHC"
    if re.search(r"(?i)\bphc\b", p):
        return "PHC"
    if HOSPITAL.search(place):
        return "hospital"
    if re.search(r"(?i)office|pshs|dms|nvbdcp|rbsk|society", place):
        return "office"
    return ""


def parse(pages, url=URL):
    """Rows; a line that is not a row (no S.N) continues the row above, cell by cell in the page's columns ("TB Health Visitor
    PHC" with the name and the rest of the place on the next line)."""
    rows, district, cols = [], "Puducherry", None
    for page in pages:
        lines = page.splitlines()
        cols = columns(lines) or cols
        last = None
        for line in lines:
            m = PART.search(line)
            if m and not ROW.match(line):
                district = _esw.clean(m.group(2)).title()
                last = None
                continue
            if not cols or not line.strip():
                continue
            if not ROW.match(line):
                if last is not None and not re.search(r"(?i)name of the staff|^\s*joining\s*$|date of\s*$", line):
                    for x, t in chunks(line):
                        last[col_of(x, cols)].append(t)
                continue
            d = DATE.search(line)
            body = line[:d.start()] if d else line
            cs = chunks(body)
            sno = cs[0][1].split()[0]
            first = cs[0][1][len(sno):].strip()
            cells = ([(cs[0][0] + len(sno) + 1, first)] if first else []) + cs[1:]
            name, post, place = split3(cells, cols)
            last = {"sno": sno, "district": district, "joined": d.group(1) if d else "", "name": [name] if name else [],
                    "post": [post] if post else [], "place": [place] if place else []}
            rows.append(last)
    recs, seen = [], set()
    for r in rows:
        name, post, place = (_esw.clean(" ".join(r[k])) for k in ("name", "post", "place"))
        if not name or not (post or place):
            continue
        key = f"PY-{_esw.slug(r['district'])}-{r['sno']}"
        if key in seen:
            continue
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="health", level="facility", layer="health", area=place or post, post=post,
                                name=name, joined=r["joined"], facility_type=ftype(place, post), state="PY",
                                district=r["district"], office_id=key, source=url))
    return recs


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "PY"}}]


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "nhm-staff-71", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
