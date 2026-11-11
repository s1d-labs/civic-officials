"""Municipal Corporation Bathinda (mcbathinda.com): the officers and staff of each branch with the zones they serve, from the branch
pages /DepartmentServices.aspx?S=<n> (ASP.NET, Softel Solutions; in archive.s1d.me, saved 2026-11-10; the pages show no date).
Each page has one table "Officer/Staff Details": Name of Officer (Sh./Smt.) | Designation | Work Assigned | Mobile No. |
Area (Zones) ("1 To 8", "6", "2,3"). Branches: 1 Water Supply & Sewerage, 2 Street Lights, 3 Sanitation, 4 Fire Brigade,
5 Horticulture, 6 Engineering, 7 Birth & Death, 8 House / Property Tax, 9 Licence, 11 Tehbazari & Advertisement, 13 Building,
14 Rent, 15 Accounts, 16 GIS, 17 Store, 18 NULM, 19 PMAY, 20 General (10 Land and 12 Building Plans had no rows). The city has
8 zones and 50 wards; the site does not say which wards each zone holds. Records: rows with zones: level "zone" (zones = the zone
numbers; area "Zone 6" / "Zones 1-8"); the other rows: level "body". The zone-wise "Employee Deployed" files are attendance sheets
of sweepers (docx), not read. Record ids: dept:ward2n_bathinda:<branch slug>:<zones | hq>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_bathinda"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Bathinda", "248367", "PB", "Bathinda"
BASE = "https://mcbathinda.com/DepartmentServices.aspx?S="
BRANCHES = {1: ("Water Supply & Sewerage", "water"), 2: ("Street Lights", "electrical"), 3: ("Sanitation", "sanitation"),
            4: ("Fire Brigade", "other"), 5: ("Horticulture", "horticulture"), 6: ("Engineering Branch", "engineering"),
            7: ("Birth & Death", "health"), 8: ("House Tax / Property Tax", "revenue"), 9: ("Licence", "revenue"),
            11: ("Tehbazari & Advertisement Branch", "revenue"), 13: ("Building Branch", "planning"), 14: ("Rent Branch", "revenue"),
            15: ("Accounts Branch", "other"), 16: ("Geographic Information System (GIS)", "other"), 17: ("Store", "other"),
            18: ("National Urban Livelihoods Mission (NULM)", "other"), 19: ("Pradhan Mantri Awas Yojana (PMAY)", "other"),
            20: ("General Branch", "administration")}


def items(get=None):
    return [{"key": f"{MODULE}-{_esw.slug(b)}", "payload": {"reader": MODULE, "url": f"{BASE}{n}", "branch": b, "state": STATE}}
            for n, (b, _) in BRANCHES.items()]


def zones_of(text):
    t = _esw.clean(text)
    if not re.search(r"\d", t):
        return []
    return [z for z in _ward.wards_of(t) if z.isdigit() and 1 <= int(z) <= 8]


def parse(html, p):
    n = int(re.search(r"S=(\d+)", p["url"]).group(1))
    branch, bwing = BRANCHES.get(n, (p.get("branch") or "", "other"))
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "name", "designation"):
        for r in rows:
            name, post = _ward.col(r, "name"), _ward.col(r, "designation")
            if not post or not name:
                continue
            zs = zones_of(_ward.col(r, "area", "zone"))
            wing = _ward.wing_of(post)
            if wing in ("other", "engineering", "administration") and bwing != "other":
                wing = bwing
            area = (f"Zone {zs[0]}" if len(zs) == 1 else f"Zones {', '.join(zs)}") if zs else BODY
            recs.append(_ward.record(MODULE, f"{_esw.slug(branch)}:{'z' + '-'.join(zs) if zs else 'hq'}:{_esw.slug(post)}:{_esw.slug(name)}",
                                     seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone" if zs else "body",
                                     area=area, zone=area if zs else None, zones=zs or None, post=post, name=name,
                                     phone=_ward.col(r, "mobile"), work=_ward.col(r, "work") or None, section=branch, wing=wing,
                                     source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, _esw.slug(p.get("branch") or "branch"), r.content)], "" if recs else "no staff rows"
