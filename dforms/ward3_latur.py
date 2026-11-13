"""Latur City Municipal Corporation (mclatur.org): "विभाग प्रमुखांची यादी" (list of heads of department, dated 06/10/2026), the PDF
linked as "Contact No HOD" from the contact page (/wp-content/uploads/2026/10/Hod%200610.pdf, 2 pages, Word, live sample from
dev-vps-3 2026-11-13; not in archive.s1d.me). One row per officer: serial | name | post | mobile; a long post wraps onto the next
line. The font has no text map for its conjunct glyphs: lines go through _ward3_west.glyph_fix.
Zone officers: the post names the zone (क्षेत्र क्र.ए / बी / सी / डी): assistant commissioner / zonal officer (head) and assistant
zonal officers and zone tax superintendents (staff) at level "zone", one record per zone named (क्र.सी व डी = zones C and D).
Every other row is a head-office officer at level "body". The list names no electoral wards (wards_note).
Ids: dept:ward3_latur:<level>:<mobile or serial>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_west as w3

METHOD = "pdf text (pypdf layout) + glyph map (_ward3_west.glyph_fix)"

MODULE = "ward3_latur"
BODY, LGD, STATE, DISTRICT = "Latur City Municipal Corporation", "251561", "MH", "Latur"
URL = "https://mclatur.org/wp-content/uploads/2026/10/Hod%200610.pdf"
ROW = re.compile(r"^\s*(\d{1,3})\s{2,}(.+?)\s{2,}(.+?)(?:\s{2,}(\d[\d ,/]{8,}\d))?\s*$")
ZONE = re.compile(r"क्षेत्र\s*क्र\.?\s*([^\s/,()]+(?:\s+व\s+[^\s/,()]+)?)")
LETTER = {"ए": "A", "बी": "B", "सी": "C", "डी": "D", "ई": "E", "एफ": "F"}


def items(get=None):
    return [{"key": f"{MODULE}-hod", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def rows(pages):
    """[(serial, name, post, mobile, page, line, raw line)]; a wrapped line (no serial) is added to the post of the row above."""
    out = []
    for pn, pg in enumerate(pages, 1):
        for ln, raw in enumerate(pg.splitlines(), 1):
            t = w3.glyph_fix(raw)
            m = ROW.match(t)
            if m:
                out.append([m.group(1), _esw.clean(m.group(2)), _esw.clean(m.group(3)), (m.group(4) or "").strip(), pn, ln, raw])
            elif out and t.strip() and out[-1][4] == pn and not re.search(r"यादी|अ\.क्र|लातूर", t):
                out[-1][2] = _esw.clean(out[-1][2] + " " + t)
    return out


def zones(post):
    m = ZONE.search(post)
    if not m:
        return []
    return [LETTER.get(z.strip(), z.strip()) for z in re.split(r"\s+व\s+", m.group(1)) if z.strip()]


def parse(pages, p):
    seen, recs = set(), []
    for serial, name, post, mobile, pn, ln, raw in rows(pages):
        pos = provenance.line_pos(pn, ln, raw)
        zs = zones(post)
        key = mobile.split(",")[0].strip() or serial
        common = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, post=post, post_regional=post, name=name,
                      name_regional=name, phone=mobile, source=p["url"], src_pos=pos)
        if not zs:
            recs.append(_ward.record(MODULE, f"body:{key}", seen, level="body", area=BODY, **common))
            continue
        head = bool(re.search(r"सहाय्यक\s*आयुक्त\s*/\s*क्षेत्रि?ी?य|^क्षेत्रि?ी?य\s*अधिकारी", post))
        for z in zs:
            recs.append(_ward.record(MODULE, f"zone:{z.lower()}:{key}", seen, level="zone", area=f"Zone {z}", zone=f"Zone {z}",
                                     role="head" if head else "staff", wing="administration" if head else "revenue" if re.search(r"(^|\s|\()कर\s", post) else None,
                                     wards_note="the source names the zone, not its electoral wards", **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "hod-list", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p)
    return recs, files, "" if recs else "no officer rows"
