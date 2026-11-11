"""Shared helpers for the blo2_<state> readers: BLO lists that states and districts publish as text PDFs.

Two ways to read a PDF table:
- `ruled_tables(content)`: tables drawn with rules (thin filled shapes or rectangles). Rows = bands between horizontal rules,
  columns = bands between vertical rules; the text of a cell is every piece of text inside it, top to bottom. Cells that wrap
  over many lines come out whole (ceodaman.nic.in lists).
- `layout_lines(content)` + `cells(line)`: tables without rules. pypdf's layout mode keeps the columns apart with 2+ spaces
  (district lists printed with "Microsoft: Print To PDF").
Verification stays on; nothing here fakes a browser.
"""
import bisect
import io
import re

from pypdf import PdfReader
from pypdf.generic import ContentStream

MOBILE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
NUM = re.compile(r"^(\d{1,4})\.?$")


def download(s, url, timeout=120):
    r = s.get(url, timeout=(20, timeout))
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        raise ValueError(f"not a PDF: {url} ({r.headers.get('content-type')})")
    return r.content


def mobiles(text):
    return MOBILE.findall(text or "")


def part_of(v):
    m = NUM.match((v or "").strip())
    return m.group(1) if m else None


def split_name(cell):
    """'Smt. A B Patel, GPT, GUPS Kachigam' -> ('Smt. A B Patel', 'GPT, GUPS Kachigam'). The name ends at the first comma."""
    cell = " ".join((cell or "").split())
    if "," not in cell:
        return cell, ""
    a, b = cell.split(",", 1)
    return a.strip(), b.strip(" ,")


# ---- ruled tables -------------------------------------------------------------------------------------------------------

def _mul(a, b):
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]


def _rules(reader, page):
    """Thin painted shapes -> (y of horizontal rules, x of vertical rules), in page space."""
    cs = ContentStream(page.get_contents(), reader)
    ctm, stack, path, hs, vs = [1, 0, 0, 1, 0, 0], [], [], [], []

    def pt(x, y):
        return x * ctm[0] + y * ctm[2] + ctm[4], x * ctm[1] + y * ctm[3] + ctm[5]

    for ops, op in cs.operations:
        if op == b"q":
            stack.append(ctm)
        elif op == b"Q":
            ctm = stack.pop() if stack else [1, 0, 0, 1, 0, 0]
        elif op == b"cm":
            ctm = _mul([float(x) for x in ops], ctm)
        elif op in (b"m", b"l"):
            if op == b"m" or not path:
                path.append([])
            path[-1].append(pt(float(ops[0]), float(ops[1])))
        elif op == b"re":
            x, y, w, h = (float(v) for v in ops)
            path.append([pt(x, y), pt(x + w, y + h)])
        elif op in (b"f", b"f*", b"F", b"S", b"s", b"B", b"B*", b"b", b"b*", b"n"):
            for sub in (path if op != b"n" else []):
                if len(sub) < 2:
                    continue
                xs, ys = [p[0] for p in sub], [p[1] for p in sub]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if h < 3 and w > 20:
                    hs.append((max(ys) + min(ys)) / 2)
                elif w < 3 and h > 5:
                    vs.append((max(xs) + min(xs)) / 2)
            path = []
    return _merge(hs), _merge(vs)


def _merge(vals, tol=2.0):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def _texts(page):
    out = []

    def visit(text, cm, tm, fd, fs):
        if text.strip():
            m = _mul(tm, cm)
            out.append((m[4], m[5], text))
    page.extract_text(visitor_text=visit)
    return out


def page_table(reader, page):
    """One page -> list of rows (top to bottom), each a list of cell texts (left to right, one per column band)."""
    ys, xs = _rules(reader, page)
    if not ys or not xs:
        return []
    cells = {}
    for x, y, t in _texts(page):
        cells.setdefault((bisect.bisect(ys, y + 2), bisect.bisect(xs, x + 1)), []).append((-y, x, t))
    rows = []
    for r in sorted({k[0] for k in cells}, reverse=True):
        rows.append([" ".join(" ".join(t.split()) for _, _, t in sorted(cells.get((r, c), []))).strip()
                     for c in range(len(xs) + 1)])
    return rows


def ruled_tables(content):
    """Every page of a ruled PDF -> [(page_no, rows)]."""
    rd = PdfReader(io.BytesIO(content))
    return [(i, page_table(rd, pg)) for i, pg in enumerate(rd.pages, 1)]


# ---- tables without rules -----------------------------------------------------------------------------------------------

def layout_lines(content):
    """[(page_no, line)] in pypdf layout mode."""
    rd = PdfReader(io.BytesIO(content))
    out = []
    for i, pg in enumerate(rd.pages, 1):
        for ln in pg.extract_text(extraction_mode="layout").splitlines():
            if ln.strip():
                out.append((i, ln))
    return out


def cells(line):
    """Columns of one layout line: runs of text separated by 2+ spaces."""
    return [c for c in re.split(r"\s{2,}", line.strip()) if c]
