"""District BLO lists as text PDFs (S3WaaS district sites: <district>.nic.in/blo-list/ and similar pages, files on
cdn.s3waas.gov.in). One queue item = one PDF, usually one Assembly Constituency (AC).

Each district uses its own columns, so this reader takes the column names from the PDF's own header line and keeps every
column verbatim in "cells". Text comes from pypdf in layout mode (columns stay apart by 2+ spaces).
- A header line has a part/PS column and a name/mobile column. Repeated headers and "1 2 3 4 ..." number lines are skipped.
- A data line has at least (columns - 2) fields and a part number or a 10-digit mobile.
- Short lines between data lines are parts of wrapped cells (e.g. "Anganwadi" above "worker"): they are added in front
  of the next data line's cell in the same column.
- A row typed on two lines ("7 | station" then "| name | post | mobile") is one row; a short line with a mobile right
  below a row (a second number) belongs to that row. A number that is the BLO's mobile in 5+ rows and 20%+ of the file
  is a supervisor's: the row's other mobile is used, or none.
- Kruti Dev (legacy Hindi font, many UP and Bihar lists): the text layer has Latin letters ("ch0,y0vks0 dk uke" =
  "बी0एल0ओ0 का नाम"). A page whose Latin letters read as Kruti Dev (cforms/cn_krutidev.is_krutidev) has each cell
  converted word by word (kd_cell) before header detection; Unicode words in the same cell stay. Column positions stay
  those of the raw text. A header on two lines ("मतदेय" above "स्थल सं0") is joined.
- No header text in the whole file (the header row is an image, as in Varanasi): the columns are named from the data
  lines (_guess_head: Mobile, Part No, Polling station name, BLO name, Designation); such rows have cells["_columns"].
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
import unicodedata

from pypdf import PdfReader

from cforms import cn_krutidev

METHOD = "pdf text (pypdf layout; Kruti Dev map on pages set in Kruti Dev)"     # source trail (provenance.py): how this reader reads its sources

SPLIT = re.compile(r"\s{2,}")
MOBILE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{9})(?!\d)")
PART_H = re.compile(r"part|\bps\b|ps\s*no|p\.s|booth|polling|भाग|मतदान|मतदेय|स्थल\s*सं|बूथ", re.I)
WHO_H = re.compile(r"name|mobile|contact|phone|नाम|मोबाइल|मोबाईल", re.I)
INT = re.compile(r"^\d{1,4}$")

# header label -> common field (first match wins; order matters)
FIELDS = [
    ("blo_phone", re.compile(r"mobile|contact|phone|मोबाइल|मोबाईल|दूरभाष", re.I)),
    ("part_no", re.compile(r"^(part|ps|booth|polling\s*station|भाग|मतदान\s*केन्द्र|मतदेय\s*स्थल|स्थल|बूथ).{0,12}(no|number|sl|क्र|संख्या|सं)|^part$|^ps\s*no|^p\.?s\.?\s*no", re.I)),
    ("ac_no", re.compile(r"^(ac|assembly|vidhan|विधान).{0,14}(no|number|सं)|^ac\s*no", re.I)),
    ("ac_name", re.compile(r"^(ac|assembly|constituency|vidhan|विधान)", re.I)),
    ("station", re.compile(r"(part|ps|polling|booth|station|भाग|केन्द्र|बूथ|मतदेय|स्थल).*(name|नाम)|name\s*of\s*(ps|polling|the\s*polling)|^part\s*name|location|building|भवन", re.I)),
    ("blo_name", re.compile(r"blo|name|नाम", re.I)),
    ("designation", re.compile(r"designation|post|पद", re.I)),
]

# ---------------------------------------------------------------- Kruti Dev
# Many UP and Bihar lists are typed in the legacy Kruti Dev font: the text layer has Latin letters ("ch0,y0vks0 dk uke" =
# "बी0एल0ओ0 का नाम"). A page whose Latin letters read as Kruti Dev (cn_krutidev.is_krutidev) has its cells converted
# word by word before header detection. Kept as they are: Devanagari words (Unicode cells next to Kruti Dev cells), numbers,
# e-mails, upper-case Latin (BLO, F:\LIST.xlsx) and a few English words; in a cell that already has Devanagari, also
# words with fewer than 2 Latin letters ("%" in a Unicode school name is not the Kruti Dev visarga).
DEVA = re.compile("[\u0900-\u097f]")
EMAIL = re.compile(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NUMERIC = re.compile(r"[\d.,:/()+-]+")
UPPER = re.compile(r"[A-Z0-9.()_:\\-]+")
ENGLISH = {"page", "of", "no", "no.", "name", "mobile", "blo", "part", "sl", "sr", "the", "and", "list"}
STRAY = re.compile(r"^[\u0900-\u0903\u093e-\u094d]+")


def kd_page(text):
    """True when the Latin letters of a page are Kruti Dev text."""
    return cn_krutidev.is_krutidev(text)


# pypdf sometimes puts a word space before a vowel sign ("jsu wnsoh" for "jsuw nsoh", रेनू देवी): no Kruti Dev word starts
# with a vowel sign (k h q w s S) or with "z" (्र) or "Z" (reph), so such a sign goes back to the word before it.
SIGN_SPLIT = re.compile(r"(?<=[A-Za-z;'\"\[\]{}|<>?/.,~+=`]) ([khqwsSzZ][khqwsSzZa`]*)(?=(\S?))")


# A second pypdf slip: the e/ai sign "s"/"S" lands one letter too far right and the next sign after a space ("nos h" for
# "nsoh" देवी, "j[s kk" for "js[kk" रेखा, "foey's k" for "foeys'k" विमलेश): put the sign back before that letter.
SIGN_SHIFT = re.compile(r"([^\s\dkhqwsSa`])([sS])\s+([kh][khqwsSa`]*)")
U_SHIFT = re.compile(r"([^\s\dkhqwsSa`])([^\s\dkhqwsSa`])([qw])\s+([sS])")   # "vunq s'kd" for "vuqns'kd" अनुदेशक
MATRA_START = re.compile(r"[khqwsS]")


def kd_fields(flds):
    """Raw fields of a Kruti Dev line -> converted fields. A field that starts with a vowel sign ("h" or "kk nos" set apart
    from its word by pypdf) joins the field before it."""
    out = []
    for a, b, t in flds:
        if out and re.search(r"(^|\s)f$", out[-1][2]) and not DEVA.search(t):   # short i "f" typed before the next field's letter
            out[-1] = (out[-1][0], out[-1][1], out[-1][2][:-1].rstrip())
            t = "f" + t
        if out and MATRA_START.match(t) and not DEVA.search(t) and not DEVA.search(out[-1][2]):
            out[-1] = (out[-1][0], b, out[-1][2] + " " + t)
        else:
            out.append((a, b, t))
    return [(a, b, t) for a, b, t in ((a, b, kd_cell(t)) for a, b, t in out) if t]


def kd_cell(text):
    """Kruti Dev words of one cell -> Devanagari; everything else as it is."""
    deva = bool(DEVA.search(text))
    if not deva:
        text = U_SHIFT.sub(r"\1\3\2\4", SIGN_SHIFT.sub(r"\2\1\3", text))
        text = SIGN_SPLIT.sub(lambda m: m.group(1) + (" " if m.group(2) else ""), text)
    out = []
    for tok in re.split(r"(\s+)", text):
        letters = sum(ch.isascii() and ch.isalpha() for ch in tok)
        if (not tok.strip() or DEVA.search(tok) or EMAIL.fullmatch(tok) or NUMERIC.fullmatch(tok) or UPPER.fullmatch(tok)
                or tok.lower() in ENGLISH or (deva and letters < 2)):
            out.append(tok)
        else:
            out.append(cn_krutidev.convert(tok).replace("]", ",").replace("¼", "(").replace("½", ")").replace("þ", "द्र"))
    s = unicodedata.normalize("NFC", "".join(out))
    s = s.replace("चैधरी", "चौधरी").replace("चैहान", "चौहान")      # the usual Kruti Dev typing slip for au
    return STRAY.sub("", s).strip()


CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")   # control characters that broken Unicode fonts leave in the text


def _fields(line):
    """[(start, end, text)] of the cells on one layout line."""
    out, pos = [], 0
    for part in SPLIT.split(line.rstrip()):
        if not part.strip():
            pos += len(part)
            continue
        i = line.index(part, pos)
        out.append((i, i + len(part), CTRL.sub("", part).strip()))
        pos = i + len(part)
    return out


def _is_header(texts):
    j = " | ".join(texts)
    return len(texts) >= 3 and PART_H.search(j) and WHO_H.search(j) and not MOBILE.search(j)


def _numbering(texts):
    """Column numbers under a header: "1 2 3 4 ..." (also with gaps, "2 3 4 5 6 8", when a number sits in a merged cell)."""
    if len(texts) < 4 or not all(INT.match(t) for t in texts):
        return False
    n = [int(t) for t in texts]
    return n == list(range(1, len(n) + 1)) or (all(a < b for a, b in zip(n, n[1:])) and n[-1] <= 2 * len(n))


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


NEAR = 10      # a field that starts this close before the next column's start belongs to that column (layout jitter)
PHONE_H = re.compile(r"mobile|contact|phone|मोबाइल|मोबाईल|दूरभाष", re.I)
SUPERVISOR = re.compile(r"supervisor|\bero\b|aero|सुपरवाइजर|सुपरवाईजर|पर्यवेक्षक", re.I)
TITLE = re.compile(r"सूची|\bblo\s+list\b", re.I)


def _map(head, flds, starts, exact=False, lab=None):
    """Data fields -> header labels: by order when the line had one field per column, else by the learned column starts.
    A field that is only a mobile number goes to the BLO's phone column when its position points at a column without one."""
    if exact and len(flds) == len(head):
        return [(h[2], f) for h, f in zip(head, flds)]
    phone = [i for i, h in enumerate(head) if (lab or {}).get(h[2]) == "blo_phone"]
    out = []
    for f in flds:
        left = [i for i, st in enumerate(starts) if st <= f[0] + 1]
        i = left[-1] if left else min(range(len(starts)), key=lambda i: abs(starts[i] - f[0]))
        if i + 1 < len(starts) and starts[i + 1] - f[0] <= NEAR and starts[i + 1] - f[0] < f[0] - starts[i]:
            i += 1
        if phone and MOBILE.fullmatch(f[2]) and not PHONE_H.search(head[i][2]) and not SUPERVISOR.search(head[i][2]):
            j = min(phone, key=lambda j: abs(starts[j] - f[0]))
            i = j if abs(starts[j] - f[0]) <= 2 * NEAR else i
        out.append((head[i][2], f))
    return out


def _merge_above(head, above):
    """A header typed on two lines ("मतदेय" above "स्थल सं0"): each word group of the line just above joins the header
    column it overlaps, or becomes a column of its own where it overlaps none. Only for a line of 2+ text fields."""
    texts = [t for _, _, t in above]
    if len(above) < 2 or MOBILE.search(" ".join(texts)) or any(INT.match(t) for t in texts):
        return head
    cols = [list(h) for h in head]
    for a, b, t in above:
        hit = [c for c in cols if a <= c[1] and c[0] <= b]
        if hit:
            c = max(hit, key=lambda c: min(b, c[1]) - max(a, c[0]))
            c[0], c[1], c[2] = min(a, c[0]), max(b, c[1]), t + " " + c[2]
        else:
            cols.append([a, b, t])
    return sorted(tuple(c) for c in cols)


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


STATION_W = re.compile(r"विद्यालय|स्कूल|कालेज|कॉलेज|भवन|केन्द्र|केंद्र|पंचायत|मन्दिर|मंदिर|मदरसा|मकतब|क0\s*सं|क0\s*न0|कक्ष"
                       r"|school|college|bhawan|bhavan|room", re.I)
GUESSED = "columns named by this reader: the PDF has no header text (an image or nothing)"


def _guess_head(pages):
    """No header line in the whole file (Varanasi: the header row is an image): name the columns from the data lines.
    The most common field count among lines with a mobile gives the columns; a column of mobiles is "Mobile", of small
    numbers "Part No", of school or building words "Polling station name"; the first other text column is "BLO name",
    the next "Designation". None when there is no mobile column or fewer than 5 such lines."""
    lines = []
    for page in pages:
        kd = kd_page(page)
        for line in page.splitlines():
            flds = _fields(line)
            if kd:
                flds = kd_fields(flds)
            if len(flds) >= 3 and MOBILE.search(line):
                lines.append(flds)
    if len(lines) < 5:
        return None
    counts = {}
    for f in lines:
        counts[len(f)] = counts.get(len(f), 0) + 1
    n = max(counts, key=lambda k: (counts[k], k))
    good = [f for f in lines if len(f) == n]
    cols = list(zip(*good))

    def share(rx_ok, c):
        return sum(1 for _, _, t in c if rx_ok(t)) / len(c)
    mob = max(range(n), key=lambda i: share(lambda t: bool(MOBILE.fullmatch(t)), cols[i]))
    if share(lambda t: bool(MOBILE.fullmatch(t)), cols[mob]) < 0.6:
        return None
    names = {mob: "Mobile"}
    part = max(range(n), key=lambda i: share(lambda t: bool(INT.match(t)), cols[i]))
    if part not in names and share(lambda t: bool(INT.match(t)), cols[part]) >= 0.6:
        names[part] = "Part No"
    text = [i for i in range(n) if i not in names]
    st = max(text, key=lambda i: share(lambda t: bool(STATION_W.search(t)), cols[i]), default=None)
    if st is not None and share(lambda t: bool(STATION_W.search(t)), cols[st]) >= 0.5:
        names[st] = "Polling station name"
    for label in ("BLO name", "Designation"):
        rest = [i for i in text if i not in names]
        if rest:
            names[rest[0]] = label
    starts = [sorted(a for a, _, _ in c)[len(c) // 2] for c in cols]
    return [(starts[i], starts[i] + 1, names.get(i, f"Column {i + 1}")) for i in range(n)]


def rows_from_pages(pages, p, head=None):
    """pages: layout text per page. Returns blo.py form rows. head: columns to start with (from _guess_head)."""
    guessed = head is not None
    lab, rows, starts = (_labels(head) if head else {}), [], None
    for page_no, page in enumerate(pages, 1):
        items, pending, prev = [], [], []     # pass 1: data lines with the wrapped cell parts above them
        pos_of = {}                           # source trail: item index -> src_pos of its data line
        kd = kd_page(page)
        for n_line, line in enumerate(page.splitlines()):
            if not line.strip():
                continue
            flds = _fields(line)
            if kd:          # convert cell by cell: the column positions stay those of the PDF's own text
                flds = kd_fields(flds)
            texts = [f[2] for f in flds]
            above, prev = prev, flds
            if _is_header(texts):
                flds = _merge_above(flds, above)
                if head is None or len(flds) >= len(head):
                    head, lab, starts = flds, _labels(flds), None
                pending = []
                continue
            if head is None or _numbering(texts):
                continue
            has_part = any(INT.match(t) or LEAD_INT.match(t) for t in texts)
            if len(flds) >= max(3, len(head) - 3) and (has_part or MOBILE.search(line)):
                last = items[-1] if items and not pending and items[-1][4] == n_line - 1 else None
                if last and not has_part and MOBILE.search(line) and not MOBILE.search(" ".join(t for _, _, t in last[0])):
                    # "7 | station | क0" then "स01 | name | post | office | mobile": one row typed on two lines
                    items[-1] = (last[0] + flds, last[1], False, last[3], n_line)
                    pos_of[len(items) - 1]["line_end"] = n_line + 1
                else:
                    items.append((_split(flds, len(head)), pending, len(flds) == len(head), [], n_line))
                    pos_of[len(items) - 1] = {"page": page_no, "line": n_line + 1, "line_text": line}
                pending = []
            elif TITLE.search(" ".join(texts)):
                pending = []                # "बी0एल0ओ0 सूची - 388 वाराणसी उत्तरी": a title, not part of a cell
            elif items and not pending and items[-1][4] == n_line - 1 and MOBILE.search(line):
                items[-1][3].extend(flds)   # a short line with a mobile right below a row: the rest of that row's cells
            else:
                pending = pending + flds   # page footers at the end are dropped with the page
        if head is None:
            continue
        good = [f for f, _, _, _, _ in items if len(f) == len(head)]   # median start per column: outliers do not move it
        starts = _starts(good, head) if good else (starts or _starts([], head))
        for k, (flds, above, exact, below, _) in enumerate(items):      # pass 2: fields -> columns
            cells = {}
            for h, f in _map(head, flds, starts, exact, lab):
                cells[h] = (cells[h] + " " + f[2]) if h in cells else f[2]
            for pf in above:
                h = _map(head, [pf], starts, lab=lab)[0][0]
                cells[h] = (pf[2] + " " + cells[h]) if cells.get(h) else pf[2]
            for pf in below:
                h = _map(head, [pf], starts, lab=lab)[0][0]
                cells[h] = (cells[h] + " " + pf[2]) if cells.get(h) else pf[2]
            rows.append(_row(cells, lab, p))
            rows[-1]["src_pos"] = pos_of[k]       # page: 1-based; line: 1-based in the page's layout text (blank lines counted)
            rows[-1]["method"] = "pdf text (pypdf layout) + Kruti Dev map" if kd else "pdf text (pypdf layout)"
            if guessed:
                rows[-1]["cells"]["_columns"] = GUESSED
    if not rows and not guessed:
        head = _guess_head(pages)
        if head:
            return rows_from_pages(pages, p, head)
    return _shared_phone(rows)


def _shared_phone(rows):
    """A number given as the BLO's mobile in 5+ rows and 20%+ of the file is a supervisor's or an office's (Meerut Cantt prints
    the supervisor's mobile in every row, and the columns drift): use another mobile of the row, else none. Cells keep all."""
    count = {}
    for r in rows:
        if r["blo_phone"]:
            count[r["blo_phone"]] = count.get(r["blo_phone"], 0) + 1
    for ph, c in count.items():
        if c < 5 or c < 0.2 * len(rows):
            continue
        for r in rows:
            if r["blo_phone"] == ph:
                other = [m.group(1) for h, v in sorted(r["cells"].items(), key=lambda hv: bool(SUPERVISOR.search(hv[0])))
                         for m in MOBILE.finditer(v) if m.group(1) != ph]
                r["blo_phone"] = other[0] if other else ""
    return rows


def _row(cells, lab, p):
    f = {}
    for h, v in cells.items():
        if h in lab and lab[h] not in f:
            f[lab[h]] = v
    phone = (MOBILE.search(f.get("blo_phone", "")) or MOBILE.search(" ".join(v for h, v in cells.items() if not SUPERVISOR.search(h)))
             or MOBILE.search(" ".join(cells.values())))     # columns drift: the BLO's own number can sit in the supervisor cell
    other = f.get("blo_phone", "") if len(re.findall(r"\d", f.get("blo_phone", ""))) >= 6 else ""
    ac_no = f.get("ac_no")
    ac_no = int(ac_no) if ac_no and ac_no.isdigit() else p.get("ac_no")
    part = f.get("part_no", "")
    if not part.isdigit():   # "26" glued to wrapped station text in the same cell: "... purbi 26"
        m = re.match(r"^(\d{1,4})\b", part) or re.search(r"\b(\d{1,4})$", part)
        ints = [t for t in part.split() if INT.match(t)]
        part = m.group(1) if m else ints[0] if len(ints) == 1 else part   # "कुबेर ... रोड 10 रोशनपुर": one number only
    part = int(part) if part.isdigit() else part
    name = f.get("blo_name", "")
    if MOBILE.fullmatch(name.strip()):   # the name was glued to the station cell; the cells keep it
        name = ""
    if ac_no is None:     # no AC known: keep record ids unique per file
        ac_no = "f" + re.sub(r"\W", "", p.get("url", "").rsplit("/", 1)[-1].rsplit(".", 1)[0])[-16:]
    r = {"ac_no": ac_no,
         "ac_name": f.get("ac_name") if f.get("ac_name") and not f.get("ac_name", "").isdigit() else p.get("ac_name"),
         "district": p.get("district"), "part_no": part, "station": f.get("station", ""), "blo_name": name,
         "blo_phone": phone.group(1) if phone else other, "cells": dict(cells)}
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
