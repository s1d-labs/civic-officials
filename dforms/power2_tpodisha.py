"""Odisha: the four Tata Power discoms (TPCODL central, TPSODL southern, TPWODL western, TPNODL northern). They share one web
template (ASP.NET, /contactus.aspx with "Customer Touch Points" and "Grievance Escalation Matrix" tabs) but each one publishes its
officer list in another file, so one queue item = one file, with "kind":
- "xlsx" (TPNODL, www.tpnodl.com/xl/contact/Worksheet-in-TPNODL-Contact-Us.xlsx, linked as "Download the contact details of Circle
  and Division offices"): sheet CIRCLE (5 circles: S.No., Circle/Division, Office Address, Office Incharge, Designation, Mobile No.,
  Email ID, Alternate Email ID) and sheet DIVISION (16 divisions: S.No., Circle, Division, Office Address, Office Incharge,
  Designation, Mobile No., Email ID). Names, mobiles and e-mails of the Superintending and Executive Engineers. 21 rows.
- "rti_manual" (TPSODL, tpsouthernodisha.com/Editor_UploadedDocuments/Content/RTI_Eng_Manual16.09.2025.pdf, "Manual-9 updated date:
  15.09.2025"): Manual-9 "Directory of Officers and employees": the corporate heads, then one block per circle (CITY, BERHAMPUR, ASKA,
  BHANJANAGAR, RAYAGADA, JEYPORE CIRCLE): office name, designation, address, name of the HOD, mobile, e-mail (cut over two lines),
  then the four GRF presidents. 33 corporate rows + 6 circles + 20 divisions + 4 GRF = 63 rows. Read from `pdftotext -layout` text
  (India pool servers): each "Mr./Ms." in the name column is one officer; the other cells go to the nearest officer line.
- "pio_pdf" (TPCODL, www.tpcentralodisha.com/Editor_UploadedDocuments/RTI/PIO_Appellate_Authority.pdf, one page, no date): the PIO
  of each circle ("TA to CIRCLE HEAD") and division (the DIVISIONAL MANAGER), with employee id and e-mail (no phones), and the
  circle head as First Appellate Authority. 5 circles (PIO + circle head), 20 divisions, 4 corporate units = 34 rows.
  Read from pypdf's layout text (cleaner than pdftotext for this file: one row per line, the cut words on the next line).
- "docx" (TPCODL, /ContactUs/contact-us/Divisional Manager Contact Details.docx and Circle Head Contact Details.docx, the "Level 2"
  and "Level 3" buttons of the escalation matrix): Word tables; read generically (header row with name / designation / mobile /
  e-mail columns). NOT checked on a real copy (the 3-request budget was used): check the first run's rows.
TPWODL (www.tpwesternodisha.com) refused this box ("Request Rejected") and timed out from India on 2026-11-11: no item yet.
tpcentralodisha.com and tpnodl.com time out from Germany: India only. Records "dept:power2_tpodisha:<discom>:<level>:<area>:<name>".
"""
import re

from dforms import _power, _util2_east
from dforms._pdftext import layout_pages
from dforms._power import pdf_pages

MODULE = "power2_tpodisha"
SITES = {"TPCODL": "https://www.tpcentralodisha.com/", "TPSODL": "https://tpsouthernodisha.com/", "TPNODL": "https://www.tpnodl.com/",
         "TPWODL": "https://www.tpwesternodisha.com/"}
DISCOM = {"TPCODL": "TP Central Odisha Distribution Ltd", "TPSODL": "TP Southern Odisha Distribution Ltd",
          "TPNODL": "TP Northern Odisha Distribution Ltd", "TPWODL": "TP Western Odisha Distribution Ltd"}
MOBILE = re.compile(r"(?<![\d@])(\+?91[\s-]?)?([6-9]\d{9}|0\d{9,10}|\d{11})(?!\d)")
POSTWORD = r"(Executive|Superintending|Addl|Additional|Assistant|Junior|Deputy|Dy|Chief|General|Sr)\b"
NAME = re.compile(r"\b(Mr|Ms|Mrs)\.?\s+[A-Z]", re.I)


def items(get=None):
    def it(discom, kind, url, key):
        return {"key": f"{MODULE}:{discom.lower()}-{key}", "payload": {"reader": MODULE, "discom": discom, "kind": kind, "url": url,
                                                                        "state": "OD", "india_only": True}}
    c = SITES["TPCODL"]
    return [it("TPNODL", "xlsx", SITES["TPNODL"] + "xl/contact/Worksheet-in-TPNODL-Contact-Us.xlsx", "contacts"),
            it("TPSODL", "rti_manual", SITES["TPSODL"] + "Editor_UploadedDocuments/Content/RTI_Eng_Manual16.09.2025.pdf", "rti"),
            it("TPCODL", "pio_pdf", c + "Editor_UploadedDocuments/RTI/PIO_Appellate_Authority.pdf", "pio"),
            it("TPCODL", "docx", c + "ContactUs/contact-us/Divisional%20Manager%20Contact%20Details.docx", "divisional-managers"),
            it("TPCODL", "docx", c + "ContactUs/contact-us/Circle%20Head%20Contact%20Details.docx", "circle-heads")]


def _out(discom, url, last_updated=None):
    return _power.Out(MODULE, "OD", url, discom=DISCOM.get(discom, discom), last_updated=last_updated)


def _add(out, discom, level, area, post=None, name=None, **kw):
    return out.add(f"{discom}:{level}:{area}:{name or post}", level, area, post=post, name=name, **kw)


def _area(s):
    s = _power.clean(s) or ""
    s = re.sub(r"^(Office of the\s+)?(Electrical\s+)?Circle\s*,\s*", "", s, flags=re.I)
    return _power.clean(re.sub(r"\s+(Electrical\s+)?Circle$", "", s.strip(" ,"), flags=re.I))


# ---- TPNODL spreadsheet ----
HEADS = {"circle": r"^circle$", "office": r"circle\s*/\s*division|^division$|office\s+name", "address": r"address",
         "name": r"incharge|name", "post": r"designation", "mobile": r"mobile|phone|contact", "email2": r"alternate",
         "email": r"e-?\s?mail"}


def parse_xlsx(content, discom, url):
    out = _out(discom, url)
    for sheet, rows in _util2_east.xlsx_rows(content).items():
        level = "division" if re.search(r"divi", sheet, re.I) else "circle"
        head = None
        for row in rows:
            if head is None:
                if any(re.search(r"designation", c, re.I) for c in row):
                    head = _util2_east.head_map(row, HEADS)
                continue
            g = {k: (row[i] if i < len(row) else "") for k, i in head.items()}
            office = _power.clean(g.get("office"))
            if not office:
                continue
            area = _area(office) if level == "circle" else office
            par = {"circle": _area(g.get("circle"))} if level == "division" and g.get("circle") else None
            _add(out, discom, level, area, post=_power.clean(g.get("post")), name=_util2_east.person(g.get("name")),
                 phone_=_power.phone(g.get("mobile")), email_=_power.email(" ".join(filter(None, (g.get("email"), g.get("email2"))))),
                 address=g.get("address"), parents=par, office_id=office)
    return out.recs


# ---- TPSODL RTI manual, Manual-9 (pdftotext -layout) ----
COLS = (("office", r"OFFICE"), ("post", r"DESIGNATION"), ("address", r"ADD"), ("name", r"NAME OF THE HOD"), ("mobile", r"MOBILE"),
        ("email", r"e-mail"))


def _chunks(line, starts=None):
    """Cells of one line (text parted by 2+ spaces); a cell that runs over a column start is cut at the space nearest to it
    ("BED-III, BERHAMPUR Executive Engineer" -> office + post)."""
    out = []
    for m in re.finditer(r"\S+(?: \S+)*", line):
        pos, txt = m.start(), m.group(0)
        for x in ([] if NAME.match(txt) else sorted((starts or {}).values())):
            if pos + 10 <= x < pos + len(txt) - 2:
                spaces = [i for i, ch in enumerate(txt) if ch == " " and abs(pos + i + 1 - x) <= 12]
                postw = [i for i in spaces if re.match(POSTWORD, txt[i + 1:])]
                spaces = [i for i in spaces if abs(pos + i + 1 - x) <= 8]
                cut = min(postw or spaces, key=lambda i: abs(pos + i + 1 - x), default=None)
                if cut is not None:
                    out.append((pos, txt[:cut]))
                    pos, txt = pos + cut + 1, txt[cut + 1:]
        out.append((pos, txt))
    return out


def _header(line):
    if not re.search(r"NAME OF THE HOD", line):
        return None
    starts = {}
    for k, rx in COLS:
        m = re.search(rx, line)
        if m:
            starts[k] = m.start()
    if "office" not in starts:
        starts["office"] = 0
    return starts


def _column(pos, starts):
    return min(starts, key=lambda k: abs(starts[k] - pos))


def parse_manual(pages, discom, url):
    out = _out(discom, url)
    text = "\n".join(pages)
    m = re.search(r"Manual-9 updated\s+date:\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        out.last_updated = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    start = text.find("MANUAL-9")
    end = text.find("Manual-9 updated", start)
    if start < 0:
        return []
    lines = text[start:end if end > 0 else None].splitlines()
    starts, section, block = None, "CORPORATE OFFICE", []
    blocks = []

    def close():
        if block:
            blocks.append((section, starts, list(block)))
        block.clear()

    for ln in lines:
        h = _header(ln)
        if h:
            close()
            starts = h
            continue
        sec = re.fullmatch(r"\s*([A-Z ]+CIRCLE|GRF Details)\s*", ln)
        if sec:
            close()
            section = sec.group(1).strip()
            if section == "GRF Details":
                starts = None
            continue
        if starts is None and section == "GRF Details":
            starts = {"office": 0, "area": 20, "name": 60, "mobile": 95, "email": 108}
        if starts:
            block.append(ln)                  # blank lines kept: they part the officers
    close()
    for section, st, blines in blocks:
        _manual_block(out, discom, section, st, blines)
    return out.recs


def _emails(frags):
    """Join e-mail pieces cut over lines: [(line, text)] in line order -> [(line of the '@' piece, address)]."""
    out, cur, prev = [], None, None
    for i, t in frags:
        if "@" in t:
            if cur:
                out.append(cur)
            head = prev[1] if prev and prev[0] == i - 1 and t.startswith("@") else ""
            cur, prev = [i, head + t], None
        elif cur and cur[0] >= i - 2 and not re.search(r"\.(com|in|org|net)$", cur[1], re.I):
            cur[1] += t
        else:
            if cur:
                out.append(cur)
                cur = None
            prev = (i, t)
    if cur:
        out.append(cur)
    return [(i, t) for i, t in out]


def _assign(items, rows, own, col):
    """Give each (line, text) of one column to an officer line: the nearest; on a tie, the officer above when its own cell ends
    with a comma (cut over two lines), else the officer whose own line has nothing in that column, else the one below."""
    mine = {i: t for i, t in items if i in own}
    for i, t in items:
        best = sorted(rows, key=lambda a: abs(a - i))
        d = abs(best[0] - i)
        tied = sorted(r for r in best if abs(r - i) == d)
        if len(tied) == 1:
            r = tied[0]
        elif mine.get(tied[0], "").endswith(","):
            r = tied[0]
        else:
            r = next((x for x in tied if x not in mine), tied[-1])
        own[r][col].append(t)


def _manual_block(out, discom, section, starts, blines):
    """One section: officer = a line with Mr./Ms. in the name column; every other cell goes to the nearest officer line. A name
    cut over lines continues on the line below; a mobile or an e-mail goes first to the officer on its own line, then to the
    nearest officer that has none yet."""
    if not starts:
        return
    cells = []                                # (line no, column, text)
    for i, ln in enumerate(blines):
        for mm in MOBILE.finditer(ln):
            cells.append((i, "mobile", mm.group(2)))
        for pos, txt in _chunks(MOBILE.sub(lambda mm: " " * len(mm.group(0)), ln), starts):
            col = "name" if NAME.match(txt) else _column(pos, starts)
            if "@" in txt or (col in ("email", "mobile") and re.fullmatch(r"[\w.@-]+", txt)):
                col = "email"
            elif col == "mobile":
                col = "name"
            cells.append((i, col, txt))
    rows = sorted({i for i, col, txt in cells if col == "name" and NAME.search(txt)})
    if not rows:
        return
    own = {r: {"office": [], "post": [], "address": [], "name": [], "mobile": [], "email": [], "area": []} for r in rows}
    for i, col, txt in cells:
        if col == "name":
            r = max([a for a in rows if a <= i] or [rows[0]])          # a cut name continues below its first line
            if NAME.search(txt):
                r = i
            own[r]["name"].append(txt)
    for col in ("office", "post", "address", "area"):
        _assign([(i, t) for i, c, t in cells if c == col], rows, own, col)
    for col, items in (("mobile", [(i, t) for i, c, t in cells if c == "mobile"]),
                       ("email", _emails([(i, t) for i, c, t in cells if c == "email"]))):
        rest = []
        for i, t in items:
            (own[i][col].append(t) if i in own and not own[i][col] else rest.append((i, t)))
        for i, t in rest:
            free = [r for r in rows if not own[r][col]] or rows
            own[min(free, key=lambda a: (abs(a - i), -a))][col].append(t)
    for r in rows:
        o = own[r]
        name = re.sub(r"^(Mr|Ms|Mrs)\.?\s*", "", " ".join(o["name"]), flags=re.I)
        name = re.sub(r"(?<=[a-z])\.(?=[A-Z])", " ", name)                      # "Aparna.Raut"
        name = _util2_east.person(re.sub(r"(?<=\b[A-Z])\.(?=\S)", ". ", name))   # "T.Tapanrasmi" -> "T. Tapanrasmi"
        mail = _power.email(", ".join(o["email"]))
        phone = _power.phone(", ".join(o["mobile"]))
        post = _power.clean(" ".join(o["post"]))
        office = _power.clean(" ".join(o["office"]))
        if section == "GRF Details":
            area = _power.clean(" ".join(o["area"])) or office
            _add(out, discom, "circle", area, post=office or "President GRF", name=name, phone_=phone, email_=mail, office_id=office)
            continue
        if section == "CORPORATE OFFICE":
            _add(out, discom, "state", "Corporate Office, Berhampur", post=post, name=name, phone_=phone, email_=mail,
                 address="Corporate Office, TPSODL, Courtpeta, Berhampur")
            continue
        circle = re.sub(r"\s+CIRCLE$", "", section).title()
        is_circle = bool(re.search(r"Electrical Circle", office or "", re.I))
        level = "circle" if is_circle else "division"
        area = circle if is_circle else (office or circle)
        _add(out, discom, level, area, post=post, name=name, phone_=phone, email_=mail, address=" ".join(o["address"]),
             office_id=office, parents=None if is_circle else {"circle": circle})


# ---- TPCODL PIO list (pypdf layout) ----
PIO_ROW = re.compile(r"(?P<name>\b(?:Mr|Ms|Mrs)\.?\s+[A-Za-z .]+?)\s{2,}(?P<emp>\d{6})\s+(?P<email>\S+@\S+)")
FAA_ROW = re.compile(r"(?P<name>\b(?:Mr|Ms|Mrs)\.?\s+[A-Za-z .]+?)\s{2,}(?P<emp>\d{6})\s+(?P<email>\S+@\S+)\s*(?P<post>.*)")
X_OFFICE = 12                                  # left of this: the circle column of the appellate authority (a merged cell)


def _faa(lines, start, end, x_faa):
    """The First Appellate Authority cell found on the lines start..end of one PIO row (pypdf puts it there, the rest of the name
    on the next one or two lines, which may belong to the next PIO row)."""
    segs = [ln[x_faa:] for ln in lines]
    for k in range(start, end):
        m = FAA_ROW.search(segs[k])
        if m:
            more = []
            for other in segs[k + 1:k + 3]:
                first = (re.split(r"\s{2,}", other.strip()) or [""])[0]
                if re.fullmatch(r"[A-Z][a-z][A-Za-z .]*", first):
                    more.append(first)
            name = _util2_east.person(re.sub(r"^(Mr|Ms|Mrs)\.?\s+", "", " ".join([m.group("name")] + more), flags=re.I))
            post = " ".join([m.group("post")] + [o.strip() for o in segs[k + 1:k + 2] if re.fullmatch(r"\s*[A-Z][A-Z &-]+\s*", o)])
            return name, m.group("emp"), m.group("email"), _power.clean(post)
    return None


def parse_pio(pages, discom, url):
    out = _out(discom, url)
    for page in pages:
        lines = page.splitlines()
        head = next((ln for ln in lines if "Authority Name" in ln and "Designation" in ln), None)
        if head is None:
            continue
        x_faa = head.find("Authority Name") - 4
        rows = [i for i, ln in enumerate(lines) if PIO_ROW.search(ln[:x_faa])]
        circle = None
        for n, i in enumerate(rows):
            block = lines[i:rows[n + 1] if n + 1 < len(rows) else len(lines)]
            m = PIO_ROW.search(lines[i][:x_faa])
            x_name, x_post = m.start("name"), m.end("email")
            office = " ".join(t for ln in block for pos, t in _chunks(ln[:x_name]) if pos >= X_OFFICE)
            office = _power.clean(re.sub(r"(?<=[-,])\s+", "", re.sub(r"(\w)\s+(ar)$", r"\1\2", office))) or ""
            post = _power.clean(" ".join(ln[x_post:x_faa].strip() for ln in block if ln[x_post:x_faa].strip())) or ""
            name = _util2_east.person(re.sub(r"^(Mr|Ms|Mrs)\.?\s+", "", m.group("name").strip(), flags=re.I))
            mail = _power.email(m.group("email"))
            if re.search(r"CIRCLE\s+HEAD", post, re.I) and re.search(r"circle", office, re.I):
                circle = office
                _add(out, discom, "circle", circle, post="Public Information Officer (TA to Circle Head)", name=name, email_=mail,
                     office_id=m.group("emp"))
            elif re.search(r"DIVISIONAL", post, re.I):
                _add(out, discom, "division", office, post="Divisional Manager (Public Information Officer)", name=name, email_=mail,
                     office_id=m.group("emp"), parents={"circle": circle} if circle else None)
            else:
                circle = None
                _add(out, discom, "state", office, post=f"Public Information Officer ({post.title()})" if post else None, name=name,
                     email_=mail, office_id=m.group("emp"))
            f = _faa(lines, i, i + len(block), x_faa)
            if f:
                fname, femp, fmail, fpost = f
                _add(out, discom, "circle" if circle else "state", circle or office,
                     post=f"{(fpost or 'Circle Head').title()} (First Appellate Authority)", name=fname, email_=_power.email(fmail),
                     office_id=femp)
    return out.recs


# ---- TPCODL Word tables (generic) ----
DOCX_HEADS = {"office": r"division|circle|office|location", "name": r"name", "post": r"designation", "mobile": r"mobile|phone|contact",
              "email": r"e-?\s?mail"}


def parse_docx(content, discom, url, level=None):
    out = _out(discom, url)
    for rows in _util2_east.docx_tables(content):
        head = None
        for row in rows:
            if head is None:
                if any(re.search(r"name", c, re.I) for c in row) and any(re.search(r"mobile|phone|contact|e-?\s?mail", c, re.I) for c in row):
                    head = _util2_east.head_map(row, DOCX_HEADS)
                continue
            g = {k: (row[i] if i < len(row) else "") for k, i in head.items()}
            office, post = _power.clean(g.get("office")), _power.clean(g.get("post"))
            if not (office or post):
                continue
            lvl = level or ("circle" if re.search(r"circle", (office or "") + " " + (post or ""), re.I) else "division")
            _add(out, discom, lvl, _area(office) if lvl == "circle" else (office or post), post=post,
                 name=_util2_east.person(g.get("name")), phone_=_power.phone(g.get("mobile")), email_=_power.email(g.get("email")))
    return out.recs


def fetch(p, get):
    url, kind, discom = p["url"], p["kind"], p.get("discom", "TPCODL")
    r = get(url)
    if r is None:
        return [], [], "no answer"
    name = f"{discom.lower()}-{url.rstrip('/').rsplit('/', 1)[-1]}".rsplit(".", 1)[0]
    content = r.content
    if kind == "xlsx":
        if not content.startswith(b"PK"):
            return [], [_power.raw(MODULE, name, content, "html")], "not a spreadsheet"
        files, recs = [_power.raw(MODULE, name, content, "xlsx")], parse_xlsx(content, discom, url)
    elif kind == "docx":
        if not content.startswith(b"PK"):
            return [], [_power.raw(MODULE, name, content, "html")], "not a word file"
        level = "circle" if re.search(r"circle", url, re.I) else "division"
        files, recs = [(f"depts/power/{MODULE}/{_power.slug(name)}.docx", content, "application/octet-stream")], \
            parse_docx(content, discom, url, level)
    else:
        if not content.startswith(b"%PDF"):
            return [], [_power.raw(MODULE, name, content, "html")], "not a pdf"
        files = [_power.raw(MODULE, name, content, "pdf")]
        if kind == "rti_manual":
            pages, _engine = layout_pages(content)
            recs = parse_manual(pages, discom, url)
        else:
            recs = parse_pio(pdf_pages(content, layout=True), discom, url)
    return recs, files, "" if recs else "no rows"
