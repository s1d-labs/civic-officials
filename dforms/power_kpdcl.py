"""KPDCL (Kashmir Power Distribution Corporation): the officers' directory page kpdcl.jk.gov.in/page/SGpLSUxqeFdPSG82c2g0ZzhlRHRVQT09.
Works from Germany. One queue item: one HTML table (pagination is done in the browser, every row is in the page), about 127
rows: Sr No, District, Department, Circle, Division, Office (SDO Office, STD-SDO, Division office, Division TO office, Circle
Office ...), Sub-Division (the office's own name), Rank/Designation, Name, Phone. Levels from the Office column: SDO / STD-SDO /
plant = sub-division, division offices = division, circle offices = circle, chief office = zone, headquarters = state.
The page's "Last Updated" date is the date of the request, so it is not kept.
Record id dept:power_kpdcl:<division>:<sub-division>:<designation>.
"""
from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, phone, raw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_kpdcl"
URL = "https://kpdcl.jk.gov.in/page/SGpLSUxqeFdPSG82c2g0ZzhlRHRVQT09"


def level(office):
    o = (office or "").lower()
    if "sdo" in o or "subdivision" in o or "sub-division" in o or o == "plant":
        return "subdivision"
    if "division" in o:
        return "division"
    if "circle" in o:
        return "circle"
    if "chief" in o:
        return "zone"
    if "kpdcl" in o or "store" in o:
        return "state"
    return None


def parse(html, url=URL):
    out = Out(MOD, "JK", url, discom="KPDCL")
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        head = [h.lower() for h in cells(trs[0])] if trs else []
        if "sub-division" not in head or "name" not in head:
            continue
        ix = {h: i for i, h in enumerate(head)}
        for tr in trs[1:]:
            c = cells(tr)
            if len(c) != len(head):
                continue
            g = lambda k: clean(c[ix[k]]) if k in ix else None  # noqa: E731
            lvl = level(g("office"))
            if not lvl:
                continue
            area = {"subdivision": g("sub-division"), "division": g("division"), "circle": g("circle")}.get(lvl) or g("sub-division")
            par = {"circle": g("circle") if lvl in ("division", "subdivision") else None,
                   "division": g("division") if lvl == "subdivision" else None}
            out.add(f"{g('division')}:{g('sub-division')}:{g('rank/designation')}", lvl, area, post=g("rank/designation"),
                    name=g("name"), phone_=phone(g("phone")), district=g("district"), parents=par,
                    office_type=g("office"), office=g("sub-division"))
    return out.recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, "directory", r.content, "html")]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
