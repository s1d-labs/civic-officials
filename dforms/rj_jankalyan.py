"""Rajasthan: contact directories of the district and department portals of the Jankalyan platform (DoIT&C, Angular).

<district>.rajasthan.gov.in and about 150 other portals (district police, NHM, PHED, Panchayati Raj ...) are empty Angular
shells: the page text comes from the API https://districtfrontwebapi.rajasthan.gov.in/ (TLS chain incomplete: the task's
insecure retry is needed, records get tls_unverified). The portal's own bundle (main-es2015.*.js, "contact-directory" route,
component hm in chunk 1) maps its host name to a department code (jaipur.rajasthan.gov.in -> 37) and asks:

  POST /PublicPortal/DepartmentWebsite/GetDepartmentContactDetail   (JSON, no key, no token)
  {"Page": 1, "PageSize": 10000, "OrderBy": "DisplayOrderNo", "OrderByAsc": 1, "IsPostBack": true, "Search": "",
   "AdvanceSearchModel": {"DepartmentCode": <code>, "CategoryCode": 0, "SearchKeyword": ""}}

CategoryCode 0 gives every entry of the portal (measured 2026-11-12 from Mumbai: Ajmer 69, Barmer 61, Kota 62, Jaipur 5).
Each entry is either a data row (OfficerName, DesignationName(+Hindi), MobileNo, PhoneNo, Email, Office, Place, Address,
ContactCategoryName such as "District Administration (DATA)", "DLO (DATA)", "Pradhan", "MP (Loksabha)", "Blood Bank") or a
file (IsPDF, AttachmentUrl: "DLO(PDF)" = district level officers, "Other Officers" = SDM / Tehsildar / BDO lists, "CHC",
"PHC", "ERO- AERO", "BLO (PDF)", "Telephone Directory"). The files are free-form PDFs (Chrome print, scans): this reader
keeps every one of them in the bucket (fetched once; the file host redirects to /WebMyWayFiles/) and writes a "source_file"
record per file, so a later step can read them from the bucket on the runners. The API gives DateOfBirth; the portal page
shows only "xx-xx-xxYY". The full date is kept (date_of_birth, ISO) with birth_year (owner, 2026-11-12: keep the full dates).

Records (depts.py contract): one dept_office per data row: dept from the designation and the category (keywords below;
default administration for district portals, the payload's dept for department portals), level from the post (SDM ->
subdivision, Tehsildar -> subdistrict, BDO / Pradhan -> block, else district; the payload's level for state portals),
post = DesignationName (post_regional = Hindi), name, name_regional, phone (MobileNo, PhoneNo, OfficeLandline), email,
office, address, place, category, district (payload). Ids: dept:rj_jankalyan:<code>:<entry Id>; files:
dept:rj_jankalyan:<code>:file:<entry Id> (type source_file, not loaded as an office).
One queue item = one portal (1 POST + its files).
"""
import json
import re

from dforms import _esw

METHOD = "json api (GetDepartmentContactDetail)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "rj_jankalyan"
API = "https://districtfrontwebapi.rajasthan.gov.in/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail"
# Each portal family has its own API base in its own bundle (environment "ApiBaseUrl"): the police portals (<district>police,
# grp*, policedepartment) use https://policedepartment.rajasthan.gov.in/webapi/ (main-es2015.98a15c4e4bec4cdbb5a4.js, build
# 2026-07-21); the Panchayati Raj portals (rajpanchayat, rdprd, zp*) use https://lsg.rajasthan.gov.in/webapi/ (it gives one or two
# rows more than districtfrontwebapi for the same code). The department codes are the same on every base (measured 2026-11-13).
API_POLICE = "https://policedepartment.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail"
API_LSG = "https://lsg.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail"
# The police portals keep almost nothing in their contact directory (Ajmer 4 rows, Alwar 2; Jaipur, Banswara, the state portal
# 967 and 28 more: "Data": [] on both bases, the same 1,034-byte answer). Their "Contact Us" menu entries (Directory, Nodal
# Officers, RPS List, Distt-Circle-P.Station, beat constables) are "Redirect only" rows of department 112 that point to old
# www.police.rajasthan.gov.in/*.aspx pages, which answer 404 since the site moved to an Angular app (/portal/, obfuscated bundle).
# So an empty answer of a police portal is the portal's real state: the item ends done with a note record, not failed.


def api_for(p):
    """The contact API of the item's portal (payload "api" first, else by its host label)."""
    if p.get("api"):
        return p["api"]
    label = (p.get("host") or "").split(".")[0]
    if label in POLICE_SITES or label == "policedepartment" or p.get("dept") == "police":
        return API_POLICE
    if label in ("rajpanchayat", "rdprd") or label.startswith("zp") or label.endswith("zp"):
        return API_LSG
    return API
# host label -> (department code of the portal, LGD district name or None, dept, level)
DISTRICT_SITES = {
    "ajmer": ("22", "Ajmer"), "alwar": ("23", "Alwar"), "balotra": ("1274", "Balotra"), "banswara": ("24", "Banswara"),
    "baran": ("25", "Baran"), "barmer": ("26", "Barmer"), "beawar": ("1275", "Beawar"), "bharatpur": ("27", "Bharatpur"),
    "bhilwara": ("28", "Bhilwara"), "bikaner": ("29", "Bikaner"), "bundi": ("30", "Bundi"), "chittorgarh": ("31", "Chittorgarh"),
    "churu": ("32", "Churu"), "dausa": ("33", "Dausa"), "deeg": ("1276", "Deeg"), "dholpur": ("34", "Dholpur"),
    "didwana-kuchaman": ("1277", "Didwana-Kuchaman"), "dungarpur": ("35", "Dungarpur"), "sriganganagar": ("51", "Ganganagar"),
    "hanumangarh": ("36", "Hanumangarh"), "jaipur": ("37", "Jaipur"), "jaisalmer": ("38", "Jaisalmer"), "jalore": ("39", "Jalore"),
    "jhalawar": ("40", "Jhalawar"), "jhunjhunu": ("41", "Jhunjhunu"), "jodhpur": ("42", "Jodhpur"), "karauli": ("43", "Karauli"),
    "khairthaltijara": ("1283", "Khairthal-Tijara"), "kota": ("44", "Kota"), "kotputlibehror": ("1282", "Kotputli-Behror"),
    "nagaur": ("45", "Nagaur"), "pali": ("46", "Pali"), "phalodi": ("1285", "Phalodi"), "pratapgarh": ("47", "Pratapgarh"),
    "rajsamand": ("48", "Rajsamand"), "salumber": ("1286", "Salumbar"), "sawaimadhopur": ("52", "Sawai Madhopur"),
    "sikar": ("49", "Sikar"), "sirohi": ("50", "Sirohi"), "tonk": ("194", "Tonk"), "udaipur": ("54", "Udaipur"),
    # districts of 2023 that were merged back in Dec 2024: the portals still answer; their offices are in the LGD district
    "anupgarh": ("1273", "Ganganagar"), "dudu": ("1278", "Jaipur"), "gangapurcity": ("1279", "Sawai Madhopur"),
    "jaipurural": ("1272", "Jaipur"), "jodhpurrural": ("1281", "Jodhpur"), "kekri": ("1280", "Ajmer"),
    "neemkathana": ("1284", "Sikar"), "sanchore": ("1287", "Jalore"), "shahpura": ("1288", "Bhilwara"),
}
POLICE_SITES = {
    "ajmerpolice": ("411", "Ajmer"), "alwarpolice": ("412", "Alwar"), "banswarapolice": ("413", "Banswara"),
    "baranpolice": ("414", "Baran"), "barmerpolice": ("415", "Barmer"), "bharatpurpolice": ("416", "Bharatpur"),
    "bhilwarapolice": ("417", "Bhilwara"), "bhiwadipolice": ("418", "Khairthal-Tijara"), "bikanerpolice": ("419", "Bikaner"),
    "bundipolice": ("420", "Bundi"), "chittorgarhpolice": ("421", "Chittorgarh"), "churupolice": ("422", "Churu"),
    "dausapolice": ("423", "Dausa"), "dholpurpolice": ("424", "Dholpur"), "dungarpurpolice": ("425", "Dungarpur"),
    "hanumangarhpolice": ("426", "Hanumangarh"), "jaipurpolice": ("410", "Jaipur"), "jaipurruralpolice": ("427", "Jaipur"),
    "jaisalmerpolice": ("428", "Jaisalmer"), "jalorepolice": ("429", "Jalore"), "jhalawarpolice": ("430", "Jhalawar"),
    "jhunjhunupolice": ("431", "Jhunjhunu"), "jodhpurcitypolice": ("433", "Jodhpur"), "jodhpurruralpolice": ("432", "Jodhpur"),
    "karaulipolice": ("434", "Karauli"), "kotacitypolice": ("435", "Kota"), "kotaruralpolice": ("436", "Kota"),
    "nagaurpolice": ("437", "Nagaur"), "palipolice": ("438", "Pali"), "pratapgarhpolice": ("439", "Pratapgarh"),
    "rajsamandpolice": ("440", "Rajsamand"), "sawaimadhopurpolice": ("441", "Sawai Madhopur"), "sikarpolice": ("442", "Sikar"),
    "sirohipolice": ("443", "Sirohi"), "sriganganagarpolice": ("444", "Ganganagar"), "tonkpolice": ("445", "Tonk"),
    "udaipurpolice": ("446", "Udaipur"),
    # Government Railway Police (codes from the police portals' bundle, 2026-11-13)
    "grpajmerpolice": ("448", "Ajmer"), "grpjodhpurpolice": ("449", "Jodhpur"),
}
DEPT_SITES = {  # state department portals: (code, dept, district or None)
    "nhm": ("236", "health", None), "phed": ("110", "water", None), "rajpanchayat": ("107", "rural_development", None),
    "rdprd": ("128", "rural_development", None), "jaipurzp": ("894", "rural_development", "Jaipur"),
    "zpajmer": ("880", "rural_development", "Ajmer"), "policedepartment": ("967", "police", None),
}

# (regex on "designation | category", dept); first match wins
DEPT_KW = [
    (r"\b(police|s\.?p\.?|sho|thana|dy\.?\s*sp|circle officer police|addl\.? s\.?p)\b|पुलिस|थाना", "police"),
    (r"cm\s*&?\s*ho|chief medical|medical|\bpmo\b|hospital|health|blood bank|\bchc\b|\bphc\b|nursing|\bdrug|ayush|ayurved|चिकित्सा|स्वास्थ्य", "health"),
    (r"educat|\bdeo\b|school|shiksha|samagra|\bdiet\b|college|principal|शिक्षा|विद्यालय", "education"),
    (r"supply|rasad|\bdso\b|food|रसद", "food_supplies"),
    (r"\bpwd\b|public works|sarvjanik|सार्वजनिक निर्माण", "public_works"),
    (r"phed|water|jal\b|irrigation|जलदाय|सिंचाई", "water"),
    (r"vvnl|electric|vidyut|discom|विद्युत", "electricity"),
    (r"zila parishad|\bceo\b|\bbdo\b|panchayat|vikas adhikari|pradhan|pramukh|sarpanch|ward panch|nrega|rural|पंचायत|विकास अधिकारी", "rural_development"),
    (r"\bero\b|aero|\bblo\b|election|निर्वाचन", "elections"),
    (r"tehsildar|tahsildar|patwari|land record|revenue|naib|तहसीलदार|राजस्व", "revenue"),
    (r"icds|women|mahila|child develop|महिला", "women_child"),
    (r"social justice|samajik|welfare|minority|सामाजिक", "social_welfare"),
    (r"agricult|krishi|horticult|animal husbandry|pashupalan|veterinar|fisher|cooperative|कृषि|पशुपालन", "agriculture"),
    (r"forest|\bdfo\b|वन ", "forest"),
    (r"transport|\brto\b|\bdto\b|roadways|परिवहन", "transport"),
    (r"treasury|kosh|कोष", "treasury"),
    (r"labour|industr|\bdic\b|mines|mining|उद्योग|श्रम", "labour_industry"),
    (r"dipr|information|public relation|सूचना", "information"),
    (r"court|judge|न्याया", "courts"),
    (r"fire|अग्नि", "fire"),
    (r"excise|commercial tax|gst|आबकारी", "excise_tax"),
    (r"municipal|nagar parishad|nagar palika|nagar nigam|\buit\b|नगर", "town_body"),
    (r"\bmla\b|\bmp\b|loksabha|lok sabha|rajyasabha|minister|prabhari", "other"),
]
SDM = re.compile(r"(?i)\bsdm\b|sub.?divisional|sub divisional|उपखंड|उपखण्ड")
TEH = re.compile(r"(?i)tehsildar|tahsildar|naib|तहसीलदार")
BLOCK = re.compile(r"(?i)\bbdo\b|block|vikas adhikari|pradhan|panchayat samiti|\bbeo\b|cbeo|विकास अधिकारी|प्रधान")
FACILITY = re.compile(r"(?i)blood bank|\bchc\b|\bphc\b|school|emitra|aadhar|enrolment|helpdesk")


def classify(designation, category, default_dept):
    # the designation first; the category only when the designation names no department ("Right to Information" is a
    # duty of the Collector, not the information department)
    dept = next((d for rx, d in DEPT_KW if re.search(rx, designation or "", re.I)), None)
    if dept is None and not re.search(r"(?i)right to information|nodal officer|content management", category or ""):
        dept = next((d for rx, d in DEPT_KW if re.search(rx, category or "", re.I)), None)
    if default_dept and default_dept != "administration" and (dept is None or dept == "other"):
        dept = default_dept
    dept = dept or default_dept or "administration"
    if FACILITY.search(category or ""):
        level = "facility"
    elif SDM.search(designation or ""):
        level, dept = "subdivision", ("administration" if dept in ("administration", "revenue") else dept)
    elif TEH.search(designation or ""):
        level = "subdistrict"
    elif BLOCK.search(f"{designation or ''} {category or ''}"):
        level = "block"
    else:
        level = "district"
    return dept, level


def body(code, category=0):
    return {"Page": 1, "PageSize": 10000, "OrderBy": "DisplayOrderNo", "OrderByAsc": 1, "IsPostBack": True, "Search": "",
            "AdvanceSearchModel": {"DepartmentCode": int(code), "CategoryCode": int(category), "SearchKeyword": ""}}


def _s(v):
    return _esw.clean(v) if isinstance(v, str) else ("" if v is None else str(v))


def parse(data, p):
    """data: the API answer (dict). Returns (records, files to fetch [(entry id, url, category)])."""
    rows = ((data or {}).get("Data") or {}).get("Data") or []
    code = str(p["code"])
    recs, files = [], []
    default_dept = p.get("dept") or "administration"
    for i, r in enumerate(rows):
        eid = r.get("Id") or r.get("Code")
        cat = _s(r.get("ContactCategoryName"))
        att = _s(r.get("AttachmentUrl"))
        if att and (r.get("IsPDF") or not _s(r.get("OfficerName"))):
            files.append((eid, att, cat))
        name, post = _s(r.get("OfficerName")), _s(r.get("DesignationName"))
        phone = _esw.phones(_s(r.get("MobileNo")).replace("\t", " , "), _s(r.get("PhoneNo")), _s(r.get("OfficeLandline")))
        email = _esw.emails(_s(r.get("Email")))
        if not (name or phone or email) or (r.get("IsPDF") and not (phone or email)):
            continue
        if re.fullmatch(r"(?i)(test|abc|xyz|none|na|-+)", name or "-") and not phone:
            continue
        dept, level = classify(post, cat, default_dept)
        if p.get("level") == "state" and level == "district" and not p.get("district"):
            level = "state"
        dob = _s(r.get("DateOfBirth"))
        recs.append(_esw.record(MODULE, f"{code}:{eid}", dept=dept, level=level, area=_s(r.get("Place")) or p.get("district") or "Rajasthan",
                                post=post or cat, post_regional=_s(r.get("DesignationNameHindi")) or None, category=cat or None,
                                name=name, name_regional=_s(r.get("OfficerNameInHindi")) or None, phone=phone, email=email,
                                office=_s(r.get("Office")) or None, office_regional=_s(r.get("OfficeHindi")) or None,
                                address=_s(r.get("Address")) or _s(r.get("AddressInHindi")) or None,
                                place_regional=_s(r.get("PlaceInHindi")) or None, qualification=_s(r.get("Qualification")) or None,
                                posting_office=_s(r.get("PostingOfficeName")) or None, home_town=_s(r.get("HomeTownName")) or None,
                                birth_year=(dob[:4] if re.match(r"^\d{4}-", dob) else None),
                                date_of_birth=(dob[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", dob) else (dob or None)), url=_s(r.get("URL")) or None,
                                attachment=att or None, portal=p.get("host"), portal_title=_s(r.get("DepartmentTitle")) or None,
                                entry_id=str(eid), state="RJ", district=p.get("district"), office_id=f"rj-jankalyan:{code}:{eid}",
                                source=p["url"], page=p["url"], src_url=api_for(p),
                                src_pos={"key": "Data.Data", "index": i, "id": str(eid)}))
    return recs, files


def items(get=None):
    out = []
    for label, (code, district) in sorted(DISTRICT_SITES.items()):
        out.append((label, code, district, "administration", "district"))
    for label, (code, district) in sorted(POLICE_SITES.items()):
        out.append((label, code, district, "police", "district"))
    for label, (code, dept, district) in sorted(DEPT_SITES.items()):
        out.append((label, code, district, dept, "district" if district else "state"))
    return [{"key": f"{MODULE}:{label}", "payload": {"reader": MODULE, "url": f"https://{label}.rajasthan.gov.in/contact-directory",
                                                    "host": f"{label}.rajasthan.gov.in", "code": code, "district": district,
                                                    "dept": dept, "level": level, "state": "RJ", "india_only": True,
                                                    "route": "direct"}}
            for label, code, district, dept, level in out]


def fetch(p, get):
    api = api_for(p)
    r = get(api, method="POST", data=json.dumps(body(p["code"])),
            headers={"Content-Type": "application/json", "Accept": "application/json"})
    if r is None:
        return [], [], "API did not answer"
    try:
        data = r.json() if hasattr(r, "json") else json.loads(r.text)
    except ValueError:
        return [], [], "API answer is not JSON"
    if not data.get("IsSuccess"):
        return [], [], f"API: {str(data.get('Message'))[:100]}"
    label = p.get("host", "").split(".")[0] or p["code"]
    files = [_esw.keep(MODULE, f"{label}/contact-detail", r.content, "json")]
    recs, pdfs = parse(data, p)
    seen = set()
    for eid, url, cat in pdfs:
        if url in seen:
            continue
        seen.add(url)
        f = get(url)
        ok = f is not None and f.content[:5] == b"%PDF-"
        path = None
        if ok:
            ext = "pdf"
            path = f"depts/{MODULE}/{label}/{eid}.{ext}"
            files.append((path, f.content, "application/pdf"))
        recs.append((f"dept:{MODULE}:{p['code']}:file:{eid}",
                     {"type": "source_file", "category": cat, "url": url, "stored": path, "bytes": len(f.content) if ok else None,
                      "fetched": ok, "portal": p.get("host"), "state": "RJ", "district": p.get("district"), "dept": p.get("dept"),
                      "source": p["url"], **({"src_url": url, "method": "file saved to the bucket (pdf)"} if ok else {})}))
    if not any(d.get("type") == "dept_office" for _, d in recs) and not pdfs:
        if api == API_POLICE:
            return [(f"dept:{MODULE}:{p['code']}:note", {"type": "note", "note": "the portal's contact directory is empty",
                                                         "portal": p.get("host"), "state": "RJ", "district": p.get("district"),
                                                         "dept": "police", "source": p["url"], "src_url": api,
                                                         "method": METHOD, "src_pos": {"key": "Data.Data", "index": None}})], files, ""
        return recs, files, "no entries"
    return recs, files, ""
