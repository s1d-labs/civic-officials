"""Punjab Police Saanjh portal: saanjh.punjabpolice.gov.in (the JSON behind its SPA; India only, no login).
GET /citizen-master/master/districts/25 -> 28 police districts (cctnsDistrictCode); GET
/reports-master/master/fetchSaanjhDetails?cctnsDistrictCd=<code>&officeType=<PSOC|WOMEN_PS> -> one row per police station
outreach centre (PSOC) or women police station: cctnsPsName, psNamePn (Punjabi), SHO name / rank / mobile / posted since,
station phone + email, address, MHC (station munshi) name + mobile, lat/lon. One queue item = one district (both office
types, 2 requests); items(get) lists them. Coordinates are often scaled (302980608.0) or swapped: fixed when the result falls
in Punjab, else left out. Rows without a station name and without an SHO (e.g. "PSOC CIA") are left out.
Some shoName / mhcName cells also hold the rank, the belt number and a phone ("SHO SI Sone No. 44/FR", "Insp/SHO Rupinder Kaur,
07/LR, 90400-83000."): split_name() moves them to rank / belt_no / phone. A 10-digit station landline that starts with 1-5
("1821513909") lost its leading 0 (all Punjab STD codes start with 01): the 0 is put back.
Record id dept:police_pb:<district code>:<row id>."""
import json
import re

from dforms._police import clean, email, gz, phones, rec, slug

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

M = "police_pb"
BASE = "https://saanjh.punjabpolice.gov.in"
SOURCE = BASE + "/"
TYPES = ("PSOC", "WOMEN_PS")


def details_url(code, office_type):
    return f"{BASE}/reports-master/master/fetchSaanjhDetails?cctnsDistrictCd={code}&officeType={office_type}"


def items(get):
    r = get(BASE + "/citizen-master/master/districts/25")
    if r is None:
        return []
    return [{"key": f"{M}:{x['cctnsDistrictCode']}-{slug(x['districtName'])}",
             "payload": {"reader": M, "url": details_url(x["cctnsDistrictCode"], "PSOC"), "state": "PB",
                         "district_code": x["cctnsDistrictCode"], "district": clean(x["districtName"]), "india_only": True}}
            for x in r.json()]


def _scale(v):
    try:
        v = abs(float(v))
    except (TypeError, ValueError):
        return None
    while v > 100:
        v /= 10
    return v or None


RANK = re.compile(r"^(?:SHO\b\s*[/,:-]?\s*)?((?:L/|LR\s+|W/|LADY\s+|LADIES\s+)?(?:INSP(?:ECTOR)?|SUB\s+INSPECTOR|S\.?S\.?I|A\.?S\.?I|"
                  r"S\.?I|H\.?C|DSP|CONST|C\.?T)\.?)(?:\s*/\s*SHO\b)?(?:(?<=\.)\s*|\s+|(?<=SHO)\s*)(?=\S)", re.I)
BELT = re.compile(r"[,\s]*\b(?:No\.?\s*)?(\d{1,5}\s*/\s*[A-Z][A-Za-z]*(?:\s+[A-Z]{2,4})?)\s*[,.]*$")
NAME_PHONE = re.compile(r"[,\s]*\b(\d{5}-?\d{5}|\d{10})\b[.,\s]*")


def split_name(s):
    """'Insp/SHO Rupinder Kaur, 07/LR, 90400-83000.' -> ('Rupinder Kaur', 'Insp', '07/LR', '90400-83000')."""
    s = clean(s)
    if not s:
        return None, None, None, None
    phone = ", ".join(m.group(1) for m in NAME_PHONE.finditer(s)) or None
    s = clean(NAME_PHONE.sub(" ", s)).strip(" ,.")
    belt = None
    m = BELT.search(s)
    if m:
        belt, s = clean(m.group(1)).replace(" / ", "/"), s[:m.start()].strip(" ,.")
    rank = None
    m = RANK.match(s)
    if m:
        rank, s = clean(m.group(1)), s[m.end():]
    else:
        s = re.sub(r"(?i)^SHO\b\s*[/,:-]?\s*(?=\S)", "", s)
    return clean(s.strip(" ,.")) or None, rank, belt, phone


def ps_phone(v):
    """The station landline; '1821513909' (STD 0 lost) -> '01821513909'."""
    v = clean(str(v)) if v is not None else None
    if v and re.fullmatch(r"[1-5]\d{9}", v):
        v = "0" + v
    return v


def latlon(lat, lon):
    a, b = _scale(lat), _scale(lon)
    if a is None or b is None:
        return None, None
    for la, lo in ((a, b), (b, a)):
        if 29.4 < la < 32.7 and 73.8 < lo < 77.1:
            return round(la, 7), round(lo, 7)
    return None, None


def parse(rows, district_code, url=SOURCE):
    recs = []
    for x in rows:
        st = clean(x.get("cctnsPsName"))
        name, rank, belt, name_phone = split_name(x.get("shoName"))
        mhc, mhc_rank, mhc_belt, _ = split_name(x.get("mhcName"))
        if not st and not name:
            continue
        lat, lon = latlon(x.get("latitude"), x.get("longitude"))
        women = x.get("officeType") == "WOMEN_PS"
        recs.append(rec(M, f"{district_code}:{x.get('id') or slug(x.get('saanjhName') or st)}", area=st or clean(x.get("saanjhName")),
                        area_regional=clean(x.get("psNamePn")), office_type="women police station" if women else "police station",
                        post="SHO", name=name, name_regional=clean(x.get("shoNamePn")), rank=clean(x.get("shoRank")) or rank,
                        belt_no=belt, posted_since=x.get("shoPostedSince"),
                        phone=phones(x.get("shoMobile"), name_phone, ps_phone(x.get("psPhone"))),
                        email=email(x.get("psEmail") or ""), address=clean(x.get("psAddress")),
                        mhc_name=mhc, mhc_rank=mhc_rank, mhc_belt_no=mhc_belt, mhc_mobile=phones(x.get("mhcMobile")), saanjh_centre=clean(x.get("saanjhName")),
                        state="PB", district=clean(x.get("cctnsDistrictName")), office_id=str(x["cctnsPsCode"]) if x.get("cctnsPsCode") else None,
                        lat=lat, lon=lon, source=url))
    return recs


def fetch(p, get):
    code = str(p["district_code"])
    recs, files, why = [], [], []
    for t in p.get("office_types", TYPES):
        r = get(details_url(code, t))
        if r is None:
            why.append(f"{t}: no answer")
            continue
        files.append(gz(M, f"{code}-{t}.json", r.content))
        try:
            rows = r.json()
        except (ValueError, json.JSONDecodeError):
            why.append(f"{t}: not json")
            continue
        recs += parse(rows if isinstance(rows, list) else rows.get("data") or [], code)
    return recs, files, "" if recs else ("; ".join(why) or "no stations")
