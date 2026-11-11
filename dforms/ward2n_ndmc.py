"""New Delhi Municipal Council (ndmc.gov.in): the sanitation officers of its 14 circles, from the Health Department's phone list
"Flag 'A' HEALTH DEPARTMENT PHONE NUMBER OF OFFICERS / OFFICIALS" (Departments/Health/DataHealthDepartment-19062023.pdf, linked
from departments/public_health.aspx as "Telephone List of Officers/Officials of Sanitation Staff under the Health Department";
in archive.s1d.me, saved 2026-11-11; the PDF was made 2023-06-19 and changed 2023-07-06; 8 pages, text layer). Three tables:
  1. Name | Designation | Mobile | Office: the Medical Officer of Health, CMOs, medical officers, the EE (Swachhata division),
     veterinary officers (head office: level "body").
  2. LIST OF CHIEF SANITARY INSPECTOR (CSI): S. No. | Circle No. ("1,3,4,10", "5 to 9") | Name | Designation | Mobile No.
     (level "circle", circles = the circle numbers).
  3. LIST SANITARY INSPECTOR (SI): Circle | Sanitary Inspector's name, post (SI-I, SI-II), mobiles | Assistant Sanitary
     Inspector's name and post (ASI-I ...) | Mobile | Jurisdiction (the roads and colonies of the circle).
Cells wrap over many lines, so each table is read by columns: the column of a text run is found from its x position in the
pdftotext -layout text (poppler; else pypdf layout mode). NDMC has no wards (it is a council with 14 sanitation circles and
13 nominated members): records carry "circles" (circle numbers as strings), not "wards". The older list Departments/Health/
TELEPHONE NO.pdf (made 2015) is not read. Record ids: dept:ward2n_ndmc:<circle-n | hq | csi-n>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_ndmc"
BODY, LGD, STATE, DISTRICT = "New Delhi Municipal Council", "276447", "DL", "New Delhi"
URL = "https://ndmc.gov.in/departments/Departments/Health/DataHealthDepartment-19062023.pdf"
PERSON = re.compile(r"(?=\b(?:Sh|Ms|MS|Smt|Mr|Mrs|Dr)\s?\.)")
MOB = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-health-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def runs(line):
    """[(x, text)] of the runs of a line (parts split by 2+ spaces)."""
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def split_cols(line, xs):
    """The line cut into len(xs)+1 columns at the x positions xs; a cut inside a word moves to the start of that word."""
    out, prev = [], 0
    for x in xs:
        x = min(x, len(line))
        while 0 < x < len(line) and x > prev and line[x - 1] != " " and line[x] != " ":
            x -= 1
        out.append(line[prev:x])
        prev = x
    out.append(line[prev:])
    return [_esw.clean(c) for c in out]


def people(text):
    """[(name, post, [mobiles])] of a column text that holds one or more "Sh. Name POST mobile" entries."""
    out = []
    for part in PERSON.split(text):
        part = _esw.clean(part).strip(" ,/")
        if not re.match(r"(?:Sh|Ms|MS|Smt|Mr|Mrs|Dr)\s?\.", part):
            continue
        mobs = MOB.findall(part)
        rest = _esw.clean(MOB.sub(" ", part)).strip(" ,/")
        m = re.search(r"[,\s-]*\b(A?SI|CSI)\b(?:\s*-\s*|\s+)?(I{1,3}|\d)?\b.*$", rest)
        post = ""
        if m:
            post = re.sub(r"\s+", "", m.group(1)) + (f"-{m.group(2)}" if m.group(2) else "")
            rest = rest[:m.start()]
        name = re.sub(r"\(\d+\)", "", rest).strip(" ,-/")
        out.append((_esw.clean(name), post, mobs))
    return out


def circles_of(text):
    t = re.sub(r"(\d)\s+(\d)(?=\s*(?:&|,|$))", r"\1\2", _esw.clean(text))
    return [w for w in _ward.wards_of(t) if w.isdigit() and 1 <= int(w) <= 14]


def section(lines, start_rx, end_rx):
    i = next((k for k, ln in enumerate(lines) if re.search(start_rx, ln)), None)
    if i is None:
        return []
    j = next((k for k in range(i + 1, len(lines)) if re.search(end_rx, lines[k])), len(lines))
    return lines[i + 1:j]


def parse(pages, p):
    text = "\n".join(pages).replace("\f", "\n")
    text = re.sub(r"(\d{10})(?=[A-Za-z])", r"\1 ", text)
    lines = text.splitlines()
    seen, recs = set(), []

    def add(level, key, post, name, phones, circles=None, area=None, note=None, wing=None):
        if not (name or phones):
            return
        area = area or (f"Circle {circles[0]}" if circles and len(circles) == 1 else
                        ("Circles " + ", ".join(circles) if circles else BODY))
        recs.append(_ward.record(MODULE, f"{key}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level=level, area=area, post=post, name=name, phone=", ".join(dict.fromkeys(phones)),
                                 circles=circles or None, jurisdiction=note or None, wing=wing or "sanitation", source=p["url"]))

    # 1. head office officers: Name | Designation | Mobile | Office, rows split by blank lines
    hq = section(lines, r"PHONE NUMBER OF OFFICERS", r"LIST OF CHIEF SANITARY")
    head = next((ln for ln in hq if re.search(r"Name\s+Designation\s+Mobile", ln)), None)
    if head:
        xs = [head.index("Designation") - 2, head.index("Mobile") - 3, head.index("Office") - 2]
        rows = [split_cols(ln, xs) if ln.strip() else None for ln in hq[hq.index(head) + 1:]]
        # a row starts at a line whose name cell starts with Sh. / Dr. / Mr.; in its blank-line group, the other lines go to the
        # row above, except a line just above a row start that holds only a post (the post wraps above a name line that has no post)
        groups, g = [], []
        for c in rows + [None]:
            if c is None:
                if g:
                    groups.append(g)
                g = []
            else:
                g.append(c)
        for g in groups:
            anchors = [i for i, c in enumerate(g) if PERSON.match(c[0]) or re.match(r"(?:Sh|Ms|MS|Smt|Mr|Mrs|Dr)\s?\.", c[0])]
            if not anchors:
                continue
            parts = {a: [] for a in anchors}
            for i, c in enumerate(g):
                before = [a for a in anchors if a <= i]
                a = before[-1] if before else anchors[0]
                if i + 1 in anchors and i not in anchors and c[1] and not c[0] and not g[i + 1][1]:
                    a = i + 1
                parts[a].append(c)
            for a in anchors:
                block = parts[a]
                name = " ".join(c[0] for c in block if c[0])
                post = " ".join(c[1] for c in block if c[1])
                phones = MOB.findall(" ".join(c[2] for c in block)) + re.findall(r"(?<!\d)2\d{7}(?!\d)", " ".join(c[3] for c in block))
                if post:
                    add("body", "hq", _esw.clean(post), _esw.clean(name), phones, wing="sanitation" if "swac" in post.lower()
                        else ("health" if re.search(r"(?i)medical|cmo|health|vety", post) else None))

    # 2. chief sanitary inspectors by circles
    csi = section(lines, r"LIST OF CHIEF SANITARY", r"LIST SANITARY INSPECTOR")
    head = next((ln for ln in csi if "Designation" in ln), None)
    if head:
        xs = [head.index("Name") - 8, head.index("Designation") - 2, head.index("Mobile") - 2]
        rows, cur = [], None
        for ln in csi[csi.index(head) + 1:]:
            if not ln.strip() or re.fullmatch(r"\s*No\.\s*", ln):
                continue
            c = split_cols(ln, xs)
            m = re.match(r"\s*(\d)\.?\s+(.*)", c[0])
            if m and c[1]:
                cur = [m.group(2), c[1], c[2], c[3]]
                rows.append(cur)
            elif cur:
                cur[0] += " " + c[0]
                cur[1] += " " + c[1]
                cur[3] += " " + c[3]
        for i, (circ, name, post, mob) in enumerate(rows, 1):
            cs = circles_of(circ) if re.fullmatch(r"[\d,&\sto]+", _esw.clean(circ)) else []
            add("circle", f"csi-{i}", _esw.clean(post) or "CSI", _esw.clean(name), MOB.findall(mob), circles=cs,
                area=None if cs else _esw.clean(circ))

    # 3. sanitary inspectors and assistant sanitary inspectors of each circle
    si = section(lines, r"LIST SANITARY INSPECTOR", r"AIR POLLUTION CELL")
    blocks, cur = [], None
    for ln in si:
        m = re.match(r"^(\s{0,8})(\d{1,2})(\s+)(?=(?:Sh|Ms|MS|Smt|Mr|Dr)\s?\.)", ln)
        if m and 1 <= int(m.group(2)) <= 14:
            cur = (m.group(2), [" " * len(m.group(0)) + ln[len(m.group(0)):]])
            blocks.append(cur)
        elif cur:
            cur[1].append(ln)
    for circle, bl in blocks:
        rs = [r for ln in bl for r in runs(ln)]
        si_x = min(x for x, t in rs)
        asi = [x for x, t in rs if re.match(r"(?:Sh|Ms|MS|Smt|Mr)\s?\.", t) and x > si_x + 12]
        if not asi:
            continue
        asi_x = min(asi)
        mob_x = min((x for x, t in rs if re.match(r"[6-9]\d{9}", t) and x > asi_x + 8), default=asi_x + 18)
        jur_x = min((x for x, t in rs if re.match(r"[A-Za-z]", t) and x > mob_x), default=mob_x + 11)
        si_txt, asis, jur, cur_asi = [], [], [], None
        for ln in bl:
            mk = [m.start() for m in re.finditer(r"(?:Sh|Ms|MS|Smt|Mr)\s?\.", ln) if m.start() >= asi_x - 4]
            ax = mk[0] if mk else asi_x
            c = split_cols(ln, [ax, max(mob_x, ax + 1), max(jur_x, ax + 2)])
            c[2], c[3] = c[2] + " " + " ".join(MOB.findall(c[3])), _esw.clean(MOB.sub(" ", c[3])).strip(" ,/")
            si_txt.append(c[0])
            if re.match(r"(?:Sh|Ms|MS|Smt|Mr)\s?\.", c[1]):
                cur_asi = [c[1], []]
                asis.append(cur_asi)
            elif cur_asi and c[1]:
                cur_asi[0] += " " + c[1]
            if cur_asi:
                cur_asi[1] += MOB.findall(c[2])
            jur.append(c[3])
        note = _esw.clean(" ".join(jur))
        for name, post, mobs in people(" ".join(si_txt)):
            add("circle", f"circle-{circle}", post or "SI", name, mobs, circles=[circle], note=note)
        for txt, mobs in asis:
            for name, post, own in people(txt):
                add("circle", f"circle-{circle}", post or "ASI", name, own + mobs, circles=[circle], note=note)
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "health-officers", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no officer tables (pdftotext missing?)"
