"""Uttarakhand: Uttarakhand Jal Sansthan (UJS) who's who, ujs.uk.gov.in/whos-who/ (pages 1-3, S3WaaS). Answers from Germany and India.
One GET per page; one table per caption ("Chief General Manager Office", "Circle", "Division", "Zonal"): Name, Designation, Email
(written [at]/[dot]), Address, Phone, Fax, Activity (the towns the office serves). Page 1 holds the CGM office, circles, the first
divisions and the zones; pages 2-3 hold the other maintenance divisions. About 52 rows. The footer shows "Last Updated: DD.MM.YYYY".
Three queue items (one per page). Record ids: dept:water_uk:<slug of designation>:<slug of area>.
"""
import re

from dforms import _esw

MODULE = "water_uk"
BASE = "https://ujs.uk.gov.in/whos-who/"
PAGES = {1: BASE, 2: BASE + "page/2/", 3: BASE + "page/3/"}
LEVEL = {"chief general manager office": "state", "circle": "circle", "division": "division", "zonal": "zone"}
ORG = "Uttarakhand Jal Sansthan"


def items(get=None):
    return [{"key": f"{MODULE}-p{n}", "payload": {"reader": MODULE, "url": u, "state": "UK", "page": n}} for n, u in PAGES.items()]


def _updated(soup):
    m = re.search(r"Last Updated:\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", _esw.clean(soup.get_text(" ")))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def _area(desig, address, served):
    """The place the office is named after: the address "... Division <place>" / "Water Works <place>", else the place at the
    end of the designation ("Superintending Engineer (Incharge) Pithoragarh"), else the first town it serves."""
    m = re.search(r"(?:Division|Water Works)\s+(.+)$", address or "", re.I)
    if m:
        return m.group(1).strip(" ,")
    if re.search(r"\b(Cell|Store|Unit|Laboratory)\b", address or "", re.I):
        return _esw.clean(address)
    d = re.sub(r"\(.*?\)", " ", desig)
    m = re.search(r"(?:Engineer|Manager)\s+(?!T\.R\.M|Head Office)([A-Z][A-Za-z ]+)$", _esw.clean(d))
    if m:
        return m.group(1).strip()
    return (served or "").split(",")[0].strip()


def parse(html, url=BASE):
    soup = _esw.soup(html)
    updated = _updated(soup)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        cap = t.find("caption")
        rows = _esw.grid(t)
        if not rows or [h.lower() for h in rows[0][:2]] != ["name", "designation"]:
            continue
        head = [h.lower() for h in rows[0]]
        level = LEVEL.get(_esw.clean(cap.get_text()).lower() if cap else "", "division")
        for row in rows[1:]:
            c = dict(zip(head, row))
            desig = c.get("designation", "")
            if not desig or desig.lower() == "designation":
                continue
            served = c.get("activity", "")
            area = _area(desig, c.get("address", ""), served)
            post = _esw.clean(re.sub(r"\(\s*in-?charge\s*\)", "", desig, flags=re.I))
            office = _esw.slug(re.sub(r"\s+" + re.escape(area) + "$", "", post) if area else post)
            key = f"{office}:{_esw.slug(area)}" if area else office
            k, i = key, 2
            while k in seen:
                k, i = f"{key}:{i}", i + 1
            seen.add(k)
            recs.append(_esw.record(MODULE, k, dept="water", level=level, area=area, post=desig, name=c.get("name"),
                                    phone=_esw.phones(c.get("phone")), email=_esw.emails(c.get("email")),
                                    address=c.get("address"), state="UK", office_id=f"UK-UJS-{k.replace(':', '-')}", org=ORG,
                                    serves=served, fax=_esw.phones(c.get("fax")), source=url, last_updated=updated))
    return recs


def fetch(p, get):
    url = p.get("url") or PAGES[int(p.get("page", 1))]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"whos-who-p{p.get('page', 1)}", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
