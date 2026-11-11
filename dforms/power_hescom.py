"""Karnataka: HESCOM (Hubballi) contact PDFs, hescom.karnataka.gov.in/storage/pdf-files/... (India only). Two queue items:
- "sections": Contact Details/Section Officers Mobile Number.pdf (9 pages, text layer): rows "SL No, Section Name, Landline Number,
  Section Officer's Mobile no", ~309 sections. The PDF names no division or sub-division.
- "officers": Announcements/HESCOMOfficersContactInfo.pdf (3 pages): one wide table Zonal Office | Circle Office | O&M Circle Office
  SEE | District | Division | Division Office EEE | Division Office AEE | Sub-Division | Sub Division AEE. Names and phones of
  divisions and circles sit in the middle of the rows they span, so each line is cut into columns by the header's positions; a
  sub-division's division is found by cutting the sub-division lines into one contiguous run per division so that each division
  name sits in the middle of its run (groups()), and the parent is kept only when that cut and the nearest name agree (agree());
  circles over divisions the same way. About 80% of the sub-divisions get a division. 2 zones, 7 circles, 26 divisions, 86 sub-divisions. Phones only, no names.
Records: dept:power_hescom:<level>:<name>.
"""
import re

from dforms._power import Out, clean, pdf_pages, phone, raw

BASE = "https://hescom.karnataka.gov.in/storage/pdf-files/"
URLS = {"sections": BASE + "Contact%20Details/Section%20Officers%20Mobile%20Number.pdf",
        "officers": BASE + "Announcements/HESCOMOfficersContactInfo.pdf"}
MOB = re.compile(r"^\d{10},?-?$")
SEC_ROW = re.compile(r"^\s*(\d{1,3})\s{2,}(\S.*)$")


def parse_sections(pages, url=URLS["sections"]):
    out = Out("power_hescom", "KA", url, discom="HESCOM")
    for pg in pages:
        for line in pg.splitlines():
            m = SEC_ROW.match(line)
            if not m:
                continue
            parts = [x.strip() for x in re.split(r"\s{2,}", m.group(2).strip()) if x.strip()]
            mob = None
            if parts and re.fullmatch(r"\d{10}-?", parts[-1]):
                mob = parts.pop().rstrip("-")
            if not parts:
                continue
            k = next((i for i, x in enumerate(parts) if i and re.search(r"\d{4,}", x)), len(parts))
            name = clean(" ".join(parts[:k]).strip(" -"))
            land = " ".join(parts[k:]) or None
            if not name or re.fullmatch(r"[\d\s/-]+", name):
                continue
            out.add(f"section:{m.group(1)}:{name}", "section", name, post="Section Officer", phone_=phone(mob, land),
                    office_id=m.group(1))
    return out.recs


COLS = ("zone", "circle", "see", "district", "division", "eee", "aee", "subdivision", "subaee")
HEAD = (("zone", r"Zonal Office"), ("circle", r"Circle Office(?!\s*SEE)"), ("see", r"(?:O&M\s+)?Circle Office SEE"),
        ("district", r"District"), ("division", r"Divison(?!\s*Office)|Division(?!\s*Office)"), ("eee", r"Division Office EEE"),
        ("aee", r"Division Office AEE"), ("subdivision", r"Sub-Divison|Sub-Division"), ("subaee", r"Sub Division AEE"))


def centers(header):
    c, pos = {}, 0
    for key, rx in HEAD:
        m = re.compile(rx).search(header, pos)
        if not m:
            return None
        c[key] = (m.start() + m.end()) / 2
        pos = m.end() if key != "circle" else m.start() + 1
    return c


def tokens(line):
    for m in re.finditer(r"\S+(?: \S+)*", line):
        yield (m.start() + m.end()) / 2, m.group()


def groups(items, anchors):
    """Cut the sorted line numbers `items` into len(anchors) contiguous, non-empty groups so that each group's middle line is
    nearest its anchor (a name printed in the middle of the rows it spans). Returns the anchor index of each item."""
    m, k = len(items), len(anchors)
    if not k or m < k:
        return [min(range(k), key=lambda j: abs(anchors[j] - x)) if k else None for x in items]
    inf = float("inf")
    cost = lambda a, b, j: (sum(items[a:b]) / (b - a) - anchors[j]) ** 2
    best = [[inf] * (m + 1) for _ in range(k + 1)]
    back = [[0] * (m + 1) for _ in range(k + 1)]
    best[0][0] = 0
    for j in range(1, k + 1):
        for b in range(j, m - (k - j) + 1):
            for a in range(j - 1, b):
                v = best[j - 1][a] + cost(a, b, j - 1)
                if v < best[j][b]:
                    best[j][b], back[j][b] = v, a
    out, b = [0] * m, m
    for j in range(k, 0, -1):
        a = back[j][b]
        out[a:b] = [j - 1] * (b - a)
        b = a
    return out


def agree(items, anchors):
    """The anchor of each item when the contiguous cut (groups) and the nearest line give the same one; else None."""
    g = groups(items, anchors)
    out = []
    for x, j in zip(items, g):
        near = sorted(range(len(anchors)), key=lambda i: abs(anchors[i] - x))
        tie = len(near) > 1 and abs(anchors[near[0]] - x) == abs(anchors[near[1]] - x)
        out.append(j if j is not None and not tie and near[0] == j else None)
    return out


def parse_officers(pages, url=URLS["officers"]):
    out = Out("power_hescom", "KA", url, discom="HESCOM")
    rows = []                                    # (line no, {col: [texts]}) over all pages
    n = 0
    zone_lines = []
    for pg in pages:
        lines = pg.splitlines()
        hi = next((i for i, l in enumerate(lines) if "Zonal Office" in l and "Sub Division AEE" in l), None)
        if hi is None:
            continue
        c = centers(lines[hi])
        if not c:
            continue
        for i, line in enumerate(lines):
            n += 1
            if i == hi or not line.strip():
                continue
            cols = {}
            for x, t in tokens(line):
                col = min(c, key=lambda k: abs(c[k] - x))
                cols.setdefault(col, []).append(t)
            z = " ".join(cols.get("zone", []))
            zm = re.search(r"(Hubballi|Belagavi|Kalaburagi)", z)
            if zm:
                zone_lines.append((n, zm.group(1)))
            if i > hi:
                rows.append((n, cols))

    def nearest(lines, at):
        if not lines:
            return None
        best = sorted(lines, key=lambda x: abs(x[0] - at))
        if len(best) > 1 and abs(best[0][0] - at) == abs(best[1][0] - at) and best[0][1] != best[1][1]:
            return None
        return best[0][1]

    circles, divisions, subs = [], [], []
    for at, cols in rows:
        name = lambda k: clean(" ".join(t for t in cols.get(k, []) if not MOB.match(t) and t != "-" and not t.isdigit()))
        mobs = lambda *ks: [t.rstrip(",-") for k in ks for t in cols.get(k, []) if MOB.match(t)]
        ci = name("circle")
        if ci and mobs("see", "circle"):
            circles.append((at, ci, mobs("see", "circle")))
        dv = name("division")
        if dv:
            divisions.append([at, dv, mobs("eee"), mobs("aee")])
        elif (mobs("eee") or mobs("aee")) and divisions and at - divisions[-1][0] <= 1:
            divisions[-1][2] += mobs("eee")
            divisions[-1][3] += mobs("aee")
        elif mobs("eee") or mobs("aee"):
            divisions.append([at, None, mobs("eee"), mobs("aee")])     # name on the next line (Mudhol)
        sd = name("subdivision")
        if sd:
            subs.append((at, sd, mobs("subaee")))
    # a division whose name came a line after its phones
    named = []
    for d in divisions:
        if d[1] is None:
            continue
        named.append(d)
    for d in divisions:
        if d[1] is None:
            nxt = next((x for x in named if 0 < x[0] - d[0] <= 2), None)
            if nxt:
                nxt[2] = d[2] + nxt[2]
                nxt[3] = d[3] + nxt[3]
    dl = sorted(named)
    sub_div = agree([at for at, _, _ in subs], [d[0] for d in dl])
    div_at = [dl[j][0] for j in range(len(dl))]
    div_circle = agree(div_at, [at for at, _, _ in circles])
    czone = {}
    for at, ci, ph in circles:
        czone[ci] = nearest(zone_lines, at)
        out.add(f"circle:{ci}", "circle", ci, post="Superintending Engineer (Ele), O&M Circle", phone_=phone(*ph),
                parents={"zone": czone[ci]})
    dpar = []
    for j, (at, dv, eee, aee) in enumerate(dl):
        ci = circles[div_circle[j]][1] if div_circle and div_circle[j] is not None else None
        par = {"zone": czone.get(ci), "circle": ci}
        dpar.append(par)
        if eee:
            out.add(f"division:{dv}:eee", "division", dv, post="Executive Engineer (Ele), O&M Division", phone_=phone(*eee), parents=par)
        if aee:
            out.add(f"division:{dv}:aee", "division", dv, post="Assistant Executive Engineer, Division Office", phone_=phone(*aee),
                    parents=par)
    for (at, sd, ph), j in zip(subs, sub_div):
        par = {**dpar[j], "division": dl[j][1]} if j is not None else {}
        out.add(f"subdivision:{sd}", "subdivision", sd, post="Assistant Executive Engineer (Ele), O&M Sub-Division",
                phone_=phone(*ph), parents=par)
    return out.recs


def fetch(p, get):
    kind = p["file"]
    url = p.get("url") or URLS[kind]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_hescom", kind, r.content, "pdf")]
    try:
        pages = pdf_pages(r.content)
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    recs = parse_sections(pages, url) if kind == "sections" else parse_officers(pages, url)
    return recs, files, "" if recs else "no rows"
