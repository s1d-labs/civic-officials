"""Andhra Pradesh municipal corporations on the CDMA AP web platform (<city>.cdma.ap.gov.in, Next.js, one site per body): the
officers of each body, department by department. The "Contact Us" page (/ulbprofile/<city>/contact) loads its list from the
platform's open API: GET https://apcmms.ap.gov.in/apiv1/open/department/list/<ulb_id> -> {"data": [{"dprt_nm": "Engineering",
"RleArray": [{"rle_nm": "Assistant Engineer", "emplArray": [{"emple_name", "mble_ph", "cfms_emple_id", "prfle_img_tx"}]}]}]}.
Departments seen (Guntur, 2026-11-11): Administration (Revenue Officers, Revenue Inspectors), Town Planning (City Planner,
Deputy / Assistant City Planners, Town Planning Supervisors), Engineering (SE, EE, DEE, AE), Public Health and Sanitation
(Health Officer, Sanitary Supervisor, Sanitary Inspectors). The ulb ids are from GET /apiv1/open/ulbs (the 17 bodies of grade
"Corp"). India only: apcmms.ap.gov.in gives no TCP answer from Germany (2026-11-11); read from India the same day (not in
archive.s1d.me). The API does not say which ward, zone or ward secretariat a person serves, so records are level "body"
(area = the body). The ward secretariat staff (ward administration / sanitation / planning / amenities secretaries) are not on
any public list that we found. No "last updated" date. Record ids: dept:ward2s_apcdma:<city>:<post slug>:<name slug>.
"""
from dforms import _esw, _ward

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_apcdma"
STATE = "AP"
API = "https://apcmms.ap.gov.in/apiv1/open/department/list/"
# city key (site sub-domain) -> (ulb_id in the API, body, LGD code, district)
BODIES = {
    "visakhapatnam": (113, "Greater Visakhapatnam Municipal Corporation", "251719", "Visakhapatnam"),
    "vijayawada": (86, "Vijayawada Municipal Corporation", "251746", "NTR"),
    "guntur": (41, "Guntur Municipal Corporation", "251757", "Guntur"),
    "nellore": (64, "Nellore Municipal Corporation", "251772", "Sri Potti Sriramulu Nellore"),
    "kurnool": (26, "Kurnool Municipal Corporation", "251789", "Kurnool"),
    "kadapa": (32, "Kadapa Municipal Corporation", "251782", "Y.S.R. Kadapa"),
    "rajahmundry": (74, "Rajamahendravaram Municipal Corporation", "251725", "East Godavari"),
    "kakinada": (69, "Kakinada Municipal Corporation", "251731", "Kakinada"),
    "tirupati": (20, "Tirupati Municipal Corporation", "248121", "Tirupati"),
    "anantapur": (1, "Anantapur Municipal Corporation", "248112", "Ananthapuramu"),
    "vizianagaram": (110, "Vizianagaram Municipal Corporation", "251709", "Vizianagaram"),
    "ongole": (59, "Ongole Municipal Corporation", "251766", "Prakasam"),
    "eluru": (89, "Eluru Municipal Corporation", "251739", "Eluru"),
    "machilipatnam": (81, "Machilipatnam Municipal Corporation", "251750", "Krishna"),
    "chittoor": (13, "Chittoor Municipal Corporation", "248122", "Chittoor"),
    "srikakulam": (102, "Srikakulam Municipal Corporation", "251700", "Srikakulam"),
    "mangalagiri": (43, "Mangalagiri Tadepalli Municipal Corporation", "251752", "Guntur"),
}


def items(get=None):
    return [{"key": f"{MODULE}-{c}", "payload": {"reader": MODULE, "url": f"{API}{v[0]}", "state": STATE, "city": c,
                                                "india_only": True}} for c, v in BODIES.items()]


def parse(data, p):
    _id, body, lgd, district = BODIES[p["city"]]
    page = f"https://{p['city']}.cdma.ap.gov.in/ulbprofile/{p['city']}/contact"
    seen, recs = set(), []
    for di, dp in enumerate((data or {}).get("data") or []):
        dept = _esw.clean(dp.get("dprt_nm"))
        for ri, role in enumerate(dp.get("RleArray") or []):
            post = _esw.clean(role.get("rle_nm"))
            for ei, e in enumerate(role.get("emplArray") or []):
                name, phone = _esw.clean(e.get("emple_name")), str(e.get("mble_ph") or "")
                if not post or not (name or phone):
                    continue
                recs.append(_ward.record(MODULE, f"{p['city']}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=body,
                                         lgd=lgd, state=STATE, district=district, level="body", area=body, post=post, name=name,
                                         phone=phone, source=page, api=p["url"], department=dept,
                                         employee_id=_esw.clean(e.get("cfms_emple_id")) or None,
                                         src_url=p["url"], src_pos={"path": f"data[{di}].RleArray[{ri}].emplArray[{ei}]"}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    try:
        data = r.json()
    except ValueError:
        return [], [_esw.keep(MODULE, p["city"], r.content, "json")], "not json"
    recs = parse(data, p)
    return recs, [_esw.keep(MODULE, p["city"], r.content, "json")], "" if recs else "no departments"
