"""APEPDCL (Andhra Pradesh Eastern Power Distribution): https://www.apeasternpower.com/contactsNew?type=<circle code>.
Answers from Germany.

One queue item = one circle (11: VSP, VZM, SKL, ASR, AKP, PVP, KKD, KON, RJY, ELR, WGD). fetch() reads the circle page, takes
the accordion headings (headTitle="Circle Office - Visakhapatnam", "Operation Division - Zone1(Visakhapatnam)", "MRT" ...) and the
circle name from the page's own script (var circle='Visakhapatnam'), then GETs each heading's table the way the page does:
getContactDetialsByType?type=<headTitle>&circle=<circle>. An item per circle (not per heading) keeps the queue stable when a
circle adds or renames a heading. Rows = designation, STD code, office no, mobile, e-mail; no names. Office from the designation
(dforms/_power_ap.py): EE/O = division, Dy.EE/O = sub-division, AE/AEE/O = section. Inside an operation division table the
rows follow the hierarchy (Dy.EE, then its sections), so a section gets the last Dy.EE above it as its sub-division.
Expected about 60 headings and 900-1,100 rows for the 11 circles (Zone-1 Visakhapatnam alone has 19 rows).
"""
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, phone, raw
from dforms._power_ap import classify

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://www.apeasternpower.com/"
MOD = "power_apepdcl"


def headings(html):
    """(circle name, [headTitle, ...]) from a circle page."""
    m = re.search(r"var\s+circle\s*=\s*'([^']+)'", html)
    titles = []
    for t in re.findall(r'headTitle="([^"]+)"', html):
        if t not in titles:
            titles.append(t)
    return (m.group(1) if m else None), titles


def office_of(title):
    """(level, area) of the office a heading names."""
    t = clean(title) or ""
    m = re.match(r"(?i)operation\s+division\s*-\s*(.*)", t)
    if m:
        return "division", clean(m.group(1))
    m = re.match(r"(?i)circle\s+office\s*-\s*(.*)", t)
    if m:
        return "circle", clean(m.group(1))
    return "circle", None


def parse(html, circle, title, out, url):
    lvl, area = office_of(title)
    circ_area = circle
    division = area if lvl == "division" else None
    sub = None
    soup = BeautifulSoup(html, "lxml")
    n = 0
    for tr in soup.find_all("tr"):
        c = cells(tr)
        if len(c) < 5 or c[0].lower() == "designation":
            continue
        desig = clean(c[0])
        if not desig:
            sub = None                                    # an empty row separates sub-division blocks
            continue
        std = clean(c[1])
        office_no = clean(c[2])
        land = f"{std}-{office_no}" if std and office_no else office_no
        level, a, staff = classify(desig, lvl if lvl == "division" else "circle", division or circ_area)
        if level == "subdivision" and not staff:
            sub = a
        parents = {"circle": circ_area}
        if division and level in ("subdivision", "section") or (division and staff):
            parents["division"] = division
        if sub and level == "section" and not staff:
            parents["subdivision"] = sub
        if title and lvl == "circle" and not area:
            parents["wing"] = clean(title)
        out.add(f"{circle}:{desig}", level, a, post=desig, phone_=phone(c[3], land), email_=email(c[4]),
                parents=parents if level != "circle" or staff else None, source=url, staff_post=True if staff else None)
        n += 1
    return n


def fetch(p, get):
    url = p.get("url") or BASE + "contactsNew?type=" + p["circle_code"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    code = p.get("circle_code") or url.rsplit("=", 1)[-1]
    files = [raw(MOD, f"{code}-index", r.content, "html")]
    circle, titles = headings(r.text)
    if not circle or not titles:
        return [], files, "no headings on the circle page"
    out = Out(MOD, "AP", url, discom="APEPDCL")
    missing = []
    for i, t in enumerate(titles, 1):
        u = BASE + "getContactDetialsByType?type=" + quote(t) + "&circle=" + quote(circle)
        f = get(u)
        if f is None:
            missing.append(t)
            continue
        files.append(raw(MOD, f"{code}-{i}", f.content, "html"))
        parse(f.text, circle, t, out, u)
    why = "" if out.recs else "no rows" + (f" ({len(missing)} headings did not answer)" if missing else "")
    return out.recs, files, why
