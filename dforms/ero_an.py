"""Andaman & Nicobar Islands: the 3 District Election Officers, the ERO (one parliamentary constituency, ANIPC; the UT has no
assembly) and the 10 AEROs (one per tehsil or area), from the CEO's "List of officers" PDF
www.ceoandaman.nic.in/election/downloads/List%20of%20officers.pdf (created 2025-11-01). Answers from Germany and India.

One GET; 2 pages. pypdf layout text keeps four columns (name & designation, phone, mobile, email); an entry starts with its serial
number and wraps over 2-3 lines; section headings ("District Election Officers (03)", "Electoral Registration Officer (01)",
"Asst. Electoral Registration Officers (10)") tell the role. The CEO office rows are left out. Long emails wrap ("...@gmail." +
"com"): the email column is joined across the lines of an entry. One queue item.
Record ids: dept:ero_an:AN-DEO-<district>, dept:ero_an:AN-PC-1:ero, dept:ero_an:AN-AERO-<area>.
"""
import re

from dforms import _esw

MODULE = "ero_an"
URL = "https://www.ceoandaman.nic.in/election/downloads/List%20of%20officers.pdf"
UPDATED = "2025-11-01"
ENTRY = re.compile(r"^\s{0,3}(\d{1,2})\.?\s{2,}\S")
SECTION = (("district election officer", "deo"), ("asst. electoral registration", "aero"), ("assistant electoral registration", "aero"),
           ("electoral registration officer", "ero"), ("chief electoral office", None))
ROLE = re.compile(r"[,\s]*\b(A?ERO|DEO)\b\s*[,(]?\s*([^)]*?)\)?\s*$")
SERVICE = re.compile(r"(?i)[,\s]+(IAS|DANICS|Tehsildar)\b[,\s]*")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "AN"}}]


def _cols(lines):
    """Column starts from the header line ("Sl. Name of the Officer & ... Phone ... Mobile No. ... e Mail ID")."""
    for ln in lines:
        if "Phone" in ln and "Mail" in ln:
            return ln.index("Phone") - 3, ln.index("Mobile") - 2, ln.index("Mail") - 4
    return None


def entries(text):
    """[(role, name+designation text, phones text, email)] from the layout text of the PDF."""
    lines = text.splitlines()
    cols = _cols(lines)
    if not cols:
        return []
    p_at, m_at, e_at = cols
    out, role, cur = [], None, None
    for ln in lines:
        if not ln.strip():
            continue
        head = ln.strip().lower()
        sec = next((r for w, r in SECTION if head.startswith(w)), "none")
        if sec != "none" and not ENTRY.match(ln):
            role, cur = sec, None
            continue
        if ENTRY.match(ln):
            cur = {"role": role, "name": [], "phone": [], "email": ""}
            out.append(cur)
            ln = re.sub(r"^\s*\d{1,2}\.?", lambda m: " " * len(m.group(0)), ln, count=1)
        if cur is None:
            continue
        for m in re.finditer(r"\S+(?:\s\S+)*", ln):
            at, chunk = m.start(), m.group(0)
            if at >= e_at:
                cur["email"] += chunk
            elif at >= p_at and re.fullmatch(r"[\d\s/,-]+", chunk):
                cur["phone"].append(chunk)
            else:
                cur["name"].append(chunk)
    return [(e["role"], _esw.clean(" ".join(e["name"])), " ".join(e["phone"]), e["email"]) for e in out if e["role"]]


def parse(pages, url=URL):
    recs, seen = [], set()
    for role, text, ph, mail in entries("\n".join(pages)):
        m = ROLE.search(text)
        area = m.group(2).strip(" ,") if m else ""
        person = text[:m.start()] if m else text
        desig = ", ".join(x.strip() for x in SERVICE.findall(person))
        name = SERVICE.split(person)[0].strip(" ,")
        f = dict(dept="elections", name=name, designation=desig, phone=_esw.phones(ph), email=_esw.emails(mail), state="AN",
                 source=url, last_updated=UPDATED)
        if role == "deo":
            key = f"AN-DEO-{_esw.slug(area)}"
            f.update(level="district", area=area, post="District Election Officer", district=area, office_id=key)
        elif role == "ero":
            key = "AN-PC-1:ero"
            f.update(level="pc", area="1 - Andaman & Nicobar Islands", post="Electoral Registration Officer", office_id="AN-PC-1")
        else:
            key = f"AN-AERO-{_esw.slug(area) or _esw.slug(name)}"
            f.update(level="subdistrict", area=area, post="Assistant Electoral Registration Officer", office_id=key)
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, **f))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "list-of-officers", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
