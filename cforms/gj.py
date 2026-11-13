"""Gujarat municipal results 2026 (sec.gujarat.gov.in, Gujarat Government Gazette Extraordinary Part IV-C, 28 Apr 2026), read by OCR.

Two index pages list the files: result-muncipality-2026.htm (15 corporations, images/<city>-corpo.pdf) and
result-nagarpalika-2026.htm (31 district files of nagarpalikas, images/pdf/<town>-np-doc.pdf). Each file holds one notice per
returning officer: a title "<body> (મહા)નગરપાલિકાની સામાન્ય ચૂંટણી-૨૦૨૬" and a ruled table with six numbered columns
(serial, ward, seat number and category, name, address, party).
The text layer keeps the layout but maps some Gujarati glyphs to wrong letters (લ comes out as િ, ૨ as ર ...). So the table
grid comes from the drawn cell borders (PDF vector paths), the ward, seat, category and party from the text layer (a small,
fixed vocabulary that survives the wrong letters), and the name, the address and the body title from Tesseract (guj) on each
cell, rendered alone at 300 dpi. One Tesseract run per page reads all crops of that page.
One queue item = one PDF and a page range (payload first, last). The site answers only from India.
cforms/mh.py uses the grid and OCR helpers of this module.
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import provenance

METHOD = "ocr tesseract guj (name and address cells) + pdf text layer by drawn cell borders (pdftotext -bbox)"     # source trail (provenance.py): how this reader reads its sources

DIGITS = str.maketrans("૦૧૨૩૪૫૬૭૮૯०१२३४५६७८९", "01234567890123456789")
ORDINAL = (("પહે", 1), ("બીજ", 2), ("ત્રીજ", 3), ("રીજ", 3), ("ચોથ", 4), ("પાંચ", 5), ("પૂંચ", 5))
PARTY = ((r"કોં?ગ્રેસ|રાષ્ટ્રીય", "INC"), (r"આ[મિ] આદ[મિ]ી|આદમી", "AAP"), (r"અ[પ૫]ક્ષ", "Independent"),
         (r"બહુ[જિ]ન", "BSP"), (r"સમા[જિ]વાદી", "SP"), (r"ઓ[લિ] ઈ?ઇ?ન|મ[જિ][લિ]ી[સિ]|મ[જિ][લિ]િસ|ઇત્તેહાદ", "AIMIM"),
         (r"રાષ્ટ્રવાદી", "NCP"), (r"આરદવાસી|આદિવાસી", "Adivasi Sena Party"), (r"ભા[જિ]પ|ભારતીય", "BJP"))


def tools(lang="guj"):
    """Tesseract with the language pack and poppler; installs them on a GitHub runner (sudo without password)."""
    def ok():
        if not (shutil.which("tesseract") and shutil.which("pdftoppm") and shutil.which("pdftotext")):
            return False
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
        return lang in (r.stdout + r.stderr).split()
    if ok():
        return True
    cmd = f"sudo -n apt-get update -q && sudo -n apt-get install -y -q tesseract-ocr tesseract-ocr-{lang} poppler-utils"
    subprocess.run(cmd, shell=True, capture_output=True)
    return ok()


def norm(s):
    return " ".join((s or "").replace("‌", "").replace("‍", "").split())


# ---------------------------------------------------------------- drawn lines (PDF vector paths)

def _mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F]


def drawn_lines(reader, index):
    """Axis-aligned lines a page draws (stroked paths and thin filled boxes), in pdftotext's top-left coordinates:
    (horizontal [(y, x0, x1)], vertical [(x, y0, y1)])."""
    from pypdf.generic import ContentStream
    page = reader.pages[index]
    height = float(page.mediabox.top)
    hs, vs = [], []

    def tp(ctm, x, y):
        return ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5]

    def seg(p, q):
        (x0, y0), (x1, y1) = p, q
        if abs(y0 - y1) < 0.8 and abs(x1 - x0) > 2:
            hs.append((height - (y0 + y1) / 2, min(x0, x1), max(x0, x1)))
        elif abs(x0 - x1) < 0.8 and abs(y1 - y0) > 2:
            vs.append(((x0 + x1) / 2, height - max(y0, y1), height - min(y0, y1)))

    def box(pts, fill):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if fill:     # a thin filled box is a line; a wide one is shading, not a border
            if h < 2.5 and w > 2:
                hs.append((height - (min(ys) + max(ys)) / 2, min(xs), max(xs)))
            elif w < 2.5 and h > 2:
                vs.append(((min(xs) + max(xs)) / 2, height - max(ys), height - min(ys)))
        else:
            for i in range(4):
                seg(pts[i], pts[(i + 1) % 4])

    def walk(content, resources, ctm, depth):
        if depth > 4:
            return
        try:
            ops = ContentStream(content, reader).operations
        except Exception:
            return
        stack, path, cur, start = [], [], None, None
        for args, op in ops:
            if op == b"q":
                stack.append(ctm)
            elif op == b"Q":
                ctm = stack.pop() if stack else ctm
            elif op == b"cm":
                ctm = _mul([float(a) for a in args], ctm)
            elif op == b"re":
                x, y, w, h = (float(a) for a in args)
                path.append(("box", [tp(ctm, x, y), tp(ctm, x + w, y), tp(ctm, x + w, y + h), tp(ctm, x, y + h)]))
            elif op == b"m":
                cur = start = tp(ctm, float(args[0]), float(args[1]))
            elif op == b"l":
                p = tp(ctm, float(args[0]), float(args[1]))
                if cur is not None:
                    path.append(("seg", (cur, p)))
                cur = p
            elif op in (b"c", b"v", b"y"):
                cur = tp(ctm, float(args[-2]), float(args[-1]))
            elif op == b"h":
                if cur is not None and start is not None:
                    path.append(("seg", (cur, start)))
                cur = start
            elif op in (b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"):
                fill = op in (b"f", b"F", b"f*")
                for kind, v in path:
                    if kind == "box":
                        box(v, fill)
                    else:
                        seg(*v)
                path, cur = [], None
            elif op == b"n":
                path, cur = [], None
            elif op == b"Do" and resources is not None:
                try:
                    xo = resources["/XObject"][args[0]].get_object()
                except Exception:
                    continue
                if xo.get("/Subtype") == "/Form":
                    m = [float(a) for a in xo.get("/Matrix", [1, 0, 0, 1, 0, 0])]
                    walk(xo, xo.get("/Resources", resources), _mul(m, ctm), depth + 1)

    res = page.get("/Resources")
    walk(page.get_contents(), res.get_object() if res is not None else None, [1, 0, 0, 1, 0, 0], 0)
    return _merge(hs), _merge(vs)


def _merge(lines, tol=1.2, gap=2.5):
    """Joins pieces of one line (same position, touching ranges)."""
    out = []
    for pos, a, b in sorted(lines):
        for o in out:
            if abs(o[0] - pos) <= tol and a <= o[2] + gap and b >= o[1] - gap:
                o[1], o[2] = min(o[1], a), max(o[2], b)
                break
        else:
            out.append([pos, a, b])
    return [tuple(o) for o in out]


# ---------------------------------------------------------------- text layer words

WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


def words(pdf, page):
    """Text layer words [(x0, y0, x1, y1, text)] (pdftotext -bbox, top-left points)."""
    import html
    out = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page), pdf, "-"], capture_output=True,
                         text=True).stdout
    return [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in WORD.findall(out)]


def in_box(w, x0, y0, x1, y1):
    cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
    return x0 <= cx <= x1 and y0 <= cy <= y1


def box_text(ws, x0, y0, x1, y1):
    sel = sorted((w for w in ws if in_box(w, x0, y0, x1, y1)), key=lambda w: (round(w[1] / 4), w[0]))
    return norm(" ".join(w[4] for w in sel))


def grid_rows(hs, vs, ncols, name_col, ref=None):
    """Table rows found from the drawn borders alone: a band between two horizontal borders is a row of a table with ncols
    columns when exactly ncols + 1 vertical borders cross its middle. A band with more borders counts when it only splits the
    columns of the last such band (the column-number row above it, or `ref` from the page before): a seat column cut into
    number and category. Bands are cut only at borders that cross the name column (cells of other columns, such as the ward,
    span several rows). Returns ([(columns {1..ncols: (x0, x1)}, y0, y1)], ref for the next page)."""
    def xs_at(y):
        xs = []
        for x in sorted(v[0] for v in vs if v[1] - 1 <= y <= v[2] + 1):
            if not xs or x - xs[-1] > 3:
                xs.append(x)
        return xs
    ys = sorted({round(h[0], 1) for h in hs})
    out = []
    for a, b in zip(ys, ys[1:]):
        if b - a < 5:
            continue
        xs = xs_at((a + b) / 2)
        if len(xs) == ncols + 1:
            ref = xs
        elif not (ref and len(xs) > ncols + 1 and all(any(abs(r - x) < 3 for x in xs) for r in ref)):
            continue
        cols = {i + 1: (ref[i], ref[i + 1]) for i in range(ncols)}
        cx = sum(cols[name_col]) / 2
        if out and abs(out[-1][0][name_col][0] - cols[name_col][0]) < 3 and out[-1][2] >= a - 0.2 and \
                not any(abs(h[0] - a) < 0.6 and h[1] <= cx <= h[2] for h in hs):
            out[-1] = (out[-1][0], out[-1][1], b)       # no border across the name column: same row
        else:
            out.append((cols, a, b))
    return out, ref


def cell_of(col, hs, y, cols):
    """The band of a (possibly merged) cell in column `col` that holds height y: between the borders crossing that column."""
    x0, x1 = cols[col]
    cx = (x0 + x1) / 2
    ys = sorted({round(h[0], 1) for h in hs if h[1] <= cx <= h[2]})
    above = [v for v in ys if v <= y]
    below = [v for v in ys if v > y]
    return (above[-1] if above else y - 10, below[0] if below else y + 10)


# ---------------------------------------------------------------- OCR of crops

def ocr_boxes(pdf, page, boxes, tmp, lang, dpi=300, psm=6):
    """Text of each box [(x0, y0, x1, y1)] in points on one page; one Tesseract run reads all crops (list file)."""
    if not boxes:
        return []
    k = dpi / 72
    base = os.path.join(tmp, f"page{page}")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True)
    with open(base + ".pgm", "rb") as f:
        img = f.read()
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", img)
    if not m:
        return ["" for _ in boxes]
    width, height, off = int(m.group(1)), int(m.group(2)), m.end()
    paths = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):     # crops cut from the one rendering (PGM rows are plain bytes)
        a, b = max(0, int(x0 * k)), min(width, int(x1 * k))
        top, bot = max(0, int(y0 * k)), min(height, int(y1 * k))
        if b - a < 2 or bot - top < 2:
            a, b, top, bot = 0, 2, 0, 2
        rows = b"".join(img[off + y * width + a:off + y * width + b] for y in range(top, bot))
        pth = os.path.join(tmp, f"c{page}_{i}.pgm")
        with open(pth, "wb") as f:
            f.write(b"P5\n%d %d\n255\n" % (b - a, bot - top) + rows)
        paths.append(pth)
    os.remove(base + ".pgm")
    lst = os.path.join(tmp, f"list{page}.txt")
    with open(lst, "w") as f:
        f.write("\n".join(paths) + "\n")
    env = dict(os.environ, OMP_THREAD_LIMIT="1")     # one thread per run: pages run in parallel, and OpenMP spins on a busy machine
    r = subprocess.run(["tesseract", lst, "-", "-l", lang, "--psm", str(psm), "--dpi", str(dpi), "tsv"], capture_output=True,
                       text=True, env=env)
    lines = {}
    for ln in r.stdout.splitlines()[1:]:
        p = ln.split("\t")
        if len(p) < 12 or p[0] != "5" or not p[11].strip():
            provenance.skip_line(ln, 'skip: len(p) < 12 or p[0] != "5" or not p[11].strip()')
            continue
        key = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
        lines.setdefault(key, []).append((p[11], float(p[10]), int(p[9])))
    out = [[] for _ in boxes]
    heights = {}
    for (pg, *_), toks in lines.items():
        heights.setdefault(pg, []).extend(h for _, _, h in toks)
    for (pg, *_), toks in sorted(lines.items()):
        if not 1 <= pg <= len(boxes):
            continue
        # a vowel sign or a border speck read as a line of its own: low confidence, small letters
        if sum(c for _, c, _ in toks) / len(toks) < 55 and max(c for _, c, _ in toks) < 80:
            continue
        hm = sorted(heights[pg])[len(heights[pg]) // 2]
        keep = [t for t, c, h in toks if not (c < 30 and h < 0.6 * hm)]
        if keep:
            out[pg - 1].append(" ".join(keep))
    for pth in paths:
        try:
            os.remove(pth)
        except OSError:
            pass
    return [norm(" ".join(x)) for x in out]


def clean_cell(s):
    """Drops border slivers OCR reads as letters at a cell's edge (|, [, _ ...)."""
    s = re.sub(r"[|\[\]{}_©®“”‘’~`]", " ", s or "")
    return norm(s).strip(" .,:;-—")


# ---------------------------------------------------------------- Gujarat tables

def seat_info(t):
    """Seat number and category from the text layer of column 3 ("૧. સામાન્ય સ્ત્રી", "પહેલી બેઠક પછાત વગગ" ...)."""
    tt = t.translate(DIGITS)
    m = re.match(r"\s*\(?(\d)\s*[.)]", tt) or re.search(r"(\d)\s*(?:લી|જી|થી|મી)", tt) or \
        re.search(r"(?:^|\s)(\d)(?:\s|$)", tt)
    seat = m.group(1) if m else next((str(n) for k, n in ORDINAL if k in t), "")
    woman = any(k in t for k in ("સ્ત્રી", "મહિલા", "મલહિા", "મજહિા", "મહીલા", "મહિિા", "મલહલા", "સ્ત્ર"))
    if "અનુસ" in t or "અનસ" in t:
        cat = "ST" if re.search(r"આ[રદ]|આદિ|જનજાતિ", t) else "SC"
    elif "પછાત" in t:
        cat = "Backward class"
    elif "સામાન્ય" in t or "સામાશય" in t or "સામાન" in t:
        cat = "General"
    else:
        cat = ""
    return seat, (cat + " woman" if woman and cat else ("Woman" if woman else cat))


def party_of(*texts):
    for t in texts:
        t = norm(t)
        if not t:
            provenance.skipped("empty")
            continue
        for k, v in PARTY:
            if re.search(k, t):
                return v
        if re.fullmatch(r"[-–—]+", t):
            return "Independent"      # a dash in the party column: no party
        if re.search(r"જનતા|િનતા", t) and "પા" in t:
            return "BJP"
    return ""


def num(t):
    """A ward or serial number. ર and પ stand in for ૨ and ૫ in some fonts, so they count only in a cell that holds nothing else."""
    t = norm(t)
    if re.fullmatch(r"[(\s]*[0-9૦-૯०-९રપ]{1,3}[\s.)]*", t):
        t = t.replace("ર", "2").replace("પ", "5")
    m = re.search(r"\d+", t.translate(DIGITS))
    return str(int(m.group(0))) if m else ""


TITLE = re.compile(r"નગરપા\S{1,3}કા")   # "...પાલિકા" in the title, with the text layer's wrong letters


def titles(ws):
    """Body titles in the text layer: lines with "...નગરપાલિકાની સામાન્ય ચૂંટણી": [(y0, y1, x0, x1, text)]."""
    rows = {}
    for w in ws:
        rows.setdefault(round(w[1] / 3), []).append(w)
    out = []
    for _, line in sorted(rows.items()):
        line.sort(key=lambda w: w[0])
        text = norm(" ".join(w[4] for w in line))
        toks = text.split()
        if toks and toks[0].startswith("ક્રમ"):       # the notice's number line ("ક્રમાંક: ...")
            continue
        at = next((i for i, t in enumerate(toks) if TITLE.search(t)), None)
        if at is not None and at <= 3 and "ટણી" in "".join(toks[at + 1:at + 5]) and len(text) < 80:
            out.append((min(w[1] for w in line), max(w[3] for w in line), min(w[0] for w in line), max(w[2] for w in line),
                        text))
    return out


def body_key(text):
    """Stable key of a title from the text layer: the words up to the one with "પાલિકા", without spaces and case ending."""
    toks = norm(text).split()
    for i, t in enumerate(toks):
        if TITLE.search(t):
            return re.sub(r"(ની|ના|નો|નું)$", "", "".join(toks[:i + 1]))
    return "".join(toks)


def body_from_ocr(text):
    """"સુરત મહાનગરપાલિકાની સામાન્ય ચૂંટણી" -> "સુરત મહાનગરપાલિકા"; "(૧) ખેડા જિલ્લાની કઠલાલ નગરપાલિકાના" -> "કઠલાલ નગરપાલિકા"."""
    toks = norm(text).split()
    for i, t in enumerate(toks):
        if re.search(r"પાલિકા|પાલીકા|પાલલકા", t):
            last = "મહાનગરપાલિકા" if t.startswith("મહા") else "નગરપાલિકા"
            name = toks[:i]
            cut = max((j + 1 for j, w in enumerate(name) if w.startswith("જિલ્લા") or re.match(r"[(]?[0-9૦-૯]+[).]", w)),
                      default=0)
            return " ".join(name[cut:] + [last]).strip(" -–:")
    return ""


def header_row(ws, cols, a, b, name_col=4):
    """A table's heading or column-number row, not a member."""
    name = box_text(ws, cols[name_col][0], a, cols[name_col][1], b)
    return bool(re.fullmatch(r"\W*[0-9૦-૯०-९રપ]?\W*", name)) or "ઉમેદ" in name or "उमेद" in name or \
        name in ("નામ", "नाव", "नाम")


def notices(ws, page):
    """Starts of notices in the text layer: titles ("<body> નગરપાલિકાની સામાન્ય ચૂંટણી") and opening paragraphs
    ("(૧) <body> નગરપાલિકાના નીચે જણાવેલ ...", some notices have no title): [(page, y0, y1, x0, x1, text, kind)]."""
    out = [(page, *t, "title") for t in titles(ws)]
    rows = {}
    for w in ws:
        rows.setdefault(round(w[1] / 3), []).append(w)
    for _, line in sorted(rows.items()):
        line.sort(key=lambda w: w[0])
        toks = [w[4] for w in line]
        at = next((i for i, t in enumerate(toks[:7]) if TITLE.search(t) and t.endswith(("ના", "ની"))), None)
        if at is None or at + 1 >= len(toks) or not toks[at + 1].startswith("નીચે"):
            continue
        if not re.match(r"[(]?[0-9૦-૯રપ]{1,2}[).]", toks[0]):
            continue
        sel = line[1:at + 1]
        out.append((page, min(w[1] for w in sel), max(w[3] for w in sel), min(w[0] for w in sel), max(w[2] for w in sel),
                    " ".join(w[4] for w in sel), "para"))
    return sorted(out, key=lambda t: t[1])


def parse(pdf, p, use_ocr=True):
    """Members on pages first..last of a downloaded file. use_ocr=False keeps the text layer's names (structure tests).
    payload "bodies": [[page, y, slug, english, local], ...] = notice starts found when the seeds were made; without it the
    titles are found here (and read by OCR)."""
    from pypdf import PdfReader
    import concurrent.futures
    reader = PdfReader(pdf)
    first, last = int(p.get("first", 1)), min(int(p.get("last", 1)), len(reader.pages))
    starts = [tuple(b) for b in p.get("bodies") or []]
    tmp = tempfile.mkdtemp()
    pages = {}
    ref = None
    for pg in range(max(1, first - 3), last + 1):     # the 3 pages before: columns and the ward running over the break
        ws = words(pdf, pg)
        hs, vs = drawn_lines(reader, pg - 1)
        grid, ref = grid_rows(hs, vs, 6, 4, ref)
        rows = [(cols, a, b) for cols, a, b in grid if not header_row(ws, cols, a, b)]
        heads = [] if starts else [t for t in notices(ws, pg) if t[6] == "title"]
        pages[pg] = (ws, hs, rows, heads)
    if not starts and first > 4:                       # the title in effect at the first page
        for pg in range(first - 4, 0, -1):
            hd = [t for t in notices(words(pdf, pg), pg) if t[6] == "title"]
            if hd:
                pages[pg] = ([], [], [], hd[-1:])
                break

    def boxes_of(pg):
        ws, hs, rows, heads = pages[pg]
        bx = [(cols[c][0] + 1.2, a + 1.2, cols[c][1] - 1.2, b - 1.2) for cols, a, b in rows for c in (4, 5)] if pg >= first else []
        return bx + [(t[3] - 4, t[1] - 3, t[4] + 4, t[2] + 3) for t in heads]

    def read(pg):
        bx = boxes_of(pg)
        return ocr_boxes(pdf, pg, bx, tmp, "guj") if use_ocr else [box_text(pages[pg][0], *b) for b in bx]
    order = sorted(pages)
    with concurrent.futures.ThreadPoolExecutor(max(1, min(len(order), os.cpu_count() or 1))) as ex:
        texts = dict(zip(order, ex.map(read, order)))
    recs = []
    cur = {}
    last_ward, ward_n = None, 0
    for pg in order:
        ws, hs, rows, heads = pages[pg]
        tx = texts[pg]
        nrow = 2 * len(rows) if pg >= first else 0
        events = [(t[1], 0, ("title", t, tx[nrow + i])) for i, t in enumerate(heads)]
        events += [(b[1], 0, ("start", b)) for b in starts if b[0] == pg]
        events += [(a, 1, ("row", k, cols, a, b)) for k, (cols, a, b) in enumerate(rows)]
        if pg == order[0] and starts:                  # a notice that starts before the pages read here
            before = [b for b in starts if (b[0], b[1]) < (pg, 0)]
            if before:
                cur = {"slug": before[-1][2], "en": before[-1][3], "local": before[-1][4]}
        for _, _, ev in sorted(events, key=lambda e: (e[0], e[1])):
            if ev[0] == "title":
                t = ev[1]
                cur = {"key": body_key(t[5]), "local": body_from_ocr(ev[2]) or body_from_ocr(t[5]) or body_key(t[5])}
                last_ward, ward_n = None, 0
                continue
            if ev[0] == "start":
                cur = {"slug": ev[1][2], "en": ev[1][3], "local": ev[1][4]}
                last_ward, ward_n = None, 0
                continue
            _, k, cols, a, b = ev
            ward = num(box_text(ws, cols[2][0], *_span(cell_of(2, hs, (a + b) / 2, cols), cols[2][1])))
            if not ward and last_ward:
                ward = last_ward           # a ward cell running over from the page before shows no number here
            if ward:
                ward_n = ward_n + 1 if ward == last_ward else 1
                last_ward = ward
            if pg < first:
                continue
            serial = num(box_text(ws, cols[1][0], *_span(cell_of(1, hs, (a + b) / 2, cols), cols[1][1])))
            seat, resv = seat_info(box_text(ws, cols[3][0], a, cols[3][1], b))
            seat_by_order = not seat and bool(ward)
            if seat_by_order:
                seat = str(ward_n)       # seats are listed in order within a ward
            name, addr = clean_cell(tx[2 * k]), clean_cell(tx[2 * k + 1])
            party_t = box_text(ws, cols[6][0], a, cols[6][1], b)
            if not name or not (ward or serial):
                continue
            alias = ""
            m = re.match(r"^(.*?)\s*\(([^()]+)\)?\s*$", name)
            if m and m.group(1):
                name, alias = m.group(1).strip(), m.group(2).strip()
            local = cur.get("local") or p.get("body_local", "")
            body_en = cur.get("en") or (p.get("body", "") if p.get("single_body") else "")
            rec = {"type": "councillor", "state": "GJ", "body": local or body_en, "body_local": local, "body_en": body_en,
                   "body_type": p.get("body_type", ""), "district": p.get("district", ""), "ward_no": ward, "seat": seat,
                   "reservation": resv, "serial": serial, "name": name,
                   "party": party_of(party_t) or norm(party_t), "votes": None, "address": addr,
                   "election": "Gujarat 2026", "url": p["url"], "page": pg, "read": "ocr+text layer" if use_ocr else "text layer",
                   # source trail: the table row (1-based among the page's data rows) and its box in PDF points (top-left origin)
                   "src_pos": {"page": pg, "row": k + 1, "box_pt": [round(cols[1][0], 1), round(a, 1), round(cols[6][1], 1), round(b, 1)]}}
            if not use_ocr:
                rec["method"] = "pdf text layer by drawn cell borders (pdftotext -bbox)"
            if seat_by_order:
                rec["seat_from"] = "row order"
            if alias:
                rec["name_alias"] = alias
            slug = cur.get("slug") or p.get("slug", "x") + (
                "-" + hashlib.sha1(cur["key"].encode()).hexdigest()[:6] if cur.get("key") and not p.get("single_body") else "")
            recs.append((f"councillor:GJ:{slug}:{ward or 'x'}-{seat or 's' + serial}", rec))
    shutil.rmtree(tmp, ignore_errors=True)
    return recs


def _span(band, x1):
    return band[0], x1, band[1]


def _body(h, ocr_text, bodies):
    k = body_key(h[4])
    info = bodies.get(k) or {}
    return {"key": k, "local": body_from_ocr(ocr_text) or info.get("local") or k, "en": info.get("en", ""),
            "slug": info.get("slug", "")}


def fetch(p, get):
    if not tools("guj"):
        return [], [], "tesseract not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    files = [(f"councillors/GJ/{key}.pdf", r.content, "application/pdf")] if int(p.get("first", 1)) == 1 else []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(r.content)
        recs = parse(pdf, p)
    return recs, files, "" if recs else "no members read"
