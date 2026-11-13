"""Bhagalpur Nagar Nigam (bhagalpurnagarnigam.in, WordPress): the health and sanitation staff of its 3 zones and 51 wards.
One PDF, "List of Helath Inchage and Others" (/wp-content/uploads/2024/09/List-of-Helath-Inchage-and-Others-1.pdf, made
2024-09-11; answers from Germany; saved in archive.s1d.me 2026-11-05; live copy 2026-11-11 is the same file). One page:
  head     "Health Section In charge" (name, mobile), "Bhandarpal" (store keeper), then three "Zonal Incharge (ward 01 to 13)",
           "(ward 14 to 32)", "(ward 33 to 51)" blocks, each with two people and mobiles: one of the corporation, one of the
           sanitation agency ("Aswani Kumar (Shine & Standard Facility Pvt. Ltd.)": the agency goes in the extra key "agency").
  table    two column pairs "ward no | name | mobile" for wards 1-51 (ward 38 has two people). The names are set in Kruti Dev
           (legacy Hindi font) and are converted with dforms/_ward_kd.py. The page does not name the post of these ward people:
           they are the ward in-charges of the health section (post "Ward In-charge (Health Section)").
Records: the zone in-charges at level "zone" (wards from the heading); the ward people at level "ward";
the section in-charge and the store keeper at level "body". The PDF names no zone: the zone area is "Zone of wards 1-13". Ward names are Hindi: name and name_regional carry the same text.
Record ids: dept:ward2s_bhagalpur:<zone or ward-N or body>:<post slug>:<name slug>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward_kd as kd

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_bhagalpur"
BODY, LGD, STATE, DISTRICT = "Bhagalpur Nagar Nigam", "249630", "BR", "Bhagalpur"
URL = "https://bhagalpurnagarnigam.in/wp-content/uploads/2024/09/List-of-Helath-Inchage-and-Others-1.pdf"
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
LABEL = re.compile(r"(?i)(health\s*section\s*in\s*charge|bhandarpal|zonal\s*in\s*charge\s*\(\s*ward\s*(\d+)\s*to\s*(\d+)\s*\))")
WARD_ROW = re.compile(r"(?:^\s*|\s{2,})(\d{1,2})\s{2,}(\S.*?)\s{2,}([6-9]\d{9})(?!\d)")
WARD_POST = "Ward In-charge (Health Section)"


def items(get=None):
    return [{"key": f"{MODULE}-health", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def _people(lines):
    """[(name, agency, phone)] of one head block: a new person starts on a name line outside an open parenthesis."""
    out, depth = [], 0
    for ln in lines:
        ph = MOBILE.findall(ln)
        frag = _esw.clean(MOBILE.sub(" ", LABEL.sub(" ", ln)))
        if frag:
            if depth > 0 and out:
                out[-1][0] += " " + frag
            else:
                out.append([frag, ""])
            depth += frag.count("(") - frag.count(")")
        for p in ph:
            if out and not out[-1][1]:
                out[-1][1] = p
            elif out:
                out[-1][1] += ", " + p
    res = []
    for name, phone in out:
        m = re.match(r"(.*?)\s*\((.*)\)\s*$", name)
        res.append((m.group(1), m.group(2), phone) if m else (name, "", phone))
    return res


def parse(pages, p):
    text = "\n".join(pages)
    lines = text.splitlines()
    at = _ward.joined_at(pages)

    def pos(i, **more):
        return provenance.line_pos(at[i][0], at[i][1], lines[i], **more) if i < len(at) else None
    first = next((i for i, ln in enumerate(lines) if re.match(r"\s*1\s{2,}\S", ln) and MOBILE.search(ln)), len(lines))
    seen, recs, src = set(), [], p.get("url") or URL
    # head: blocks between blank lines, each with its label
    blocks, cur, starts = [], [], []
    for i, ln in enumerate(lines[:first]):
        if ln.strip():
            if not cur:
                starts.append(i)
            cur.append(ln)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    for b, b0 in zip(blocks, starts):
        m = next((LABEL.search(ln) for ln in b if LABEL.search(ln)), None)
        if not m:
            provenance.skip_row(b, 'skip: not m')
            continue
        if m.group(2):
            lo, hi = int(m.group(2)), int(m.group(3))
            zone = f"Zone of wards {lo}-{hi}"
            level, area, post, wards = "zone", zone, "Zonal In-charge (Health Section)", [str(n) for n in range(lo, hi + 1)]
            zone_key = f"zone-{lo}-{hi}"
        elif "bhandar" in m.group(1).lower():
            level, area, post, wards, zone, zone_key = "body", BODY, "Store Keeper (Bhandarpal), Health Section", None, None, "body"
        else:
            level, area, post, wards, zone, zone_key = "body", BODY, "Health Section In-charge", None, None, "body"
        for name, agency, phone in _people(b):
            recs.append(_ward.record(MODULE, f"{zone_key}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level=level, area=area, zone=zone, post=post, name=name,
                                     phone=phone, wards=wards, source=src, agency=agency or None, wing="sanitation",
                                     src_pos=pos(b0, lines_in_block=len(b))))
    # ward table: Kruti Dev names
    found = [(m.groups(), i) for i, ln in enumerate(lines[first:], first) for m in WARD_ROW.finditer(ln)]
    rows = [g for g, _ in found]
    is_kd = kd.is_krutidev(" ".join(r[1] for r in rows))
    for (ward, raw, phone), li in found:
        name = kd.convert(raw) if is_kd or not re.search("[ऀ-ॿ]", raw) else raw
        name = _esw.clean(name)
        w = str(int(ward))
        recs.append(_ward.record(MODULE, f"ward-{w}:{_esw.slug(WARD_POST)}:{phone}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="ward", area=f"Ward {w}", post=WARD_POST, name=name, name_regional=name,
                                 phone=phone, wards=[w], source=src, wing="sanitation", src_pos=pos(li)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, [_esw.keep(MODULE, "health", r.content, "pdf")], "" if recs else "no rows"
