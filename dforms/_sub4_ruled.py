"""Rows of a ruled PDF table (every cell drawn with lines), for the sub4 readers.

rows(content, first_col_max=None) -> [{"cells": [[pieces of column 0], [pieces of column 1], ...], "_pos": {"page", "row", "sn"}}]
How: pypdf pieces with their position (dforms._util2_pdfgrid.page_parts). Column borders = the x of the vertical lines of the page.
Row borders = the y of the horizontal lines that cross the first column. A piece goes to the column and the row band it sits in.
A row is a data row when its first column holds a serial number. A band at the top of a page without a serial number continues
the last row of the page before (a cell split over two pages). Rows are numbered 1, 2 ... on each page, top to bottom (header
rows not counted); "sn" is the serial number as printed.
"""
import io
import re


def _merge(vals, tol=2.0):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def text(pieces):
    """Pieces of one cell (top to bottom, left to right) as one text."""
    t = " ".join(p.replace("\n", " ").strip() for p in pieces if p and p.strip())
    return re.sub(r"\s+", " ", t).strip()


def rows(content):
    from pypdf import PdfReader

    from dforms._util2_pdfgrid import page_parts
    reader = PdfReader(io.BytesIO(content))
    out = []
    for n, page in enumerate(reader.pages, 1):
        texts, hlines, vlines = page_parts(reader, page)
        xs = _merge([x for x, y0, y1 in vlines if y1 - y0 > 5])
        if len(xs) < 3:
            continue
        x0, x1 = xs[0], xs[1]
        ys = _merge([y for a, b, y in hlines if a <= x0 + 3 and b >= x1 - 3 and b - a > 10], tol=1.5)
        ys = sorted(ys, reverse=True)
        if len(ys) < 2:
            continue
        bands = []
        for top, bot in zip(ys, ys[1:]):
            cells = [[] for _ in range(len(xs) - 1)]
            for x, y, t in sorted(texts, key=lambda a: (-round(a[1], 0), a[0])):
                if not (bot < y < top) or not t.strip():
                    continue
                for k in range(len(xs) - 1):
                    if xs[k] - 2 <= x < xs[k + 1] - 1:
                        cells[k].append(t)
                        break
            bands.append(cells)
        no = 0
        for i, cells in enumerate(bands):
            sn = text(cells[0])
            if re.fullmatch(r"\d{1,4}\.?", sn):
                no += 1
                out.append({"cells": cells, "_pos": {"page": n, "row": no, "sn": sn.rstrip(".")}})
            elif out and no == 0 and any(c for c in cells[1:]) and not re.search(r"(?i)\bname\b|sl\.?\s*no", text(sum(cells, []))):
                # continuation of the last row of the page before
                for k, c in enumerate(cells):
                    if k < len(out[-1]["cells"]):
                        out[-1]["cells"][k].extend(c)
    return out
