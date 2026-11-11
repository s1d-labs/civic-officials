"""District BLO lists as text PDFs (S3WaaS district sites: <district>.nic.in/blo-list/ and similar pages, files on
cdn.s3waas.gov.in). One queue item = one PDF, usually one Assembly Constituency (AC).

Each district uses its own columns, so this reader takes the column names from the PDF's own header line and keeps every
column verbatim in "cells". Text comes from pypdf in layout mode (columns stay apart by 2+ spaces).
- A header line has a part/PS column and a name/mobile column. Repeated headers and "1 2 3 4 ..." number lines are skipped.
- A data line has at least (columns - 2) fields and a part number or a 10-digit mobile.
- Short lines between data lines are parts of wrapped cells (e.g. "Anganwadi" above "worker"): they are added in front
  of the next data line's cell in the same column.
- Every fetched PDF is saved to the bucket (store_path: blo2/<state>/<sha1(url)[:12]>.pdf in the project), also when it
  cannot be read here. Scanned PDFs (no text) end with "scanned: no text layer, needs OCR"; PDFs whose text pypdf cannot
  lay out (legacy fonts such as Kruti Dev, Type 3 fonts) end with "text layer unreadable". forms/blo2_ocr.py reads the
  saved copy of both by OCR (task blo2-ocr).
Payload: {"kind": "form-blo2_pdf", "state", "url", "district", "ac_no", "ac_name", "list_date", "source_page", "label"}.
cdn.s3waas.gov.in answered from Germany on 2026-11-11 (no India proxy needed).
"""
import hashlib
import io
import re

from pypdf import PdfReader

SPLIT = re.compile(r"\s{2,}")
MOBILE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{9})(?!\d)")
PART_H = re.compile(r"part|\bps\b|ps\s*no|p\.s|booth|polling|भाग|मतदान|बूथ", re.I)
WHO_H = re.compile(r"name|mobile|contact|phone|नाम|मोबाइल", re.I)
INT = re.compile(r"^\d{1,4}$")

# header label -> common field (first match wins; order matters)
FIELDS = [
    ("blo_phone", re.compile(r"mobile|contact|phone|मोबाइल|दूरभाष", re.I)),
    ("part_no", re.compile(r"^(part|ps|booth|polling\s*station|भाग|मतदान\s*केन्द्र|बूथ).{0,12}(no|number|sl|क्र|संख्या|सं)|^part$|^ps\s*no|^p\.?s\.?\s*no", re.I)),
    ("ac_no", re.compile(r"^(ac|assembly|vidhan|विधान).{0,14}(no|number|सं)|^ac\s*no", re.I)),
    ("ac_name", re.compile(r"^(ac|assembly|constituency|vidhan|विधान)", re.I)),
    ("station", re.compile(r"(part|ps|polling|booth|station|भाग|केन्द्र|बूथ).*(name|नाम)|name\s*of\s*(ps|polling|the\s*polling)|^part\s*name|location|building", re.I)),
    ("blo_name", re.compile(r"blo|name|नाम", re.I)),
    ("designation", re.compile(r"designation|post|पद", re.I)),
]


def _fields(line):
    """[(start, end, text)] of the cells on one layout line."""
    out, pos = [], 0
    for part in SPLIT.split(line.rstrip()):
        if not part.strip():
            pos += len(part)
            continue
        i = line.index(part, pos)
        out.append((i, i + len(part), part.strip()))
        pos = i + len(part)
    return out


def _is_header(texts):
    j = " | ".join(texts)
    return len(texts) >= 3 and PART_H.search(j) and WHO_H.search(j) and not MOBILE.search(j)


def _numbering(texts):
    return len(texts) >= 4 and all(INT.match(t) for t in texts) and [int(t) for t in texts] == list(range(1, len(texts) + 1))


LEAD_INT = re.compile(r"^(\d{1,4})\s+(\S.*)$")
MOB_IN = re.compile(r"^(.*?\S)?\s*((?:\+?91[\s-]?)?[6-9]\d{9})\s*(\S.*)?$")


def _split(flds, n):
    """Too few fields: cut "12 Some School" into "12" + "Some School" and "Name 9876543210" into name + mobile."""
    if len(flds) >= n:
        return flds
    out = []
    for a, b, t in flds:
        m = LEAD_INT.match(t)
        if m:
            out.append((a, a + len(m.group(1)), m.group(1)))
            a, t = b - len(m.group(2)), m.group(2)
        m = MOB_IN.match(t)
        if m and (m.group(1) or m.group(3)):
            i = t.index(m.group(2))
            if m.group(1):
                out.append((a, a + len(m.group(1)), m.group(1)))
            out.append((a + i, a + i + len(m.group(2)), m.group(2)))
            if m.group(3):
                out.append((b - len(m.group(3)), b, m.group(3)))
        else:
            out.append((a, b, t))
    return out


def _starts(good, head):
    """Column start of each header column, from the lines that have exactly one field per column."""
    if not good:
        return [h[0] for h in head]
    cols = list(zip(*[[f[0] for f in g] for g in good]))
    return [sorted(c)[len(c) // 2] for c in cols]


def _map(head, flds, starts, exact=False):
    """Data fields -> header labels: by order when the line had one field per column, else by the learned column starts."""
    if exact and len(flds) == len(head):
        return [(h[2], f) for h, f in zip(head, flds)]
    out = []
    for f in flds:
        left = [i for i, st in enumerate(starts) if st <= f[0] + 1]
        i = left[-1] if left else min(range(len(starts)), key=lambda i: abs(starts[i] - f[0]))
        out.append((head[i][2], f))
    return out


def _labels(head):
    """Header label -> common field name, each field used once."""
    used, lab = set(), {}
    for _, _, h in head:
        for name, rx in FIELDS:
            if name not in used and rx.search(h):
                lab[h] = name
                used.add(name)
                break
    return lab


def rows_from_pages(pages, p):
    """pages: layout text per page. Returns blo.py form rows."""
    head, lab, rows, starts = None, {}, [], None
    for page in pages:
        items, pending = [], []     # pass 1: data lines with the wrapped cell parts above them
        for line in page.splitlines():
            if not line.strip():
                continue
            flds = _fields(line)
            texts = [f[2] for f in flds]
            if _is_header(texts):
                if head is None or len(flds) >= len(head):
                    head, lab, starts = flds, _labels(flds), None
                pending = []
                continue
            if head is None or _numbering(texts):
                continue
            has_part = any(INT.match(t) or LEAD_INT.match(t) for t in texts)
            if len(flds) >= max(3, len(head) - 3) and (has_part or MOBILE.search(line)):
                items.append((_split(flds, len(head)), pending, len(flds) == len(head)))
                pending = []
            else:
                pending = pending + flds   # page footers at the end are dropped with the page
        if head is None:
            continue
        good = [f for f, _, _ in items if len(f) == len(head)]   # median start per column: outliers do not move it
        starts = _starts(good, head) if good else (starts or _starts([], head))
        for flds, above, exact in items:      # pass 2: fields -> columns
            cells = {}
            for h, f in _map(head, flds, starts, exact):
                cells[h] = (cells[h] + " " + f[2]) if h in cells else f[2]
            for pf in above:
                h = _map(head, [pf], starts)[0][0]
                cells[h] = (pf[2] + " " + cells[h]) if cells.get(h) else pf[2]
            rows.append(_row(cells, lab, p))
    return rows


def _row(cells, lab, p):
    f = {}
    for h, v in cells.items():
        if h in lab and lab[h] not in f:
            f[lab[h]] = v
    phone = MOBILE.search(f.get("blo_phone", "")) or MOBILE.search(" ".join(cells.values()))
    ac_no = f.get("ac_no")
    ac_no = int(ac_no) if ac_no and ac_no.isdigit() else p.get("ac_no")
    part = f.get("part_no", "")
    if not part.isdigit():   # "26" glued to wrapped station text in the same cell: "... purbi 26"
        m = re.match(r"^(\d{1,4})\b", part) or re.search(r"\b(\d{1,4})$", part)
        part = m.group(1) if m else part
    part = int(part) if part.isdigit() else part
    name = f.get("blo_name", "")
    if MOBILE.fullmatch(name.strip()):   # the name was glued to the station cell; the cells keep it
        name = ""
    if ac_no is None:     # no AC known: keep record ids unique per file
        ac_no = "f" + re.sub(r"\W", "", p.get("url", "").rsplit("/", 1)[-1].rsplit(".", 1)[0])[-16:]
    r = {"ac_no": ac_no,
         "ac_name": f.get("ac_name") if f.get("ac_name") and not f.get("ac_name", "").isdigit() else p.get("ac_name"),
         "district": p.get("district"), "part_no": part, "station": f.get("station", ""), "blo_name": name,
         "blo_phone": phone.group(1) if phone else f.get("blo_phone", ""), "cells": dict(cells)}
    if f.get("designation"):
        r["designation"] = f["designation"]
    for k in ("list_date", "source_page"):
        if p.get(k):
            r["cells"]["_" + k] = p[k]
    return r


def pages_of(pdf_bytes):
    return [(pg.extract_text(extraction_mode="layout") or "") for pg in PdfReader(io.BytesIO(pdf_bytes)).pages]


def store_path(p):
    """Where the fetched PDF is saved, relative to the project (forms/blo2_ocr.py reads it back from there)."""
    return f"blo2/{p.get('state', 'xx')}/{hashlib.sha1(p['url'].encode()).hexdigest()[:12]}.pdf"


def unreadable(pdf_bytes, pages):
    """'' when the layout text has content; else why the file needs OCR."""
    if any(t.strip() for t in pages):
        return ""
    try:
        plain = "".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:  # noqa: BLE001
        plain = ""
    if plain.strip():
        return "text layer unreadable (legacy or Type 3 font), needs OCR"
    return "scanned: no text layer, needs OCR"


def read(s, p, hub=None):
    """(rows, files, why): the rows, the PDF to save, and why there are no rows."""
    r = s.get(p["url"], timeout=(20, 180))
    r.raise_for_status()
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [(store_path(p), r.content, "application/pdf")]
    pages = pages_of(r.content)
    why = unreadable(r.content, pages)
    if why:
        return [], files, why
    rows = rows_from_pages(pages, p)
    return rows, files, "" if rows else "no rows"


def fetch(s, p):
    rows, _, why = read(s, p)
    if why and not rows:
        raise RuntimeError(why)
    return rows
