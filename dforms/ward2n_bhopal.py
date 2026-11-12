"""Bhopal Municipal Corporation (bmconline.gov.in): the officers of its 21 zones. The site is a SAP UI5 app; its "Zone Officer" page
(view ZoneOfficer) reads the OData set ZHP_TELEPHONE_LISTSet of service ZHP_ADMIN_SRV with the filter TeleType eq '02' (the same set
gives the 85 councillors with TeleType '03'). One JSON answer (answers from Germany without a login; live sample 2026-11-11, not in
archive.s1d.me: the archive holds only the start page). Each row: NameEn / NameHi, Designation (Hindi), Mobile, Contact, ZoneWardNo
("ZONE 7"). 5 posts per zone: जोनल अधिकारी (Zonal Officer, head), स्वच्छता प्रभारी (AHO) (sanitation in charge, Assistant Health
Officer), सहायक यंत्री (सिविल) (उद्यान एवं झील) (Assistant Engineer civil, gardens and lakes), उपयंत्री (सिविल) (Sub Engineer civil),
सहायक यंत्री (जलकार्य) (सीवेज) (Assistant Engineer water works and sewage). The answer does not say which wards a zone holds.
Records: level "zone". Ids: dept:ward2n_bhopal:zone-<n>:<post slug>.
"""
import json
import re

from dforms import _esw, _ward

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_bhopal"
BODY, LGD, STATE, DISTRICT = "Bhopal Municipal Corporation", "250946", "MP", "Bhopal"
URL = ("https://www.bmconline.gov.in/sap/opu/odata/sap/ZHP_ADMIN_SRV/ZHP_TELEPHONE_LISTSet"
       "?$filter=TeleType%20eq%20%2702%27&$format=json")
POSTS = (("जोनल अधिकारी", "Zonal Officer", "administration"),
         ("स्वच्छता प्रभारी", "Sanitation In Charge (Assistant Health Officer)", "sanitation"),
         ("सहायक यंत्री (सिविल) (उद्यान", "Assistant Engineer (Civil, Gardens and Lakes)", "engineering"),
         ("सहायक यंत्री (जलकार्य)", "Assistant Engineer (Water Works, Sewage)", "water"),
         ("उपयंत्री (जलकार्य)", "Sub Engineer (Water Works)", "water"),
         ("उपयंत्री (सिविल)", "Sub Engineer (Civil)", "engineering"),
         ("सहायक यंत्री", "Assistant Engineer", "engineering"), ("उपयंत्री", "Sub Engineer", "engineering"))


def items(get=None):
    return [{"key": f"{MODULE}-zone-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def post_of(hi):
    h = _esw.clean(hi)
    for k, en, wing in POSTS:
        if h.startswith(k):
            return en, wing
    return _ward.hi_post(h), None


def parse(data, p):
    rows = (data.get("d") or {}).get("results") or []
    seen, recs = set(), []
    for x in rows:
        m = re.search(r"(?i)zone\s*0*(\d+)", x.get("ZoneWardNo") or "")
        if not m:
            continue
        z = m.group(1)
        en, wing = post_of(x.get("Designation") or "")
        name_en, name_hi = _esw.clean(x.get("NameEn")), _esw.clean(x.get("NameHi"))
        recs.append(_ward.record(MODULE, f"zone-{z}:{_esw.slug(en)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=f"Zone {z}", zone=f"Zone {z}", post=en,
                                 post_regional=_esw.clean(x.get("Designation")), name=name_en or name_hi,
                                 name_regional=name_hi or None, phone=" ".join(filter(None, [x.get("Mobile"), x.get("Contact")])),
                                 wing=wing, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    try:
        data = json.loads(r.content)
    except ValueError:
        return [], [_esw.keep(MODULE, "zone-officers", r.content, "txt")], "not JSON"
    recs = parse(data, p)
    return recs, [_esw.keep(MODULE, "zone-officers", r.content, "json")], "" if recs else "no zone rows"
