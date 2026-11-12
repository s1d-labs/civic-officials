"""PVVNL (Paschimanchal Vidyut Vitran Nigam, west Uttar Pradesh): office hierarchy pages, pvvnl.org/office_hierarchy/<District>.
Works from Germany. One queue item = one of the 14 districts. Each page has one table (S.No, Name of Office = officer name,
Designation, Area, Twitter, Email Id, Contact No.) in zone order: Chief Engineer (zone), Superintending Engineer (circle),
Executive Engineer (division), Assistant Engineer / SDO (sub-division). "Vacant" and "---" mean empty. About 75-90 rows per
district, about 1,000 in all. The zone JSON pvvnl.org/read_data/<id> is a subset of these pages, so it is not read.
Record id dept:power_pvvnl:<district>:<designation>:<area>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, phone, raw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_pvvnl"
BASE = "https://pvvnl.org/office_hierarchy/"
DISTRICTS = ["Amroha", "Baghpat", "Bijnor", "Bulandshahar", "Gautam Buddha Nagar", "Ghaziabad", "Hapur", "Meerut", "Moradabad",
             "Muzaffarnagar", "Rampur", "Saharanpur", "Sambhal", "Shamli"]


def level(post):
    p = (post or "").lower()
    if p.startswith("chief engineer") or p.startswith("ce "):
        return "zone"
    if "superintend" in p:
        return "circle"
    if p.startswith("executive engineer") or p.startswith("xen"):
        return "division"
    if p.startswith("assistant engineer") or p.startswith("sdo") or p.startswith("ae"):
        return "subdivision"
    if p.startswith("junior engineer") or p.startswith("je"):
        return "section"
    return None


def parse(html, district, url):
    out = Out(MOD, "UP", url, discom="PVVNL")
    soup = BeautifulSoup(html, "lxml")
    t = soup.find("table")
    if not t:
        return out.recs
    zone = circle = None
    circles = []
    for tr in t.find_all("tr"):
        c = cells(tr)
        if len(c) < 7 or not c[0].strip().isdigit():
            continue
        name, post, area, mail, tel = c[1], clean(c[2]), clean(c[3]), c[5], c[6]
        lvl = level(post)
        if not lvl:
            continue
        attached = "attach" in (post or "").lower()
        if lvl == "zone" and not attached:
            zone, circles = area, []
        elif lvl == "circle" and not attached:
            circles.append(area)
        circle = circles[0] if len(circles) == 1 else None
        par = {"zone": zone if lvl != "zone" else None, "circle": circle if lvl in ("division", "subdivision") else None}
        office = area
        if lvl == "subdivision":
            par["division"] = area
            m = re.match(r"(?i)^SDO\b[\s\-]*(.*)$", post or "")
            if m:                                   # "SDO-2 Balramnagar": the sub-division is named in the designation
                office = post
        out.add(f"{district}:{post}:{area}", lvl, office, post=post, name=name, phone_=phone(tel), email_=email(mail),
                district=district, parents=par)
    return out.recs


def fetch(p, get):
    district = p["district"]
    url = p.get("url") or BASE + district
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, district, r.content, "html")]
    recs = parse(r.text, district, url)
    return recs, files, "" if recs else "no rows"
