"""West Bengal: WBSEDCL important telephone numbers, www.wbsedcl.in/irj/go/km/docs/internet/new_website/Imp_Phone_Number.html (one
page, one queue item). One table of two columns; a heading row (ZONE | TELEPHONE, REGIONAL OFFICE | TELEPHONE, DIVISION ...)
starts each block, then one office per row: name | telephone. About 76 offices: 5 zones, ~20 regional offices (WBSEDCL regions sit
between zone and division: level circle) and the distribution divisions. No officer names and no posts: the office telephone only.
Customer care centres (CCC = section level, Contact_Customer_Care.html) and the regional grievance officers with names
(Grievance_Redressal_for_consumers.html) are read by dforms/power2_wbsedcl_rgro.py.
No page date. Records "dept:power2_wbsedcl:<level>:<office>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power, _util2

MODULE = "power2_wbsedcl"
URL = "https://www.wbsedcl.in/irj/go/km/docs/internet/new_website/Imp_Phone_Number.html"
HEADS = (("zone", r"^ZONE"), ("circle", r"^REGION"), ("division", r"^DIVISION"), ("section", r"^(CCC|CUSTOMER|SUPPLY|GROUP)"),
         ("state", r"^(CORPORATE|HEAD|VIDYUT|CENTRAL)"))


def items(get=None):
    return [{"key": f"{MODULE}:phones", "payload": {"reader": MODULE, "url": URL, "state": "WB", "india_only": False}}]


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    out = _power.Out(MODULE, "WB", url, discom="WBSEDCL")
    for tb in soup.find_all("table"):
        level = None
        for tr in tb.find_all("tr"):
            c = [x for x in _power.cells(tr) if x]
            if not c:
                continue
            if len(c) >= 2 and re.search(r"TELEPHONE|PHONE", c[-1], re.I):
                level = next((lv for lv, rx in HEADS if re.search(rx, c[0].strip().upper())), "division")
                continue
            if level is None or len(c) < 2:
                continue
            post = {"zone": "Zonal Manager office", "circle": "Regional Manager office", "division": "Divisional Manager office",
                    "section": "Station Manager office", "state": "Office"}[level]
            out.add(f"{level}:{c[0]}", level, re.sub(r"\s+Zone$", "", c[0]), post=post,
                    phone_=_util2.tel(c[1]))
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_power.raw(MODULE, "phones", r.content, "html")], "" if recs else "no rows"
