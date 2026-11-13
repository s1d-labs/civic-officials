"""Manipur: every anganwadi centre of the state with its national AWC code and the names of its anganwadi worker and
anganwadi helper, from the Social Welfare Department's list "awc_in_manipur.pdf" (socialwelfare.mn.gov.in, Downloads).

File (archive.s1d.me copy of 2026-11-07, sha256 1267564c...): 332 pages, 3.3 MB, "Microsoft: Print To PDF" with a text layer
(no OCR). One table: "S.No. | District Name | Project Name | AWC Name | Awc Code | Anganwadi Worker Name | Anganwadi Helper Name";
serials 1-11,585, 16 districts; about 2,100 cells read "Vacant". No phone numbers, no date in the file.
Lines are read from the layout text (pdftotext -layout, else pypdf layout): the 11-digit AWC code anchors each row; the text
before it splits at runs of 2+ spaces into district, project and AWC name (the district is also checked against the 16 district
names), the text after it into worker and helper. A row whose parts do not split cleanly keeps its raw line and gets
"split_unsure": true.
Records: one per named person (a "Vacant" cell gives none): dept women_child, level village, layer village_worker, post
"Anganwadi Worker" / "Anganwadi Helper", name, area = AWC name, awc_code, project (ICDS project), district, state MN,
src_pos = page + line (provenance.line_pos). Ids dept:vil_mn_awc:<awc code>:aww / :awh.
"""
import re

import provenance
from dforms import _esw, _field

METHOD = "pdf text (layout), rows anchored on the 11-digit AWC code, columns split at runs of 2+ spaces"     # source trail

MODULE = "vil_mn_awc"
DISTRICTS = ["Bishnupur", "Chandel", "Churachandpur", "Imphal East", "Imphal West", "Jiribam", "Kakching", "Kamjong",
             "Kangpokpi", "Noney", "Pherzawl", "Senapati", "Tamenglong", "Tengnoupal", "Thoubal", "Ukhrul"]
ROW = re.compile(r"^\s*(\d{1,5})\s+(.*?)\s+(\d{11})(?:\s+(.*?))?\s*$")
SERIAL_ONLY = re.compile(r"^\s*\d{1,5}\s+\S.*$(?<!\d{11})")     # a serial line without a code at its end
CODE_FIRST = re.compile(r"^\s+14\d{9}\b")                       # the next line starts (indented) with an AWC code
# the AWC name runs into the code: "Ward No.11" + "14252011018", "Maning14252011611", "Pareng 37" + "14711010205"
GLUED = re.compile(r"(?:(?<=[^\s\d])|(?<=\s)(?=\d{12,14}(?!\d)))(\d{0,3})(14\d{9})(?!\d)")
VACANT = re.compile(r"(?i)^(vacant|nil|-+|n\.?a\.?)$")


def split_n(s, n):
    """Split s into n parts at its n-1 widest runs of spaces (in text order). sure = each cut is 2+ spaces wide and wider than
    every gap not cut (pypdf layout text puts 2 spaces inside some names; the column gaps are wider)."""
    s = s.strip()
    gaps = [(m.end() - m.start(), m.start(), m.end()) for m in re.finditer(r"\s+", s)]
    if n <= 1 or len(gaps) < n - 1:
        return [s] + [""] * (n - 1), False
    cut = sorted(sorted(gaps, key=lambda g: (-g[0], g[1]))[:n - 1], key=lambda g: g[1])
    rest = [g[0] for g in gaps if g not in cut]
    sure = all(g[0] >= 2 for g in cut) and (not rest or min(g[0] for g in cut) > max(rest))
    parts, prev = [], 0
    for _, a, b in cut:
        parts.append(s[prev:a])
        prev = b
    parts.append(s[prev:])
    return parts, sure


def split_before(s):
    """'Bishnupur   Bishnupur   Langpok Mamang Leikai' -> (district, project, awc name, sure)."""
    (dist, proj, awc), sure = split_n(s, 3)
    if dist.lower() not in {d.lower() for d in DISTRICTS}:
        d = next((d for d in sorted(DISTRICTS, key=len, reverse=True) if s.strip().lower().startswith(d.lower())), "")
        return d, "", s.strip()[len(d):].strip(), False
    return dist, proj, awc, sure


def rows(text):
    """[(serial, district, project, awc, code, worker, helper, sure, page, line no, line)] from the layout text.
    Two layouts that the one-line pattern misses (full file, 2026-11-13: 180 of 11,580 AWC codes) are read too:
      - a long AWC name wraps: "138 Bishnupur   Bishnupur   Maibam ... Makhong" and the code + names on the next line;
        the two lines are read as one row (line = the serial's line; line_text = both lines joined by " | ");
      - the AWC name runs into the code: "... Ward No.1114252011018 Ningthoujam ...": the code is the last 11 digits of the run
        (every AWC code in the file starts with 14, the Manipur state code)."""
    out = []
    for pg, page in enumerate(text.split("\f"), 1):
        lines = page.splitlines()
        skip_next = False
        for ln, line in enumerate(lines, 1):
            if skip_next:
                skip_next = False
                continue
            raw = line
            line = GLUED.sub(lambda g: f"{g.group(1)} {g.group(2)}", line)
            m = ROW.match(line)
            if not m and SERIAL_ONLY.match(line):
                nxt = next(((k, x) for k, x in enumerate(lines[ln:], ln + 1) if x.strip()), None)
                if nxt and CODE_FIRST.match(nxt[1]) and nxt[0] == ln + 1:
                    line = line.rstrip() + "   " + nxt[1].strip()
                    raw = lines[ln - 1].rstrip() + " | " + nxt[1].strip()
                    m = ROW.match(line)
                    skip_next = m is not None
            if not m:
                provenance.skip_line(line, "line does not match the row pattern")
                continue
            sno, before, code, after = m.group(1), m.group(2), m.group(3), m.group(4) or ""
            if not after.strip() and ln < len(lines) and re.match(r"^\s{20,}\S", lines[ln]) and not ROW.match(lines[ln]):
                # the names are on the next (indented) line; a short first part there is the AWC name's tail ("1(B)")
                parts = re.split(r"\s{2,}", lines[ln].strip())
                if len(parts) == 3 and len(parts[0]) <= 8:
                    before, parts = before + " " + parts[0], parts[1:]
                after = "    ".join(parts)
                raw = raw.rstrip() + " | " + lines[ln].strip()
                skip_next = True
            dist, proj, awc, sure = split_before(before)
            if re.search(r"\s{2,}", after.strip()):
                (worker, helper), s2 = split_n(after, 2)
            else:       # one name only (or both names with single spaces between): kept whole as the worker
                worker, helper, s2 = after.strip(), "", False
            out.append((sno, dist, proj, awc, code, worker, helper, sure and s2, pg, ln, raw))
    return out


def parse(content, url, p=None):
    text, engine = _field.pdf_text_engine(content)
    recs, seen = [], set()
    for sno, dist, proj, awc, code, worker, helper, sure, pg, ln, line in rows(text):
        for post, tag, name in (("Anganwadi Worker", "aww", worker), ("Anganwadi Helper", "awh", helper)):
            name = _esw.clean(name)
            if not name or VACANT.match(name):
                provenance.skipped("vacant or no name")
                continue
            key = f"{code}:{tag}"
            while key in seen:
                key += "-b"
            seen.add(key)
            recs.append(_esw.record(
                MODULE, key, dept="women_child", level="village", layer="village_worker", post=post, name=name, area=awc,
                awc_code=code, project=proj, district=dist, state="MN", serial=sno, split_unsure=None if sure else True,
                office_id=key, source=url, src_url=url, src_pos=provenance.line_pos(pg, ln, line),
                method=f"pdf text ({engine}), rows anchored on the AWC code"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    files = [_esw.keep(MODULE, "awc_in_manipur", r.content, "pdf")]
    recs = parse(r.content, p["url"], p)
    return recs, files, "" if recs else "no AWC rows"
