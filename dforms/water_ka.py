"""Karnataka water offices. Two pages, one queue item each (payload "page"), both answer only from India:
- "kuwsdb": Karnataka Urban Water Supply and Drainage Board, "Know your office" (kuwsdb.karnataka.gov.in/1/know-your-office/en): one
  table, about 110 officers (Name of the officer | Designation | Division | Location | Office numbers | email ID | Office Address):
  chairman and central office, chief engineers of the revenue zones, EEs of divisions, AEEs of sub-divisions.
  Record ids: dept:water_ka:KA-KUWSDB-<slug of division>:<slug of post>.
- "bwssb": Bangalore Water Supply and Sewerage Board service stations (bwssb.karnataka.gov.in/7/service-station/en): one table, one row
  per service station; the three cells hold the division (EE), the sub-division (AEE) and the service station (AE/JE), each as
  lines "<code or place> | [Name:] <name> | <post> | Address: ... | Office Number: ... | Mobile...: ... | Mail: ...". Each distinct
  division, sub-division and station is one office (about 10 divisions, 40 sub-divisions, 140 stations).
  Record ids: dept:water_ka:KA-BWSSB-<slug of division / sub-division / station code>.
No date on either page.
"""
import re

from dforms import _esw, _water
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_ka"
PAGES = {"kuwsdb": "https://kuwsdb.karnataka.gov.in/1/know-your-office/en",
         "bwssb": "https://bwssb.karnataka.gov.in/7/service-station/en"}
ORGS = {"kuwsdb": "Karnataka Urban Water Supply and Drainage Board", "bwssb": "Bangalore Water Supply and Sewerage Board"}


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "page": k, "url": u, "state": "KA", "india_only": True}}
            for k, u in PAGES.items()]


def kuwsdb(html, url=PAGES["kuwsdb"]):
    soup = _esw.soup(html)
    t = next((t for t in soup.find_all("table") if "Name of the officer" in t.get_text(" ")), None)
    if t is None:
        return []
    rows = pgrid(t)
    head = [h.lower() for h in rows[0]]
    recs, seen = [], set()
    for row in rows[1:]:
        c = dict(zip(head, row))
        post, div = c.get("designation", ""), c.get("division", "")
        if not (post and div):
            continue
        level = _water.level_of(post, _water.level_of(div, "state"))
        if level == "state" and re.search(r"(?i)zone", div):
            level = "zone"
        if level == "zone" and re.search(r"(?i)central office", div):
            level = "state"
        name = c.get("name of the officer", "")
        bare = re.sub(r"(?i)\(\s*a\s*/?\s*c\s*\)|\(i/?c\)", "", post)    # "(A/C)" = additional charge: not part of the office
        key = _water.unique(f"KA-KUWSDB-{_esw.slug(div)}:{_esw.slug(bare)}", seen)
        recs.append(_esw.record(MODULE, key, dept="water", level=level, area=div, post=post, name=name if not re.match(r"(?i)vacant", name) else None,
                                phone=_esw.phones(c.get("office numbers")), email=_esw.emails(c.get("email id")),
                                address=c.get("office address"), state="KA", district=c.get("location"),
                                office_id=f"KA-KUWSDB-{_esw.slug(div)}", org=ORGS["kuwsdb"], source=url, src_pos=row.pos))
    return recs


LABEL = re.compile(r"^(name|address|office number|mobile(?: number| no\.?)?|mail)\s*[:.\-]*\s*(.*)$", re.I)


def officer_cell(text):
    """'C 11 | Name: Mahesh Kumar K.S | Assistant Executive Engineer | Address: ... | Office Number: ... | Mobile Number: ... | Mail: ...'
    -> dict(code, name, post, address, office, mobile, mail)."""
    lines = [x.strip() for x in text.split(" | ") if x.strip()]
    d = {"code": lines[0] if lines else ""}
    free = []
    for x in lines[1:]:
        # "Address: ... Office Number:22945171" can share one line
        for part in re.split(r"\s+(?=(?:Office Number|Mobile(?: Number| No\.?)?|Mail)\s*[:.\-])", x, flags=re.I):
            m = LABEL.match(part)
            if m:
                k = m.group(1).lower().split()[0]
                k = {"office": "office"}.get(k, k)
                d[k] = (d.get(k, "") + " " + m.group(2)).strip()
            else:
                free.append(part)
    if "name" not in d and free:
        d["name"] = free.pop(0)
    if free:
        d["post"] = free[0]
    return d


def bwssb(html, url=PAGES["bwssb"]):
    soup = _esw.soup(html)
    t = next((t for t in soup.find_all("table") if "Service Stations" in t.get_text(" ")), None)
    if t is None:
        return []
    recs, done = [], set()
    for row in pgrid(t)[1:]:
        if len(row) < 3:
            continue
        cells = [officer_cell(x) for x in row[:3]]
        div, sub, stn = (c.get("code", "") for c in cells)
        for col, (c, level, area, parent, post) in enumerate(((cells[0], "division", div, None, "Executive Engineer"),
                                             (cells[1], "subdivision", sub, div, "Assistant Executive Engineer"),
                                             (cells[2], "section", stn, sub, "Assistant Engineer")), 1):
            key = f"KA-BWSSB-{_esw.slug(area)}" if level != "section" else f"KA-BWSSB-{_esw.slug(parent)}-{_esw.slug(area)}"
            if not area or key in done:
                continue
            done.add(key)
            name = c.get("name", "")
            m = re.search(r"\((JE|AE|AEE)\)\s*$", name)
            if m:
                name, post = name[:m.start()].strip(), {"JE": "Junior Engineer", "AE": "Assistant Engineer", "AEE": post}[m.group(1)]
            recs.append(_esw.record(MODULE, key, dept="water", level=level, area=area, post=c.get("post") or post, name=name,
                                    phone=_esw.phones(c.get("office"), c.get("mobile")), email=_esw.emails(c.get("mail")),
                                    address=c.get("address"), state="KA", district="Bengaluru Urban", office_id=key,
                                    org=ORGS["bwssb"], parent=f"KA-BWSSB-{_esw.slug(parent)}" if parent else None, source=url,
                                    src_pos=dict(row.pos, col=col)))
    return recs


PARSE = {"kuwsdb": kuwsdb, "bwssb": bwssb}


def fetch(p, get):
    page = p.get("page", "kuwsdb")
    url = p.get("url", PAGES[page])
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, page, r.content)]
    recs = PARSE[page](r.text, url)
    return recs, files, "" if recs else "no rows"
