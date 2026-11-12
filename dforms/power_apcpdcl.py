"""APCPDCL (Andhra Pradesh Central Power Distribution): https://apcpdcl.in/contact-phno-<circle>.php. India only (apcpdcl.in times
out from Germany).

One queue item = one page (8, listed on https://apcpdcl.in/phone-numbers.php): corporate office, Krishna, NTR (vjayawada), CRDA,
Guntur, Bapatla, Palnadu, Prakasam (ongole). Each page has one table per office or wing; the h4 before it names it ("CIRCLE
OFFICE", "M&P WING", "GUNTUR CIRCLE :: DIVISION : TENALI"). Rows = S.No, designation, number, mail ([at]/[dot] written out); no
names. Office from the designation (dforms/_power_ap.py): EE = division, DEE/Dy.EE/ADE = sub-division, AE/AEE (O) = section;
inside a division table a section gets the last sub-division above it. The corporate page is kept as level "state" staff posts.
Expected about 1,000 rows (Guntur 112 rows; the home page states 253 sections).
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, phone, raw
from dforms._power_ap import classify

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_apcpdcl"


def table_office(head, circle):
    """(level, area, wing) of the office one table belongs to."""
    h = clean(head) or ""
    m = re.search(r"(?i)DIVISION\s*[:(]\s*([^)]*)\)?", h)
    if m:
        return "division", clean(m.group(1)).title(), None
    if re.search(r"(?i)circle\s+office", h):
        return "circle", circle, None
    return "circle", circle, h or None


def parse(html, circle, url, corporate=False):
    out = Out(MOD, "AP", url, discom="APCPDCL")
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        h = t.find_previous(["h3", "h4", "h5"])
        head = h.get_text(" ", strip=True) if h else ""
        lvl, area, wing = table_office(head, circle)
        division = area if lvl == "division" else None
        sub = None
        for tr in t.find_all("tr"):
            c = cells(tr)
            if len(c) < 3 or not clean(c[1]) or c[1].lower() == "designation":
                continue
            desig = clean(c[1])
            if corporate:
                level, a, staff = "state", "APCPDCL Corporate Office", True
            elif wing:
                level, a, staff = "circle", circle, True
            else:
                level, a, staff = classify(desig, lvl, area)
            if level == "subdivision" and not staff:
                sub = a
            parents = {}
            if circle and not corporate and (level != "circle" or staff):
                parents["circle"] = circle
            if division and level != "division" or (division and staff):
                parents["division"] = division
            if sub and level == "section" and not staff:
                parents["subdivision"] = sub
            if wing:
                parents["wing"] = wing
            out.add(f"{circle or 'corporate'}:{desig}", level, a, post=desig, phone_=phone(c[2]),
                    email_=email(c[3]) if len(c) > 3 else None, parents=parents, staff_post=True if staff else None)
    return out.recs


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    page = url.rsplit("/", 1)[-1].replace(".php", "")
    files = [raw(MOD, page, r.content, "html")]
    corporate = "corporate" in page
    recs = parse(r.text, None if corporate else p.get("circle"), url, corporate)
    return recs, files, "" if recs else "no rows"
