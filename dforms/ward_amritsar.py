"""Municipal Corporation Amritsar (www.amritsarcorp.com): the engineers of each zone office and the wards each one holds. Answers
from Germany (live samples 2026-11-11; the site's older pages are in archive.s1d.me). Two PDFs linked from the home page, renamed
by the site when it updates them (the seed names the files as linked on 2026-11-11; when one is gone, re-seed from the home page):
  /NoticePDF/Civil-Update-14-9-26.pdf        "Engineering Staff in Civil Department": S.N | Name | Mobile No. | Designation |
                                             Office ("Zone No.8, 5") | Area (New Wards) ("1,2,64,65 ..."); SE / XEN / SDO / JE.
Not read: /NoticePDF/OandM_Department-Sep-2026.pdf (O&M cell: water supply and sewerage JEs with wards) and
/NoticePDF/Health-Update-8-9-26.pdf (zone CSO, CSI, SI with wards): their cells are centred over several lines with names and
mobiles on different lines, so a line reader puts phones and wards on the wrong officer. They need a box-based (pdftotext
-bbox) reader. A text PDF (pdftotext -layout; pypdf puts the columns elsewhere). The reader finds the columns from the heading line, takes each line with a mobile
number as one officer, and adds the ward fragments that stand alone in the ward column to the nearest officer whose own ward
cell is empty (else the nearest officer). Records: level "ward" when wards are given, else "zone" (XEN / SE: "Whole Assembly Area").
Record ids: dept:ward_amritsar:<file>:<post slug>:<mobile>.
"""
import re

import provenance
from dforms import _esw, _ward

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_amritsar"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Amritsar", "248273", "PB", "Amritsar"
BASE = "https://www.amritsarcorp.com/NoticePDF/"
FILES = {"civil": ("Civil-Update-14-9-26.pdf", "engineering")}
MOBILE = re.compile(r"(?<!\d)(\d{5}-?\s?\d{5})(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": BASE + f, "state": STATE, "kind": k}}
            for k, (f, _) in FILES.items()]


def _runs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def columns(lines):
    """{name: start column} from the heading line (the one with "Name" and "Designation")."""
    for ln in lines:
        if re.search(r"\bName\b", ln) and re.search(r"Designation", ln) and re.search(r"Ward|Area", ln):
            cols = {}
            for key, rx in (("name", r"Name"), ("post", r"Designation"), ("mobile", r"Mobile"), ("ward", r"Ward|Area"),
                            ("office", r"Office")):
                m = re.search(rx, ln)
                if m:
                    cols[key] = m.start()
            return cols
    return {}


def rows(text):
    """[{"name", "post", "mobile", "ward", "office"}] of one file's layout text."""
    lines = text.splitlines()
    cols = columns(lines)
    if not {"name", "post", "mobile", "ward"} <= set(cols):
        return []
    order = sorted(cols.items(), key=lambda kv: kv[1])

    def col_of(x):
        best = order[0][0]
        for k, s in order:
            if x + 6 >= s:
                best = k
        return best
    people, frags = [], []
    for i, ln in enumerate(lines):
        cells = {}
        for x, t in _runs(ln):
            for part, px in _split(t, x):
                k = "mobile" if MOBILE.fullmatch(part.strip()) else col_of(px)
                cells.setdefault(k, []).append(part)
        cells = {k: _esw.clean(" ".join(v)) for k, v in cells.items()}
        mob = MOBILE.findall(ln)
        if mob and re.search(r"[A-Za-z]{3}", cells.get("name", "") + cells.get("post", "")):
            people.append({"line": i, "name": re.sub(r"^\s*([ivx]+\)|\d+|\*+|[ivx]+)\s+", "", cells.get("name", "")),
                           "post": cells.get("post", ""), "mobile": ", ".join(mob), "ward": cells.get("ward", ""),
                           "office": cells.get("office", "")})
        elif mob and people:
            people[-1]["mobile"] += ", " + ", ".join(mob)
        elif set(cells) <= {"ward", "office"} and re.fullmatch(r"[\d,\s()A-Za-z]*\d[\d,\s()A-Za-z]*", cells.get("ward", "") or "x"):
            frags.append((i, cells["ward"]))
        elif cells.get("post") and people and not cells.get("name") and i - people[-1]["line"] == 1:
            people[-1]["post"] += " " + cells["post"]
    for i, t in frags:
        near = sorted(people, key=lambda p: (abs(p["line"] - i), p["line"] > i))
        empty = [p for p in near[:3] if not p["ward"] or p.get("frag")]
        p = (empty or near)[0] if near else None
        if p is None or abs(p["line"] - i) > 3:
            continue
        p.setdefault("frag", []).append((i, t))
    for p in people:
        parts = sorted(p.pop("frag", []) + ([(p["line"], p["ward"])] if p["ward"] else []))
        joined = ""
        for _, t in parts:
            joined += ("" if joined and joined[-1].isdigit() and t[:1].isdigit() else ",") + t if joined else t
        p["ward"] = joined
    return people


def _split(text, x):
    """A run that holds a name and a mobile number side by side ("Sukhwinder Singh 9888482426") as two parts with their columns."""
    out, pos = [], 0
    for m in MOBILE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()].strip(), x + pos))
        out.append((m.group(1), x + m.start()))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:].strip(), x + pos))
    return [(t, px) for t, px in out if t]


def parse(pages, p):
    kind = p.get("kind") or "civil"
    wing = FILES.get(kind, ("", "engineering"))[1]
    seen, recs = set(), []
    for pn, pg in enumerate(pages, 1):
        lines = pg.splitlines()
        for r in rows(pg):
            wards = [] if re.search(r"(?i)whole|---|new appointment", r["ward"]) else _ward.wards_of(re.sub(r"\([^)]*\)", "", r["ward"]))
            post = r["post"] or "Engineer"
            mob = r["mobile"].split(",")[0].strip().replace(" ", "").replace("-", "")
            area = (("Ward " if len(wards) == 1 else "Wards ") + ", ".join(wards)) if wards else (r["office"] or r["ward"] or BODY)
            recs.append(_ward.record(MODULE, f"{kind}:{_esw.slug(post)}:{mob}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="ward" if wards else "zone", area=area, post=post, name=r["name"],
                                     phone=r["mobile"], wards=wards, zone=r["office"] or None, wing=wing,
                                     ward_text=r["ward"] or None, source=p["url"],
                                     src_pos=provenance.line_pos(pn, r["line"] + 1, lines[r["line"]])))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (the file name changes on every update: re-seed from the home page)"
    files = [_esw.keep(MODULE, p.get("kind") or "file", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no officer table"
