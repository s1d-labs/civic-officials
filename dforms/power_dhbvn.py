"""DHBVN (Dakshin Haryana Bijli Vitran Nigam, south Haryana): "Contact Details of <X> Circle" PDF of each operation circle,
dhbvn.org.in/staticContent/contactus/<circle>.pdf (linked from dhbvn.org.in/web/portal/contact-us). India only.
One queue item = one of the 11 operation circle files (Bhiwani, Faridabad, Fatehabad, Gurugram-1, Gurugram-2, Hisar, Jind,
Narnaul, Palwal, Rewari, Sirsa); 2-3 pages, about 30-45 offices each, about 400 in all. Table: Name of Office ("XEN/OP Old
Faridabad", "SDO East FARIDABAD", "Superintending Engineer/OP Circle"), Name of Officer In-Charge ("Er. X, AE" or "Vacant"),
Contact Number (office landline, mobile), Email (x[at]dhbvn[dot]org[dot]in). An office name may wrap over 2-3 lines.
The table cells are centred in their rows, so a row's office name, phones and e-mail pieces can be printed above or below
its officer line; each officer line (a name or "Vacant") anchors one row and rows_of() gives the other lines to their row.
(The reader used to start a row only at "XEN"/"SDO"/"SE", so in the circles that write "S/D Adampur", "S/Divn. Jui",
"CCC, City Hisar" or only the place, a whole division ran into one row.)
Levels: SDO / S/D / S/Divn / S/U / CCC / Sub Office, or an AE / AEE without an office word = sub-division (its XEN above it
= parent division), JE = section, XEN = division, SE = circle; other rows (CE, Supdt.) are left out. About 220 offices.
The FRTRTS files (RTS_<Circle>_Circle.pdf) add JE and linemen per shift but their table does not read as text; not used.
Record id dept:power_dhbvn:<circle>:<office>.
"""
import re

from dforms._pdftext import cut, layout_pages, settle
from dforms._power import Out, clean, email, raw

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_dhbvn"
BASE = "https://dhbvn.org.in/staticContent/contactus/"
CIRCLES = ["bhiwani", "faridabad", "fatehabad", "gurugram-1", "gurugram-2", "hisar", "jind", "narnaul", "palwal", "rewari", "sirsa"]
NAME = re.compile(r"\b(?:Er|Sh|Smt|Mrs|Ms|Dr|Shri)\s?\.\s?\S|\bVacant\b")
TEL = re.compile(r"(?<![\d@])(?:0\d{2,4}[- ]?\d{6,8}|0?[6-9]\d{9})(?![\d])")
# an office name starts with one of these words; a line of the office column without one is the end of a wrapped name
OFFICE = re.compile(r"^(XEN|SDO|S/D|S/U|S/Divn|Sub\s*Divn|Sub\s+Office|OP\b|OP'|OP\.|\(OP\)|SE\b|SE/|Superintending|Supdt|"
                    r"City\b|CCC|CE\b|CE/|Executive|AEE|AE\b|JE\b)", re.I)
HEADING = re.compile(r"(Executive|Superintending|Chief)\s+Engineer|CONTACT|Contact Numbers|Complex|Road|Charge\s*$", re.I)
LAND = re.compile(r"(?<![\d@])0\d{2,4}-\s?\d{6,8}(?!\d)")
MORE = re.compile(r"([A-Z][a-z.]+( [A-Z][a-z.]+)?,\s*)?(AEE|AE|JE)")     # the officer's name goes on below: "Sheoran, AE"
POST = re.compile(r",?\s+(AEE|AE|XEN|SE|JE|SDO)\s*$")


def level(office, post=None):
    """Level from the office name; a sub-division row that gives only a place ("Tosham-I", "Rania") is read from the post."""
    o = " ".join((office or "").upper().split())
    if re.match(r"(SUPERINTENDING|SE\b|SE/)", o):
        return "circle"
    if re.match(r"XEN\b", o) and "WORKS" not in o:
        return "division"
    if re.match(r"(CE\b|CE/|CHIEF|SUPDT|UNDER SECRETARY)", o):
        return None
    if re.search(r"(^|\s|\b)(SDO|S/D|S/U|S/DIVN|SUB\s*DIVN|CCC)\b", o) or re.match(r"(OP\b|OP'|OP\.|CITY\b)", o):
        return "section" if post == "JE" else "subdivision"
    if post == "JE":
        return "section"
    if re.match(r"SUB\s+OFFICE", o):
        return "subdivision"
    if post in ("AE", "AEE", "SDO"):
        return "subdivision"
    return None


def area_of(office):
    a = re.sub(r"(?i)^(XEN\s*/\s*OP|XEN\s*\(OP\)|XEN\s+OP|XEN|SDO\s*/\s*OP|SDO)\b\.?,?", " ", office)
    a = re.sub(r"(?i)\(new\)|(^|\s)(OP'?\.?\s*)?(S/Divn\.?|Sub\s*Divn\.?|S/D\.?)(?=\s|$|[A-Z])|(?<!/)\bDivn\.?(?=\s|$)", " ", a)
    a = re.sub(r"(?i)^\s*(OP'?\.?|\(OP\))\s+(?=\S)", " ", a)
    a = re.sub(r"^\s*Division\s+(?!(No|[IVX]+)\b)(?=[A-Z])", " ", a)
    return " ".join(a.split()).strip(" ,.") or office


def header(lines):
    """Column starts [office, officer, contact, email] and the header's last line. The headings may sit on two or three lines
    ("Name of Officer In-" above, "Charge" below)."""
    for i, ln in enumerate(lines):
        m = re.search(r"Name of Office(?!r)", ln)
        if not m:
            continue
        block = [ln] + [b for b in lines[max(0, i - 2):i + 3] if b is not ln and not re.search(r"(?i)contact (numbers|details) of", b)]

        def find(rx, after=0):
            return next((x.start() for b in block for x in [re.search(rx, b)] if x and x.start() > after), -1)
        off = find(r"Name of Officer")
        if off < 0:
            off = find(r"\bCharge\b", m.start() + 14)
        xs = [m.start(), off, find(r"Contact"), find(r"Email")]
        if min(xs) < 0:
            return None, i
        hi = i + next((k for k in (2, 1) if i + k < len(lines) and re.fullmatch(r"\s*Charge\s*", lines[i + k])), 0)
        return xs, hi
    return None, None


def frags(ln, cols):
    """The pieces of an e-mail address in a line: tokens with @ / [at] right of the officer column, and the address's broken
    parts (no digit run, a lower-case letter) in the e-mail column."""
    out = []
    for m in re.finditer(r"\S+", ln):
        t, x = m.group(), m.start()
        if x < cols[2] - 2:
            continue
        if "@" in t or "[at]" in t.lower():
            out.append(t)
        elif x >= cols[3] - 14 and re.fullmatch(r"[A-Za-z0-9._\[\]-]*[A-Za-z0-9\]]", t) and re.search(r"[a-z]", t) \
                and t.lower() != "fax" and not re.search(r"\d{4,}", t):
            out.append(t)
    return out


def complete(buf):
    return bool(re.search(r"(\[at\]|@).*(\[dot\]|\.)(in|com)$", buf, re.I))


def mails_of(fr):
    """E-mail addresses from the pieces of a row, in order: a piece with [at] starts a new address once the one before is whole."""
    addrs, buf = [], ""
    for t in fr:
        if ("@" in t or "[at]" in t.lower()) and buf and ("@" in buf or "[at]" in buf.lower()) and complete(buf):
            addrs.append(buf)
            buf = ""
        buf += t
    if buf:
        addrs.append(buf)
    return email(" ".join(a for a in addrs if "@" in a or "[at]" in a.lower()))


def rows_of(body, cols):
    """The table rows of one page. A row is anchored on its officer line (a name or "Vacant" in the officer column); the office
    name and contact lines printed above or below it (cells are centred in the row) are given to the row they belong to."""
    lines, brk = [], set()                               # brk: a heading line ("Executive Engineer/Operation, ...") came before
    for ln in body:
        if not ln.strip():
            continue
        if HEADING.search(ln) and not NAME.search(ln[:cols[2]]) and not TEL.search(ln) and not re.search(r"@|\[at\]", ln, re.I):
            brk.add(len(lines))
            continue
        lines.append(ln)
    kind = []
    for ln in lines:
        p = cut(ln, cols) + [""] * 4
        more = MORE.fullmatch(" ".join((p[0] + " " + p[1]).split()))
        kind.append("anchor" if NAME.search(ln[:cols[2]]) else "office" if p[0] and not more else "other")
    anchors = [i for i, k in enumerate(kind) if k == "anchor"]
    rows = [{"anchor": i, "lines": [i], "office": bool(office_part(lines[i], cols))} for i in anchors]
    at = {i: n for n, i in enumerate(anchors)}

    def prev_row(i):
        return max((at[a] for a in anchors if a < i), default=None)

    def next_row(i):
        return min((at[a] for a in anchors if a > i), default=None)

    def buf(n):
        return "".join(t for j in sorted(rows[n]["lines"]) for t in frags(lines[j], cols))

    pending = False
    for i, k in enumerate(kind):
        if k == "anchor":
            pending = False
            continue
        pv, nx = prev_row(i), next_row(i)
        fr = frags(lines[i], cols)
        tail = fr and not ("@" in fr[0] or "[at]" in fr[0].lower()) or fr and fr[0].lower().startswith("[at]")
        target = None
        if tail and pv is not None and not complete(buf(pv)):
            target = pv                                  # the end of the address above: "ot]in", "[at]dhbvn[dot]org[dot]in"
        elif k == "office":
            text = office_part(lines[i], cols)
            if pv is not None and not rows[pv]["office"] and i - anchors[pv] == 1:
                target = pv                              # the officer line came first: "Er. Pardeep Kumar Soni," / "S/D Siswal"
            elif OFFICE.match(text) or pending or (i + 1 < len(lines) and kind[i + 1] == "office" and i + 1 not in brk
                                                     and re.fullmatch(r"(S/Divn|Sub\s*Divn|S/D)\.?,?", office_part(lines[i + 1], cols))):
                target, pending = nx, True               # an office name printed above its officer line ("New Palam Vihar,"
                #                                          / "S/Divn." / "Er. Vikram Singh, AE")
            else:
                target = pv if pv is not None else nx    # the end of the name above: "Hisar", "(New)"
            if target is not None:
                rows[target]["office"] = True
        else:
            pending = False
            if pv is None or nx is None:
                target = pv if nx is None else nx
            else:
                dp, dn = i - anchors[pv], anchors[nx] - i
                head = bool(fr) and not tail and not complete("".join(fr))
                # a tie: a broken address goes down (its end is on the officer line below); a landline goes to the officer
                # line that has none ("01250-220142" above "XEN Charkhi Dadri Vacant 9812451203")
                down = head or LAND.search(lines[i]) and not LAND.search(lines[anchors[nx]]) and LAND.search(lines[anchors[pv]])
                target = nx if dn < dp or (dn == dp and down) else pv
        if target is not None:
            rows[target]["lines"].append(i)
    return [[lines[j] for j in sorted(r["lines"])] for r in rows], lines


def office_part(ln, cols):
    hit = NAME.search(ln[:cols[2]])
    return " ".join((ln[:hit.start()] if hit else (cut(ln, cols) + [""])[0]).split())


def parse_text(pages, circle, url):
    out = Out(MOD, "HR", url, discom="DHBVN")
    label = circle.replace("-", " ").title()
    division = last = None
    for text in pages:
        lines = [ln.rstrip() for ln in text.splitlines()]
        cols, hi = header(lines)
        if cols:
            cols = last = [0] + settle(cols[1:], [ln for ln in lines[hi + 1:] if NAME.search(ln)] or lines)
            body = lines[hi + 1:]
        elif last:                                       # a later page without the header row
            cols, body = last, lines
        else:
            continue
        rows, _ = rows_of(body, cols)
        for rl in rows:
            office, name, rest, fr = [], [], [], []
            for ln in rl:
                hit = NAME.search(ln[:cols[2]])
                p = cut(ln, cols) + [""] * 4
                more = not hit and name and MORE.fullmatch(" ".join((p[0] + " " + p[1]).split()))
                if not more:
                    office.append(office_part(ln, cols))
                if hit:                                  # "XEN/OP NIT Faridabad Er. Urmila Rani": the name may start early
                    name.append(re.split(r"\s{2,}|\s(?=0?\d{5,}|\d{3,5}-\d)", ln[hit.start():].strip())[0])
                elif more:
                    name.append(" ".join((p[0] + " " + p[1]).split()))
                rest.append(" ".join(ln[cols[1]:].split()) if not hit else ln[hit.start():])
                fr += frags(ln, cols)
            office = " ".join(" ".join(office).split())
            office = re.sub(r"\s+Fax\s+\d+.*$", "", office)
            nm = clean(re.sub(r"\s*Fax.*$", "", " ".join(name)).rstrip(" ,"))
            post = None
            if nm:
                m = POST.search(nm)
                if m:
                    post, nm = m.group(1), clean(nm[:m.start()].rstrip(","))
            lvl = level(office, post)
            if not lvl:
                continue
            if lvl == "division":
                division = area_of(office)
            post = post or {"subdivision": "SDO", "division": "XEN", "circle": "SE", "section": "JE"}[lvl]
            txt = re.sub(r"\S*(@|\[at\])\S*", " ", " ".join(rest))
            txt = re.sub(r"(\b0\d{2,4})-\s+(\d{6,8})\b", r"\1-\2", txt)
            tels = list(dict.fromkeys(TEL.findall(txt)))
            par = {"circle": f"Operation Circle {label}" if lvl != "circle" else None,
                   "division": division if lvl in ("subdivision", "section") else None}
            area = f"Operation Circle {label}" if lvl == "circle" else area_of(office)
            out.add(f"{circle}:{office}", lvl, area, post=post, name=nm, phone_=", ".join(tels) or None,
                    email_=mails_of(fr), parents=par, office=office)
    return out.recs


def fetch(p, get):
    circle = p["circle"]
    url = p.get("url") or f"{BASE}{circle}.pdf"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, circle, r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    pages, _ = layout_pages(r.content)
    recs = parse_text(pages, circle, url)
    return recs, files, "" if recs else "no offices in the pdf"
