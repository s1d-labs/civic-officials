"""Table cells of a text PDF printed from a spreadsheet (Excel, Google Sheets), for readers whose rows have wrapped and
overflowing cells that layout text mixes up (West Bengal CEO officials lists).

How: poppler `pdftotext -raw -bbox` gives every word with its box in the order the PDF draws it (one cell after the other);
pypdf gives the grid lines (dforms/_util2_pdfgrid.page_parts). Rows = the bands between full-width horizontal lines. In one
band the words are cut into segments (one cell each) where the drawing order jumps: back to the left on the same line, forward
by more than a word gap, or over a vertical line. Each segment goes to the column (between vertical lines) that holds its
centre: a Google Sheets cell whose text overflows to the left still has its centre in its own column.

pages(content) -> [{"page", "columns": [(x0, x1)], "rows": [[cell text per column], ...], "texts": [band text]}].
Needs poppler (pdftotext); ensure_poppler() installs it on a GitHub runner (sudo without password).
"""
import html
import io
import re
import shutil
import subprocess

WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)


def ensure_poppler():
    if shutil.which("pdftotext"):
        return True
    subprocess.run("sudo -n apt-get -o DPkg::Lock::Timeout=600 install -y -q poppler-utils", shell=True, capture_output=True)
    return bool(shutil.which("pdftotext"))


def raw_words(content):
    """[(width, height, [(x0, y0, x1, y1, text)])] per page, words in drawing order, y from the top."""
    r = subprocess.run(["pdftotext", "-raw", "-bbox", "-enc", "UTF-8", "-", "-"], input=content, capture_output=True, timeout=300)
    out = []
    for m in PAGE.finditer(r.stdout.decode("utf-8", "replace")):
        words = [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in WORD.findall(m.group(3))]
        out.append((float(m.group(1)), float(m.group(2)), words))
    return out


def _merge(vals, tol):
    out = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def grid_lines(content):
    """[(hlines y from the top [(x0, x1, y)], vlines [(x, y0, y1)])] per page, from pypdf."""
    from pypdf import PdfReader

    from dforms._util2_pdfgrid import page_parts
    out = []
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception:
        return out
    for pg in reader.pages:
        try:
            top = float(pg.mediabox.top)
            _, h, v = page_parts(reader, pg)
        except Exception:
            h, v, top = [], [], 0
        out.append(([(x0, x1, top - y) for x0, x1, y in h], [(x, top - y1, top - y0) for x, y0, y1 in v]))
    return out


def segments(words, vxs, gap=5.0):
    """Cut a band's words (drawing order) into cell segments: [(x0, x1, text)]."""
    segs, cur = [], []
    for w in words:
        if cur:
            p = cur[-1]
            same = abs(w[1] - p[1]) < 2.0
            over = any(p[2] - 1 <= vx <= w[0] + 1 for vx in vxs) and w[0] > p[2] - 1
            if over or (same and (w[0] < p[0] - 0.5 or w[0] - p[2] > gap)) or (not same and w[0] > p[2] + gap):
                segs.append(cur)
                cur = []
        cur.append(w)
    if cur:
        segs.append(cur)
    return [(min(w[0] for w in s), max(w[2] for w in s), " ".join(w[4] for w in s)) for s in segs]


def pages(content):
    out = []
    lines = grid_lines(content)
    for i, (width, height, words) in enumerate(raw_words(content)):
        h, v = lines[i] if i < len(lines) else ([], [])
        full = [y for x0, x1, y in h if x1 - x0 > width * 0.3]
        ys = _merge(full, 2.0)
        vxs = _merge([x for x, y0, y1 in v if y1 - y0 > 6], 2.0)
        cols = list(zip(vxs, vxs[1:])) or [(0, width)]
        bands = {}
        for w in words:
            cy = (w[1] + w[3]) / 2
            b = sum(1 for y in ys if y < cy)            # band index: lines above the word's centre
            bands.setdefault(b, []).append(w)
        rows, texts = [], []
        for b in sorted(bands):
            ws = bands[b]
            row = [""] * len(cols)
            for x0, x1, t in segments(ws, vxs):
                c = (x0 + x1) / 2
                k = next((j for j, (a, z) in enumerate(cols) if a <= c < z), 0 if c < cols[0][0] else len(cols) - 1)
                row[k] = (row[k] + " " + t).strip()
            rows.append(row)
            texts.append(" ".join(w[4] for w in ws))
        out.append({"page": i + 1, "columns": cols, "rows": rows, "texts": texts})
    return out
