"""Delhi: Delhi State Election Commission lists of elected MCD councillors (sec.delhi.gov.in).

- "mcd2022": the SEC's own list of all 250 winners of the MCD general election, 04.12.2022 (16-page scan, no text layer).
  Ruled table, one line per ward: Sr. No | Ward No | Ward Name | Reservation Status | Name of the Elected Councillor | Party.
  The page is warped (its vertical rules lean by different amounts), so each row between two horizontal rules is cut out
  and read as one text line; the reservation word and the party name split the line into its fields. Wards are listed in
  order, so the ward number is checked against the row order.
- "bye2025": Delhi Gazette list of the 12 wards of the bye-election of 30.11.2025. The Hindi half is in a legacy font; the
  English half has a clean text layer, read with pdftotext -layout.
The 2022 winner of a ward that had a bye-election gets the id suffix "-2022" (payload bye_wards); the bye winner holds the
plain id councillor:DL:municipal-corporation-of-delhi:<ward no>.
One queue item = one PDF and a page range (payload first, last).
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

from cforms import hr

METHOD = "ocr tesseract eng (one strip per ruled row) or pdf text (pdftotext -layout), by payload source"     # source trail (provenance.py): how this reader reads its sources

BODY = "Municipal Corporation of Delhi"
COLS = ["sr", "ward", "ward_name", "reservation", "name", "party"]
PARTIES = [("BHARATIYA JANATA PARTY", "Bharatiya Janata Party"), ("AAM AADMI PARTY", "Aam Aadmi Party"),
           ("INDIAN NATIONAL CONGRESS", "Indian National Congress"), ("ALL INDIA FORWARD BLOC", "All India Forward Bloc"),
           ("BAHUJAN SAMAJ PARTY", "Bahujan Samaj Party"), ("INDEPENDENT", "Independent")]


def party(s):
    t = re.sub(r"[^A-Z]", "", (s or "").upper())
    if re.search(r"BHA|JANAT|BJP", t):
        return "Bharatiya Janata Party"
    if re.search(r"AAM|AADM|ADMI|AAP", t):
        return "Aam Aadmi Party"
    if re.search(r"CONG|NATIONALC", t):
        return "Indian National Congress"
    if re.search(r"FORWARD|BLOC", t):
        return "All India Forward Bloc"
    if re.search(r"INDEP|NDEPEND", t):
        return "Independent"
    if re.search(r"BAHUJAN|BSP", t):
        return "Bahujan Samaj Party"
    return hr.clean(s)


def reservation(s):
    t = re.sub(r"[^A-Z]", "", (s or "").upper())
    if t.startswith("SC") and ("W" in t[2:] or "WOMAN" in t):
        return "SC Woman"
    if t.startswith("SC") or "SCHED" in t:
        return "SC"
    if "WOM" in t or "WMN" in t:
        return "Woman"
    if "GEN" in t or "ENERAL" in t:
        return "General"
    return hr.clean(s)


def title(s):
    s = hr.clean(s)
    return " ".join(w.title() if w.isupper() and len(w) > 1 else w for w in s.split())


def record(p, ward, ward_name, res, name, pty, page, read, pos=None):
    bye = p.get("source") == "bye2025"
    rid = f"councillor:DL:{hr.slug(BODY)}:{ward}"
    status = None
    if not bye and int(ward) in set(p.get("bye_wards", [])):
        rid += "-2022"
        status = "seat filled again in the bye-election of 30.11.2025"
    d = {"type": "councillor", "state": "DL", "body": BODY, "body_type": "Municipal Corporation", "district": "Delhi",
         "ward_no": str(ward), "ward_name": title(ward_name), "name": title(name), "name_as_printed": hr.clean(name),
         "party": party(pty), "reservation": reservation(res), "position": "Councillor", "status": status,
         "election": "MCD bye-election 2025" if bye else "MCD 2022", "url": p["url"], "page": page, "read": read,
         "src_pos": {"page": page, **pos} if pos else None,
         "method": {"ocr": "ocr tesseract eng (one strip per ruled row)", "text layer": "pdf text (pdftotext -layout)"}.get(read)}
    return rid, {k: v for k, v in d.items() if v not in (None, "")}


def row_lines(pgm):
    """Horizontal rules of the table: y centres (the page is warped, so its vertical rules lean by different amounts and
    are not used; one table row is one text line)."""
    w, h, data = hr.read_pgm(pgm)
    bits = data.translate(hr.LINE)
    x0, x1 = w // 20, w - w // 20
    ys = []
    for y in range(h - 3):
        r = hr._pool([bits[(y + k) * w + x0:(y + k) * w + x1] for k in range(3)])
        if hr._long(r, 120) > 0.45 * (x1 - x0):
            ys.append(y)
    return w, h, data, [(g0 + g1) // 2 for g0, g1 in hr._groups(ys)]


def strips(pgm, tmp, page, lang):
    """Each table row (between two rules) cut out, the strips stacked with white gaps and read in one Tesseract run."""
    w, h, data, hl = row_lines(pgm)
    rows = [(a, b) for a, b in zip(hl, hl[1:]) if 25 <= b - a <= 220]
    gap = 40
    img, spans = bytearray(), []
    for a, b in rows:
        y0, y1 = a + 6, b - 5
        strip = bytearray(data[y0 * w:y1 * w]).translate(hr.BIN)
        hh = y1 - y0
        for x in range(w):            # vertical rules inside the strip: dark for most of its height -> white
            col = strip[x::w]
            if col.count(0) >= 0.7 * hh:
                strip[x::w] = bytes([255]) * hh
        spans.append((len(img) // w, len(img) // w + hh))
        img += strip + bytes([255]) * (w * gap)
    if not rows:
        return []
    path = os.path.join(tmp, f"rows{page}.pgm")
    hr.write_pgm(path, w, len(img) // w, img)
    out = [[] for _ in rows]
    for cx, cy, t, conf in hr.words(path, lang, "6"):
        i = next((k for k, (s0, s1) in enumerate(spans) if s0 - 10 <= cy <= s1 + 10), None)
        if i is not None and conf >= 10:
            out[i].append((cx, t))
    return [" ".join(t for _, t in sorted(r)) for r in out]


RES = re.compile(r"^(GENERAL|GENERA\w*|GENRAL|WOMAN|W[O0]MAN|WOMEN|SC|S\.?C\.?|SCW|SC-?WOMAN)$", re.I)
PARTY_START = re.compile(r"^(BHARATIYA|BHARTIYA|JANATA|AAM|AADMI|INDIAN|CONGRESS|BAHUJAN|INDEPENDENT|ALL|FORWARD|NATIONALIST|"
                         r"SAMAJWADI)", re.I)


def parse_row(text):
    """"12. 12 MALKA GANJ SCW REKHA BHARATIYA JANATA PARTY" -> (sr, ward, ward name, reservation, name, party)."""
    toks = [t.strip(".,'‘’`\"!;:_—–~()[]{}") for t in text.replace("|", " ").split()]
    # the list is printed in capitals: lower-case tokens are OCR noise (stray marks, table rules)
    toks = [t for t in toks if re.search(r"[A-Za-z0-9]", t) and (t.isupper() or RES.match(t) or re.fullmatch(r"[\dOIl.,]+", t))]
    if len(toks) < 5:
        return None
    nums = []
    while toks and re.fullmatch(r"[\dOIl|.,]+", toks[0]) and len(nums) < 2:
        nums.append(hr.fix_ward(toks.pop(0)))
    ri = next((i for i, t in enumerate(toks) if RES.match(t.strip(".,"))), None)
    if ri is None:
        return None
    res = toks[ri]
    if res.upper().startswith("SC") and ri + 1 < len(toks) and re.match(r"W[O0]M", toks[ri + 1], re.I):
        res, ri2 = "SC WOMAN", ri + 1
    else:
        ri2 = ri
    rest = toks[ri2 + 1:]
    pi = next((i for i, t in enumerate(rest) if i > 0 and PARTY_START.match(t)), None)
    if pi is None:
        return None
    wname = toks[:ri]
    while wname and len(wname[0]) == 1:
        wname.pop(0)
    name = rest[:pi]
    while len(name) > 1 and len(name[-1]) <= 2:        # stray marks after the name
        name.pop()
    return (nums + ["", ""])[:2], " ".join(wname), res, " ".join(name), " ".join(rest[pi:])


def scan_page(p, pdf, page, tmp, state):
    out = []
    for k, text in enumerate(strips(hr.render(pdf, page, tmp), tmp, page, p.get("lang", "eng")), 1):
        got = parse_row(text)
        if not got:
            continue
        (sr, wd), wname, res, name, pty = got
        if state.get("last") is None:           # first row of an item that starts inside the file: trust the reading
            if not (wd or sr) or (wd and sr and wd != sr):
                continue
            ward = int(wd or sr)
        else:
            nxt = int(state["last"]) + 1
            # rows run 1..250 in order and Sr. No = Ward No: take the reading that fits the order, else the order itself
            ward = next((int(v) for v in (wd, sr) if v and int(v) == nxt), nxt)
        state["last"] = ward
        # source trail: k = the row's place among the page's ruled rows (top to bottom), its OCR text as read
        out.append(record(p, ward, wname, res, name, pty, page, "ocr", {"row": k, "line_text": text}))
    return out


def split_party(c):
    """Name and party sometimes run together on the row line: "SUMAN KUMAR BHARATIYA JANATA PARTY"."""
    joined = f"{c['name']} {c['party']}".strip()
    for up, _ in PARTIES:
        if up in joined.upper():
            i = joined.upper().index(up)
            c["name"], c["party"] = (joined[:i] + joined[i + len(up):]).strip(), up
            return


def text_rows(text, first=1, pos=None):
    """English list of the 2025 gazette (pdftotext -layout) -> [(ward, ward name, reservation, name, party, page)].
    pos: a list; when given, it gets each row's src_pos {"line": 1-based in its page's text, "line_text"}."""
    rows, starts, cur, page, li = [], None, None, first, 0
    for ln in text.split("\n"):              # not splitlines(): it would drop the form feeds that mark new pages
        if "\f" in ln:
            li = 0
        li += 1
        page += ln.count("\f")
        ln = ln.replace("\f", "")
        if re.match(r"\s*Sr\.?\s+Ward", ln):
            m = {k: ln.find(k) for k in ("Sr.", "Reservation", "Name of", "Party")}
            w = [x.start() for x in re.finditer(r"Ward", ln)]
            if len(w) >= 2 and all(v >= 0 for v in m.values()):
                starts = [m["Sr."], w[0], w[1], m["Reservation"], m["Name of"], m["Party"]]
            cur = None
            continue
        if starts is None:
            continue
        if re.search(r"Election Commissioner|DELHI GAZETTE", ln) or not ln.strip():
            cur = None if not ln.strip() else cur
            continue
        cells = hr.split_cols(ln, starts)
        c = dict(zip(COLS, cells))
        if re.fullmatch(r"\d+\.?", c["sr"]) and re.fullmatch(r"\d+", c["ward"]):
            cur = c
            c["page"] = page
            c["_pos"] = {"line": li, "line_text": ln}
            split_party(c)
            rows.append(c)
        elif cur is not None and not c["sr"] and not c["ward"]:
            for k in ("ward_name", "reservation", "name"):
                if c[k]:
                    cur[k] = (cur[k] + " " + c[k]).strip()
    out = []
    for c in rows:
        out.append((int(c["ward"]), c["ward_name"], c["reservation"], c["name"], c["party"], c["page"]))
        if pos is not None:
            pos.append(c["_pos"])
    return out


def fetch(p, get):
    scan = p.get("source") == "mcd2022"
    if (scan or not shutil.which("pdftotext")) and not hr.tools():
        return [], [], "tesseract or poppler not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    first, last = int(p.get("first", 1)), int(p.get("last", 1))
    files = [(f"councillors/DL/{key}.pdf", r.content, "application/pdf")] if first == 1 else []
    recs = []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(r.content)
        if scan:
            state = {"last": 0 if first == 1 else None}
            for pg in range(first, last + 1):
                recs += scan_page(p, pdf, pg, tmp, state)
        else:
            t = subprocess.run(["pdftotext", "-layout", "-f", str(first), "-l", str(last), pdf, "-"], capture_output=True,
                               text=True).stdout
            pos = []
            for row, rp in zip(text_rows(t, first, pos), pos):
                recs.append(record(p, *row, "text layer", rp))
    return recs, files, "" if recs else "no councillors read"
