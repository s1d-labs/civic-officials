"""Tamil Nadu: fire and rescue stations of the Tamil Nadu Fire and Rescue Services, from www.tnfrs.tn.gov.in, menu "Fire and
Rescue Stations": one page per region (Northern, North Western, Western, Central, Southern, Salem, Tirunelveli, Villupuram):
subsubmenu_page_content.php?menu_id=NDM2&submenu_id=ODk5&thirdlvl_id=<base64 of 411..418>&dept_id=443&lang=MQ==.
Each page has a heading "<Region> (<n> Stations)" and one table per district ("1. Chennai South District"):
S.No | Fire Station | Tab Number | Landline Number | CUG Number | Fire Station Mail ID. No officer names. Page date "Last Updated:
21 Oct 2026". Answers only from India (this box gets no answer). 8 queue items, about 350 stations.
Record ids: dept:civic_fire_tn:<district slug>:<station slug>.
"""
import base64
import re
from datetime import datetime

from dforms import _civic, _esw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fire_tn"
PAGE = ("https://www.tnfrs.tn.gov.in/subsubmenu_page_content.php?menu_id=NDM2&submenu_id=ODk5&thirdlvl_id={}&dept_id=443"
        "&lang=MQ==")
REGIONS = {411: "Northern", 412: "North Western", 413: "Western", 414: "Central", 415: "Southern", 416: "Salem",
           417: "Tirunelveli", 418: "Villupuram"}


def items(get=None):
    return [{"key": f"{MODULE}-{n}", "payload": {"reader": MODULE, "url": PAGE.format(base64.b64encode(str(n).encode()).decode()),
                                                 "state": "TN", "india_only": True, "region": f"{r} Region"}}
            for n, r in REGIONS.items()]


def last_updated(html):
    m = re.search(r"Last Updated:\s*(\d{1,2} \w{3} \d{4})", html)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def heading(table):
    """The nearest text above a table that names a district ('1. Chennai South District' -> 'Chennai South')."""
    for e in table.find_all_previous(string=True, limit=60):
        x = _esw.clean(e)
        m = re.match(r"^\d{1,2}\.\s*(.+?)\s+District$", x, re.I)
        if m:
            return m.group(1)
    return ""


def parse(html, url, region=""):
    soup = _esw.soup(html)
    lu = last_updated(html)
    recs, seen = [], set()
    for table in soup.find_all("table"):
        gp = []
        g = _esw.grid(table, pos=gp)
        if not g or "fire station" not in " ".join(g[0]).lower():
            continue
        head = [h.lower() for h in g[0]]
        col = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("station", "tab", "landline", "cug", "mail")}
        district = heading(table)
        for gi, row in enumerate(g[1:], 1):
            if col["station"] is None or len(row) <= col["station"]:
                provenance.skip_row(row, 'skip: col["station"] is None or len(row) <= col["station"]')
                continue
            station = _esw.clean(row[col["station"]])
            if not station or station.lower().startswith(("s.no", "total")):
                provenance.skip_row(row, 'skip: not station or station.lower().startswith(("s.no", "total"))')
                continue
            cell = lambda k: row[col[k]] if col[k] is not None and col[k] < len(row) else ""   # noqa: E731
            name = re.sub(r"\s+FS$", "", station).strip()
            key = _civic.unique(f"{_esw.slug(district)}:{_esw.slug(name)}", seen)
            recs.append(_civic.record(
                MODULE, key, "fire", dept="fire", level="facility", area=name, office=f"{name} Fire and Rescue Station",
                post="Station Officer", phone=_esw.phones(cell("landline"), cell("cug"), cell("tab")),
                landline=_esw.phones(cell("landline")), cug=_esw.phones(cell("cug")), tab=_esw.phones(cell("tab")),
                email=_esw.emails(cell("mail")), district=district, region=region, state="TN", office_id=f"TN-FIRE-{key}",
                source=url, last_updated=lu, src_pos=gp[gi]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    m = re.search(r"thirdlvl_id=([^&]+)", p["url"])
    files = [_esw.keep(MODULE, (m.group(1) if m else "page").strip("="), r.content)]
    recs = parse(r.text, p["url"], p.get("region", ""))
    return recs, files, "" if recs else "no rows"
