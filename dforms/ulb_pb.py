"""Punjab: the tenant list of mSeva (Department of Local Government's eGov DIGIT platform), one POST to
https://mseva.lgpunjab.gov.in/egov-mdms-service/v1/_search?tenantId=pb with the MDMS criteria for module "tenant", master
"tenants" (JSON body, no login: the citizen web app reads the same master before sign-in). India only (times out from Germany;
answered from vpsin on 2026-11-11).

One answer (about 270 KB, 202 tenants on 2026-11-11) lists every urban local body of Punjab: code "pb.<town>", ulbName,
ulbLgdCode (the LGD local body code), city.districtName, city.ulbType (Municipal Corporation / Municipal Council / Nagar
Panchayat), city.ulbGrade, emailId, contactNumber (the office telephone, written without the leading 0), address,
PGRMasterContact (the grievance mobile). No officer names and no date.
The email is the body's official mailbox. In 118 of 199 it is the Executive Officer's post mailbox (eo.mc<town>@punjab.gov.in,
eomcabh@yahoo.in); "cmc<town>" is the Commissioner's of a corporation. So the post comes from the mailbox: "Executive Officer"
for eo..., "Commissioner" for cmc..., else "Office" (role staff). Extra key post_from = "email" says so. Name is always empty.
Left out: the 28 Improvement Trust tenants (code pb.it<town>: they repeat the town's LGD code), "pb.punjab" (the department) and
"pb.<town>pwssb" (the water board) and a "Testing" tenant. One record per body; lgd_code, ulb_grade and grievance_phone are extra keys.
"""
import json
import re

from dforms import _esw, _ulb

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_pb"
URL = "https://mseva.lgpunjab.gov.in/egov-mdms-service/v1/_search?tenantId=pb"
BODY = {"RequestInfo": {}, "MdmsCriteria": {"tenantId": "pb", "moduleDetails": [{"moduleName": "tenant", "masterDetails": [{"name": "tenants"}]}]}}
SOURCE = "https://mseva.lgpunjab.gov.in/"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "PB", "india_only": True}}]


def phone(s):
    """'1634220233' (STD code without its 0) -> '01634220233'; mobiles stay as they are."""
    d = re.sub(r"\D", "", s or "")
    if len(d) == 10 and d[0] not in "6789":
        d = "0" + d
    return d if len(d) >= 6 else ""


def post_of(email):
    local = (email or "").split("@")[0].lower()
    if re.match(r"eo\b|eo[._-]|eo(mc|np|mb)", local):
        return "Executive Officer"
    if re.match(r"cmc", local):
        return "Commissioner"
    return "Office"


def parse(data, url=URL):
    tenants = data.get("MdmsRes", {}).get("tenant", {}).get("tenants", [])
    recs, seen = [], set()
    for i, t in enumerate(tenants):
        code = t.get("code") or ""
        city = t.get("city") or {}
        if re.match(r"pb\.(it|testing)", code) or "pwssb" in code or code == "pb.punjab" or re.search(r"(?i)test", t.get("ulbName") or ""):
            continue
        if city.get("ulbType") not in ("Municipal Corporation", "Municipal Council", "Nagar Panchayat"):
            continue
        email = _esw.emails(t.get("emailId"))
        email = ", ".join(e for e in email.split(", ") if re.search(r"\.[a-z]{2,}$", e) and not e.endswith("punjab.gov"))   # "eo.npbhulath@punjab.gov." is cut
        ph = phone(t.get("contactNumber"))
        post = post_of(t.get("emailId"))
        if not (email or ph):
            continue
        body = _esw.clean(t.get("ulbName") or t.get("name"))
        recs.append(_ulb.record(MODULE, "PB", body, post, seen, phone=ph, email=email,
                                district=_esw.clean(city.get("districtName")), body_type=city.get("ulbType"), source=SOURCE,
                                lgd_code=t.get("ulbLgdCode") if re.fullmatch(r"\d{5,6}", t.get("ulbLgdCode") or "") and t["ulbLgdCode"] != "000000" else None,
                                ulb_grade=city.get("ulbGrade"), address=_esw.clean(t.get("address")) or None,
                                grievance_phone=phone(t.get("PGRMasterContact")) or None, post_from="email", tenant=code,
                                src_pos={"key": "MdmsRes.tenant.tenants", "index": i, "code": code}))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL), method="POST", data=json.dumps(BODY), headers={"Content-Type": "application/json"})
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "tenants", r.content, "json")]
    try:
        data = json.loads(r.content)
    except ValueError:
        return [], files, "not JSON"
    recs = parse(data, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
