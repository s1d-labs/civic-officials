"""Assam: APDCL contact directory, www.apdcl.org/website/api/web/allContact (the JSON behind apdcl.org/website/Contact). Answers
from Germany. One GET returns all 320 entries; one queue item.

Fields: zone_name, circle_name, division_name, sd_name, contact_person, designation, phone, mobile, email, type, updated_time.
type: 1 headquarters, 2 zone (GM), 3 circle (DGM), 4 division (AGM), 5 sub-division (SDE), 6 IRCA, 7 T&C, 8 district AGM (Project).
Kept: types 2-5 (about 230: 8 zones, 20 circles, 45 divisions, 158 sub-divisions), with officer names; last_updated = the row's
own updated_time. Record id dept:power_apdcl:<id>.
"""
import json

from dforms._power import Out, clean, email, phone, raw

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

URL = "https://www.apdcl.org/website/api/web/allContact"
TYPES = {2: ("zone", "zone_name", "General Manager"), 3: ("circle", "circle_name", "Deputy General Manager"),
         4: ("division", "division_name", "Assistant General Manager"), 5: ("subdivision", "sd_name", "Sub-Divisional Engineer")}


def parse(js, source=URL):
    out = Out("power_apdcl", "AS", source, discom="APDCL")
    for x in js.get("allContact") or []:
        t = TYPES.get(x.get("type"))
        if not t:
            continue
        lvl, field, post = t
        par = {"zone": x.get("zone_name") if lvl != "zone" else None,
               "circle": x.get("circle_name") if lvl in ("division", "subdivision") else None,
               "division": x.get("division_name") if lvl == "subdivision" else None}
        out.add(str(x.get("id")), lvl, x.get(field), post=clean(x.get("designation")) or post, name=x.get("contact_person"),
                phone_=phone(x.get("mobile"), x.get("phone")), email_=email(x.get("email")), district=x.get("district"),
                office_id=str(x.get("id")), parents=par, last_updated=(x.get("updated_time") or "")[:10] or None)
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_apdcl", "allContact", r.content, "json")]
    try:
        js = json.loads(r.content)
    except ValueError:
        return [], files, "not json"
    recs = parse(js, url)
    return recs, files, "" if recs else "no offices"
