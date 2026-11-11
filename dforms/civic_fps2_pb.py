"""Punjab: fair price shops (ration shops) and their owners from the state's ePoS portal https://epos.punjab.gov.in (NIC, JSP; not the
AePDS page set: FPS_Device_Mapping.jsp is 404 there). The "FPS Details" report (dfso_fps_details) has no login and three levels:
1. dfso_fps_details: one row per district, onclick detailsR(<dist_code>,'T') (codes in DISTRICTS, read from the page 2026-11-06).
2. POST afso_fps_details.action (dist_code, status=T): one row per supply office (AFSO), onclick detailsRR('<dist>','<office>','T').
3. POST fps_aso_details.action (dist_code, office_code, status=T): one row per shop: FPS id, total cards, terminal id, owner name,
   mobile. The site masks the terminal id and the mobile (XXXXX-04081), so no phone. The page source comments out the Location and
   Village columns. The header gives "<office> / <district>".
One queue item per district (seeds/dept_civic_fps2_pb.json, 23 districts, 16,551 shops on the site's own count of 2026-11-06).
Owner names come as the site shows them; some use "_" for a space (Gurwinderjit_singh): `name` has the space, `name_source` keeps the
source value when it differs. Record ids: dept:civic_fps2_pb:<fps_id>.
"""
import re

from dforms import _civic_fps, _esw

MODULE = "civic_fps2_pb"
STATE = "PB"
BASE = "https://epos.punjab.gov.in"
INDIA_ONLY = False
DISTRICTS = {"049": "Amritsar", "054": "Barnala", "046": "Bathinda", "045": "Faridkot", "040": "Fatehgarh Sahib", "648": "Fazilka",
             "043": "Ferozepur", "035": "Gurdaspur", "038": "Hoshiarpur", "037": "Jalandhar", "036": "Kapurthala", "041": "Ludhiana",
             "781": "Malerkotla", "047": "Mansa", "042": "Moga", "647": "Pathankot", "048": "Patiala", "051": "Rupnagar",
             "052": "Sahibzada Ajit Singh Nagar", "053": "Sangrur", "039": "Shahid Bhagat Singh Nagar", "044": "Sri Muktsar Sahib",
             "050": "Tarn Taran"}
FORM = {"Content-Type": "application/x-www-form-urlencoded"}
OFFICE = re.compile(r"detailsRR\('(\d+)','(\d+)','T'\);?\"?\s*>\s*([^<]+?)\s*<")
DIST = re.compile(r"detailsR\((\d+),'T'\)[^>]*>\s*([^<]+?)\s*<")


def districts(html):
    """[(dist_code, name)] from the dfso_fps_details page."""
    seen, out = set(), []
    for code, name in DIST.findall(html or ""):
        if code not in seen:
            seen.add(code)
            out.append((code, _esw.clean(name)))
    return out


def items(get):
    r = get(f"{BASE}/dfso_fps_details")
    found = districts(r.text) if r is not None else []
    return [{"key": f"{MODULE}-{c}", "payload": {"reader": MODULE, "url": BASE, "state": STATE, "dist_code": c, "district": n}}
            for c, n in (found or sorted(DISTRICTS.items()))]


def offices(html):
    """[(office_code, office name)] from one afso_fps_details answer."""
    seen, out = set(), []
    for _, code, name in OFFICE.findall(html or ""):
        if code not in seen:
            seen.add(code)
            out.append((code, _esw.clean(name)))
    return out


def parse(html, dist_code, office_code="", office="", district=""):
    soup = _esw.soup(html or "")
    table = soup.find("table", id="Report") or soup.find("table")
    if table is None:
        return []
    th = table.find("th")
    head = _esw.clean(th.get_text(" ")) if th else ""
    m = re.search(r"FPS Details for\s*(.+?)\s*/\s*(.+)$", head)
    if m:
        office, district = office or m.group(1), m.group(2)
    district = district or DISTRICTS.get(dist_code, "")
    recs, seen = [], set()
    for tr in table.find_all("tr"):
        tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) < 5 or not re.fullmatch(r"\d{6,15}", tds[1]):
            continue
        fid, cards, term, owner = tds[1], tds[2], tds[3], tds[4]
        mob = tds[5] if len(tds) > 5 else ""
        if _civic_fps.TEST_ID.match(fid) or fid in seen:
            continue
        seen.add(fid)
        src_name = _civic_fps.name_of(owner)
        name = _esw.clean(src_name.replace("_", " "))
        if not name:
            continue
        recs.append(_esw.record(
            MODULE, fid, dept="food_supplies", level="facility", layer="fps", area=office or district, post=_civic_fps.POST,
            name=name, name_source=src_name if src_name != name else "", phone=_civic_fps.unmasked(mob), state=STATE,
            district=district, subdistrict=office, block=office, afso_code=office_code, fps_id=fid, office_id=fid,
            terminal_id="" if _civic_fps.MASKED.search(term) else _civic_fps.name_of(term), total_cards=int(cards) if cards.isdigit() else None, dist_code=dist_code,
            source=f"{BASE}/dfso_fps_details"))
    return recs


def fetch(p, get):
    code = str(p["dist_code"])
    district = p.get("district") or DISTRICTS.get(code, "")
    r = get(f"{BASE}/afso_fps_details.action", method="POST", data={"dist_code": code, "status": "T"}, headers=FORM)
    if r is None:
        return [], [], "no office list"
    files = [_esw.keep(MODULE, f"afso-{code}", r.content)]
    recs, seen = [], set()
    for oc, oname in offices(r.text):
        a = get(f"{BASE}/fps_aso_details.action", method="POST", data={"dist_code": code, "office_code": oc, "status": "T"},
                headers=FORM)
        if a is None:
            continue
        files.append(_esw.keep(MODULE, f"fps-{code}-{oc}", a.content))
        for rid, d in parse(a.text, code, oc, oname, district):
            if rid not in seen:                               # a shop shows once, under its first office
                seen.add(rid)
                recs.append((rid, d))
    return recs, files, "" if recs else "no rows"
