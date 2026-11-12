"""Andhra Pradesh: commissioners of all urban bodies, from the CDMA's APCMMS public API
apcmms.ap.gov.in/apiv1/public/web/ulbdetails/ulbprofiles (JSON, about 100 KB; answers only from India: this box in Germany got no
connection, the India server got the answer).

Answer: {"status": 200, "data": [{"ulb_nm", "ulb_grde_nm" (Corp / Spl / Sel / I / II / III / NP), "comm_name", "mble_ph", "dstrt_nm",
"erp_ulb_sbdmn_tx" (the body's web sub-domain), "election_wards", "total_ward_secretariats", "svms" ...}]}, one object per body
(123 on 2026-11-11). One record per body: post "Commissioner", name, mobile, district. The answer has no date.
Names follow the CDMA's spelling, in capitals, with a district tag in brackets for twin names ("ATMAKUR(NLR)", "ATMAKUR(NANDYAL)"):
the reader removes the tag from area (the district carries it) and keeps the list name in name_list. LGD keeps older names for some
bodies (Rajahmundry = RAJAMAHENDRAVARAM, Cuddapah = KADAPA, Nuzvid = NUZIVIDU, Palacole = PALAKOL).
"""
import json
import re

from dforms import _esw, _ulb

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_ap"
URL = "https://apcmms.ap.gov.in/apiv1/public/web/ulbdetails/ulbprofiles"
GRADES = {"CORP": "Municipal Corporation", "NP": "Nagar Panchayat"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "AP", "india_only": True}}]


def body_type(grade):
    g = _esw.clean(grade)
    return GRADES.get(g.upper()) or (f"Municipality ({g})" if g else None)


def parse(text, url=URL):
    data = json.loads(text) if isinstance(text, (str, bytes)) else text
    rows = data.get("data") if isinstance(data, dict) else data
    recs, seen = [], set()
    for o in rows or []:
        listed = _esw.clean(o.get("ulb_nm"))
        if not listed:
            continue
        body = _esw.clean(re.sub(r"\s*\([^)]*\)\s*$", "", listed)).title()
        name = _esw.clean(o.get("comm_name"))
        phone = _esw.clean(str(o.get("mble_ph") or ""))
        if not (name or phone):
            continue
        site = _esw.clean(o.get("erp_ulb_sbdmn_tx"))
        recs.append(_ulb.record(MODULE, "AP", body, "Commissioner", seen, name=name, phone=phone, district=_esw.clean(o.get("dstrt_nm")),
                                body_type=body_type(o.get("ulb_grde_nm")), source=url, name_list=listed if listed.title() != body else None,
                                grade=_esw.clean(o.get("ulb_grde_nm")) or None, ulb_id=o.get("ulb_id"),
                                election_wards=o.get("election_wards"), web_subdomain=site or None))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "ulbprofiles", r.content, "json")]
    try:
        recs = parse(r.text, p.get("url", URL))
    except ValueError:
        return [], files, "not json"
    return recs, files, "" if recs else "no rows"
