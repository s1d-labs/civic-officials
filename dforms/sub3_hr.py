"""Haryana: tehsildars, naib tehsildars and Sub-Divisional Officers (Civil) / SDMs per district, from the Revenue and Disaster
Management Department's "Who's Who District" page (revenueharyana.gov.in/Home/WhoIsWhoDistrict/; answers from India, vpsin).

The site is a Next.js app. The page has no API call in the browser: the server fetches the personnel list (from
api.revenueharyana.gov.in, address not in the page) and puts it in the page's flight data, as the prop "initialData" of the
table component (script chunk be1cffa1f95159f0.js, module 23247). The component reads these keys of each entry: officerId,
officer_Name, designationName, email, district_Name (or district_name / DistrictName / district); it shows Name, Designation,
Email, District and "-" for Address. It shows no phone.
On 2026-11-11 the page came with "initialData":[] (no entries), so the reader could not be checked on real district rows. The
flight-data decoder is checked on the state "Who's Who" page of the same site (/About/whoIsWho/, archive.s1d.me copy of
2026-11-05: keys id, name, designation, email, address, phone), which uses the same component pattern. The field names for the
district list come from the component code. Unverified until the page has data.

Kept: entries whose designation is a tehsildar, naib tehsildar or SDO (Civil) / SDM (POSTS). Area = the place in the designation
("Tehsildar, Panipat" -> Panipat; "SDO(C) Gohana" -> Gohana), else the district. Emails as written ([at]/[dot] decoded).
One queue item: 1 GET. Record ids: dept:sub3_hr:<district slug>:<post key>:<area slug>[:n].
"""
import json
import re

from dforms import _esw

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub3_hr"
URL = "https://revenueharyana.gov.in/Home/WhoIsWhoDistrict/"
PUSH = re.compile(r"self\.__next_f\.push\(\[\s*1\s*,\s*(\"(?:[^\"\\]|\\.)*\")\s*\]\)", re.S)
# (key, post, level, pattern on the designation); first match wins: "Naib Tehsildar" before "Tehsildar"
POSTS = (("naib-tehsildar", "Naib Tehsildar", "subdistrict", r"naib\s*-?\s*t[ae]h?si?ld[ae]r"),
         ("tehsildar", "Tehsildar", "subdistrict", r"\bt[ae]h?si?ld[ae]r"),
         ("sdm", "Sub Divisional Officer (Civil)", "subdivision",
          r"\bs\.?\s*d\.?\s*o\.?\s*\(?\s*c(ivil)?\s*\)?|\bs\.?\s*d\.?\s*m\b|sub[\s-]*divisional\s*(officer|magistrate)"))
LGD = {"Ambala": "58", "Bhiwani": "59", "Faridabad": "60", "Fatehabad": "61", "Gurugram": "62", "Hisar": "63", "Jhajjar": "64",
       "Jind": "65", "Kaithal": "66", "Karnal": "67", "Kurukshetra": "68", "Mahendragarh": "69", "Panchkula": "70", "Panipat": "71",
       "Rewari": "72", "Rohtak": "73", "Sirsa": "74", "Sonipat": "75", "Yamunanagar": "76", "Nuh": "604", "Palwal": "619",
       "Charkhi Dadri": "701", "Hansi": "792"}   # lgd.subdistricts, state 6
ALIAS = {"gurgaon": "Gurugram", "mewat": "Nuh", "narnaul": "Mahendragarh", "charkidadri": "Charkhi Dadri", "dadri": "Charkhi Dadri",
         "charkhidadri": "Charkhi Dadri", "yamunanagar": "Yamunanagar", "sonepat": "Sonipat", "hissar": "Hisar"}


def items(get=None):
    return [{"key": "sub3_hr", "payload": {"reader": MODULE, "url": URL, "state": "HR", "india_only": True}}]


def flight_text(html):
    """The page's Next.js flight data: every self.__next_f.push([1, "..."]) string, decoded and joined."""
    out = []
    for m in PUSH.finditer(html or ""):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            continue
    return "".join(out)


def initial_data(html):
    """Every "initialData" list in the flight data (a list of entries each); [] when the page has none."""
    text, out, dec = flight_text(html), [], json.JSONDecoder()
    for m in re.finditer(r'"initialData"\s*:\s*', text):
        try:
            val, _ = dec.raw_decode(text, m.end())
        except ValueError:
            continue
        if isinstance(val, list):
            out.append([v for v in val if isinstance(v, dict)])
    return out


def field(e, *names):
    for n in names:
        if e.get(n) not in (None, ""):
            return str(e[n])
    return ""


def district(name):
    s = _esw.clean(name)
    k = s.lower()
    name = ALIAS.get(k) or ALIAS.get(re.sub(r"[^a-z]", "", k)) or next((n for n in LGD if n.lower() == k), None)
    return (name, LGD[name]) if name else (s.title() if s.isupper() else s, "")


def post_of(designation):
    for key, post, level, rx in POSTS:
        if re.search(rx, designation or "", re.I):
            return key, post, level
    return None


def area_of(designation, rx):
    """The place named after the post: "Tehsildar, Panipat" -> "Panipat"; "SDO (C), Gohana" -> "Gohana"; "" when none."""
    m = re.search(rf"(?i)(?:{rx})\s*[,:\-]?\s*(?:cum\s+[^,]*,\s*)?(.*)$", designation or "")
    rest = _esw.clean(m.group(m.lastindex) if m else "")
    rest = re.sub(r"(?i)^\(?\s*(civil|c)\s*\)\s*", "", rest)
    rest = re.sub(r"(?i)^(of|at)\s+", "", rest.strip(" ,.-")).strip(" ,.-()")
    if not rest or re.search(r"(?i)\b(district|haryana|government|office|department|election|record|recovery|agrarian|"
                             r"consolidation|headquarters?|hq|land|kanungo|court|branch)\b", rest):
        return ""
    return rest.title() if rest.isupper() or rest.islower() else rest


def build(entries, source):
    recs, seen = [], set()
    for e in entries:
        des = _esw.clean(field(e, "designationName", "designation", "Designation"))
        found = post_of(des)
        if not found:
            continue
        key, post, level = found
        name = _esw.clean(field(e, "officer_Name", "officerName", "name", "Name"))
        dist, dc = district(field(e, "district_Name", "district_name", "DistrictName", "district", "District"))
        area = area_of(des, dict((k, rx) for k, _, _, rx in POSTS)[key]) or dist
        phone = _esw.phones(field(e, "mobile", "mobileNo", "mobile_No", "phone", "phoneNo", "contactNo", "contact"))
        email = _esw.emails(field(e, "email", "Email", "emailId"))
        if not (name or phone or email) or not area:
            continue
        base = f"{_esw.slug(dist) or 'hr'}:{key}:{_esw.slug(area)}"
        rid, i = base, 2
        while rid in seen:
            rid, i = f"{base}:{i}", i + 1
        seen.add(rid)
        recs.append(_esw.record(MODULE, rid, dept="revenue" if key != "sdm" else "administration", level=level, area=area,
                                post=post, designation=des, name=name, phone=phone, email=email, district=dist,
                                district_code=dc, state="HR", office_id=field(e, "officerId", "id"), source=source))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "whoiswho-district", r.content)]
    lists = initial_data(r.text)
    if not lists:
        return [], files, "no initialData in the page"
    entries = [e for lst in lists for e in lst]
    if not entries:
        return [], files, "the page lists no officers (initialData is empty)"
    recs = build(entries, url)
    return recs, files, "" if recs else f"no tehsildar / naib tehsildar / SDM among {len(entries)} entries"
