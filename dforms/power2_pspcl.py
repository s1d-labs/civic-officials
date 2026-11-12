"""Punjab: PSPCL (Punjab State Power Corporation Ltd) heads of offices, www.pspcl.in/Otherlinks/Contact-Hods.aspx (one page, one queue
item). About 35 tables; each starts with a one-cell title row (an organisation: "CHIEF ENGINEER/DS (NORTH), JALANDHAR", or a circle:
"DISTRIBUTION CIRCLE, JALANDHAR") followed by post rows: Post [e-mail] | Landline (with (R) = residence, Fax) | Mobile, or Post |
Landline | Mobile | E-mail (Hydel), or an empty first cell. Further one-cell rows start a new office inside the same table.
No officer names: the page gives posts only (CE, Dy.CE = circle head, Addl.SE / ASE = division, AEE, P.S., P.A. ...). About 400 posts:
5 distribution zones (CE/DS North, Central, West, South, Border), their ~25 distribution circles, and the HQ organisations
(enforcement, P&M, metering, IT, hydel and thermal plants, finance, audit ...).
Sub-division (AEE / SDO) contacts are in the PIO list and the office hierarchy PDF: dforms/power2_pspcl_offices.py reads them
("List-of-Offices.doc", old Word format, is not read). Level from the office title: DS zone -> zone,
circle -> circle, "Divn" -> division, else state. Records "dept:power2_pspcl:<office>:<post>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power
from dforms._power import tr_pos

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_pspcl"
URL = "https://www.pspcl.in/Otherlinks/Contact-Hods.aspx"
CITIES = ("Amritsar", "Jalandhar", "Ludhiana", "Bathinda", "Patiala", "Mohali", "Sangrur", "Barnala", "Faridkot", "Ferozepur",
          "Hoshiarpur", "Kapurthala", "Gurdaspur", "Pathankot", "Tarn Taran", "Ropar", "Roopnagar", "Khanna", "Moga", "Muktsar",
          "Nawanshahr", "Mansa", "Anandpur Sahib", "Lehra Mohabbat", "Fatehgarh Sahib", "Malerkotla", "Fazilka")


def items(get=None):
    return [{"key": f"{MODULE}:hods", "payload": {"reader": MODULE, "url": URL, "state": "PB", "india_only": False}}]


def office_level(title):
    t = title.upper()
    if re.search(r"\bDIV(N|ISION)?\b", t):
        return "division"
    if re.search(r"CIRCLE", t):
        return "circle"
    if re.search(r"/\s*DS\b|DS\s*\(|\bOP\.?\s*\(|\(SOUTH\)|\(NORTH\)|\(WEST\)|\(CENTRAL\)|BORDER", t):
        return "zone"
    return "state"


def district(title):
    for c in CITIES:
        if re.search(r"\b" + c.upper() + r"\b", title.upper()):
            return {"Ropar": "Rupnagar", "Roopnagar": "Rupnagar", "Pta": "Patiala"}.get(c, c)
    if re.search(r"\bPTA\b", title.upper()):
        return "Patiala"
    if re.search(r"\bLDH\b", title.upper()):
        return "Ludhiana"
    return None


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    out = _power.Out(MODULE, "PB", url, discom="PSPCL")
    for tb in soup.find_all("table"):
        org, office = None, None
        for tr in tb.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = [x for x in _power.cells(tr)]
            if not any(c):
                continue
            filled = [x for x in c if x]
            if len(filled) == 1 and not re.search(r"\d{5,}", filled[0]):
                office = filled[0]
                org = org or office
                continue
            if not office:
                continue
            if c and not c[0] and len(c) >= 4:
                c = c[1:]
            post_cell = c[0]
            mails = _power.email(" ".join(c))
            post = _power.clean(_power.EMAIL.sub("", re.sub(r"\s*@\s*", "@", post_cell)).strip(" ,"))
            if not post:
                continue
            land = c[1] if len(c) > 1 else ""
            mob = c[2] if len(c) > 2 else ""
            nums = [x for x in re.split(r",\s*|\s{2,}|\s+(?=9\d{4}[- ]?\d{5})", f"{mob}, {land}") if re.search(r"\d{4}", x)]
            lvl = office_level(office)
            par = {"zone": org} if org and org != office and lvl in ("circle", "division") else None
            out.add(f"{office}:{post}", lvl, office, post=post, phone_=_power.phone(*nums), email_=mails,
                    district=district(office) or district(org or ""), parents=par)
    out.src = {}
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_power.raw(MODULE, "hods", r.content, "html")], "" if recs else "no rows"
