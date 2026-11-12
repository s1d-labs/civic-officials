"""Assam: the Deputy Commissioner, Additional Deputy Commissioners, Sub-Divisional Officers (Civil), council secretaries and the food
and civil supplies officers of every district, from the PDS portal's "DC Offices" page pds.assam.gov.in/portal/dc-offices.html
(Food, Public Distribution & Consumer Affairs Department). Answers only from India; the server does not send its intermediate
certificate (GoDaddy Secure CA - G2: certs/godaddy_secure_ca_g2.pem completes the chain, verification stays on).

One GET (about 320 KB, saved 2026-11-11): "Statewise All District List", one <h5> "District - NAME" per district, then one card per
officer (name, designation, email, mobile, office phone, office address, PIN). 35 districts, about 290 officers. The district
portals (*.assam.gov.in) and the CEO site time out from every route, so this page is the one public list of Assam's DCs with phones.
Designations: Deputy Commissioner / Additional Deputy Commissioner / District Development Commissioner / Principal Secretary and
Secretary of the autonomous councils (BTC, KAAC, NCHAC) -> dept administration, level district; Sub-Divisional Officer(C) ->
administration, level subdivision (area = the sub-division in the office address); the FCS&CA officers (Joint / Deputy / Assistant
Director, Superintendent, Inspector, Sub-Inspector) -> dept food_supplies. Phones "(+91)0000000000" are left out. The page shows no date.
District names go to the LGD spelling (KARIMGANJ -> Sribhumi, N. C. HILLS -> Dima Hasao, SIVSAGAR -> Sivasagar ...): district().
Record ids: dept:sub_as:AS-<district slug>:<designation slug>[:<name slug>] (the name only where a district has two of that post).
"""
import html as _html
import re

from dforms import _esw

METHOD = "html cards (label / value divs under <h5> headings)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_as"
URL = "https://pds.assam.gov.in/portal/dc-offices.html"

# LGD district names of Assam (lgd.districts, state 18), keyed by letters only, plus the spellings that the state's sites use.
LGD = ["Bajali", "Baksa", "Barpeta", "Biswanath", "Bongaigaon", "Cachar", "Charaideo", "Chirang", "Darrang", "Dhemaji", "Dhubri",
       "Dibrugarh", "Dima Hasao", "Goalpara", "Golaghat", "Hailakandi", "Hojai", "Jorhat", "Kamrup", "Kamrup Metro", "Karbi Anglong",
       "Kokrajhar", "Lakhimpur", "Majuli", "Marigaon", "Nagaon", "Nalbari", "Sivasagar", "Sonitpur", "South Salmara Mancachar",
       "Sribhumi", "Tamulpur", "Tinsukia", "Udalguri", "West Karbi Anglong"]
ALIAS = {"nchills": "Dima Hasao", "northcacharhills": "Dima Hasao", "haflong": "Dima Hasao", "karimganj": "Sribhumi",
         "sivsagar": "Sivasagar", "sibsagar": "Sivasagar", "southsalmara": "South Salmara Mancachar",
         "southsalamara": "South Salmara Mancachar", "southsalmaramankachar": "South Salmara Mancachar", "morigaon": "Marigaon",
         "kamrupm": "Kamrup Metro", "kamrupmetropolitan": "Kamrup Metro", "kamruprural": "Kamrup", "kamrupr": "Kamrup",
         "tezpur": "Sonitpur", "silchar": "Cachar", "mangaldoi": "Darrang", "diphu": "Karbi Anglong"}
_KEY = {re.sub(r"[^a-z]", "", d.lower()): d for d in LGD}

ADMIN = ("deputy commissioner", "additional deputy commissioner", "district development commissioner", "principal secretary",
         "secretary", "sub-divisional officer")


def district(name):
    """LGD spelling of an Assam district name as the state's sites write it ("KAMRUP METRO", "Kamrup (M)", "N.C. Hills",
    "Nagaon(Attached)"); the name in title case when it is not known."""
    s = re.sub(r"\((attached|pt\.?)\)", "", _esw.clean(name), flags=re.I)
    s = re.sub(r"^\s*(district\s*-\s*|d\.?\s*c\.?\s+)", "", s, flags=re.I)
    k = re.sub(r"[^a-z]", "", s.lower())
    return _KEY.get(k) or ALIAS.get(k) or s.strip().title()


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "AS", "india_only": True}}]


def _phone(v):
    v = re.sub(r"\(\+91\)", "", v or "").strip()
    return "" if not re.sub(r"[0\D]", "", v) else v


def _subdivision(address):
    """The sub-division of an SDO (Civil) office from its address: "SDO CIVIL | NORTH SALMARA | ABHAYAPURI" -> NORTH SALMARA,
    "Office of the SDO Civil Kaliabor | Food and Civil Supply Branch" -> Kaliabor."""
    parts = [p.strip(" ,.") for p in address.split("|") if p.strip(" ,.")]
    skip = re.compile(r"(?i)office|\bsdo\b|s\.d\.o|civil|branch|fcs|food|supply|^dist|p\.?\s?o\b|assam|district|^\d")
    for p in parts[1:]:
        if not skip.search(p):
            return p
    m = re.search(r"(?i)(?:sdo|officer)[\s,]*(?:\(?civil\)?)?[\s,]+([a-z][a-z .-]+)$", parts[0] if parts else "")
    return m.group(1).strip() if m else ""


def cards(html, where=None):
    """[(district as the page writes it, {label: value})] for every officer card, in page order. where: a list; when given, it
    gets the src_pos of each card: {"selector": "h5", "h5": n} = the card's block follows the n-th <h5> after the list title."""
    i = html.find("Statewise All District List")
    parts = re.split(r"<h5>(.*?)</h5>", html[i:] if i >= 0 else html, flags=re.S)
    out, dist = [], ""
    for k in range(1, len(parts), 2):
        h = _esw.clean(_html.unescape(re.sub(r"<[^>]+>", " ", parts[k])))
        if h:
            dist = re.sub(r"(?i)^district\s*-\s*", "", h)
        f = {}
        for label, val in re.findall(r'<div class="col">\s*([^<]*?)\s*</div>\s*<div class="col fw-bold">(.*?)</div>', parts[k + 1], re.S):
            val = _html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?i)<br\s*/?>", " | ", val)))
            f[_esw.clean(label)] = re.sub(r"(\s*\|\s*)+", " | ", _esw.clean(val)).strip(" |")
        if f.get("Name of the Officer") or f.get("Designation"):
            out.append((dist, f))
            if where is not None:
                where.append({"selector": "h5", "h5": (k + 1) // 2})
    return out


def parse(html, url=URL):
    where = []
    rows = cards(html, where)
    count = {}
    for dist, f in rows:
        k = (dist, _esw.slug(f.get("Designation", "")))
        count[k] = count.get(k, 0) + 1
    recs, seen = [], set()
    for (dist, f), pos in zip(rows, where):
        desig = _esw.clean(f.get("Designation", "")).strip(" ,")
        name = _esw.clean(f.get("Name of the Officer", ""))
        d = district(dist)
        dslug = _esw.slug(desig)
        base = f"AS-{_esw.slug(d)}:{dslug}"
        if count[(dist, dslug)] > 1:
            base += ":" + _esw.slug(name)
        key, n = base, 2
        while key in seen:
            key, n = f"{base}:{n}", n + 1
        seen.add(key)
        low = desig.lower()
        admin = low.startswith(ADMIN)
        level, area = "district", d
        if low.startswith("sub-divisional officer"):
            level, area = "subdivision", _subdivision(f.get("Office Address", ""))
        addr = f.get("Office Address", "").replace(" | ", ", ")
        if f.get("PIN"):
            addr = f"{addr} - {f['PIN']}" if addr else f["PIN"]
        rec = _esw.record(MODULE, key, dept="administration" if admin else "food_supplies", level=level, area=area, post=desig,
                          designation=desig, name=name, phone=_esw.phones(_phone(f.get("Contact Number (M)")),
                                                                         _phone(f.get("Phone Number (O)"))),
                          email=_esw.emails(f.get("Email Id", "")), address=addr, district=d, state="AS", source=url,
                          src_pos=pos)
        if rec[1].get("name") or rec[1].get("phone") or rec[1].get("email"):
            recs.append(rec)
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "dc-offices", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
