"""Tamil Nadu Police citizen portal "Contact Us": www.police.tn.gov.in/digigov/contactUs (India only).
GET /getDistrict?officeTypeId=7 -> the 9 city commissionerates, ?officeTypeId=3 -> the districts and special units
(ORGANIZATION_ID, ORGANIZATION_NAME); GET /getContactUsGrid?unitId=<7|3>&dsgnId=&psId=&distId=<id>&villageId= ->
responseObject.data[] {unitName, designationName, empName, contactNo, email, address}. One row per officer, several per
station (law and order, crime, women). One queue item = one district or city; items(get) lists them.
The portal mixes official and personal contacts: phone is kept only for the TN Police CUG series 9498xxxxxx, email only for
official domains (not the generic police@tncctns.gov.in); other numbers and gmail addresses are left out. Rows of
subdivisions ('<name> SD', DSP) are level subdivision, the SP / Commissioner row is level district; wings (PEW, DCB, CCB, ...)
are kept with office_type "wing". Record id dept:police_tn:<dist id>:<unit>:<officer>."""
import json
import re

from dforms._police import clean, email, gz, rec, slug, uniq

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

M = "police_tn"
BASE = "https://www.police.tn.gov.in/digigov/contactUs"
SOURCE = "https://www.police.tn.gov.in/citizenportal/contactus"
CUG = re.compile(r"^9498\d{6}$")
WING = re.compile(r"\b(PEW|DCB|DCRB|CCB|CCIW|SB|DSB|SJHR|IUCAW|CWC|DCRB|CYBER CRIME WING|NIB|EOW|TRAFFIC INVESTIGATION|"
                  r"CSR|DCRB|OCIU|SIU|CB ?CID|Q ?BRANCH|PRO|MOB|DIST\.? ?CRIME)\b", re.I)
OFFICIAL = re.compile(r"@(?:[\w.-]+\.)?(?:gov\.in|nic\.in)$", re.I)


def grid_url(unit_id, dist_id):
    return f"{BASE}/getContactUsGrid?unitId={unit_id}&dsgnId=&psId=&distId={dist_id}&villageId="


def items(get):
    out = []
    for unit_id in (7, 3):
        r = get(f"{BASE}/getDistrict?officeTypeId={unit_id}")
        if r is None:
            continue
        for x in (r.json().get("responseObject") or {}).get("data") or []:
            did, name = x["ORGANIZATION_ID"], clean(x["ORGANIZATION_NAME"])
            out.append({"key": f"{M}:{unit_id}-{did}", "payload": {"reader": M, "url": grid_url(unit_id, did), "state": "TN",
                                                                  "unit_id": unit_id, "dist_id": did, "district": name, "india_only": True}})
    return out


def level_of(unit, desig):
    d = (desig or "").upper()
    if ("SUPERINTENDENT OF POLICE" in d and "DEPUTY" not in d) or ("COMMISSIONER" in d and "ASSISTANT" not in d and "DEPUTY" not in d):
        return "district"
    if re.search(r"\bSD\b", unit or "") or "DEPUTY SUPERINTENDENT" in d or "ASSISTANT COMMISSIONER" in d:
        return "subdivision"
    if "DEPUTY COMMISSIONER" in d:
        return "division"
    return "police_station"


def parse(rows, dist_id, district, url=SOURCE):
    recs = []
    for x in rows:
        unit, desig, name = clean(x.get("unitName")), clean(x.get("designationName")), clean(x.get("empName"))
        if not unit:
            continue
        phone = re.sub(r"\D", "", x.get("contactNo") or "")[-10:]
        mail = email(x.get("email") or "")
        mail = mail if mail and OFFICIAL.search(mail) and mail != "police@tncctns.gov.in" else None
        level = level_of(unit, desig)
        addr = clean(x.get("address"))
        recs.append(rec(M, f"{dist_id}:{slug(unit)}:{slug(name or desig)}", level=level, area=unit,
                        office_type="wing" if level == "police_station" and WING.search(unit) else None, post=desig, name=name,
                        phone=phone if CUG.match(phone) else None, email=mail,
                        address=None if addr in (None, "TAMILNADU, INDIA") else addr, state="TN", district=district, source=url))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or grid_url(p["unit_id"], p["dist_id"])
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, f"grid-{p.get('unit_id')}-{p['dist_id']}.json", r.content)]
    try:
        rows = (r.json().get("responseObject") or {}).get("data") or []
    except (ValueError, json.JSONDecodeError, AttributeError):
        return [], files, "not json"
    recs = parse(rows, p["dist_id"], p.get("district"))
    return recs, files, "" if recs else "no rows"
