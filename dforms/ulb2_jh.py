"""Jharkhand: the Urban Development & Housing Department's contact form, udhd.jharkhand.gov.in/ContactUs4.aspx (ASP.NET). India only
(no answer from Germany on 2026-11-11; vpsin got the page).

The page has one drop-down of 52 bodies (and 7 state agencies, left out). Choosing a body posts the form back (the page's own form
fields from the GET just before, no login, no captcha) and the answer fills six labels: lblAddress, lblemail, lblPhone, lblfaxno,
lbleo (the Executive Officer's / Municipal Commissioner's name) and lbleomobile (that officer's mobile). The answer shows no date.
Checked 2026-11-11 for Giridih Municipal Corporation: "Vijya Yadav", 9431978557, giridihmunicipalcorporation@gmail.com.
This list names the officer of every body, also of the 34 bodies whose UDHD body page (dforms/ulb_jh.py) shows no officer card.

One queue item per body: the GET and the POST of that body. Records: "Executive Officer" (role head) with the name and mobile, the
office phone / email / address as extra keys; an "Office" record when the label holds no name. Body names, districts and LGD codes:
BODIES below (option value | name as the form writes it | LGD district | LGD code), tied by hand 2026-11-11 (Bachra has no LGD body).
"""
import html as _html
import re

from dforms import _esw, _ulb

METHOD = "pdf text (pypdf) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_jh"
STATE = "JH"
URL = "https://udhd.jharkhand.gov.in/ContactUs4.aspx"
SELECT = "ctl00$ContentPlaceHolderBody$ddlULB"
BODIES = """39|Adityapur Municipal Corporation|Saraikela Kharsawan|253166
56|Bachra Nagar Panchayat|Chatra|
54|Badaki Saraiya Nagar Panchayat|Giridih|290364
57|Barharwa Nagar Panchayat|Sahebganj|277137
10|Basukinath Nagar Panchayat|Dumka|250352
31|Bishrampur Nagar Parishad|Palamu|253231
35|Bundu Nagar Panchayat|Ranchi|250415
42|Chaibasa Nagar Parishad|West Singhbhum|250430
43|Chakradharpur Nagar Parishad|West Singhbhum|250416
12|Chakulia Nagar panchayat|East Singhbum|250445
3|Chas Municipal Corporation|Bokaro|248056
5|Chatra Nagar Parishad|Chatra|248129
45|Chhatarpur Nagar Panchayat|Palamu|300374
8|Chirkunda Nagar Parishad|Dhanbad|248055
6|Deoghar Municipal Corporation|Deoghar|248049
9|Dhanbad Municipal Corporation|Dhanbad|250378
53|Dhanvar Nagar Panchayat|Giridih|277138
55|Domchanch Nagar Panchayat|Koderma|277135
11|Dumka Nagar Parishad|Dumka|248054
16|Garhwa Nagar Parishad|Garhwa|248128
19|Giridih Municipal Corporation|Giridih|250349
20|Godda Nagar Parishad|Godda|248051
21|Gumla Nagar Parishad|Gumla|248057
58|Hariharganj Nagar Panchayat|Palamu|300371
22|Hazaribagh Municipal Corporation|Hazaribagh|248130
32|Hussainabad Nagar Panchayat|Palamu|250323
13|Jamshedpur NAC|East Singhbum|250434
23|Jamtara Nagar Panchayat|Jamtara|248134
26|Jhumritilaiya Nagar Parishad|Koderma|248132
14|Jugsalai Nagar Parishad|East Singhbum|250435
46|Kapali Nagar Parishad|Saraikela Kharsawan|276352
25|Khunti Nagar Panchayat|Khunti|250414
27|Koderma Nagar Panchayat|Koderma|248131
28|Latehar Nagar Panchayat|Latehar|250326
29|Lohardaga Nagar Parishad|Lohardaga|248137
7|Madhupur Nagar Parishad|Deoghar|248050
59|Mahagama Nagar Panchayat|Godda|300370
15|Mango Municipal Corporation|East Singhbum|250433
17|Manjhiaon Nagar Panchayat|Garhwa|253228
33|Medininagar Municipal Corporation|Palamu|250324
24|Mihijham Nagar Parishad|Jamtara|248135
18|Nagar Uttari Nagar Panchayat|Garhwa|274815
30|Pakur Nagar Parishad|Pakur|248133
4|Phusro Nagar Parishad|Bokaro|248136
37|Rajmahal Nagar Panchayat|Sahebganj|248053
34|Ramgarh Nagar Parishad|Ramgarh|274814
36|Ranchi Municipal Corporation|Ranchi|250413
38|Sahibganj Nagar Parishad|Sahebganj|248052
40|Saraikela Nagar Panchayat|Saraikela Kharsawan|250423
41|Simdega Nagar Parishad|Simdega|248138"""
TYPE = re.compile(r"(?i)\s+(municipal\s+corporation|nagar\s+parishad|nagar\s+panchayat|nac)$")
LABELS = {"address": "lblAddress", "email": "lblemail", "phone": "lblPhone", "fax": "lblfaxno", "eo": "lbleo", "eo_mobile": "lbleomobile"}


def items(get=None):
    out = []
    for line in BODIES.splitlines():
        val, name, district, lgd = line.split("|")
        out.append({"key": f"{MODULE}-{_esw.slug(name)}",
                    "payload": {"reader": MODULE, "url": URL, "value": val, "body": name, "district": district, "lgd_code": lgd or None,
                                "state": STATE, "india_only": True}})
    return out


def split_type(name):
    name = _esw.clean(name)
    m = TYPE.search(name)
    return (name[:m.start()].strip(), m.group(1)) if m else (name, None)


def form_fields(page):
    """The hidden fields of the page's form (__VIEWSTATE, __EVENTVALIDATION ...), as the browser sends them back."""
    return {k: _html.unescape(v) for k, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page)}


def labels(page):
    out = {}
    for k, lid in LABELS.items():
        m = re.search(r'id="ContentPlaceHolderBody_' + lid + r'"[^>]*>(.*?)</span>', page, re.S)
        out[k] = _esw.clean(_html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else ""
    return out


def parse(page, body, district=None, lgd=None, url=URL):
    lab = labels(page)
    area, btype = split_type(body)
    phone = lab["phone"] if re.sub(r"\D", "", lab["phone"]).strip("0") else ""
    office = {k: v for k, v in (("address", lab["address"]), ("office_phone", phone), ("office_email", _esw.emails(lab["email"])))
              if v}
    common = {"district": district, "body_type": btype, "list_name": body, "lgd_code": lgd, **office}
    seen = set()
    name = lab["eo"] if re.search(r"[A-Za-zऀ-ॿ]", lab["eo"]) else ""
    mob = lab["eo_mobile"] if re.sub(r"\D", "", lab["eo_mobile"]).strip("0") else ""
    if name or mob:
        return [_ulb.record(MODULE, STATE, area, "Executive Officer", seen, name=name, phone=mob, source=url, **common)]
    if office.get("office_phone") or office.get("office_email"):
        return [_ulb.record(MODULE, STATE, area, "Office", seen, phone=office.get("office_phone", ""),
                            email=office.get("office_email", ""), source=url, **common)]
    return []


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    f = form_fields(r.text)
    if "__VIEWSTATE" not in f:
        return [], [], "no form"
    f.update({SELECT: p["value"], "__EVENTTARGET": SELECT, "__EVENTARGUMENT": ""})
    r2 = get(p["url"], method="POST", data=f)
    if r2 is None:
        return [], [], "no answer to the form"
    files = [_esw.keep(MODULE, _esw.slug(p["body"]), r2.content)]
    recs = parse(r2.text, p["body"], p.get("district"), p.get("lgd_code"), p["url"])
    return recs, files, "" if recs else "no rows"
