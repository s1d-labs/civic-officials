"""Chhattisgarh municipal general and bye-elections of June 2026 (SEC page cgsec.gov.in/hin_june26AamUpChunavNagarPalika.html,
"आम/उप निर्वाचन जून 2026", linked from hin_vigat_chunav_np.html):
- Notification2026/election/निर्वाचित अध्यक्ष की जानकारी.pdf (1 page): elected chairpersons, general election of 4 new nagar
  panchayats (Bamhanidih, Shivnandanpur, Palari of Balod, Ghumka) and the bye-election of the Sahaspur-Lohara chairperson.
  Columns: serial | district | body | elected chairperson | party.
- Notification2026/election/निर्वाचित पार्षदों की जानकारी.pdf (3 pages): elected councillors, 60 wards of the 4 new bodies
  (15 each) and, on page 3, the bye-elections of 11 wards in 10 bodies (Jagdalpur 16, Bilaspur 29, Dipka 15, Jashpur Nagar 8
  and 14, Kirodimal Nagar 6, Sargaon 7, Farasgaon 1 and 12, Charama 13, Pakhanjur 9).
  Columns: serial | district | body | ward no | ward name | elected councillor | party.
Both are Microsoft Print To PDF files with NO text layer (the letters are drawn as outlines), so every cell is read by
Tesseract (hin, cforms/cw_cg.ocr_cells) on GitHub runners. The table grid comes from the drawn borders: a row band lies between
two borders that cross the right-hand columns (ward / name / party); the Devanagari head strokes are too short to count. The
district and body cells of a bye-election body with two wards are merged over both rows: such a cell is cut from the top of
its merged span and read once. A band without the full set of column borders is a title ("नगरपालिका उप निर्वाचन 2026"); a title
after data rows starts the bye-election part.
The body of each row comes from the payload map ("bodies": {"general" | "bye": [[first row, last row, body, LGD code, district,
body slug of the 2025 records], ...]}, made from the rendered pages and checked by eye), counted by data row, so an OCR slip in a
serial or a town name does not move a member. A bye-election winner names the 2025 record of the same seat ("replaces",
councillor:CG:2025:<slug>:<ward> of cforms/cw_cg.py / :chair of cforms/cw_cg_heads.py), which the site can then show as stale.
One queue item = one file. The site answers only from India (first item through a proxy, or a stored copy).
Record id councillor:CG:2026:<slug>:<ward> or :chair.
"""
import hashlib
import os
import re
import tempfile

from cforms import cw_cg, gj
from cforms.tn import mark_stored, stored

METHOD = "ocr tesseract hin (every cell; no text layer), cell grid from the drawn borders"

BASE = "https://cgsec.gov.in/Notification2026/election/"
HEADS_URL = BASE + "%E0%A4%A8%E0%A4%BF%E0%A4%B0%E0%A5%8D%E0%A4%B5%E0%A4%BE%E0%A4%9A%E0%A4%BF%E0%A4%A4%20%E0%A4%85%E0%A4%A7%E0%A5%8D%E0%A4%AF%E0%A4%95%E0%A5%8D%E0%A4%B7%20%E0%A4%95%E0%A5%80%20%E0%A4%9C%E0%A4%BE%E0%A4%A8%E0%A4%95%E0%A4%BE%E0%A4%B0%E0%A5%80.pdf"
MEMBERS_URL = BASE + "%E0%A4%A8%E0%A4%BF%E0%A4%B0%E0%A5%8D%E0%A4%B5%E0%A4%BE%E0%A4%9A%E0%A4%BF%E0%A4%A4%20%E0%A4%AA%E0%A4%BE%E0%A4%B0%E0%A5%8D%E0%A4%B7%E0%A4%A6%E0%A5%8B%E0%A4%82%20%E0%A4%95%E0%A5%80%20%E0%A4%9C%E0%A4%BE%E0%A4%A8%E0%A4%95%E0%A4%BE%E0%A4%B0%E0%A5%80.pdf"
GENERAL = "Chhattisgarh municipal general election June 2026 (SEC list)"
BYE = "Chhattisgarh municipal bye-election June 2026 (SEC list)"
COLS = {5: ("serial", "district", "body", "name", "party"),
        7: ("serial", "district", "body", "ward_no", "ward_name", "name", "party")}


def coverage(segs, x0, x1):
    """Length of [x0, x1] that the horizontal segments (y, a, b) cover."""
    iv = sorted((max(a, x0), min(b, x1)) for _, a, b in segs if min(b, x1) > max(a, x0))
    cov, cur = 0, None
    for a, b in iv:
        if cur and a <= cur[1] + 1:
            cur = (cur[0], max(cur[1], b))
        else:
            cov += cur[1] - cur[0] if cur else 0
            cur = (a, b)
    return cov + (cur[1] - cur[0] if cur else 0)


def by_y(hs):
    out = {}
    for h in hs:
        out.setdefault(round(h[0] * 2) / 2, []).append(h)
    ys = []
    for y in sorted(out):                       # borders drawn twice, 0.5 pt apart: one
        if ys and y - ys[-1][0] <= 1.5:
            ys[-1][1].extend(out[y])
        else:
            ys.append((y, list(out[y])))
    return ys


def verticals_at(vs, y):
    xs = []
    for x in sorted(v[0] for v in vs if v[2] - v[1] > 8 and v[1] - 1 <= y <= v[2] + 1):
        if not xs or x - xs[-1] > 3:
            xs.append(x)
    return xs


def grid(hs, vs, ncols):
    """Bands of one page: [{"y0", "y1", "cols": {1..ncols: (x0, x1)} or None (title band), "top": {c: border at y0 crosses c}}]."""
    ys = by_y(hs)
    # the column borders: the most common set of ncols + 1 verticals over all border gaps
    sets = {}
    for (a, _), (b, _) in zip(ys, ys[1:]):
        xs = verticals_at(vs, (a + b) / 2)
        if len(xs) == ncols + 1:
            k = tuple(round(x) for x in xs)
            sets[k] = sets.get(k, 0) + 1
    if not sets:
        return []
    xs = max(sets, key=sets.get)
    cols = {i + 1: (xs[i], xs[i + 1]) for i in range(ncols)}
    rx0, rx1 = cols[4][0], cols[ncols][1]
    borders = [(y, segs) for y, segs in ys if coverage(segs, rx0, rx1) >= 0.9 * (rx1 - rx0)
               or coverage(segs, cols[1][0], cols[ncols][1]) >= 0.9 * (cols[ncols][1] - cols[1][0])]
    out = []
    for (a, sa), (b, _) in zip(borders, borders[1:]):
        if b - a < 8:
            continue
        here = verticals_at(vs, (a + b) / 2)
        data = len(here) >= ncols + 1 and all(any(abs(x - c[0]) < 3 for x in here) for c in cols.values())
        out.append({"y0": a, "y1": b, "cols": cols if data else None,
                    "top": {c: coverage(sa, *cols[c]) >= 0.8 * (cols[c][1] - cols[c][0]) for c in cols}})
    # the column-number row ("1 2 3 ...") is lower than the data rows; it and a header row with all column borders just above
    # it are not data
    hts = sorted(x["y1"] - x["y0"] for x in out if x["cols"])
    if hts:
        med = hts[len(hts) // 2]
        for i, x in enumerate(out):
            if x["cols"] and x["y1"] - x["y0"] < 0.75 * med:
                x["cols"] = None
                if i and out[i - 1]["cols"] and out[i - 1]["y1"] == x["y0"]:
                    out[i - 1]["cols"] = None
                    out[i - 1]["header"] = True
                x["header"] = True
    return out


def page_cells(bands, ncols):
    """Data rows of a page with the box of each cell (merged cells of columns 1-3 span from the top of their merge) and the
    title bands between them: [("title", band) | ("row", band, {c: box})]."""
    out, span_top = [], {}
    for b in bands:
        if b.get("header"):
            continue
        if b["cols"] is None:
            out.append(("title", b))
            span_top = {}
            continue
        boxes = {}
        for c, (x0, x1) in b["cols"].items():
            if c <= 3 and not b["top"][c] and c in span_top:
                y0 = span_top[c]
            else:
                y0 = b["y0"]
                span_top[c] = y0
            boxes[c] = (x0, y0, x1, b["y1"])
        out.append(("row", b, boxes))
    # a merged cell's box ends at the bottom of its last row
    rows = [x for x in out if x[0] == "row"]
    for c in (1, 2, 3):
        for i, r in enumerate(rows):
            j = i
            while j + 1 < len(rows) and rows[j + 1][2][c][1] == r[2][c][1]:
                j += 1
            x0, y0, x1, _ = r[2][c]
            r[2][c] = (x0, y0, x1, rows[j][2][c][3])
    return out


def lookup(bodies, part, n):
    for first, last, *rest in (bodies or {}).get(part, []):
        if int(first) <= n <= int(last):
            return rest
    return None


def parse(pdf, p, ocr=None):
    """Records of one file. ocr(pdf, page, boxes) -> texts (default: Tesseract via cw_cg.ocr_cells)."""
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    heads = p.get("post") == "chair"
    ncols = 5 if heads else 7
    names = COLS[ncols]
    part, seen_data, n = p.get("first_part", "general"), False, {"general": 0, "bye": 0}     # first_part: a cut file (tests)
    recs = []
    for pg in range(1, len(reader.pages) + 1):
        hs, vs = gj.drawn_lines(reader, pg - 1)
        cells = page_cells(grid(hs, vs, ncols), ncols)
        boxes, where = [], []
        for x in cells:
            if x[0] == "row":
                for c in range(1, ncols + 1):
                    where.append((id(x), c))
                    boxes.append(x[2][c])
        if ocr:
            texts = ocr(pdf, pg, boxes)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                texts = cw_cg.ocr_cells(pdf, pg, boxes, tmp)
        got = {}
        for (k, c), t in zip(where, texts):
            got.setdefault(k, {})[names[c - 1]] = t
        for ri, x in enumerate(cells, 1):
            if x[0] == "title":
                if seen_data:
                    part = "bye"
                continue
            seen_data = True
            n[part] += 1
            t = got.get(id(x), {})
            b = lookup(p.get("bodies"), part, n[part]) or [None, None, None, None]
            body, lgd, district, slug = (list(b) + [None] * 4)[:4]
            slug = slug or (cw_cg.slug_of(body) if body else f"row-{part}-{n[part]}")
            ward = cw_cg.num(t.get("ward_no")) if not heads else "chair"
            if not heads and not ward:
                ward = f"row{n[part]}"
            name = cw_cg.fix_name(t.get("name", ""))
            d = {"type": "councillor", "state": "CG", "body": body or t.get("body"), "body_ocr": t.get("body"),
                 "district": district, "district_ocr": t.get("district"), "lgd_code": lgd, "local_body_code": lgd,
                 "ward_no": ward, "ward_name": cw_cg.fix_name(t.get("ward_name", "")) if not heads else None, "name": name,
                 "position": "Chairperson" if heads else "Member", "position_local": "अध्यक्ष" if heads else "पार्षद",
                 "party": cw_cg.party_of(t.get("party", "")) or None, "party_ocr": t.get("party"),
                 "serial": n[part], "serial_ocr": t.get("serial"), "bye_election": part == "bye",
                 "elected_by": "voters (direct election)" if heads else None,
                 "election": BYE if part == "bye" else GENERAL, "url": p.get("url"), "page": pg,
                 "src_pos": {"page": pg, "band": ri, "part": part, "row_in_part": n[part],
                             "box_pt": [round(x[1]["cols"][1][0], 1), round(x[1]["y0"], 1),
                                        round(x[1]["cols"][ncols][1], 1), round(x[1]["y1"], 1)]}}
            if part == "bye" and slug and ward and not ward.startswith("row"):
                d["replaces"] = f"councillor:CG:2025:{slug}:{ward}"
            rid = f"councillor:CG:2026:{slug}:{ward}"
            recs.append((rid, {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def fetch(p, get):
    if not cw_cg.tools():
        return [], [], "tesseract not available"
    url = p.get("url") or (HEADS_URL if p.get("post") == "chair" else MEMBERS_URL)
    content = stored(p, get)
    from_bucket = content is not None
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    k = hashlib.sha1(url.encode()).hexdigest()[:12]
    files = [] if p.get("stored") else [(f"councillors/CG/{k}.pdf", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, {**p, "url": url})
    if from_bucket:
        mark_stored(recs, p, content, url)
    return recs, files, "" if recs else "no rows read"


def slug_ok(s):
    return bool(re.fullmatch(r"[a-z0-9-]+", s or ""))
