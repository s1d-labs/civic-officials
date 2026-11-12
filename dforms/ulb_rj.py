"""Rajasthan: the Jankalyan contact service behind lsg.rajasthan.gov.in, one POST to
https://lsg.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail with the body {} (JSON).

One answer (about 4.8 MB, 3,808 rows on 2026-11-11, "TotalRecords" in the answer) holds the contact rows of EVERY department site
on the Rajasthan sectoral portal: state departments, district sites ("District Churu") and the town sites of the LSG department
("Nagar Palika, NIMBAHERA", one Angular site per body at lsg.rajasthan.gov.in/<vdir>/). Fields per row: DepartmentTitle,
DesignationName (+Hindi), OfficerName (+Hindi), MobileNo, PhoneNo, OfficeLandline, Email, Place, Address, Office,
ContactCategoryName, IsPDF + AttachmentUrl (a contact PDF instead of data). The rows carry no date. Not India-only (answered from
Germany on 2026-11-11).

Kept (dept town_body, level body):
- rows of a town site (title "Nagar Palika|Nagar Parishad|Municipal Corporation|Nagar Nigam, <BODY>[, <DISTRICT>]"): every row
  with a name, phone or email (most sites list only the EO / Commissioner / Chief Municipal Officer and the chairperson;
  Nimbahera lists its whole staff). About 60 of the 261 town sites have such rows.
- rows of a district site ("District <name>") whose post is a town body post: "Commissioner Nagar Parishad/Nagar Nigam",
  "Executive Officer" (not the supply department's "E.O. रसद"), "Chairman"/"Mayor" of a Nagar Palika/Parishad/Nigam. The body
  is the town in Place / Address / Office ("Nagar Palika Bandikui", "CHURU", "Mundawar NP"); the district is the site's own.
  A Commissioner Nagar Parishad / Chairman Nagar Parishad row with no town falls back to the district's own name (the district
  HQ council: Anupgarh); Nagar Nigam and Mayor rows with no town are left out (Jodhpur has two corporations).
  These district rows are what civic.official_dir loads as "LSG Rajasthan (district)" with local_body_code null (sql/47 ties
  only town-site rows to a body), so they matched no body before this reader.
Left out: UIT / KDA / RUDSICO sites (not urban local bodies), the "District Jaipur Test" site (test data), PDF-only rows,
rows with no name, phone and email. When one body has the same post twice, the row with the higher Id (newer entry) wins.
Hindi names go to name_regional when an English name exists.
"""
import json
import re

from dforms import _esw, _ulb

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_rj"
URL = "https://lsg.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail"
SOURCE = "https://lsg.rajasthan.gov.in/"
TOWN = re.compile(r"(?i)^\s*(nagar\s*palika|nagar\s*parishad|municipal\s*corporation|nagar\s*nigam)\s*,\s*(.+?)\s*$")
TYPE_WORDS = re.compile(r"(?i)\b(nagar\s*(palika|parishad|nigam)|nagarpalika|nagarparishad|nagarnigam|municipal\s*(council|corporation|"
                        r"board)?|muncipal\s*council|parisar|bhawan|n\.?\s?p\.?|m\.?\s?b\.?)\b")
BODY_POST = re.compile(r"(?i)commissioner\s+nagar|executive\s+officer|^\s*chairman\s*$|^\s*mayor\s*$")
NOT_BODY = re.compile(r"(?i)रसद|supply|zila|panchayat\s*samiti|devasthan|chief\s+executive|divisional")
TOWN_WORDS = re.compile(r"(?i)nagar\s*(palika|parishad|nigam)|nagarpalika|nagarparishad|municipal|\bn\.?p\.?\b|mayor|chairman nagar")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "RJ", "india_only": False}}]


def val(x, k):
    v = _esw.clean(x.get(k))
    return "" if re.fullmatch(r"[\s.\-–*]*|none|null|n/?a", v, re.I) else v


def town_name(s):
    """'Nagar Palika Bandikui' -> 'Bandikui'; 'NAGAR PARISHAD TIJARA' -> 'TIJARA'; 'Mundawar NP' -> 'Mundawar'; 'Hindaun' -> 'Hindaun'."""
    s = re.sub(r"\(.*?\)", " ", s or "")
    s = s.split(",")[0]
    s = _esw.clean(TYPE_WORDS.sub(" ", s)).strip(" ,.-")
    return s if len(s) >= 3 and not re.search(r"(?i)collectorate|office|zila|^ward", s) else ""


def person(x):
    en, hi = val(x, "OfficerName"), val(x, "OfficerNameInHindi")
    en = _esw.clean(re.sub(r"\(\s*(?:E\.?\s?O\.?|रसद)[^)]*\)", " ", en))        # "(E.O.N.P. Todabhim)" names the post, not the person
    if re.match(r"(?i)^(nodal off|collector,)", en):
        en = ""
    if re.match(r"(?i)^(nodal off|collector,)", hi):
        hi = ""
    return (en or hi), (hi if en and hi != en else "")


def body_of(x):
    """(body, district, body_type, kind) for a row, or None when the row is not a town body's."""
    title = val(x, "DepartmentTitle")
    m = TOWN.match(title)
    if m:
        parts = [p.strip() for p in m.group(2).split(",") if p.strip()]
        return parts[0], (parts[1] if len(parts) > 1 else None), _esw.clean(m.group(1)).title(), "town"
    d = re.match(r"(?i)^district\s+(.+)$", title)
    if not d or re.search(r"(?i)test", title):
        return None
    post = val(x, "DesignationName")
    cat = val(x, "ContactCategoryName")
    if not BODY_POST.search(post) or NOT_BODY.search(" ".join([post, val(x, "OfficerName"), val(x, "Place"), val(x, "Address")])):
        return None
    where = [val(x, "Place"), val(x, "Address"), val(x, "Office")]
    ctx = " ".join([post, cat] + where)
    if re.match(r"(?i)\s*(chairman|mayor)\s*$", post) and not TOWN_WORDS.search(ctx):
        return None
    btype = None
    for t in [post, cat] + where:
        mt = re.search(r"(?i)nagar\s*(palika|parishad|nigam)|nagarpalika|nagarparishad", t)
        if mt:
            btype = "Nagar " + re.sub(r"(?i)^nagar\s*", "", mt.group(0)).title()
            break
    body = next((town_name(w) for w in where[:2] if town_name(w)), "")
    district = _esw.clean(d.group(1))
    if not body:
        if btype in ("Nagar Parishad", "Nagar Palika") and not re.search(r"(?i)\(rural\)|nigam", ctx):
            body = district
        else:
            return None
    return body, district, btype, "district"


def parse(data, url=URL):
    rows = data["Data"]["Data"] if isinstance(data.get("Data"), dict) else data.get("Data") or []
    path = "Data.Data" if isinstance(data.get("Data"), dict) else "Data"
    best = {}
    for i, x in enumerate(rows):
        x = {**x, "_index": i}
        if x.get("IsPDF") and not (val(x, "OfficerName") or val(x, "MobileNo")):
            continue
        b = body_of(x)
        if not b:
            continue
        body, district, btype, kind = b
        name, name_hi = person(x)
        phone = _esw.phones(val(x, "MobileNo"), val(x, "PhoneNo"), val(x, "OfficeLandline"))
        email = _esw.emails(val(x, "Email"))
        if not (name or phone or email):
            continue
        post = val(x, "DesignationName") or val(x, "ContactCategoryName") or "Contact"
        if not val(x, "DesignationName") and re.search(r"(?i)employee", post):
            post = "Staff"
        k = (_esw.slug(district or ""), _esw.slug(body), _esw.slug(post), _esw.slug(name) if post == "Staff" else "")
        if k not in best or int(x.get("Id") or 0) > int(best[k][0].get("Id") or 0):
            best[k] = (x, body, district, btype, kind, post, name, name_hi, phone, email)
    recs, seen = [], set()
    for x, body, district, btype, kind, post, name, name_hi, phone, email in sorted(best.values(), key=lambda v: int(v[0].get("Id") or 0)):
        recs.append(_ulb.record(MODULE, "RJ", body, post, seen, name=name, phone=phone, email=email, district=district, body_type=btype,
                                source=SOURCE, name_regional=name_hi or None, post_regional=val(x, "DesignationNameHindi") or None,
                                list_site=_esw.clean(x.get("DepartmentTitle")), list_kind=kind, contact_id=x.get("Id"),
                                src_pos={"key": path, "index": x["_index"], "Id": x.get("Id")}))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL), method="POST", data="{}", headers={"Content-Type": "application/json"})
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contacts", r.content, "json")]
    try:
        data = json.loads(r.content)
    except ValueError:
        return [], files, "not JSON"
    recs = parse(data, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
