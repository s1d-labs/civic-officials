"""All India: every post office (head, sub and branch offices) with its PIN code, division, region, circle, district and point.
Source: the All India Pincode Directory of the Department of Posts (data.gov.in "All India Pincode Directory", monthly), as served
by Esri India's Living Atlas: livingatlas.esri.in/server1/rest/services/India/All_India_Pincode_Directory/MapServer/0 (layer
"Post office Location", fields circlename, regionname, divisionname, officename, pincode, officetype (HO/SO/BO/PO), delivery,
district, statename, lat, long, comments). 165,366 offices, objectid 1..165366 (checked 2026-11-11). data.gov.in itself needs an
API key (a sign-up) for its API, and India Post's own locator (indiapost.gov.in/locate-postoffice) answers through Next.js server
actions only, so this copy is used. Answers from anywhere.

One queue item = one block of 2000 objectids (the layer's maxRecordCount): 83 items. The directory gives no postmaster names or
phones: the record carries the post ("Postmaster" for a head office, "Sub Postmaster" for a sub office, "Branch Postmaster" for a
branch office) and the office in "area". Record ids: dept:civic_post_in:<pincode>-<slug of office name>.
"""
import json
from urllib.parse import urlencode

from dforms import _civic, _esw

MODULE = "civic_post_in"
LAYER = "https://livingatlas.esri.in/server1/rest/services/India/All_India_Pincode_Directory/MapServer/0/query"
TOTAL = 165366
STEP = 2000
POSTS = {"HO": "Postmaster", "SO": "Sub Postmaster", "BO": "Branch Postmaster", "PO": "Postmaster"}
TYPES = {"HO": "Head Office", "SO": "Sub Office", "BO": "Branch Office", "PO": "Post Office"}


def query_url(lo, hi):
    return LAYER + "?" + urlencode({"where": f"objectid>={lo} AND objectid<={hi}", "outFields": "*", "returnGeometry": "false",
                                    "orderByFields": "objectid", "resultRecordCount": STEP, "f": "json"})


def items(get=None):
    out = []
    for lo in range(1, TOTAL + 1, STEP):
        hi = lo + STEP - 1
        out.append({"key": f"{MODULE}-{lo:06d}", "payload": {"reader": MODULE, "url": query_url(lo, hi), "state": "IN",
                                                              "india_only": False, "lo": lo, "hi": hi, "expected": STEP}})
    return out


def parse(doc, url=LAYER):
    recs, seen = [], set()
    for f in doc.get("features") or []:
        a = f.get("attributes") or {}
        office = _esw.clean(a.get("officename"))
        pin = str(a.get("pincode") or "").strip()
        if not office:
            continue
        typ = _esw.clean(a.get("officetype")).upper()
        key = _civic.unique(f"{pin}-{_esw.slug(office)}", seen)
        recs.append(_civic.record(
            MODULE, key, "post", dept="postal", level="facility", area=office, post=POSTS.get(typ, "Postmaster"),
            office_type=typ, office_type_name=TYPES.get(typ), delivery=_esw.clean(a.get("delivery")), pincode=pin,
            division=_esw.clean(a.get("divisionname")), region=_esw.clean(a.get("regionname")),
            circle=_esw.clean(a.get("circlename")), district=_esw.clean(a.get("district")),
            state=_civic.state_code(a.get("statename")) or "IN", state_name=_esw.clean(a.get("statename")),
            lat=_civic.lat(a.get("lat")), lon=_civic.lon(a.get("long")), notes=_esw.clean(a.get("comments")),
            office_id=key, objectid=a.get("objectid"), source=url, source_org="Department of Posts, All India Pincode Directory"))
    return recs


def fetch(p, get):
    lo = p.get("lo", 1)
    url = p.get("url") or query_url(lo, p.get("hi", lo + STEP - 1))
    r = get(url)
    if r is None:
        return [], [], "no answer"
    try:
        doc = json.loads(r.content)
    except ValueError:
        return [], [], "not json"
    if doc.get("error"):
        return [], [], f"arcgis error {doc['error'].get('code')}"
    files = [_esw.keep(MODULE, f"objectid-{lo:06d}", r.content, "json")]
    recs = parse(doc, url)
    return recs, files, "" if recs else "no rows"
