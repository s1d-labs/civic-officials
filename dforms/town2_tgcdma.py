"""Telangana: the office staff of the town bodies on the CDMA town site platform (<site>.telangana.gov.in, the 112 sites of
platform_sites.csv), from each site's "Staff Directory" page, /pages/staff-directory.

The page is one table: Sno | Name | Designation | Mobile. The Commissioner comes first (role head), then the office: Manager,
Senior / Junior Assistants, Executive Engineer, Municipal Engineer, Deputy Executive Engineer, Assistant Engineers, Town Planning
Officer and Town Planning Building Overseers (TPBO), Revenue Officer, Revenue Inspectors, Sanitary Inspectors, Environment
Engineer. Every named row is kept. The page shows no date.
Sample (live from India, dev-vps-3 Mumbai, 2026-11-13): Suryapet Municipality, 23 rows. The platform host of Achampet is
"atchampetmunicipality" (the name "achampetmunicipality" does not resolve).

Sites: dforms/town2_tgcdma_sites.json = platform_sites.csv (Telangana) minus the 6 sites whose three pages ulb2_tg reads
already (jangoan, sircilla, nandikonda, jadcherla, kothur, kothapally: ulb2_tg.BODIES kind "cdma") and minus badepallymunicipality
(Badepally is part of Jadcherla; LGD has no body of its own). Each site has the LGD local body code, body name and district of
civic.ulb, matched by name (letters only, then consonant skeleton; 106 of 107 matched that way, Atchampet = Achampet by hand).
Some bodies near Hyderabad were merged into GHMC in December 2025; their sites may be gone (the item then fails).
India only (ulb2_tg: no answer from Germany, 2026-11-11), route "direct" (the India server answers).
Records: dept town_body, level body, area = body, lgd_code, role, phone = Mobile. Ids: dept:town2_tgcdma:<site>:<post>:<name>.
"""
import json
from pathlib import Path

from dforms import _esw, _town2

METHOD = "html table"

MODULE = "town2_tgcdma"
STATE = "TG"
SITES = json.loads((Path(__file__).with_name("town2_tgcdma_sites.json")).read_text())


def items(get=None):
    out = []
    for s in SITES:
        p = {"reader": MODULE, "url": f"https://{s['site']}.telangana.gov.in/pages/staff-directory", "site": s["site"],
             "body": s["body"], "lgd_code": s["lgd_code"], "district": s["district"], "state": STATE, "india_only": True,
             "route": "direct"}
        out.append({"key": f"{MODULE}-{s['site']}", "payload": p})
    return out


def parse(html, p, url, seen=None):
    seen = seen if seen is not None else set()
    return [_town2.record(MODULE, STATE, p["site"], p["body"], row, seen, district=p.get("district"), lgd_code=p.get("lgd_code"),
                          source=url, src_url=url) for row in _town2.staff_rows(html)]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p, p["url"])
    return recs, [_esw.keep(MODULE, p["site"], r.content)], "" if recs else "no staff rows"
