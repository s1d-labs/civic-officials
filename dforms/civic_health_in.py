"""All India: public health facilities (sub centres, PHCs, CHCs, UPHCs, urban health posts, dispensaries, district and sub-district
hospitals) from the Hospital Directory of India layer on Esri India's Living Atlas, an ArcGIS MapServer with no login:
livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Hospital_Directory/MapServer/0. It is the National Health Portal's
geo-coded facility directory (NIN health facilities, data.gov.in): 165,111 rows, every row with lat/lon; fields
health_facility_name, address, street, landmark, locality, posatalcode (PIN), landline_number, facility_type, state_name,
district_name, taluka_name, block_name. The layer has no officer names and no last-updated date (data.gov.in: "updated till last
month"). Facility types (2026-11-11): SubCentre 131,975, Primary Health Centre 21,565, Community Health Center 4,462, Others 2,173,
Urban Health Centre 1,418, Sub-District Hospital 846, Dispensaries 707, District Hospital 588, Urban Health Posts 436, ...

A second layer on the same server, "Health Centers in India" (LivingAtlas/IND_Health/MapServer/0, 199,604 rows on 2026-11-11):
statename, districtname, subdistrictname, facilitytype (PHC, Sub Centre, CHC, ...), facilityname, facilityaddress, locationtype
(Rural / Urban), typeoffacility (Public / Private), notionalphysical, point geometry. No phone. Payload "layer": "centres" reads it
(lat/lon from the geometry, outSR=4326); "layer": "directory" (or none) reads the Hospital Directory.

One queue item = one objectid range of 2,000 rows (the layers' maxRecordCount): where=objectid >= a AND objectid < b, outFields=*,
f=json. items(get) asks each layer's max objectid and cuts ranges.
Records: dept health, level facility, layer health, area = facility name, post = the facility type as the source gives it
("Health sub centre", "Primary health centre", "Community health centre", "Health facility" for "Others", else the type as
written; the source names no officer, so no post is inferred), facility_type, phone = landline, address, PIN, district,
block, taluka / sub-district, location_type, ownership, lat/lon.
The landline column lost the leading 0 of many STD codes ("2184254444" for 02184-254444: the source once held it as a
number): a 10-digit number that is not a mobile (first digit 1-5) gets its 0 back ("5315-245188", "4371 291191" too; "91" +
10 digits becomes 0 + 10 digits); a number equal to the PIN (the record's or one in its address) and a 0-only placeholder
("07263-000000", "0") are left out.
Record ids: dept:civic_health_in:hd-<objectid> (directory), dept:civic_health_in:hc-<objectid> (centres).
"""
import json
import re
import urllib.parse

from dforms import _esw

MODULE = "civic_health_in"
LAYER = "https://livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Hospital_Directory/MapServer/0"
CENTRES = "https://livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Health/MapServer/0"
LAYERS = {"directory": (LAYER, "hd"), "centres": (CENTRES, "hc")}
STEP = 2000
STATE = {"andaman and nicobar islands": "AN", "andaman & nicobar islands": "AN", "andhra pradesh": "AP", "arunachal pradesh": "AR",
         "assam": "AS", "bihar": "BR", "chandigarh": "CH", "chhattisgarh": "CG", "dadra and nagar haveli": "DH",
         "dadra & nagar haveli": "DH", "daman and diu": "DH", "daman & diu": "DH", "delhi": "DL", "nct of delhi": "DL", "goa": "GA",
         "gujarat": "GJ", "haryana": "HR", "himachal pradesh": "HP", "jammu and kashmir": "JK", "jammu & kashmir": "JK",
         "jharkhand": "JH", "karnataka": "KA", "kerala": "KL", "ladakh": "LA", "lakshadweep": "LD", "madhya pradesh": "MP",
         "maharashtra": "MH", "manipur": "MN", "meghalaya": "ML", "mizoram": "MZ", "nagaland": "NL", "odisha": "OD", "orissa": "OD",
         "puducherry": "PY", "pondicherry": "PY", "punjab": "PB", "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN",
         "telangana": "TG", "tripura": "TR", "uttar pradesh": "UP", "uttarakhand": "UK", "uttaranchal": "UK", "west bengal": "WB"}
EMPTY = {"", "na", "n/a", "0", "nil", "null", "none", "-", "not available"}


def query_url(lo, hi, layer="directory"):
    q = {"where": f"objectid >= {lo} AND objectid < {hi}", "outFields": "*", "orderByFields": "objectid",
         "resultRecordCount": str(STEP), "f": "json"}
    q.update({"returnGeometry": "true", "outSR": "4326"} if layer == "centres" else {"returnGeometry": "false"})
    return f"{LAYERS[layer][0]}/query?" + urllib.parse.urlencode(q)


def ranges(max_id):
    return [(lo, lo + STEP) for lo in range(1, int(max_id) + 1, STEP)]


def item(lo, hi, layer="directory"):
    tag = LAYERS[layer][1]
    return {"key": f"{MODULE}-{tag}-{lo:06d}", "payload": {"reader": MODULE, "url": query_url(lo, hi, layer), "state": "IN",
                                                            "layer": layer, "lo": lo, "hi": hi}}


def items(get):
    stats = json.dumps([{"statisticType": "max", "onStatisticField": "objectid", "outStatisticFieldName": "m"}])
    out = []
    for layer, (url, _) in LAYERS.items():
        r = get(f"{url}/query?" + urllib.parse.urlencode({"where": "1=1", "outStatistics": stats, "f": "json"}))
        if r is None:
            continue
        m = r.json()["features"][0]["attributes"]["m"]
        out += [item(lo, hi, layer) for lo, hi in ranges(m)]
    return out


def val(v):
    v = _esw.clean(v)
    return "" if v.lower() in EMPTY else v


def post_of(ft):
    """The facility type as the post (sql/86b A3): the source names the facility, not the officer in charge."""
    t = _esw.clean(ft)
    if re.match(r"(?i)sub\s*-?\s*cent", t):
        return "Health sub centre"
    if re.match(r"(?i)(phc\b|primary health)", t):
        return "Primary health centre"
    if re.match(r"(?i)(chc\b|community health)", t):
        return "Community health centre"
    if not t or re.fullmatch(r"(?i)others?", t):
        return "Health facility"
    return t


def landline(v, pin="", addr=""):
    """The landline column as phones: the lost STD 0 put back (10 digits, first digit 1-5: "2184254444", "5315-245188",
    "4371 291191"; "91" + 10 digits: "913325000000"), PINs (the record's own or one in its address) and 0-only placeholders left out."""
    out = []
    pins = set(re.findall(r"(?<!\d)\d{6}(?!\d)", addr)) | ({pin} if pin else set())
    for x in filter(None, _esw.phones(v).split(", ")):
        d = re.sub(r"\D", "", x)
        if d in pins or re.search(r"(?:^|[-\s])0+$", x) or re.fullmatch(r"0*", d):
            continue
        if re.fullmatch(r"91[1-5]\d{9}", d):
            x = d = "0" + d[2:]
        if re.fullmatch(r"[1-5]\d{9}", d) and re.fullmatch(r"\d{2,5}[\s-]?\d{5,8}", x):
            x = "0" + x
        if x not in out:
            out.append(x)
    return ", ".join(out)


def in_india(lat, lon):
    return isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and 6 <= lat <= 38 and 68 <= lon <= 98


def parse(doc, url=LAYER, layer="directory"):
    recs = []
    tag = LAYERS[layer][1]
    for f in doc.get("features") or []:
        a = f.get("attributes") or {}
        oid = a.get("objectid")
        if layer == "centres":
            name = val(a.get("facilityname"))
            if oid is None or not name:
                continue
            g = f.get("geometry") or {}
            lat, lon = g.get("y"), g.get("x")
            ok = in_india(lat, lon)
            st = val(a.get("statename"))
            recs.append(_esw.record(MODULE, f"{tag}-{oid}", dept="health", level="facility", layer="health", area=name,
                                    post=post_of(val(a.get("facilitytype"))), facility_type=val(a.get("facilitytype")),
                                    address=val(a.get("facilityaddress")), location_type=val(a.get("locationtype")),
                                    ownership=val(a.get("typeoffacility")), notional=val(a.get("notionalphysical")),
                                    state=STATE.get(st.lower(), st), state_name=st, district=val(a.get("districtname")),
                                    subdistrict=val(a.get("subdistrictname")), office_id=f"{tag}-{oid}",
                                    lat=round(lat, 6) if ok else None, lon=round(lon, 6) if ok else None,
                                    source=f"{CENTRES}?objectid={oid}"))
            continue
        name = val(a.get("health_facility_name"))
        if oid is None or not name:
            continue
        addr = ", ".join(x for x in (val(a.get(k)) for k in ("address", "street", "landmark", "locality")) if x)
        pin = val(a.get("posatalcode"))
        st = val(a.get("state_name"))
        lat, lon = a.get("lat"), a.get("lon")
        ok = in_india(lat, lon)
        recs.append(_esw.record(MODULE, f"{tag}-{oid}", dept="health", level="facility", layer="health", area=name,
                                post=post_of(val(a.get("facility_type"))), facility_type=val(a.get("facility_type")),
                                phone=landline(val(a.get("landline_number")), pin, addr), address=", ".join(x for x in (addr, pin) if x),
                                pin=pin, state=STATE.get(st.lower(), st), state_name=st, district=val(a.get("district_name")),
                                block=val(a.get("block_name")), subdistrict=val(a.get("taluka_name")), office_id=f"{tag}-{oid}",
                                lat=lat if ok else None, lon=lon if ok else None, source=f"{LAYER}?objectid={oid}"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    try:
        doc = r.json()
    except ValueError:
        return [], [], "not json"
    if doc.get("error"):
        return [], [], f"layer error {doc['error'].get('code')}"
    layer = p.get("layer") or "directory"
    files = [_esw.keep(MODULE, f"{LAYERS[layer][1]}-{p.get('lo', 0):06d}", r.content, "json")]
    recs = parse(doc, p["url"], layer)
    return recs, files, "" if recs else "no rows"
