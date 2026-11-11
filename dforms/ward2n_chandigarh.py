"""Municipal Corporation Chandigarh (mcchandigarh.gov.in): the sanitary inspectors of its 35 wards, from "List of CSI"
(/upload/List of CSI.pdf; in archive.s1d.me as text only, saved 2026-11-06; the file answers only from India: live sample through
vpsin 2026-11-11; PDF made 2024-12-31; 2 pages, text layer). Columns: Name of C.S.I | Name of S.I/MPW | Phone. No | Sector/Area |
Ward Wise. Cells wrap over several lines and are not aligned in rows, so the reader works by position (pdftotext -layout):
  - an SI row is a line with a 10-digit mobile in the phone column; the other lines of the page go to the nearest such line
    (a tie goes to the line above): their SI name parts, sector / area text and ward numbers (1-2 digit numbers in the last column).
  - the C.S.I. column holds the chief sanitary inspectors ("Gulab Singh, CSI 94631-55571"): one record each (level "body":
    the file does not draw the line between the CSI groups in its text, so the reader does not tie SIs or wards to a CSI).
SIs with ward numbers: level "ward"; SIs with duties only (dog control cell, dumping ground, MRF, SBM cell): level "body".
Record ids: dept:ward2n_chandigarh:<ward-a-b | duty slug | csi>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_chandigarh"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Chandigarh", "276386", "CH", "Chandigarh"
URL = "https://mcchandigarh.gov.in/upload/List%20of%20CSI.pdf"
MOB = re.compile(r"(?<![\d-])[6-9]\d{9}(?![\d-])")
CSI_PH = re.compile(r"\(?\b([6-9]\d{4}-\d{5}|[6-9]\d{9})\b\)?")


def items(get=None):
    return [{"key": f"{MODULE}-list-of-csi", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def runs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def cut(line, xs):
    """The line cut into columns at the x positions xs; a cut inside a word moves to the nearer end of that word."""
    out, prev = [], 0
    for x in xs:
        x = max(min(x, len(line)), prev)
        if 0 < x < len(line) and line[x - 1] != " " and line[x] != " ":
            s, e = x, x
            while s > prev and line[s - 1] != " ":
                s -= 1
            while e < len(line) and line[e] != " ":
                e += 1
            x = s if x - s <= e - x else e
        out.append(line[prev:x])
        prev = x
    out.append(line[prev:])
    return [_esw.clean(c) for c in out]


def page_rows(page):
    """[(si name, mobile, area, [wards])] and [(csi text)] of one page."""
    lines = [ln for ln in page.splitlines()]
    anchors = []
    for i, ln in enumerate(lines):
        for x, t in runs(ln):
            m = MOB.match(t)
            if m and 30 <= x <= 70:
                anchors.append((i, x))
                break
    if not anchors:
        return [], []
    phone_x = min(x for _, x in anchors)
    starts = sorted(x for i, _ in anchors for x, t in runs(lines[i]) if 12 <= x < phone_x - 4)
    si_x = starts[len(starts) // 2] - 2 if starts else phone_x - 24
    wards_x = [x for ln in lines for x, t in runs(ln) if re.fullmatch(r"\d{1,2}", t) and x > phone_x + 30]
    ward_x = min(wards_x) - 2 if wards_x else 10 ** 4
    area_x = phone_x + 11
    rows = {i: {"name": [], "mob": [], "area": [], "wards": []} for i, _ in anchors}
    csi = []
    aidx = [i for i, _ in anchors]
    cols = {i: cut(ln, [si_x, phone_x, area_x, ward_x]) for i, ln in enumerate(lines)
            if ln.strip() and not re.search(r"Name of C\.?S\.?I", ln)}
    for i, c in cols.items():
        if c[0]:
            csi.append((i, c[0]))
        near = min(aidx, key=lambda a: (abs(a - i), 0 if a <= i else 1))
        r = rows[near]
        if c[1]:
            # a name part between two rows goes to the row whose own line has no name (its name wraps above and below)
            nb = [a for a in aidx if abs(a - i) == abs(near - i) and a != near]
            if nb and cols.get(near, ["", ""])[1] and not cols.get(nb[0], ["", ""])[1]:
                r = rows[nb[0]]
            rows_name = r
            rows_name["name"].append(c[1])
            r = rows[near]
        r["mob"] += MOB.findall(c[2])
        if c[3]:
            r["area"].append(c[3])
        r["wards"] += re.findall(r"\b\d{1,2}\b", c[4])
    out = []
    for i in aidx:
        r = rows[i]
        out.append((_esw.clean(" ".join(r["name"])), r["mob"], _esw.clean(" ".join(r["area"])), r["wards"]))
    return out, csi


def csi_people(entries):
    """[(name, post, [phones], duty text)] of the chief sanitary inspectors and veterinary officers in the C.S.I. column lines
    [(line no, text)]: the post marker ("CSI", "Veterinary Officer") ends the name; a short line just above without digits is the
    first part of the name ("Sh. CHANDER" / "MOHAN CSI,"); the phone is on that line or the next two; the lines below up to the
    next name are the duty ("Dumping Ground/Sanitary Landfill ...")."""
    out, by = [], dict(entries)
    nums = sorted(by)
    marks = [i for i in nums if re.search(r"\bCSI\b|Vet[e]?r[i]?nary\b", by[i])]
    for k, i in enumerate(marks):
        t = by[i]
        m = re.search(r",?\s*\b(CSI|Vet[e]?r[i]?nary(?:\s+Officer)?)\b[.,]?", t)
        name, after = t[:m.start()], t[m.end():]
        prev = by.get(i - 1)
        if prev is not None and not re.search(r"\d", prev) and (len(name.split()) <= 1 or re.match(r"(Sh|Dr)\.", prev)) \
                and i - 1 not in marks:
            name = prev + " " + name
        nxt = marks[k + 1] if k + 1 < len(marks) else 10 ** 6
        tail = [by[j] for j in nums if i < j < nxt and j - i <= 6]
        rest = _esw.clean(" ".join([after] + tail))
        if nxt - i > 1 and k + 1 < len(marks):
            # the line just above the next marker may be the first part of the next name
            if (nxt - 1) in by and not re.search(r"\d", by[nxt - 1]) and re.match(r"(Sh|Dr)\.", by[nxt - 1]):
                rest = _esw.clean(rest.replace(by[nxt - 1], ""))
        ph = CSI_PH.findall(rest)[:2]
        duty = _esw.clean(CSI_PH.sub(" ", rest)).strip(" ,.-")
        duty = re.sub(r"^(Officer|-)[,\s-]*", "", duty)
        post = "CSI" if m.group(1) == "CSI" else "Veterinary Officer"
        out.append((_esw.clean(name).strip(" ,"), post, ph, duty))
    return out


def parse(pages, p):
    seen, recs, done = set(), [], set()
    for pg in pages:
        rows, csi = page_rows(pg)
        for name, mobs, area, wards in rows:
            m = re.search(r"[,\s]*\b(SI|MPW)\b\.?\s*$", name)
            post = {"SI": "Sanitary Inspector", "MPW": "Multi Purpose Worker"}.get(m.group(1)) if m else "Sanitary Inspector"
            nm = name[:m.start()] if m else name
            nm = _esw.clean(re.sub(r"\bSI\b", "", nm)).strip(" ,")
            ws = [str(int(w)) for w in wards if 1 <= int(w) <= 35]
            ws = list(dict.fromkeys(ws))
            if ws:
                key, level, ar = "ward-" + "-".join(ws), "ward", "Ward " + ", ".join(ws)
            else:
                key, level, ar = _esw.slug(area)[:40] or "duty", "body", BODY
            recs.append(_ward.record(MODULE, f"{key}:{_esw.slug(post)}:{_esw.slug(nm) or 'n'}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level=level, area=ar, post=post, post_as_written=m.group(1) if m else None,
                                     name=nm, phone=", ".join(dict.fromkeys(mobs)), wards=ws or None, sectors=area or None,
                                     wing="sanitation", source=p["url"]))
        for name, post, ph, duty in csi_people(csi):
            if (name, tuple(ph)) in done:
                continue
            done.add((name, tuple(ph)))
            full = "Chief Sanitary Inspector" if post == "CSI" else "Veterinary Officer"
            recs.append(_ward.record(MODULE, f"csi:{_esw.slug(full)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="body", area=BODY, post=full, post_as_written=post, name=name,
                                     phone=", ".join(ph), duty=duty or None, wing="sanitation" if post == "CSI" else "health",
                                     source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (the file answers only from India)"
    files = [_esw.keep(MODULE, "list-of-csi", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no SI rows (pdftotext missing?)"
