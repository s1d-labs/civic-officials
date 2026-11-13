"""Brihanmumbai Municipal Corporation (BMC / MCGM, Greater Mumbai, LGD 251488): the Assistant Municipal Commissioner of each
administrative ward (A to T: 24 wards on the ward list, 26 on the officer list since K/North and P/East were added) and the
Deputy Municipal Commissioners, from the MCGM portal (SAP NetWeaver portal, Marathi page with English in each cell).

Sources (all public pages, no login):
  /irj/portal/anonymous/qlListofAsstMC  "List of Assistant Municipal Commissioner": table#RecTable, columns Sr. No. | Name (Marathi
     name and post, then the English name and post in the same cell: "श्री.जितेंद्र घोराडे, कार्यकारी अभियंताShri. Jitendra Ghorade,
     Executive Engineer") | Department ("बी विभाग (प्र.)B Ward (i/c)") | Date of appointment to the current post ("दि.03.10.2025",
     or "... Additional charge with effect from 21.05.2026"). 32 rows: 26 wards + Estate, Market, Removal of Encroachment (City / WS /
     ES), Hospitals. No phones, no emails. "Last updated on 03/07/2026". Live sample 2026-11-11.
  /irj/portal/anonymous/qlListofDeputyMC  "List of Deputy Municipal Commissioners" (zones / departments): same page family; NOT
     sampled (request limit). parse_table() reads any table#RecTable of this family; a zone ("Zone 3", "परिमंडळ ३") in the
     Department cell gives level "zone", else level "body".
  Area of each ward (which electoral wards / prabhags it covers): Vonter/city-officials static/mumbai/boundaries_bmc_prabhag.json
     (CC BY 4.0, TopoJSON; properties ward "FN" and prabhag_no 1-227 = the 2017 / 2026 delimitation). The MCGM portal publishes
     no ward -> prabhag list that this reader could find. K/North and P/East (new wards) have no prabhag list anywhere public: they
     get no prabhags, only a wards_note naming the ward they were probably formed from (K/East, P/North).
The portal answers with an error page ("iView is not compatible with your browser") unless the User-Agent is a normal desktop
browser. The owner allowed a standard browser User-Agent for portal.mcgm.gov.in and dm.mcgm.gov.in only (2026-11-11): UA below.
It answers from Germany (no India server needed).

Records (dforms/_ward.py record()): level "ward" for the 26 ward posts (area "<X> Ward", e.g. "F/North Ward", area_regional as
written, admin_ward code "F/N", wards = prabhag numbers), level "body" for the other Assistant Commissioner posts, level "zone" /
"body" for the Deputy Commissioners. name = English name without the title (Shri / Smt / Dr), name_regional = the Marathi name,
holder_post = the person's own post when it differs ("Executive Engineer"), in_charge True for "(i/c)" / "(प्र.)", since =
date of appointment (ISO), charge = the additional-charge note as written, vacant True when the post has no named holder.
Ids: dept:ward2n_mumbai:ac:<ward code>, ac:<post>, dmc:<n>. Expected rows: 32 (AC list) + ~15 (DMC list).
"""
import json
import re

from dforms import _esw, _ward
import provenance

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_mumbai"
BODY, LGD, STATE, DISTRICT = "Brihanmumbai Municipal Corporation", "251488", "MH", "Mumbai"
BASE = "https://portal.mcgm.gov.in"
AC_URL = f"{BASE}/irj/portal/anonymous/qlListofAsstMC"
DMC_URL = f"{BASE}/irj/portal/anonymous/qlListofDeputyMC"
AREAS_URL = "https://raw.githubusercontent.com/Vonter/city-officials/main/static/mumbai/boundaries_bmc_prabhag.json"
# A standard desktop browser User-Agent: allowed by the owner for portal.mcgm.gov.in and dm.mcgm.gov.in only (2026-11-11).
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 "
                    "Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}

# The administrative wards: code -> (English name, compact code as in Vonter's layer, quick link of the ward's documents page on
# the portal "प्रभागांची यादी" list /irj/portal/anonymous/qlallward, quick link of its RTI page). K/N and P/E are not on that list.
WARDS = {
    "A": ("A", "A", "qlwrda", "qlacaward"), "B": ("B", "B", "qlwrdb", "qlacbward"), "C": ("C", "C", "qlwrdc", "qlaccward"),
    "D": ("D", "D", "qlwrdd", "qlacdward"), "E": ("E", "E", "qlwarde", "qlaceward"),
    "F/N": ("F North", "FN", "qlwrdfn", "qlrtiacfward"), "F/S": ("F South", "FS", "qlwrdfs", "qlacfsward"),
    "G/N": ("G North", "GN", "qlwrdgn", "qlacgnward"), "G/S": ("G South", "GS", "qlacgswarddocs", "qlacgn"),
    "H/E": ("H East", "HE", "qlachewarddocs", "qlacheward"), "H/W": ("H West", "HW", "qlwrdhw", "qlachwward"),
    "K/E": ("K East", "KE", "qlackewarddocs", "qlackeward"), "K/W": ("K West", "KW", "qlwrdkw", "qlackwward"),
    "K/N": ("K North", "KN", None, None), "L": ("L", "L", "qlwrdl", "qlaclward"),
    "M/E": ("M East", "ME", "qlwrdme", "qlacmeward"), "M/W": ("M West", "MW", "qlwrdmw", "qlacmwward"),
    "N": ("N", "N", "qlwrdn", "qlacnward"), "P/N": ("P North", "PN", "qlwrdpn", "qlacpnward"),
    "P/S": ("P South", "PS", "qlwrdps", "qlacpsward"), "P/E": ("P East", "PE", None, None),
    "R/N": ("R North", "RN", "qlwrdrn", "qlacrnward"), "R/S": ("R South", "RS", "qlwrdrs", "qlacrsouthward"),
    "R/C": ("R Central", "RC", "qlacrcwarddocs", "qlacrcward"), "S": ("S", "S", "qlwrds", "qlacsward"),
    "T": ("T", "T", "qlwrdt", "qlactward"),
}
# new wards -> the ward they were formed from (their prabhags are not published separately)
FORMED_FROM = {"K/N": "K/E", "P/E": "P/N"}
SIDES = {"north": "N", "south": "S", "east": "E", "west": "W", "central": "C"}
HONORIFIC = re.compile(r"(?i)^(?:shri|smt|kum|km|dr|mr|mrs|ms|miss)(?:\.\s*|\s+)")
HONORIFIC_MR = re.compile(r"^(?:श्रीमती|श्रीम|श्री|कु|डॉ)\.?\s*")
AREA_EN = {"रुग्णालये": "Hospitals"}


def items(get=None):
    return [{"key": f"{MODULE}-ac", "payload": {"reader": MODULE, "url": AC_URL, "areas_url": AREAS_URL, "state": STATE}},
            {"key": f"{MODULE}-dmc", "payload": {"reader": MODULE, "url": DMC_URL, "areas_url": AREAS_URL, "state": STATE}}]


def split_lang(cell):
    """("Marathi part", "English part") of a cell that writes Marathi first and English right after it ("मालमत्ताEstate")."""
    s = _esw.clean(cell)
    m = re.search(r"[A-Za-z]", s)
    if not m:
        return s, ""
    i = m.start()
    # an English honorific glued to the Marathi ("...आयुक्तShri.") starts the English part; Marathi never holds Latin letters
    return s[:i].strip(" ,"), s[i:].strip(" ,")


def ward_code(text):
    """'F/North Ward' -> 'F/N', 'B Ward (i/c)' -> 'B', 'R/South' -> 'R/S', 'L Ward' -> 'L'; None when the text names no ward."""
    t = _esw.clean(text)
    m = re.match(r"(?i)^\s*([A-HK-NPRST])\s*(?:[/-]\s*(north|south|east|west|central)\b)?\s*(?:ward\b|$|\()", t)
    if not m:
        return None
    code = m.group(1).upper() + ("/" + SIDES[m.group(2).lower()] if m.group(2) else "")
    return code if code in WARDS else None


def iso(d):
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def person(cell):
    """(name, holder_post, name_regional) from a Name cell. name = the English name without its title; when the cell has no English,
    name = the Marathi name. name_regional = the Marathi name without its title."""
    mr, en = split_lang(cell)
    name, _, post = en.partition(",")
    name = HONORIFIC.sub("", _esw.clean(name)).strip(" .,")
    if re.fullmatch(r"(?i)vacant", name):
        name = ""
    mr_name = HONORIFIC_MR.sub("", _esw.clean(mr.split(",")[0])).strip(" .,")
    if mr_name == "रिक्त":
        mr_name = ""
    return name or mr_name, _esw.clean(post), mr_name


def parse_table(html):
    """Rows of the portal's officer list table (table#RecTable, or the first table whose heading has 'Name' and 'Department'):
    [{"sr", "name_cell", "dept_cell", "date_cell"}] and the page's "Last updated on dd/mm/yyyy" date (ISO) or None."""
    soup = _esw.soup(html)
    t = soup.find("table", id="RecTable")
    if t is None:
        t = next((x for x in soup.find_all("table") if re.search(r"(?i)name", x.get_text()) and
                  re.search(r"(?i)department|विभाग|खाते", x.get_text())), None)
    rows = []
    if t is not None:
        for tr in t.find_all("tr"):
            tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
            if len(tds) >= 3 and re.fullmatch(r"\d{1,3}", tds[0]):
                rows.append({"sr": tds[0], "name_cell": tds[1], "dept_cell": tds[2], "date_cell": tds[3] if len(tds) > 3 else ""})
            else:
                provenance.skip_row(tr, 'skip: not (len(tds) >= 3 and re.fullmatch(r"\\d{1,3}", tds[0]))')
    m = re.search(r"(?i)last\s*updated\s*on\s*(\d{1,2})/(\d{1,2})/(\d{4})", soup.get_text(" "))
    upd = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
    return rows, upd


def areas(content):
    """{ward code 'F/N': [prabhag numbers as strings]} from Vonter's TopoJSON / GeoJSON (properties ward, prabhag_no)."""
    try:
        d = json.loads(content)
    except (ValueError, TypeError):
        return {}
    feats = [g for o in (d.get("objects") or {}).values() for g in o.get("geometries", [])] or d.get("features") or []
    compact = {v[1]: k for k, v in WARDS.items()}
    out = {}
    for f in feats:
        p = f.get("properties") or {}
        w, n = compact.get(str(p.get("ward", "")).replace("/", "").upper()), p.get("prabhag_no")
        if w and str(n).isdigit():
            out.setdefault(w, []).append(int(n))
    return {w: [str(n) for n in sorted(set(v))] for w, v in out.items()}


def ward_area(code, area_map):
    """(prabhag list, note) of a ward."""
    if code in area_map:
        return area_map[code], None
    src = FORMED_FROM.get(code)
    if src and src in area_map:
        # no source gives the split: tie no prabhags rather than guess (the owner's rule: only what a source says)
        return None, (f"{code} is a new ward, probably formed from {src}; no prabhag list of {code} is published")
    return None, None


def zone_of(text):
    m = re.search(r"(?i)\bzone\s*[-–.:]?\s*([IVX]+|\d)\b", text) or re.search(r"परिमंडळ\s*[-–.:]?\s*([०-९\d]+)", text)
    if not m:
        return None
    z = m.group(1).translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
    return f"Zone {roman.get(z.upper(), z)}"


def ward_codes_in(text):
    """Administrative ward codes named in a text: "(A, B, C, D, E wards)", "F/South, F/North" -> ["A", ...]."""
    out = []
    for m in re.finditer(r"(?i)(?<![A-Za-z])([A-HK-NPRST])(?:\s*[/-]\s*(north|south|east|west|central|[NSEWC])\b)?(?![A-Za-z])", text):
        side = m.group(2)
        code = m.group(1).upper() + ("/" + (SIDES.get(side.lower()) or side.upper()) if side else "")
        if code in WARDS and code not in out:
            out.append(code)
    return out


def parse_ac(html, url, area_map, seen=None):
    seen = set() if seen is None else seen
    rows, upd = parse_table(html)
    recs = []
    for r in rows:
        name, holder_post, mr_name = person(r["name_cell"])
        dept_mr, dept_en = split_lang(r["dept_cell"])
        date_en = split_lang(r["date_cell"])[1]
        code = ward_code(dept_en)
        in_charge = bool(re.search(r"(?i)\(\s*i\s*/\s*c\s*\)", dept_en) or "(प्र" in dept_mr) or None
        charge = date_en if re.search(r"(?i)charge|assigned", date_en) else None
        holder = None
        if not name and charge:     # vacant post held by another Assistant Commissioner as additional charge
            m = re.match(r"(?i)([^,]+?)\s*,\s*[^,]*commiss?ioner", charge)
            if m:
                holder = HONORIFIC.sub("", m.group(1)).strip(" .")
        common = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, source=url, last_updated=upd, name_regional=mr_name,
                      holder_post=holder_post if holder_post and not re.search(r"(?i)assistant\s+commiss?ioner", holder_post) else None,
                      in_charge=in_charge, since=iso(r["date_cell"]),
                      charge=charge, sr=r["sr"], role="head", wing="administration")
        if code:
            wards, note = ward_area(code, area_map)
            area_en = re.sub(r"(?i)\s*\(\s*i\s*/\s*c\s*\)", "", dept_en).strip()
            area_en = area_en if re.search(r"(?i)ward$", area_en) else f"{area_en} Ward"
            recs.append(_ward.record(MODULE, f"ac:{code.lower().replace('/', '')}", seen, level="ward", area=area_en,
                                     area_regional=dept_mr, admin_ward=code, post="Assistant Municipal Commissioner",
                                     post_regional="सहाय्यक आयुक्त", name=name or holder or "", wards=wards, wards_note=note,
                                     vacant=True if not name and not holder else None, **common))
        else:
            area = dept_en or AREA_EN.get(_esw.clean(dept_mr).replace("‍", ""), dept_mr)
            recs.append(_ward.record(MODULE, f"ac:{_esw.slug(area)}", seen, level="body", area=area, area_regional=dept_mr,
                                     post=f"Assistant Commissioner ({area})", post_regional=f"सहाय्यक आयुक्त ({dept_mr})",
                                     name=name or holder or "", vacant=True if not name and not holder else None,
                                     post_vacant=True if holder else None, acting=True if holder else None, **common))
    return recs


def parse_dmc(html, url, area_map, seen=None):
    """Deputy Municipal Commissioners (zones and departments) from the same table family (not sampled live yet)."""
    seen = set() if seen is None else seen
    rows, upd = parse_table(html)
    recs = []
    for r in rows:
        name, holder_post, mr_name = person(r["name_cell"])
        dept_mr, dept_en = split_lang(r["dept_cell"])
        date_en = split_lang(r["date_cell"])[1]
        zone = zone_of(r["dept_cell"])
        codes = ward_codes_in(re.sub(r"(?i)\bzone\s*[-–.:]?\s*[IVX\d]+", " ", dept_en)) if zone else []
        wards = sorted({w for c in codes for w in (ward_area(c, area_map)[0] or [])}, key=int) or None
        area = zone or dept_en or dept_mr
        recs.append(_ward.record(MODULE, f"dmc:{r['sr']}", seen, level="zone" if zone else "body", area=area, area_regional=dept_mr,
                                 zone=zone, admin_wards=codes or None, wards=wards, post="Deputy Municipal Commissioner" +
                                 ("" if zone else f" ({area})" if area else ""), post_regional="उप आयुक्त", name=name,
                                 name_regional=mr_name, holder_post=holder_post or None, since=iso(r["date_cell"]),
                                 charge=date_en if re.search(r"(?i)charge", date_en) else None, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, source=url, last_updated=upd, sr=r["sr"], role="head",
                                 wing="administration", vacant=True if not name else None))
    return recs


def fetch(p, get):
    files = []
    areas_url = p.get("areas_url", AREAS_URL)
    a = get(areas_url) if areas_url else None
    area_map = areas(a.content) if a is not None else {}
    r = get(p["url"], headers=UA)
    if r is None:
        return [], files, "no answer from the portal"
    html = r.text
    if "not compatible with your browser" in html and "RecTable" not in html:
        return [], files, "portal error page (browser check)"
    name = "dmc" if "DeputyMC" in p["url"] else "ac"
    files.append(_esw.keep(MODULE, name, r.content))
    recs = (parse_dmc if name == "dmc" else parse_ac)(html, p["url"], area_map)
    why = "" if recs else "no officer table"
    if recs and not area_map:
        why = "no prabhag layer (wards left out)"
    return recs, files, why
