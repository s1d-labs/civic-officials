"""APSPDCL (Andhra Pradesh Southern Power Distribution): https://www.apspdcl.in/phonenumbers.php. Answers from Germany.

One page, one queue item. Panels (h4.panel-title) = corporate office + 9 circles (Tirupati, Chittoor, Nellore, Sri Sathya Sai,
Anantapur, Kurnool, Nandyal, Kadapa, Annamayya); each row = #, designation, number. No names, no email, no address. The office
is written into the designation ("AE/O/Kallur", "DE / O / Adoni", "DEE/Town/1/Tirupati"): dforms/_power_ap.py reads it.
Rows do not follow the hierarchy in every circle (Kurnool lists all DEs first), so only the circle is given as parent.
About 1,105 rows: ~520 AE section rows, ~150 DEE/ADE sub-division rows, ~65 EE/DE division rows, the rest wing/staff posts.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, phone, raw
from dforms._power_ap import classify

URL = "https://www.apspdcl.in/phonenumbers.php"
MOD = "power_apspdcl"


def circle_name(title):
    t = clean(title) or ""
    return clean(re.sub(r"\s*CIRCLE\s*$", "", t, flags=re.I)).title() if t else None


def parse(html, url=URL):
    out = Out(MOD, "AP", url, discom="APSPDCL")
    soup = BeautifulSoup(html, "lxml")
    for h in soup.select("h4.panel-title"):
        panel = h.find_parent(class_="panel") or h.parent
        title = clean(h.get_text(" ", strip=True))
        corporate = "CORPORATE" in (title or "").upper()
        circ = None if corporate else circle_name(title)
        for tr in panel.select("tbody tr") or panel.find_all("tr"):
            c = cells(tr)
            if len(c) < 3 or not clean(c[1]) or c[1].lower() == "designation":
                continue
            desig = clean(c[1])
            if corporate:
                level, area, staff = "state", "APSPDCL Corporate Office", True
            else:
                level, area, staff = classify(desig, "circle", circ)
            out.add(f"{circ or 'corporate'}:{desig}", level, area, post=desig, phone_=phone(c[2]),
                    parents={"circle": circ} if circ and level != "circle" or (circ and staff) else None,
                    staff_post=True if staff else None)
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, "phonenumbers", r.content, "html")]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
