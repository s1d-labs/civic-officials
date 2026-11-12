"""Jharkhand: fair price shop dealers with their map position from the state's Aahar portal https://aahar.jharkhand.gov.in, page
"Locate Your Dealer On Google Map" (/secc-cardholders/locate-your-dealer, CakePHP, no login, no captcha). The dealer names and shop ids
of Jharkhand are already in dforms/civic_fps_jh.py (SMART-PDS); this reader adds the dealer's coordinates and the details that the map
page shows.
Steps, as the page's own script does them (one requests session; the CSRF token is the one the GET in the same run gives):
1. GET the page: the hidden _csrfToken (also sent as the X-CSRF-Token header of the two lookups).
2. POST /transactions/get-blocks-by-district (id=<rgi_district_code>) -> JSON {block code: block / municipality name}.
3. POST /secc-cardholders/get-dealers-by-block (rgi_block_code=<code>) -> JSON {dealer id: dealer label}.
4. POST the form (rgi_district_code, rgi_block_code, dealer_id) -> the map page of that dealer: parse() takes the coordinates
   (google.maps.LatLng(..), lat/lng variables or labelled cells) and every labelled value (dealer, licence, mobile, address).
One queue item per district (24, codes = Census 2011 district codes from the page's list, seeds/dept_civic_fps2_jh.json). About
24,690 dealers (the site's district-dealer report, 2026-11-05), so a district item makes 1 + 1 + blocks + dealers requests.
Payload "locate": false stops after step 3 (names and ids only). The raw answers are kept per block (dealers JSON + map pages).
NOT VERIFIED LIVE: the host did not answer on 2026-11-11 (connection timeout from this box and from the India server vpsin, 3 tries),
so the map page (step 4) was never seen; parse() is written for the usual shapes and the kept pages show what the site sends.
Record ids: dept:civic_fps2_jh:<dealer id>.
"""
import json
import re

from dforms import _civic_fps, _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_jh"
STATE = "JH"
BASE = "https://aahar.jharkhand.gov.in"
PAGE = BASE + "/secc-cardholders/locate-your-dealer"
INDIA_ONLY = True
DISTRICTS = {"346": "Garhwa", "347": "Chatra", "348": "Kodarma", "349": "Giridih", "350": "Deoghar", "351": "Godda", "352": "Sahibganj",
             "353": "Pakur", "354": "Dhanbad", "355": "Bokaro", "356": "Lohardaga", "357": "East Singhbhum", "358": "Palamu",
             "359": "Latehar", "360": "Hazaribagh", "361": "Ramgarh", "362": "Dumka", "363": "Jamtara", "364": "Ranchi", "365": "Khunti",
             "366": "Gumla", "367": "Simdega", "368": "West Singhbhum", "369": "Saraikela-Kharsawan"}
FORM = {"Content-Type": "application/x-www-form-urlencoded"}
TOKEN = re.compile(r'name="_csrfToken"[^>]*value="([0-9a-f]+)"')
NUM = r"(-?\d{1,3}\.\d+)"
COORDS = [re.compile(r"LatLng\(\s*['\"]?" + NUM + r"['\"]?\s*,\s*['\"]?" + NUM),
          re.compile(r"\blat(?:itude)?['\"]?\s*[:=]\s*['\"]?" + NUM + r"['\"]?\s*,\s*['\"]?(?:lng|lon|long|longitude)['\"]?\s*[:=]\s*['\"]?"
                     + NUM, re.I),
          re.compile(r"[?&](?:q|ll|center|query|daddr)=" + NUM + r"\s*,\s*" + NUM)]
LABELS = {"dealer": "name", "dealer name": "name", "name of dealer": "name", "fps name": "shop_name", "shop name": "shop_name",
          "licence no": "licence_no", "license no": "licence_no", "licence number": "licence_no", "license number": "licence_no",
          "mobile": "phone", "mobile no": "phone", "mobile number": "phone", "contact no": "phone", "phone": "phone",
          "address": "address", "shop address": "address", "village": "village", "block": "block", "district": "district",
          "panchayat": "panchayat", "latitude": "lat", "longitude": "lon", "fps id": "fps_id", "fps code": "fps_id"}


def items(get=None):
    return [{"key": f"{MODULE}-{c}", "payload": {"reader": MODULE, "url": BASE, "state": STATE, "dist_code": c, "district": n,
                                                 "india_only": True}} for c, n in DISTRICTS.items()]


def token(html):
    m = TOKEN.search(html or "")
    return m.group(1) if m else ""


def options(r):
    """{value: label} from a lookup answer (a JSON object, or a list of {id/value, name/text})."""
    d = _civic_fps._json(r)
    if isinstance(d, dict):
        return {str(k): _esw.clean(str(v)) for k, v in d.items() if str(k).strip() and str(v).strip()}
    if isinstance(d, list):
        out = {}
        for x in d:
            if isinstance(x, dict):
                k = x.get("id") or x.get("value") or x.get("code")
                v = x.get("name") or x.get("text") or x.get("label")
                if k and v:
                    out[str(k)] = _esw.clean(str(v))
        return out
    return {}


def dealer_label(label):
    """(name, licence or shop number) from a dropdown label such as "RAM KUMAR (123456)" or "123456 - RAM KUMAR"."""
    label = _esw.clean(label)
    m = re.fullmatch(r"(.+?)\s*[\(\[]\s*([\w/-]*\d[\w/-]*)\s*[\)\]]", label)
    if m:
        return m.group(1).strip(" -"), m.group(2)
    m = re.fullmatch(r"([\w/-]*\d[\w/-]*)\s*[-:|]\s*(.+)", label) or None
    if m:
        return m.group(2).strip(), m.group(1)
    m = re.fullmatch(r"(.+?)\s*[-:|]\s*([\w/-]*\d[\w/-]*)", label)
    if m:
        return m.group(1).strip(), m.group(2)
    return label, ""


def coords(html):
    for rx in COORDS:
        for m in rx.finditer(html or ""):
            lat, lon = float(m.group(1)), float(m.group(2))
            if 21 <= lat <= 26 and 83 <= lon <= 88.5:          # inside Jharkhand's box; 0,0 and swapped pairs are no position
                return lat, lon
    return None, None


def fields(html):
    """{field: value} from label/value cells (th/td pairs, "Label : value" cells or two-cell rows)."""
    out = {}
    soup = _esw.soup(html or "")
    for tr in soup.find_all("tr"):
        cells = [_esw.clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
        pairs = []
        if len(cells) >= 2 and len(cells) % 2 == 0:
            pairs = list(zip(cells[::2], cells[1::2]))
        for c in cells:
            if ":" in c:
                k, _, v = c.partition(":")
                pairs.append((k, v))
        for k, v in pairs:
            key = LABELS.get(re.sub(r"[^a-z ]", "", k.lower()).strip())
            v = _esw.clean(v)
            if key and v and key not in out:
                out[key] = v
    return out


def parse(html, dealer_id, label, block_code, block, dist_code, district):
    """One record for one dealer: dropdown label + what the map page gives."""
    name, lic = dealer_label(label)
    f = fields(html) if html else {}
    lat, lon = coords(html) if html else (None, None)
    if lat is None and f.get("lat") and f.get("lon"):
        try:
            lat, lon = float(f["lat"]), float(f["lon"])
        except ValueError:
            lat = lon = None
    phone = _civic_fps.unmasked(f.get("phone", ""))
    return _esw.record(
        MODULE, dealer_id, dept="food_supplies", level="facility", layer="fps", area=block or district, post=_civic_fps.POST,
        name=_civic_fps.name_of(f.get("name", "")) or name, dealer_label=label, licence_no=f.get("licence_no") or lic,
        fps_id=f.get("fps_id", ""), shop_name=f.get("shop_name", ""), phone=phone, address=f.get("address", ""),
        village=f.get("village", ""), panchayat=f.get("panchayat", ""), state=STATE, district=district, subdistrict=block,
        block=block, block_code=block_code, dist_code=dist_code, office_id=dealer_id, lat=lat, lon=lon,
        source=PAGE)


def fetch(p, get):
    code = str(p["dist_code"])
    district = p.get("district") or DISTRICTS.get(code, "")
    page = get(PAGE)
    tok = token(page.text) if page is not None else ""
    if not tok:
        return [], [], "no page or no form token"
    ajax = dict(FORM, **{"X-CSRF-Token": tok})
    blocks = options(get(f"{BASE}/transactions/get-blocks-by-district", method="POST", data={"id": code}, headers=ajax))
    if not blocks:
        return [], [], "no block list"
    recs, files, seen = [], [], set()
    for bcode, bname in blocks.items():
        r = get(f"{BASE}/secc-cardholders/get-dealers-by-block", method="POST", data={"rgi_block_code": bcode}, headers=ajax)
        dealers = options(r)
        kept = {"block": bcode, "dealers": _civic_fps._json(r), "pages": {}}
        for did, label in dealers.items():
            if did in seen:
                continue
            seen.add(did)
            html = ""
            if p.get("locate", True):
                a = get(PAGE, method="POST", headers=FORM,
                        data={"_method": "POST", "_csrfToken": tok, "rgi_district_code": code, "rgi_block_code": bcode, "dealer_id": did})
                html = a.text if a is not None else ""
                kept["pages"][did] = html
            recs.append(parse(html, did, label, bcode, bname, code, district))
        files.append(_esw.keep(MODULE, f"{code}-{bcode}", json.dumps(kept, ensure_ascii=False), "json"))
    return recs, files, "" if recs else "no rows"
