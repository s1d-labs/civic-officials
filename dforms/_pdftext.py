"""Page text of a PDF with its columns kept apart: `pdftotext -layout` (poppler) when the machine has it (the India pool
servers do), else pypdf's layout mode (GitHub runners). Both keep each line's text at its column position, so readers slice
lines at the header's column starts."""
import shutil
import subprocess

import provenance

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


class Lines:
    """Source trail positions in one PDF page: Lines(page_no, page_text) splits the text as text.splitlines() does; pos(row)
    gives provenance.line_pos for the line(s) a row was read from (matched by their text, rstripped, first unused match in page
    order, so repeated lines map in order). A row of several lines gets "line" = its first line, "lines" = all line numbers and
    "line_text" = the lines joined by newlines."""

    def __init__(self, page, text):
        self.page = page
        self.lines = [ln.rstrip() for ln in (text.splitlines() if isinstance(text, str) else text)]
        self.used = set()

    def find(self, ln):
        ln = (ln or "").rstrip()
        for i, x in enumerate(self.lines):
            if i not in self.used and x == ln:
                self.used.add(i)
                return i + 1
        for i, x in enumerate(self.lines):            # a line already given to an earlier row (a shared heading line)
            if x == ln:
                return i + 1
        return None

    def pos(self, row, **more):
        row = [row] if isinstance(row, str) else list(row)
        nos = sorted({n for n in (self.find(x) for x in row if (x or "").strip()) if n})
        if not nos:
            return {"page": self.page, **{k: v for k, v in more.items() if v is not None}}
        if len(nos) > 1:
            more = {"lines": nos, **more}
        return provenance.line_pos(self.page, nos[0], "\n".join(self.lines[n - 1] for n in nos), **more)


def block_pos(page, lines, idx, **more):
    """src_pos of the lines idx (0-based indices into this page's lines) of one page: "line" = the first (1-based), "lines" = all
    when more than one, "line_text" = their raw text joined by newlines."""
    idx = sorted({k for k in idx if 0 <= k < len(lines)})
    if not idx:
        return {"page": page, **{k: v for k, v in more.items() if v is not None}}
    if len(idx) > 1:
        more = {"lines": [k + 1 for k in idx], **more}
    return provenance.line_pos(page, idx[0] + 1, "\n".join(lines[k].rstrip() for k in idx), **more)


def line_no(text, line):
    """1-based number of a line (rstripped) in a page's text.splitlines(), or None."""
    line = (line or "").rstrip()
    return next((i for i, x in enumerate(text.splitlines(), 1) if x.rstrip() == line), None)


def page_lines(pages):
    """(page, line, text) for every line of every page (1-based page and line; text.splitlines() of each page): the same lines a
    reader gets from "\n".join(pages).splitlines(), with their place."""
    for pn, t in enumerate(pages, 1):
        for ln, x in enumerate((t or "").splitlines(), 1):
            yield pn, ln, x
