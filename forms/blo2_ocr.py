"""Scanned district BLO lists, read by OCR (task "blo2-ocr", project civic-officials-blo2-ocr).

forms/blo2_pdf.py reads the BLO PDFs of district sites that have a text layer. Scans (no text layer) and files whose text
layer cannot be read (Kruti Dev or Type 3 fonts) come here. The reader does not need the site: it reads the copy of the PDF
in the bucket (payload "stored", saved by the first fetch), so any runner can take the item ("fetch once, process
anywhere"). Only when no copy is saved, it fetches the file once and saves it in its own project.

Each page: rendered at 300 dpi (grey); drawn pages (fonts, no page image) get grey cell shading turned white; the page is
straightened (the slope of its lines, from projection profiles); then the ruled table is read with the grid reader of
cforms/hr.py (lines found and erased, one Tesseract run per column). Numeric columns (part, mobile) are read a second
time with digits only. English pages accept faint, broken rules; Devanagari pages do not (word head lines look like rules).
Columns get their meaning from the header text (Hindi or English, H_RULES); a page without a header uses the header of the
page before it when the count of columns is the same, else the columns by content (content_labels).
Rules for a data row:
- part number: from the part cell, both readings ("9/ 12" = AC/part gives 12; "9112" can be 9/12), and from the serial
  cell when serial and part agree on the page. The list order decides between readings; a row between two parts one
  apart gets the part between them (cells._part_inferred). A row without a part number is dropped; the same part twice:
  the first is kept.
- mobile: exactly 10 digits, first digit 6-9 (or 91 + 10), after common OCR slips (O->0, l/I/|->1). Taken when one
  reading gives a clean number or both give the same one; two different clean readings: left empty.
- name: the BLO name cell. A Devanagari name with Latin fragments (words Tesseract could not read) is left empty, and
  the reading goes to cells._name_incomplete. "Name, post" cells are split.
- a cell with two part numbers or two mobile numbers (a rule between two rows not found): the row is dropped.
Records carry ocr: true and page. The OCR result of every page (cells per row, digit readings, confidences, lines, slope)
is saved next to the PDF as <path>.ocr.json.gz.
Payload: blo2_pdf's payload + {"kind": "form-blo2_ocr", "stored": ["<project>/<path>", ...], "lang" (optional)}.
"""
import concurrent.futures
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

import requests

from cforms import hr
from forms.blo2_pdf import store_path

# Tesseract languages per state (the payload's "lang" wins). Manipur, Mizoram, Meghalaya, Nagaland: English lists.
LANGS = {"UP": "hin+eng", "BR": "hin+eng", "MP": "hin+eng", "RJ": "hin+eng", "HR": "hin+eng", "DL": "hin+eng", "UK": "hin+eng",
         "JH": "hin+eng", "CG": "hin+eng", "HP": "hin+eng", "MH": "mar+eng", "GA": "mar+eng", "GJ": "guj+eng", "WB": "ben+eng",
         "TR": "ben+eng", "AS": "asm+eng", "OD": "ori+eng", "PB": "pan+eng", "TN": "tam+eng", "KA": "kan+eng", "KL": "mal+eng",
         "TG": "tel+eng", "AP": "tel+eng", "MN": "eng", "MZ": "eng", "ML": "eng", "NL": "eng", "AR": "eng", "SK": "eng"}
PACK = {"hin": "hin", "eng": "eng", "mar": "mar", "guj": "guj", "ben": "ben", "asm": "asm", "ori": "ori", "pan": "pan",
        "tam": "tam", "kan": "kan", "mal": "mal", "tel": "tel"}


def lang_of(p):
    return p.get("lang") or LANGS.get(p.get("state", ""), "eng")


def tools(lang):
    """Tesseract with the languages and poppler; installs them on a GitHub runner (sudo without password). A runner job runs
    two processes: while one installs, the other waits for the apt lock instead of failing every item it claims."""
    need = lang.split("+")

    def ok():
        if not (shutil.which("tesseract") and shutil.which("pdftoppm")):
            return False
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
        have = (r.stdout + r.stderr).split()
        return all(x in have for x in need)
    if ok():
        return True
    pkgs = " ".join(f"tesseract-ocr-{PACK[x]}" for x in need if x in PACK)
    cmd = ("sudo -n apt-get -o DPkg::Lock::Timeout=600 update -q && sudo -n apt-get -o DPkg::Lock::Timeout=600 install -y -q "
           f"tesseract-ocr {pkgs} poppler-utils")
    for _ in range(3):
        subprocess.run(cmd, shell=True, capture_output=True)
        if ok():
            return True
        time.sleep(30)
    return ok()


# ---------------------------------------------------------------- page image -> table

def skew(w, h, data, step=4, dark=150):
    """Slope dy/dx of the page's horizontal lines (table rules and text rows), by projection profiles on every 4th pixel:
    the slope that gives the sharpest row profile."""
    pts = []
    for y in range(0, h, step):
        row = data[y * w:(y + 1) * w:step]
        pts += [(x * step, y) for x, v in enumerate(row) if v < dark]
    if not pts:
        return 0.0
    if len(pts) > 200000:                      # dark scans: a sample is enough
        pts = pts[::len(pts) // 200000 + 1]

    def score(s):
        hist = {}
        for x, y in pts:
            k = int(y - s * x) // step
            hist[k] = hist.get(k, 0) + 1
        return sum(v * v for v in hist.values())
    best = max((i / 1000 for i in range(-40, 41, 2)), key=score)
    return max((best + i / 5000 for i in range(-5, 6)), key=score)


def straighten(w, h, data, s):
    """A small rotation as two shears: columns move by -s*x (rows level), then rows move by s*y (columns upright)."""
    if abs(s) < 0.0004:
        return data
    out = bytearray(b"\xff" * (w * h))
    for x in range(w):
        col = data[x::w]
        d = int(round(-s * (x - w / 2)))
        if d > 0:
            col = b"\xff" * d + col[:h - d]
        elif d < 0:
            col = col[-d:] + b"\xff" * (-d)
        out[x::w] = col
    return hr.shear(out, w, h, s)


DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "l": "1", "I": "1", "|": "1", "i": "1", "]": "1", "[": "1",
                           "!": "1", "S": "5", "s": "5", "B": "8", "Z": "2", "z": "2", "G": "6", "b": "6", "q": "9", "g": "9",
                           "०": "0", "१": "1", "२": "2", "३": "3", "४": "4", "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"})


WHITEN = bytes(255 if i > 170 else i for i in range(256))


def page_table(pdf, page, tmp, lang, vector=False):
    """One page -> {"slope", "rows": [[cell text per column]], "digits": [[digits-only reading per column]]}. digits is
    filled for every column whose cells look like numbers, from a second Tesseract run (eng, digits only).
    vector: the page is drawn, not scanned (a legacy-font text layer): grey cell shading is turned white first, else the
    grid reader takes a shaded column for a thick line and erases its text. English pages: faint, broken rules count as
    lines (Devanagari and Bengali words have a head line, so those pages keep the strict rule)."""
    pgm = hr.render(pdf, page, tmp)
    w, h, data = hr.read_pgm(pgm)
    if vector:
        data = data.translate(WHITEN)
    s = skew(w, h, data)
    hr.write_pgm(pgm, w, h, straighten(w, h, data, s))
    meta = {}
    loose = {"hcover": 0.4, "hrun": 0.25} if lang == "eng" else {}
    rows = hr.table_pgm(pgm, lang, meta=meta, **loose)
    out = {"page": page, "slope": round(s, 5), "rows": [r["cells"] for r in rows], "vl": meta.get("vl", []),
           "hl": meta.get("hl", []), "conf": [[None if c is None else round(c) for c in r["conf"]] for r in rows]}
    if not rows:
        return out
    hl, ncol = meta["hl"], len(meta["vl"]) - 1

    def numeric(i):
        vals = [r["cells"][i] for r in rows if r["cells"][i].strip()]
        dig = [v for v in vals if len(re.sub(r"\D", "", v.translate(DIGIT_FIX))) >= 1
               and len(re.sub(r"[\W\d_]", "", v.translate(DIGIT_FIX))) <= 2]
        return len(vals) >= 2 and len(dig) >= 0.6 * len(vals) or any(len(re.sub(r"\D", "", v)) >= 7 for v in vals)

    def digits(i):
        path, ax, ay = meta["strips"][i]
        r = subprocess.run(["tesseract", path, "-", "-l", "eng", "--psm", "6", "-c", "tessedit_char_whitelist=0123456789/",
                            "tsv"], capture_output=True, text=True)
        cells = [[] for _ in rows]
        for ln in r.stdout.splitlines()[1:]:
            f = ln.split("\t")
            if len(f) < 12 or not f[11].strip():
                continue
            x, y, ww, hh = map(int, f[6:10])
            cy = y + hh / 2 + ay
            if not hl[0] < cy < hl[-1]:
                continue
            ri = max(k for k, a in enumerate(hl[:-1]) if a <= cy)
            cells[ri].append((x + ax, f[11].strip()))
        return i, [" ".join(t for _, t in sorted(c)) for c in cells]

    cols = [i for i in range(ncol) if numeric(i)]
    out["digits"] = {}
    with concurrent.futures.ThreadPoolExecutor(3) as ex:
        for i, cells in ex.map(digits, cols):
            out["digits"][str(i)] = cells
    return out


def ocr_pages(pdf_bytes, lang, first=1, last=None):
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "f.pdf")
        with open(pdf, "wb") as f:
            f.write(pdf_bytes)
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        n = int(m.group(1)) if m else 1
        pages = range(first, min(n, last or n) + 1)
        # a page is drawn (vector) when the file has fonts and the page has no large image (scans carry the page as images)
        fonts = subprocess.run(["pdffonts", pdf], capture_output=True, text=True).stdout.splitlines()[2:]
        scanned = set()
        for ln in subprocess.run(["pdfimages", "-list", pdf], capture_output=True, text=True).stdout.splitlines()[2:]:
            f = ln.split()
            if len(f) > 4 and f[0].isdigit() and f[3].isdigit() and int(f[3]) >= 1000:
                scanned.add(int(f[0]))
        return [page_table(pdf, pg, tmp, lang, vector=bool(fonts) and pg not in scanned) for pg in pages]


# ---------------------------------------------------------------- table -> BLO rows

DEV = re.compile(r"[ऀ-ॿ]")
BOOTH = r"(?:ब[ुू]?[थधद]|भाग|मतद[ेा]\S*|part|booth|polling\s*station|p\.?\s*s\.?)"
NUMW = r"(?:सं|संख्या|क्र|न0|नं|नम्बर|no|number|num)"
H_RULES = [   # (field, pattern) in order: the first field whose pattern matches a header cell takes the column
    ("blo_phone", re.compile(r"mob|contact|phone|cell|मोबा|मोत्रा|मोबइ|मो0|मो\.|दूरभाष|फोन|फ़ोन", re.I)),
    ("designation", re.compile(r"^(?!.*(?:नाम\s*(?:एवं|व|और)|name\s*(?:and|&))).*(?:design|^\W*post\W*$|पद\s*[नत]ाम|पदनाम|का पद|^पद)", re.I)),
    ("blo_name", re.compile(r"(blo|b\.l\.o|officer|अधिकारी|अधिकरी|बी0\s*एल0|बीएलओ|बी\.एल\.ओ)|^\W*name\W*$|^\W*नाम\W*$", re.I)),
    ("part_no", re.compile(rf"^(?!.*(?:नाम|name)).*{BOOTH}\W*\s*{NUMW}|^\W*part\W*$", re.I)),
    ("serial", re.compile(r"^\W*(sl|sr|s)\W*\s*no|^\W*s\.?\s*n\.?\W*$|क्र\W*\s*सं|क्र0|क्रम|क्रमांक|^\W*क्र", re.I)),
    ("station", re.compile(rf"{BOOTH}|station|building|location|केन्द्र|केंद्र|भवन|स्थल|विद्यालय", re.I)),
    ("department", re.compile(r"depart|institution|office|विभाग|कार्यालय|संस्था", re.I)),
    ("address", re.compile(r"address|पता|निवास", re.I)),
    ("block", re.compile(r"block|ब्ला|ब्लॉ|लाक|विकास\s*खण्ड|विकासखंड", re.I)),
]
MOBILE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
# posts that end a "name and post" cell when the comma between them was not read
POST_END = re.compile(r"\s(?:आं?ग[नं]?\s?[बव]ा[डड़]ी\s+)?(?:सेविका|सहायिका|शिक्षक|शिक्षिका|विकास मित्र|टोला सेवक|लिपिक|पंचायत सचिव|"
                      r"आवास सहायक|किसान सलाहकार|कार्यपालक सहायक|जीविका\s*\S*|ए\.?एन\.?एम\.?)$")
PART_PAIR = re.compile(r"(\d{1,3})\s*[/|)}\]]\s*(\d{1,4})")


def labels(head):
    """Header text per column -> {column: field}. Each field is used once."""
    out, used = {}, set()
    for i, t in enumerate(head):
        t = " ".join(t.split())
        if not t:
            continue
        for name, rx in H_RULES:
            if name not in used and rx.search(t):
                out[i] = name
                used.add(name)
                break
    return out


def phone_of(t):
    """The mobile number in one reading of a cell: exactly 10 digits (or 91 + 10) after common OCR slips, else ''."""
    d = re.sub(r"[\s\-.,+]", "", (t or "").translate(DIGIT_FIX))
    n = re.sub(r"\D", "", d)
    if len(n) == 12 and n.startswith("91"):
        n = n[2:]
    return n if len(n) == 10 and n[0] in "6789" and len(d) - len(n) <= 2 else ""


def phone_pick(*readings):
    """Readings of one cell (digits-only pass, normal pass): a number when one reading gives a clean number, or both give
    the same; '' when two clean readings disagree."""
    got = {phone_of(r) for r in readings} - {""}
    return got.pop() if len(got) == 1 else ""


def numbers(t):
    return [int(x) for x in re.findall(r"\d{1,5}", (t or "").translate(DIGIT_FIX))]


def part_cands(t, ac):
    """Part numbers one reading of the part cell can mean. ac: the AC number that the column puts before the part
    ("9/ 12", read as "9112", "9 12" or "gf 12"), or None."""
    t = (t or "").translate(DIGIT_FIX)
    m = PART_PAIR.search(t)
    if m:
        return [int(m.group(2))]
    ns = numbers(t)
    if not ns:
        return []
    if ac is None:
        return [ns[0]]
    a = str(ac)
    if len(ns) >= 2:
        return [ns[-1]]
    s = str(ns[0])
    if s.startswith(a) and len(s) > len(a):
        rest = s[len(a):]
        out = [int(rest[1:])] if rest[0] == "1" and len(rest) >= 2 else []     # "9/12" read as "9112": the slash as a 1
        return out + [int(rest), ns[0]]
    return [ns[0]]


def clean_name(t):
    """(name, complete): Latin fragments in a Devanagari name are OCR noise from words Tesseract could not read; such a
    name is incomplete."""
    t = hr.clean(t)
    if not DEV.search(t):
        return t, True
    words = t.split()
    keep = [w for w in words if DEV.search(w)]
    t = re.sub(r"\s+([ािीुूृेैोौंँः्])", r"\1", " ".join(keep))
    return hr.clean(t), len(keep) == len(words)


def _filled(rows, i):
    return sum(1 for r in rows if r[i].strip())


def content_labels(rows, dig):
    """Columns by content, for pages whose header is missing or unreadable: the mobile column has the most clean numbers;
    the part column is the last numeric column before the first text column; the next two text columns are the polling
    station and the BLO name (the order in every list seen)."""
    n = len(rows[0])
    lab, used = {}, set()
    ph = max(range(n), key=lambda i: sum(1 for k, r in enumerate(rows) if phone_pick(dig.get(i, [""] * len(rows))[k], r[i])))
    if sum(1 for k, r in enumerate(rows) if phone_pick(dig.get(ph, [""] * len(rows))[k], r[ph])) >= max(1, len(rows) // 3):
        lab[ph] = "blo_phone"
        used.add(ph)
    live = [i for i in range(n) if i not in used and _filled(rows, i) >= max(1, len(rows) // 3)]

    def numeric(i):
        vals = [r[i] for r in rows if r[i].strip()]
        ok = [v for v in vals if numbers(v) and len(re.sub(r"[\W\d_]", "", v.translate(DIGIT_FIX))) <= 2]
        return len(ok) >= 0.6 * len(vals)
    nums = [i for i in live if numeric(i)]
    texts = [i for i in live if i not in nums and i != ph]
    first_text = texts[0] if texts else n
    before = [i for i in nums if i < first_text]
    if before:
        lab[before[-1]] = "part_no"
        if len(before) >= 2:
            lab[before[-2]] = "serial"
    for i, f in zip(texts, ("station", "blo_name", "designation")):
        lab[i] = f
    return lab


def _numbering(cells):
    vals = [c.strip() for c in cells if c.strip()]
    return len(vals) >= 4 and all(re.fullmatch(r"\d{1,2}\W?", v) for v in vals)


def _datalike(cells, digits):
    return any(phone_of(x) for x in list(cells) + list(digits))


def _ac_prefix(vals):
    """The AC number that most part cells start with ("9/ 12"), or None."""
    lead = [int(m.group(1)) for v in vals for m in [PART_PAIR.search((v or "").translate(DIGIT_FIX))] if m]
    if len(lead) < max(2, len([v for v in vals if v.strip()]) // 3):
        return None
    top = max(set(lead), key=lead.count)
    return top if lead.count(top) >= 0.6 * len(lead) else None


def pick_parts(cands):
    """One part number per row from the candidates of its readings (with votes), using the order of the list: a value
    that continues the sequence from a neighbour wins; a row between two neighbours one apart from it gets the number
    between them (marked inferred)."""
    n = len(cands)
    val = []
    for c in cands:
        val.append(max(c, key=lambda x: (c[x], -list(c).index(x))) if c else None)
    for _ in range(2):
        for k in range(n):
            prev = val[k - 1] if k and val[k - 1] is not None else None
            nxt = val[k + 1] if k + 1 < n and val[k + 1] is not None else None
            if prev is not None and val[k] == prev + 1 or nxt is not None and val[k] == nxt - 1:
                continue
            if prev is not None and prev + 1 in cands[k]:
                val[k] = prev + 1
            elif nxt is not None and nxt - 1 in cands[k]:
                val[k] = nxt - 1
    inferred = [False] * n
    for k in range(1, n - 1):
        a, b = val[k - 1], val[k + 1]
        if a is not None and b is not None and b == a + 2 and val[k] != a + 1:
            val[k], inferred[k] = a + 1, True
    return val, inferred


def parse(pages, p):
    """OCR pages (page_table results) -> blo form rows (the fields of blo2_pdf, plus ocr, page and checks)."""
    head_lab, head_n, items = {}, None, []
    for pg in pages:
        rows = pg.get("rows") or []
        if not rows:
            continue
        n = len(rows[0])
        dig = {int(k): v for k, v in (pg.get("digits") or {}).items()}
        first = next((k for k, r in enumerate(rows) if _datalike(r, [dig[c][k] for c in dig])), None)
        numbering = next((k for k, r in enumerate(rows) if _numbering(r)), None)
        if numbering is not None and (first is None or numbering < first):
            first = numbering + 1          # the "1 2 3 4 ..." line under the header: data starts below it
        if first is None or first >= len(rows):
            continue
        head = [" ".join(r[i] for r in rows[:first] if not re.fullmatch(r"[\d\s.|]*", " ".join(r))).strip() for i in range(n)]
        got = labels(head) if any(head) else {}
        if "blo_name" in got.values() or "blo_phone" in got.values():
            head_lab, head_n = got, n
        data = rows[first:]
        ddig = {c: v[first:] for c, v in dig.items()}
        lab = dict(content_labels(data, ddig))
        if head_n == n:          # the header of this page or of the page before it (same columns) wins
            lab = {i: f for i, f in lab.items() if f not in head_lab.values() and i not in head_lab}
            lab.update(head_lab)
        cols = {f: i for i, f in lab.items()}
        names = {i: (head[i] if head[i] else f"col{i + 1}") for i in range(n)}
        pi, si, phi = cols.get("part_no"), cols.get("serial"), cols.get("blo_phone")
        sti = cols.get("station")
        if pi is None and sti is not None and \
                sum(1 for r in data if re.match(r"^\W*\d{1,4}\b", r[sti].translate(DIGIT_FIX))) >= 0.6 * len(data):
            pi = sti                       # "05 उच्च विद्यालय ...": the part number leads the polling station cell
        if pi is None and si is not None:
            pi, si = si, None
        ac = _ac_prefix([r[pi] for r in data] + ddig.get(pi, [])) if pi is not None else None
        same = 0
        for k, r in enumerate(data):
            if pi is not None and si is not None:
                a = part_cands(ddig.get(pi, [""] * len(data))[k] or r[pi], ac)
                b = numbers(ddig.get(si, [""] * len(data))[k] or r[si])
                same += bool(a and b and a[0] == b[0])
        serial_is_part = si is not None and same >= 0.6 * len(data)
        for k, r in enumerate(data):
            votes = {}
            if pi is not None:
                for t in (ddig.get(pi, [""] * len(data))[k], r[pi]):
                    for x in part_cands(t, ac):
                        if 0 < x < 1000:
                            votes[x] = votes.get(x, 0) + 1
            if serial_is_part:
                for t in (ddig.get(si, [""] * len(data))[k], r[si]):
                    for x in numbers(t)[:1]:
                        if 0 < x < 1000:
                            votes[x] = votes.get(x, 0) + 1
            phone = phone_pick(ddig.get(phi, [""] * len(data))[k], r[phi]) if phi is not None else ""
            two = [r[phi], ddig.get(phi, [""] * len(data))[k]] if phi is not None else []
            if pi is not None and len(PART_PAIR.findall(r[pi].translate(DIGIT_FIX))) >= 2 or \
                    any(sum(1 for x in t.split() if phone_of(x)) >= 2 for t in two):
                continue                   # two table rows in one (a rule between them was not found): not split, dropped
            name, whole = clean_name(r[cols["blo_name"]]) if "blo_name" in cols else ("", True)
            post = ""
            if "blo_name" in cols and re.search(r"पद|post|desig", head[cols["blo_name"]], re.I):
                if "," in name:            # "शान्ति देवी, सेविका": name and post in one cell
                    name, post = (x.strip() for x in name.split(",", 1))
                else:
                    m = POST_END.search(name)
                    if m and m.start() > 0:
                        name, post = name[:m.start()].strip(), m.group(0).strip()
            if not (phone or name) or not votes and not phone:
                continue
            cells = {names[i]: r[i] for i in range(n)}
            if phi is not None and ddig.get(phi, [""] * len(data))[k]:
                cells["_mobile_digits"] = ddig[phi][k]
            items.append({"votes": votes, "phone": phone, "name": name if whole else "", "name_read": name, "cells": cells,
                          "station": hr.clean(r[cols["station"]]) if "station" in cols else "",
                          "designation": post or (hr.clean(r[cols["designation"]]) if "designation" in cols else ""),
                          "page": pg.get("page")})
    parts, inferred = pick_parts([it["votes"] for it in items])
    out, seen = [], set()
    for it, part, inf in zip(items, parts, inferred):
        if part is None or part in seen:       # no number, or the same part read twice (keep the first)
            continue
        seen.add(part)
        row = {"ac_no": p.get("ac_no"), "ac_name": p.get("ac_name"), "district": p.get("district"), "part_no": part,
               "station": it["station"], "blo_name": it["name"], "blo_phone": it["phone"], "cells": it["cells"],
               "ocr": True, "page": it["page"]}
        if it["designation"]:
            row["designation"] = it["designation"]
        if inf:
            row["cells"]["_part_inferred"] = True
        if not it["name"] and it["name_read"]:
            row["cells"]["_name_incomplete"] = it["name_read"]
        for key in ("list_date", "source_page"):
            if p.get(key):
                row["cells"]["_" + key] = p[key]
        out.append(row)
    return out


# ---------------------------------------------------------------- the bucket copy

def stored(p, hub):
    """The PDF from the bucket (payload "stored": "<project>/<path>", or a list); None when no copy is there."""
    keys = p.get("stored") or []
    keys = [keys] if isinstance(keys, str) else list(keys)
    own = os.environ.get("SCRAPE_POOL_PROJECT")
    if own:
        keys.append(f"{own}/{store_path(p)}")
    for k in keys:
        if not hub or "/" not in k:
            continue
        try:
            url = hub.read_urls(k.split("/", 1)[0], [k]).get(k)
            if not url:
                continue
            r = requests.get(url, timeout=(20, 180))
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content
        except Exception:  # noqa: BLE001 - try the next copy, then the site
            continue
    return None


def read(s, p, hub=None):
    """(rows, files, why). files: the PDF when it had to be fetched from the site, and the OCR result."""
    lang = lang_of(p)
    if not tools(lang):
        return [], [], f"tesseract {lang} not available"
    files = []
    content = stored(p, hub)
    if content is None:
        r = s.get(p["url"], timeout=(20, 180))
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            return [], [], "not a PDF"
        content = r.content
        files.append((store_path(p), content, "application/pdf"))
    pages = ocr_pages(content, lang, int(p.get("first", 1)), p.get("last"))
    raw = {"url": p["url"], "lang": lang, "sha256": hashlib.sha256(content).hexdigest(), "pages": pages}
    files.append((store_path(p)[:-4] + ".ocr.json.gz", gzip.compress(json.dumps(raw, ensure_ascii=False).encode()),
                   "application/gzip"))
    rows = parse(pages, p)
    if rows:
        return rows, files, ""
    found = sum(len(pg.get("rows") or []) for pg in pages)
    return [], files, f"no rows (ocr {len(pages)} pages, {found} table rows)"
