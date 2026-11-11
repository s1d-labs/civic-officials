"""Page text of a PDF with its columns kept apart: `pdftotext -layout` (poppler) when the machine has it (the India pool
servers do), else pypdf's layout mode (GitHub runners). Both keep each line's text at its column position, so readers slice
lines at the header's column starts."""
import shutil
import subprocess

from dforms._power import pdf_pages


def layout_pages(content):
    """[(page text), ...]; engine name in the second value: "pdftotext" or "pypdf"."""
    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", "-", "-"], input=content, capture_output=True, timeout=180)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", "replace").split("\f"), "pdftotext"
        except (OSError, subprocess.SubprocessError):
            pass
    return pdf_pages(content, layout=True), "pypdf"


def cut(line, starts):
    """Split one line at the column starts [x0, x1, ...]: a word that crosses a start stays in the left column."""
    out, prev = [], 0
    for x in list(starts[1:]) + [None]:
        if x is None:
            out.append(line[prev:])
            break
        if x >= len(line):
            out.append(line[prev:])
            out.extend([""] * (len(starts) - len(out)))
            break
        while 0 < x < len(line) and line[x - 1] != " " and line[x] != " " and x > prev:
            x += 1                       # keep a crossing word whole, in the left column
        out.append(line[prev:x])
        prev = x
    return [" ".join(c.split()) for c in out[:len(starts)]]


def settle(starts, lines, left=6, right=1):
    """Column starts taken from the data: a header word is often printed a few characters right of its column's cells.
    For each start, the leftmost cell start within [x - left, x + right] that at least two lines share."""
    import re
    from collections import Counter
    seen = Counter(m.start() for ln in lines for m in re.finditer(r"(?:(?<=\s\s)|^)\S", ln))
    out = []
    for x in starts:
        near = [p for p in range(max(0, x - left), x + right + 1) if seen[p] >= 2]
        out.append(min(near) if near and x > 0 else x)
    return out
