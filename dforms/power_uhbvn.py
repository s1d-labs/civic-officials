"""UHBVN (Uttar Haryana Bijli Vitran Nigam, north Haryana): "Telephone Numbers" PDF of each operation circle,
uhbvn.org.in/staticContent/documents/contact_us/<Circle>.pdf (linked from uhbvn.org.in/web/portal/contact-us). India only.
One queue item = one of the 10 operation circles (Ambala, Jhajjar, Kaithal, Karnal, Kurukshetra, Panchkula, Panipat, Rohtak,
Sonipat, Yamunanagar); 1-2 pages, about 20-35 offices each, about 300 in all. Text PDF with a table: Sr. No., Name of Office,
Address of the Office, Name of the Officer ("Sh. X, AE"), Office Telephone, Mobile, Email. A line "XEN ..." without a number
starts the offices of one division; the division's own row (XEN ... Divn.) and the circle's (SE ... Circle) come last in it.
Levels: SDO = sub-division, XEN = division, SE = circle. Bijli Suvidha Kendra and other rows are left out.
Record id dept:power_uhbvn:<circle>:<office>.
"""
import re

from dforms._pdftext import cut, layout_pages, settle
from dforms._power import Out, clean, email, raw

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_uhbvn"
BASE = "https://uhbvn.org.in/staticContent/documents/contact_us/"
CIRCLES = ["Ambala", "Jhajjar", "Kaithal", "Karnal", "Kurukshetra", "Panchkula", "Panipat", "Rohtak", "Sonipat", "Yamunanagar"]
NAME = re.compile(r"\b(?:Sh|Smt|Mrs|Ms|Miss|Dr|Er|Shri)\s?\.\s?\S|\bVacant\b")
TEL = re.compile(r"(?<![\d@])(?:0\d{2,4}[- ]?\d{6,8}|\+?91[- ]?\d{10}|[6-9]\d{9})(?![\d])")


def mails(lines):
    """Email tokens only: _power.email() joins the words of a free-text line before it looks for addresses."""
    toks = [t for ln in lines for t in ln.split() if "@" in t or "[at]" in t.lower()]
    return email(" ".join(toks)) if toks else None


def level(office):
    o = (office or "").upper()
    if o.startswith("SDO") or "S/D" in o:
        return "subdivision"
    if o.startswith("XEN") or o.startswith("EXECUTIVE"):
        return "division"
    if o.startswith("SE ") or o.startswith("SE(") or o.startswith("SUPERINTENDING"):
        return "circle"
    return None


def area_of(office, lvl):
    a = re.sub(r"(?i)\((?:op\w*|operation\w*)\)", " ", office)
    a = re.sub(r"(?i)^(SDO|XEN|SE)\b\.?", " ", a)
    a = re.sub(r"(?i)\b(S/D|Divn|Division|Circle)\b\.?,?", " ", a)
    a = " ".join(a.replace(" ,", ",").split()).strip(" ,.")
    return a or office


def header(lines):
    for ln in lines:
        if "Name of Office" in ln and "Address" in ln and ("Officer" in ln or "Email" in ln):
            xs = [ln.find("Name of Office"), ln.find("Address"), ln.find("Name of the Officer") if "Name of the Officer" in ln
                  else ln.find("Officer")]
            if min(xs) < 0:
                return None
            tel = ln.find("Office", xs[2] + len("Name of the Officer"))
            mob = ln.find("Mobile")
            mail = ln.find("Email")
            starts = [0, xs[1] - 1, xs[2] - 1] + [x - 1 for x in (tel, mob, mail) if x > 0]
            return sorted(set(starts))
    return None


def parse_text(pages, circle, url):
    out = Out(MOD, "HR", url, discom="UHBVN")
    division = None
    rows = []
    for text in pages:
        lines = text.splitlines()
        cols = header(lines)
        if not cols:
            continue
        cols = settle(cols, [ln for ln in lines if re.match(r"\s{0,8}\d{1,3}\s", ln)] or lines)
        cur = None
        for ln in lines:
            if not ln.strip() or "Name of Office" in ln or re.match(r"\s*(Telephone|No\.)\s*$", ln) or "1912" in ln:
                continue
            m = re.match(r"\s{0,8}(\d{1,3})\s+(\S.*)", ln)
            if m and cols and len(ln) > cols[1]:
                cur = {"division": division, "lines": [" " * (len(ln) - len(ln.lstrip()) + len(m.group(1))) +
                                                       ln[len(ln) - len(ln.lstrip()) + len(m.group(1)):]]}
                rows.append(cur)
                continue
            if re.match(r"^(XEN|SE)\b", ln) and not TEL.search(ln):
                division, cur = " ".join(ln.split()), None     # "XEN City KARNAL": the offices of one division follow
                continue
            if cur is not None and ln.startswith(" "):
                cur["lines"].append(ln)
        for r in rows:
            _row(out, dict(r, cols=cols), circle)
        rows = []
    return out.recs


def _row(out, r, circle):
    cols = r["cols"]                      # [office, address, officer, telephone, mobile, email] column starts
    office, addr, name, tels = [], [], [], []
    for ln in r["lines"]:
        p = cut(ln, cols) + [""] * 6
        office.append(p[0])
        mid = ln[cols[1]:cols[3]] if len(cols) > 3 else ln[cols[1]:]
        hit = NAME.search(mid)
        if hit:                           # the officer's name is found by its title ("Sh.", "Smt."), the address is before it
            addr.append(mid[:hit.start()])
            name.append(re.split(r"\s{2,}", mid[hit.start():].strip())[0])
        else:
            addr.append(p[1])
            if p[2] and not TEL.search(p[2]) and "@" not in p[2]:
                name.append(p[2])
        tels += TEL.findall(re.sub(r"\S+@\S+", " ", ln[cols[2]:] if len(cols) > 2 else ln))
    office = " ".join(" ".join(office).split())
    lvl = level(office)
    if not lvl:
        return
    nm = clean(" ".join(name))
    post = None
    if nm:
        m = re.search(r",\s*([A-Z][A-Za-z./()]*)\s*$", nm)
        if m and len(m.group(1)) <= 6:
            post, nm = m.group(1), clean(nm[:m.start()])
    post = post or office.split()[0]
    par = {"circle": f"Operation Circle {circle}" if lvl != "circle" else None,
           "division": r["division"] if lvl == "subdivision" else None}
    area = f"Operation Circle {circle}" if lvl == "circle" else area_of(office, lvl)
    out.add(f"{circle}:{office}", lvl, area, post=post, name=nm, phone_=", ".join(dict.fromkeys(tels)) or None,
            email_=mails(r["lines"]), address=clean(" ".join(" ".join(addr).split())), parents=par, office=office)


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
