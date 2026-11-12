"""Haryana: State Election Commission gazette notifications of elected Mayors/Presidents and Members (secharyana.gov.in).

Two kinds of file, both on cdnbbsr.s3waas.gov.in:
- 2025 general election (poll 02.03.2025, Panipat 09.03.2025): Word-made gazettes, a Hindi half in the Kruti Dev legacy font
  and an English half with a clean text layer. Only the English half is read (pdftotext -layout; columns from the English
  header line "Sr. District Name of ... W. No ...").
- 2026 general election and bye-elections (poll 10.05.2026): scans of a ruled table. The table lines are found in the page
  image and erased, Tesseract reads the page once (word boxes), and every word goes to the cell between the lines around it.
  Only the English pages are queued (the Hindi copy follows on later pages).
One queue item = one PDF and a page range (payload first, last; mode "text" or "ocr"). Record id
councillor:HR:<body slug>:<ward no or "chair">.

The grid reader (render, grid, words, table) is also used by cforms/dl.py.
"""
import concurrent.futures
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

METHOD = "pdf text (pdftotext -layout) or ocr tesseract (ruled grid, one image per column), by payload mode"     # source trail (provenance.py): how this reader reads its sources

BIN = bytes(0 if i < 145 else 255 for i in range(256))
LINE = bytes(1 if i < 205 else 0 for i in range(256))    # ruled lines are thin and light grey in these scans
OFFICE_CHAIR = re.compile(r"may|pres|chair", re.I)
HEAD_WORDS = re.compile(r"District|Category|Political|Candidate|Husband|Office|Ward\s*Name|Reservation|Affiliation", re.I)
BODY_SUFFIX = {"Corporation": "Municipal Corporation", "Council": "Municipal Council", "Committee": "Municipal Committee"}


def tools(langs="tesseract-ocr-hin"):
    """Tesseract (eng + hin) and poppler; installs them on a GitHub runner (sudo without password)."""
    have = shutil.which("tesseract") and shutil.which("pdftoppm")
    if have:
        got = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout.split()
        if "hin" in got and "eng" in got:
            return True
    cmd = f"sudo -n apt-get update -q && sudo -n apt-get install -y -q tesseract-ocr tesseract-ocr-eng {langs} poppler-utils"
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0 and bool(shutil.which("tesseract"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def clean(s):
    s = " ".join((s or "").replace("|", " ").split())
    return s.strip(" .,:;-_—–'\"‘’*")


# ---------------------------------------------------------------- grid reader (scans of ruled tables)

def render(pdf, page, tmp, dpi=300):
    base = os.path.join(tmp, f"g{page}")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True)
    return base + ".pgm"


def read_pgm(path):
    raw = open(path, "rb").read()
    toks, i = [], 0
    while len(toks) < 4:                      # P5 width height maxval, comments allowed
        while raw[i:i + 1].isspace():
            i += 1
        if raw[i:i + 1] == b"#":
            i = raw.index(b"\n", i) + 1
            continue
        j = i
        while not raw[j:j + 1].isspace():
            j += 1
        toks.append(raw[i:j])
        i = j
    w, h = int(toks[1]), int(toks[2])
    return w, h, bytearray(raw[i + 1:i + 1 + w * h])


def write_pgm(path, w, h, data):
    with open(path, "wb") as f:
        f.write(b"P5\n%d %d\n255\n" % (w, h))
        f.write(data)


def _long(bits, minrun):
    """Dark pixels in runs of at least minrun (bits: 0/1 bytes)."""
    return sum(len(r) for r in bits.split(b"\x00") if len(r) >= minrun)


def _groups(idx, gap=4):
    out = []
    for i in idx:
        if out and i - out[-1][1] <= gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def _pool(rows):
    """OR of several 0/1 rows of the same length (tolerates a slight skew of the scan)."""
    acc = 0
    for r in rows:
        acc |= int.from_bytes(r, "big")
    return acc.to_bytes(len(rows[0]), "big")


def lean(bits, w, h, bands=10):
    """Lean of the table's vertical lines (dx/dy). Scans and photocopies are often sheared, not rotated: the vertical lines
    lean while the horizontal ones stay level. Line pieces are found in horizontal bands and followed from band to band."""
    cols = [bytes(bits[x::w]) for x in range(w)]
    bh = h // bands
    peaks = []
    for i in range(bands):
        y0 = i * bh
        cnt = [c[y0:y0 + bh].count(1) for c in cols]
        xs = [x for x in range(1, w - 1) if max(cnt[x - 1:x + 2]) >= 0.6 * bh]
        peaks.append([(g0 + g1) / 2 for g0, g1 in _groups(xs)])
    chains = []
    for i, ps in enumerate(peaks):
        free = list(ps)
        for c in chains:
            if c[-1][0] != i - 1 or not free:
                continue
            z = min(free, key=lambda v: abs(v - c[-1][1]))
            if abs(z - c[-1][1]) <= 12:
                c.append((i, z))
                free.remove(z)
        chains += [[(i, x)] for x in free]
    sl = sorted((c[-1][1] - c[0][1]) / ((c[-1][0] - c[0][0]) * bh) for c in chains if len(c) >= 3)
    return sl[len(sl) // 2] if sl else 0.0


def shear(data, w, h, slope, fill=255):
    """Shift each row sideways by slope * y: a vertical line drawn with that skew becomes vertical."""
    out = bytearray(len(data))
    pad = bytes([fill]) * w
    for y in range(h):
        sft = int(round(slope * (y - h / 2)))
        row = data[y * w:(y + 1) * w]
        if sft > 0:
            row = pad[:sft] + row[:w - sft]
        elif sft < 0:
            row = row[-sft:] + pad[:-sft]
        out[y * w:(y + 1) * w] = row
    return out


def grid(pgm, binarize=True, hcover=0.75, hrun=0.75):
    """Ruled table lines: (vertical x centres, horizontal y centres, x0, x1, image with lines erased). A horizontal line
    covers hcover of a column's width, with one unbroken piece of hrun of it (lower both for faint, broken rules)."""
    w, h, data = read_pgm(pgm)
    bits = data.translate(LINE)
    slope = -lean(bits, w, h)
    if abs(slope) > 0.0012:          # shear rows so the vertical lines stand straight (horizontal ones are found per column)
        data, bits = shear(data, w, h, slope), shear(bits, w, h, slope, fill=0)
    cols = [bytes(bits[x::w]) for x in range(w)]
    vx = [x for x in range(1, w - 1) if _long(_pool(cols[x - 1:x + 2]), 60) > 0.08 * h]
    vl = [(a + b) // 2 for a, b in _groups(vx)]
    if len(vl) < 3:
        return [], [], {}, (w, h), pgm
    x0, x1 = vl[0], vl[-1]
    ext = []
    for x in vl:
        runs = [m.span() for m in re.finditer(rb"\x01{60,}", _pool(cols[x - 2:x + 3]))]
        ext.append((runs[0][0], runs[-1][1]))
    top, bottom = min(e[0] for e in ext), max(e[1] for e in ext)
    # horizontal lines, column by column (a slight skew of the scan stays small within one column; merged cells have none)
    ncol = len(vl) - 1
    found = []                                   # (y, column)
    for i in range(ncol):
        a, b = vl[i] + 8, vl[i + 1] - 8
        if b - a < 20:
            continue
        need, run = max(40, int(hcover * (b - a))), max(40, int(hrun * (b - a)))
        ys = []
        for y in range(max(0, top - 20), h - 3):     # not limited at the bottom: lines fade in some scans
            r = _pool([bits[(y + k) * w + a:(y + k) * w + b] for k in range(3)])
            if r.count(1) >= need and max(map(len, r.split(b"\x00"))) >= run:
                ys.append(y)
        found += [((g0 + g1) // 2 + 1, i, g0, g1) for g0, g1 in _groups(ys)]
    found.sort()
    clusters = []
    for f in found:
        if clusters and f[0] - clusters[-1][-1][0] <= 14:
            clusters[-1].append(f)
        else:
            clusters.append([f])
    hl, crosses = [], {}
    for c in clusters:
        cs = {f[1] for f in c}
        if len(cs) < max(2, 0.4 * ncol):
            continue
        y = sorted(f[0] for f in c)[len(c) // 2]
        hl.append(y)
        crosses[y] = [i in cs for i in range(ncol)]
        for _, i, g0, g1 in c:                   # erase the line in that column
            for yy in range(max(0, g0 - 2), min(h, g1 + 6)):
                data[yy * w + vl[i] - 2:yy * w + vl[i + 1] + 3] = bytes([255]) * (vl[i + 1] - vl[i] + 5)
    for g0, g1 in _groups(vx):
        for y in range(h):
            o = y * w
            data[o + g0 - 3:o + g1 + 4] = bytes([255]) * (g1 - g0 + 7)
    out = pgm[:-4] + "-clean.pgm"
    write_pgm(out, w, h, data.translate(BIN) if binarize else data)   # scans: black on white drops the grey background
    return vl, hl, crosses, (w, h), out


def words(png, lang, psm="6"):
    r = subprocess.run(["tesseract", png, "-", "-l", lang, "--psm", psm, "tsv"], capture_output=True, text=True)
    out = []
    for ln in r.stdout.splitlines()[1:]:
        f = ln.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        x, y, ww, hh = map(int, f[6:10])
        out.append((x + ww / 2, y + hh / 2, f[11].strip(), float(f[10])))
    return out


def table(pdf, page, tmp, lang, psm="6", binarize=True):
    """One scanned page -> list of rows; row = {"cells": [text per column], "new": [line above crosses column?]}."""
    return table_pgm(render(pdf, page, tmp), lang, psm, binarize)


def table_pgm(pgm, lang, psm="6", binarize=True, meta=None, **grid_kw):
    """table() on a page image that is already rendered (forms/blo2_ocr.py straightens it first). meta (a dict), when
    given, gets the lines ("vl", "hl") and each column's image ("strips": [(path, x offset, y offset)]) for a second reading."""
    vl, hl, crosses, _, clean_pgm = grid(pgm, binarize, **grid_kw)
    if len(vl) < 3 or len(hl) < 2:
        return []
    ncol = len(vl) - 1
    w, h, data = read_pgm(clean_pgm)
    y0, y1, pad = hl[0], hl[-1], 20

    def strip(i):
        """One column of the table as its own image: Tesseract reads a column far better than the whole ruled page."""
        a, b = vl[i] + 5, vl[i + 1] - 4
        cw = b - a + 2 * pad
        blank = bytes([255]) * cw
        img = bytearray(blank * pad)
        for y in range(y0, y1):
            img += bytes([255]) * pad + data[y * w + a:y * w + b] + bytes([255]) * pad
        img += blank * pad
        path = f"{clean_pgm[:-4]}-c{i}.pgm"
        write_pgm(path, cw, len(img) // cw, img)
        return [(cx - pad + a, cy - pad + y0, t, conf) for cx, cy, t, conf in words(path, lang, psm)]

    with concurrent.futures.ThreadPoolExecutor(3) as ex:
        ws = [x for col in ex.map(strip, range(ncol)) for x in col]
    if meta is not None:
        meta.update(vl=vl, hl=hl, strips=[(f"{clean_pgm[:-4]}-c{i}.pgm", vl[i] + 5 - pad, y0 - pad) for i in range(ncol)])
    # "row": the row's place in the ruled grid (1-based, from the top rule), for the source trail
    rows = [{"cells": [[] for _ in range(ncol)], "new": crosses[a], "y": a, "row": i} for i, a in enumerate(hl[:-1], 1)]
    for cx, cy, t, conf in ws:
        if conf < 20 or not (vl[0] < cx < vl[-1] and hl[0] < cy < hl[-1]):
            continue
        ri = max(i for i, a in enumerate(hl[:-1]) if a <= cy)
        ci = max(i for i, a in enumerate(vl[:-1]) if a <= cx)
        rows[ri]["cells"][ci].append((cy, cx, t))
        rows[ri].setdefault("conf", [None] * ncol)
        c0 = rows[ri]["conf"][ci]
        rows[ri]["conf"][ci] = conf if c0 is None else min(c0, conf)     # lowest word confidence in the cell
    for r in rows:
        r.setdefault("conf", [None] * ncol)
        cells = []
        for c in r["cells"]:
            c.sort()
            lines, cur, last = [], [], None    # words to lines by y, each line left to right
            for cy, cx, t in c:
                if last is not None and cy - last > 18:
                    lines.append(cur)
                    cur = []
                cur.append((cx, t))
                last = cy
            if cur:
                lines.append(cur)
            cells.append(" ".join(t for ln in lines for _, t in sorted(ln)))
        r["cells"] = cells
    return rows


# ---------------------------------------------------------------- Haryana

COLS = ["sr", "district", "body", "ward", "name", "father", "office", "category", "party"]


def fix_ward(s):
    s = s.replace("O", "0").replace("o", "0").replace("I", "1").replace("l", "1").replace("|", "1").replace("S", "5")
    m = re.search(r"\d+", s)
    return m.group(0).lstrip("0") or "0" if m else ""


def fix_party(s):
    s = clean(s)
    if re.search(r"Bh\w*\s*J\w*|Janat|Bharat", s, re.I):
        return "Bharatiya Janata Party"
    if re.search(r"Cong|Nation\w* C", s, re.I):
        return "Indian National Congress"
    if re.search(r"Indep|ndep|ndcp", s, re.I):
        return "Independent"
    if re.search(r"Aam Aadmi", s, re.I):
        return "Aam Aadmi Party"
    if re.search(r"Lok\s*Dal|INLD", s, re.I):
        return "Indian National Lok Dal"
    if re.search(r"Bahujan|BSP", s, re.I):
        return "Bahujan Samaj Party"
    return s


def fix_category(s):
    s = clean(s)
    t = re.sub(r"[^a-z]", "", s.lower())
    women = "women" in t or "wom" in t or "wen" in t
    if "backward" in t or "class" in t or "bc" == t[:2]:
        m = re.search(r"[‘'`\"]?\s*([AB])\s*[’'`\"]", s) or re.search(r"Class\W*([AB])\b", s)
        base = f"Backward Class '{m.group(1)}'" if m else "Backward Class"
        return base + (" (Women)" if women and "(" in s or women and "class" in t and t.endswith(("women", "wen"))
                       else "")
    if "schedul" in t or "caste" in t:
        return "Scheduled Caste" + (" (Women)" if women else "")
    if women:
        return "Women"
    if "unres" in t or "reser" in t or "served" in t:
        return "Unreserved"
    return s


def record(p, st, x, page, read):
    body = clean(x["body"])
    btype = x.get("body_type") or p.get("body_type") or ""
    full = body if not body or re.search(r"Corporation|Council|Committee", body) else f"{body} {btype}".strip()
    office = clean(x.get("office", ""))
    chair = bool(OFFICE_CHAIR.search(office)) or not x["ward"]
    if chair:
        position = "Mayor" if btype == "Municipal Corporation" else "President"
    else:
        position = "Member"
    ward = "chair" if chair else x["ward"]
    pos = x.get("_pos")
    d = {"type": "councillor", "state": "HR", "body": full, "body_type": btype, "district": clean(x.get("district")),
         "ward_no": ward, "name": clean(x["name"]).lstrip("* ").strip(), "father_or_husband": clean(x.get("father")),
         "party": fix_party(x.get("party", "")), "reservation": fix_category(x.get("category", "")), "position": position,
         "unopposed": True if "*" in (x["name"] or "") else None, "election": p.get("election"), "url": p["url"],
         "page": page, "read": read,
         # source trail: where on the page (text: line; scan: grid row, its top y in pixels at 300 dpi, lowest word confidence)
         "src_pos": {"page": page, **pos} if pos else None,
         "method": {"ocr": "ocr tesseract (ruled grid, one image per column)", "text layer": "pdf text (pdftotext -layout)"}.get(read)}
    rid = f"councillor:HR:{slug(full)}:{ward}"
    if f"{slug(full)}:{ward}" in p.get("replaced", []):     # seat filled again in a later bye-election (which holds the id)
        rid += f"-{(p.get('election') or '')[8:12]}"
        d["status"] = "seat filled again in a later bye-election"
    return rid, {k: v for k, v in d.items() if v not in (None, "")}


# ---- 2025: English text layer

def header_cols(line):
    """Column starts from the English header line (Sr. District Name of W. Name of Elected Father's/ Name of Office ...)."""
    pos = {}
    m = re.search(r"\bSr\.?", line)
    pos["sr"] = m.start() if m else 0
    for key, rx in (("district", r"District"), ("ward", r"\bW\.?\s*No|\bW\.\s"), ("father", r"Father"),
                    ("category", r"Category"), ("party", r"Political")):
        m = re.search(rx, line)
        if not m:
            return None
        pos[key] = m.start()
    names = [m.start() for m in re.finditer(r"Name\s+[Oo]f", line)]
    # Name of (body) < W. < Name of Elected < Father < Name of Office
    pos["body"] = next((n for n in names if n < pos["ward"]), pos["district"] + 10)
    pos["name"] = next((n for n in names if pos["ward"] < n < pos["father"]), pos["ward"] + 5)
    pos["office"] = next((n for n in names if pos["father"] < n < pos["category"]), pos["father"] + 15)
    return [pos[c] for c in COLS]


def split_cols(line, starts):
    cells = [""] * len(starts)
    for m in re.finditer(r"\S+", line):
        s = m.start()
        ci = max([i for i, a in enumerate(starts) if a - 3 <= s] or [0])
        cells[ci] = (cells[ci] + " " + m.group(0)).strip()
    return cells


def text_rows(text):
    """English half of a 2025 gazette page -> rows (dicts with COLS keys)."""
    rows, starts, cur = [], None, None
    for li, ln in enumerate(text.splitlines(), 1):
        if re.search(r"ftyk|Ukxj|Ø-", ln):          # Kruti Dev (Hindi) header: Hindi half
            starts, cur = None, None
            continue
        if re.match(r"\s*Sr\.?\s", ln) and "District" in ln:
            starts, cur = header_cols(ln), None
            continue
        if starts is None:
            continue
        if not ln.strip() or re.search(r"HARYANA GOVT|Elected unopposed|State Election Commissioner|unopposed", ln, re.I):
            cur = None
            continue
        c = dict(zip(COLS, split_cols(ln, starts)))
        if re.fullmatch(r"(Member|Mayor|President|Chairperson)\b.*", c["office"]) or re.search(r"\b(Member|Mayor|President)\b",
                                                                                                c["office"]):
            w = c["ward"].strip().rstrip(".")
            if not (re.fullmatch(r"\d+", w) or re.fullmatch(r"-+", w) or not w and OFFICE_CHAIR.search(c["office"])):
                # ward and name sometimes share a chunk: "12 Suman Bala"
                m = re.match(r"(\d+|-{2,})\.?\s+(.*)", (w + " " + c["name"]).strip())
                if not m:
                    continue
                w, c["name"] = m.group(1), m.group(2)
            c["ward"] = w if w.isdigit() else ""
            c["_pos"] = {"line": li, "line_text": ln}       # the row's first line in this page's text
            cur = c
            rows.append(c)
        elif cur is not None:
            for k in ("district", "body", "name", "father", "category", "party"):
                if c[k]:
                    cur[k] = (cur[k] + " " + c[k]).strip()
    return rows


def body_fill(rows, state):
    """District/body are printed only on a body's first row: carry them down."""
    for r in rows:
        if r.get("body"):
            state["body"], state["district"] = r["body"], r.get("district") or state.get("district", "")
        else:
            r["body"], r["district"] = state.get("body", ""), state.get("district", "")
    return rows


# ---- 2026: scans

def row_pos(r):
    """src_pos of one grid row (table_pgm): grid row, top y (pixels), lowest word confidence over its cells."""
    conf = [c for c in r.get("conf") or [] if c is not None]
    return {k: v for k, v in (("row", r.get("row")), ("y", r.get("y")), ("conf", min(conf) if conf else None)) if v is not None}


def scan_rows(trows, cols, state, sequential=True):
    """Grid rows -> member rows; district and body cells span several rows (no line crosses them)."""
    out = []
    ci = {c: i for i, c in enumerate(cols)}
    for r in trows:
        c = dict(zip(cols, r["cells"]))
        if len(r["cells"]) != len(cols) or HEAD_WORDS.search(" ".join(r["cells"])):
            continue
        ward = c.get("ward", "")
        office = c.get("office", "")
        is_member = re.search(r"m[ec]m|mbe|emb|ember|men", office, re.I)
        is_chair = bool(OFFICE_CHAIR.search(office) or re.fullmatch(r"[-–—_.\s]{2,}", ward or ""))
        if not (is_member or is_chair or re.search(r"\d", ward or "")) or not clean(c.get("name")):
            continue
        new = r["new"][ci["body"]] if "body" in ci and ci["body"] < len(r["new"]) else False
        if new or not state.get("body"):
            state["body"], state["district"], state["last"] = "", "", 0
        if "body" in ci and clean(c.get("body")):
            state["body"] = clean((state["body"] + " " + c["body"]) if not new else c["body"])
            if new:
                state["body"] = clean(c["body"])
        if "district" in ci and clean(c.get("district")):
            state["district"] = clean(c["district"]) if new or not state["district"] else state["district"]
        w = "" if is_chair and not is_member else fix_ward(ward)
        if not is_chair or is_member:
            nxt = str(int(state.get("last") or 0) + 1)
            if sequential or not w:       # general elections list every ward in order: OCR slips (7 for 11, l for 1) fixed
                w = nxt
            state["last"] = w
        btype = None
        if "body2" in ci:          # bye-election list: one column for councils, one for committees ("--" in the other)
            b1, b2 = clean(c.get("body")), clean(c.get("body2"))
            b1, b2 = ("" if re.fullmatch(r"[-–—_.\s]*", b1) else b1), ("" if re.fullmatch(r"[-–—_.\s]*", b2) else b2)
            state["body"], btype = (b1, "Municipal Council") if b1 else (b2, "Municipal Committee")
        x = {"district": state["district"], "body": state["body"], "ward": w, "body_type": btype, "name": c.get("name", ""),
             "father": c.get("father", ""), "office": "Mayor" if is_chair and not is_member else office,
             "category": c.get("category", ""), "party": c.get("party", ""), "_pos": row_pos(r)}
        out.append(x)
    return out


def fetch(p, get):
    mode = p.get("mode", "text")
    if mode == "ocr" and not tools():
        return [], [], "tesseract not available"
    if not shutil.which("pdftotext") and not tools():
        return [], [], "poppler not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    first, last = int(p.get("first", 1)), int(p.get("last", 1))
    files = [(f"councillors/HR/{key}.pdf", r.content, "application/pdf")] if first == int(p.get("file_first", 1)) else []
    recs, seen = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(r.content)
        pages = list(range(first, last + 1))
        state = {}
        if mode == "text":
            for pg in pages:
                t = subprocess.run(["pdftotext", "-layout", "-f", str(pg), "-l", str(pg), pdf, "-"], capture_output=True,
                                   text=True).stdout
                for x in body_fill(text_rows(t), state):
                    recs.append(record(p, state, x, pg, "text layer"))
        else:
            with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), (os.cpu_count() or 2) // 2))) as ex:
                tabs = dict(zip(pages, ex.map(lambda pg: table(pdf, pg, tmp, p.get("lang", "eng")), pages)))
            for pg in pages:
                for x in scan_rows(tabs[pg], p.get("cols", COLS), state, p.get("sequential", True)):
                    recs.append(record(p, state, x, pg, "ocr"))
    out = []
    for rid, d in recs:
        if not d.get("body") or not d.get("name"):
            continue
        n = seen[rid] = seen.get(rid, 0) + 1
        out.append((rid + (f"-{n}" if n > 1 else ""), d))
    return out, files, "" if out else "no members read"
