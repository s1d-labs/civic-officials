"""Rajasthan, second source: the nodal officers of the Jankalyan sites, one POST to
https://lsg.rajasthan.gov.in/webapi/api/JankalyanHome/GetAllUserDetailList (JSON body below, no login: the public scheme pages
of the portal call it for their "contact" tab). Answered from Germany on 2026-11-11 (3.2 MB, "TotalRecords" 1,572).

ulb_rj reads the contact rows of the town sites (GetDepartmentContactDetail). Only about 100 of the 261 town sites have such rows,
so 220 of the 260 Rajasthan towns with no official in DB civic stay empty. This list is different: it gives the user that each
department site registered as its nodal officer (UserType "DPTO" = department nodal officer, "DLO" = district nodal officer),
with DesignationName (+ Hindi), OfficeName ("Nagar Palika, KHERLI", "Nagar Parishad, CHURU", "Municipal Corporation, Ajmer"),
DistrictNames, UserEmail, Mobile, LandlineNo, UserCreateDate, ModifiedDate. On 2026-11-11, 335 rows had a town office as
OfficeName, for 220 town names; 288 of them have the post "EXECUTIVE OFFICER", 11 a Commissioner post.
The list gives NO person name (UserName and SSOID are login ids, not names: they are left out). So a record gives the post,
the post holder's mobile and mailbox as the portal holds them, and the date of the row (row_modified; 186 rows date from 2023,
143 from 2026). The mobile can belong to an earlier holder of the post when the row is old: row_modified says how old it is.

Kept (dept town_body, level body): rows whose OfficeName is a town body, active and not deleted, except the posts that are not
officers of the body (Regional Commissioner / Regional Deputy Director of LSG, District Collector, ACP / Deputy Director of the
LSG department), and filler mailboxes ("abcd@rajasthan.gov.in"). The area is the town name as OfficeName writes it; lgd_code comes from dforms/ulb2_rj_lgd.json (office name ->
LGD code, made 2026-11-11 by name in civic.ulb, district and hand checks: "KHERTHAL" = Khairthal-Tijara 248698, "BADI SADRI" =
Bari Sadri 248843, "KHUDALA FALNA ST." = Falna 248784, "LAXMANGARH" of Sikar = Lachhmangarh 248740, "BARDODMEV" = Baroda Meo
300347). Offices with no LGD body (Jodhpur North and Kota North, the corporations merged in 2025; Kaithoon, Raniwara,
Rishabhdeo, Semari, Lalgarh-Jatan, Gudha Gorji, which LGD does not list as active town bodies) get no lgd_code.
"""
import json
import re

from dforms import _esw, _ulb

MODULE = "ulb2_rj"
STATE = "RJ"
URL = "https://lsg.rajasthan.gov.in/webapi/api/JankalyanHome/GetAllUserDetailList"
SOURCE = "https://lsg.rajasthan.gov.in/"
BODY = {"Page": 1, "PageSize": 10000, "Search": None, "OrderBy": None, "IsPostBack": False, "UserType": "DPTO,DLO",
        "DepartmentCode": 0}
TOWN = re.compile(r"(?i)^\s*(nagar\s*palika|nagar\s*parishad|municipal\s*corporation|nagar\s*nigam)\s*,\s*(.+?)\s*$")
NOT_BODY = re.compile(r"(?i)regional\s+commiss|district\s+collector|\bacp\b|deputy\s+director")
FILLER = re.compile(r"(?i)^(abcd?|abc|xyz|test|dummy|na|nil|none)@")          # a filler mailbox ("abcd@rajasthan.gov.in", Bari Sadri)
with open(__file__.rsplit("/", 1)[0] + "/ulb2_rj_lgd.json", encoding="utf-8") as _f:
    LGD = json.load(_f)


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": False}}]


def okey(office):
    """The key of an office name in ulb2_rj_lgd.json: spaces folded, upper case."""
    return re.sub(r"\s+", " ", (office or "").replace("\xa0", " ")).strip().upper()


def val(x, k):
    v = _esw.clean(x.get(k))
    return "" if re.fullmatch(r"[\s.\-–*]*|none|null|n/?a", v, re.I) else v


def parse(data, url=URL):
    rows = data["Data"]["Data"] if isinstance(data.get("Data"), dict) else data.get("Data") or []
    rows = sorted(rows, key=lambda x: (str(x.get("ModifiedDate") or ""), int(x.get("UserId") or 0)), reverse=True)
    recs, seen = [], set()
    for x in rows:
        if not x.get("UserIsActive") or x.get("UserIsDeleted"):
            continue
        office = _esw.clean(val(x, "OfficeName").replace("\xa0", " "))
        m = TOWN.match(office)
        post = val(x, "DesignationName")
        if not m or not post or NOT_BODY.search(post):
            continue
        phone = _esw.phones(val(x, "Mobile"), val(x, "LandlineNo"))
        email = val(x, "UserEmail").lower()
        email = "" if FILLER.match(email) else _esw.emails(email)
        if not (phone or email):
            continue
        town = _esw.clean(m.group(2))
        tie = LGD.get(okey(office), {})
        district = val(x, "DistrictNames") or None
        extra = {k: v for k, v in (("lgd_code", tie.get("lgd_code")), ("area_latin", tie.get("lgd_name"))) if v}
        recs.append(_ulb.record(MODULE, STATE, town, post, seen, phone=phone, email=email, district=district,
                                body_type=_esw.clean(m.group(1)).title(), source=SOURCE, list_name=office,
                                post_regional=val(x, "DesignationNameHindi") or None, nodal_type=val(x, "UserType") or None,
                                user_id=x.get("UserId"), row_created=val(x, "UserCreateDate")[:10] or None,
                                row_modified=val(x, "ModifiedDate")[:10] or None, api=url, **extra))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL), method="POST", data=json.dumps(BODY), headers={"Content-Type": "application/json"})
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "nodal-officers", r.content, "json")]
    try:
        data = json.loads(r.content)
    except ValueError:
        return [], files, "not JSON"
    recs = parse(data, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
