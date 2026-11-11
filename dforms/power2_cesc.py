"""West Bengal: CESC Limited (Kolkata and Howrah licence area), www.cesc.co.in. One queue item:
- /HTcustomerLogin/groCgro ("Grievance Redressal Information", public, no login despite the path): one table Address | name (with the
  matter in brackets) | Designation | Email Id., in two blocks: "HT GRIEVANCE REDRESSAL OFFICERS" (2: billing, supply) and "CENTRAL
  GRIEVANCE REDRESSAL OFFICERS" (2). Names, posts, e-mails and addresses; no phones. 4 rows, level state (one licence area).
Not read: /connectWithUs "Locate the nearest office" (Regional Offices, District Offices, Cash Offices): the office list comes from a
script (custom.js) that was not fetched (3-request budget); check it for regional / district office officers.
Answers from Germany (2026-11-11). No page date. Records "dept:power2_cesc:<block>:<name>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power, _util2_east

MODULE = "power2_cesc"
URL = "https://www.cesc.co.in/HTcustomerLogin/groCgro"


def items(get=None):
    return [{"key": f"{MODULE}:gro", "payload": {"reader": MODULE, "url": URL, "state": "WB", "india_only": False}}]


def _lines(td):
    return [_power.clean(x) for x in td.get_text("\n", strip=True).split("\n") if _power.clean(x)]


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    out = _power.Out(MODULE, "WB", url, discom="CESC Limited")
    for tb in soup.find_all("table"):
        block = None
        for tr in tb.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 1:
                block = _power.clean(tds[0].get_text(" ", strip=True))
                continue
            if len(tds) < 3 or not block:
                continue
            cell = {td.get("data-label", str(i)): td for i, td in enumerate(tds)}
            who = _lines(next((v for k, v in cell.items() if k.startswith("For both")), tds[1]))
            name = _util2_east.person(who[0]) if who else None
            matter = re.sub(r"^\((.*)\)$", r"\1", who[1]) if len(who) > 1 else None
            post = " ".join(_lines(cell.get("Designation", tds[2])))
            kind = "Central Grievance Redressal Officer" if block.upper().startswith("CENTRAL") else "HT Grievance Redressal Officer"
            mail = _power.email(cell["Email Id."].get_text(" ", strip=True)) if "Email Id." in cell else None
            addr = ", ".join(_lines(cell["Address"])) if "Address" in cell else None
            out.add(f"{_power.slug(block)}:{name}", "state", "CESC licence area (Kolkata and Howrah)",
                    post=f"{kind}{' (' + matter + ')' if matter else ''}: {post}", name=name, email_=mail, address=addr,
                    district="Kolkata")
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_power.raw(MODULE, "gro-cgro", r.content, "html")], "" if recs else "no rows"
