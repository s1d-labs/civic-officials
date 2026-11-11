"""DHBVN (Dakshin Haryana Bijli Vitran Nigam, south Haryana): "Contact Details of <X> Circle" PDF of each operation circle,
dhbvn.org.in/staticContent/contactus/<circle>.pdf (linked from dhbvn.org.in/web/portal/contact-us). India only.
One queue item = one of the 11 operation circle files (Bhiwani, Faridabad, Fatehabad, Gurugram-1, Gurugram-2, Hisar, Jind,
Narnaul, Palwal, Rewari, Sirsa); 2-3 pages, about 30-45 offices each, about 400 in all. Table: Name of Office ("XEN/OP Old
Faridabad", "SDO East FARIDABAD", "Superintending Engineer/OP Circle"), Name of Officer In-Charge ("Er. X, AE" or "Vacant"),
Contact Number (office landline, mobile), Email (x[at]dhbvn[dot]org[dot]in). An office name may wrap over 2-3 lines.
Levels: SDO = sub-division (its XEN above it = parent division), XEN = division, SE = circle; other rows are left out.
The FRTRTS files (RTS_<Circle>_Circle.pdf) add JE and linemen per shift but their table does not read as text; not used.
Record id dept:power_dhbvn:<circle>:<office>.
"""
import re

from dforms._pdftext import cut, layout_pages, settle
from dforms._power import Out, clean, email, raw

MOD = "power_dhbvn"
BASE = "https://dhbvn.org.in/staticContent/contactus/"
CIRCLES = ["bhiwani", "faridabad", "fatehabad", "gurugram-1", "gurugram-2", "hisar", "jind", "narnaul", "palwal", "rewari", "sirsa"]
START = re.compile(r"^(XEN|SDO|SE|Superintending|Supdt|AEE|AE|JE|Executive|Sr\.?\s*XEN)\b", re.I)
NAME = re.compile(r"\b(?:Er|Sh|Smt|Mrs|Ms|Dr|Shri)\s?\.\s?\S|\bVacant\b")
TEL = re.compile(r"(?<![\d@])(?:0\d{2,4}[- ]?\d{6,8}|0?[6-9]\d{9})(?![\d])")


def level(office):
    o = (office or "").upper()
    if o.startswith("SDO"):
        return "subdivision"
    if o.startswith("XEN") and "WORKS" not in o:
        return "division"
    if o.startswith("SUPERINTENDING") or o.startswith("SE "):        # the SE row may be cut by the page end
        return "circle"
    return None


def mails(lines):
    """Email tokens of an entry; a cut address ("...[dot]org[dot]i" + a line "n") is joined again."""
    toks = [t for ln in lines for t in ln.split() if "@" in t or "[at]" in t.lower()]
    tails = [m.group(1) for ln in lines for m in [re.search(r"(?:^|\s{5,})([a-z]{1,3})\s*$", ln)] if m]
    toks = [t + tails.pop(0) if tails and re.search(r"(\[dot\]|\.)[a-z]?$", t) else t for t in toks]
    return email(" ".join(toks)) if toks else None


def area_of(office):
    a = re.sub(r"(?i)^(XEN\s*/\s*OP|XEN|SDO\s*/\s*OP|SDO)\b\.?", " ", office)
    a = re.sub(r"(?i)\(new\)", " ", a)
    return " ".join(a.split()).strip(" ,.") or office


def header(lines):
    for ln in lines:
        if "Name of Office" in ln and ("Officer" in ln or "Contact" in ln):
            xs = [ln.find("Name of Office"), ln.find("Name of Officer"), ln.find("Contact"), ln.find("Email")]
            if min(xs) < 0:
                return None
            return xs
    return None


def parse_text(pages, circle, url):
    out = Out(MOD, "HR", url, discom="DHBVN")
    label = circle.replace("-", " ").title()
    division = last = None
    for text in pages:
        lines = [ln.rstrip() for ln in text.splitlines()]
        cols = header(lines)
        if cols:
            cols = last = [0] + settle(cols[1:], [ln for ln in lines if START.match(ln)] or lines)
            body = lines[next(i for i, ln in enumerate(lines) if "Name of Office" in ln) + 1:]
        elif last:                                       # a later page without the header row
            cols, body = last, lines
        else:
            continue
        entries, cur, pend = [], None, []
        for i, ln in enumerate(body):
            if not ln.strip():
                continue
            if START.match(ln):
                cur = {"lines": pend + [ln]}
                pend = []
                entries.append(cur)
            elif not ln.startswith(" ") and cur is not None:
                cur["lines"].append(ln)                  # office name wraps: "(Sector-22 & 23 Faridabad)"
            elif ln.startswith(" "):
                nxt = next((x for x in body[i + 1:] if x.strip()), "")
                only_mail = re.fullmatch(r"\s*\S*(@|\[at\])\S*", ln) is not None
                cut_mail = only_mail and not re.search(r"(\[dot\]|\.)(in|com|org|net)\s*$", ln)
                if cut_mail and START.match(nxt):
                    pend.append(ln)                      # an email cut in two: its first half is printed above the next row
                elif cur is not None:
                    cur["lines"].append(ln)
        for e in entries:
            office, name, rest = [], [], []
            for ln in e["lines"]:
                p = cut(ln, cols) + [""] * 4
                hit = NAME.search(ln[:cols[2]])
                if hit:                                  # "XEN/OP NIT Faridabad Er. Urmila Rani": the name may start early
                    office.append(ln[:hit.start()])
                    name.append(re.split(r"\s{2,}|\s(?=0?\d{5,}|\d{3,5}-\d)", ln[hit.start():].strip())[0])
                else:
                    office.append(p[0])
                    if p[1]:
                        name.append(p[1])
                rest.append(ln[cols[1]:])
            office = " ".join(" ".join(office).split())
            office = re.sub(r"\s+Fax\s+\d+.*$", "", office)
            lvl = level(office)
            if not lvl:
                continue
            if lvl == "division":
                division = area_of(office)
            nm = clean(re.sub(r"\s*Fax.*$", "", " ".join(name)))
            post = None
            if nm:
                m = re.search(r",?\s+(AEE|AE|XEN|SE|JE|SDO)\s*$", nm)
                if m:
                    post, nm = m.group(1), clean(nm[:m.start()].rstrip(","))
            post = post or {"subdivision": "SDO", "division": "XEN", "circle": "SE"}[lvl]
            txt = re.sub(r"\S*(@|\[at\])\S*", " ", " ".join(rest))
            tels = list(dict.fromkeys(TEL.findall(txt)))
            par = {"circle": f"Operation Circle {label}" if lvl != "circle" else None,
                   "division": division if lvl == "subdivision" else None}
            area = f"Operation Circle {label}" if lvl == "circle" else area_of(office)
            out.add(f"{circle}:{office}", lvl, area, post=post, name=nm, phone_=", ".join(tels) or None,
                    email_=mails(e["lines"]), parents=par, office=office)
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
