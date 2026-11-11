"""Gujarat: Sub-Registrar offices and the villages / town wards in each office's jurisdiction, from the "List of sub registrar
office" workbook of the Revenue Department's GARVI portal (garvi.gujarat.gov.in/Download/HelpFile/gARVI_SRO_Office_list.xlsx).
India only. One GET of one XLSX (about 1 MB, one sheet, 20,245 rows). Columns: A district (Gujarati), B SRO name (Gujarati),
C office address (English), D address (Gujarati), E village or ward (English), F village or ward (Gujarati), G remarks. A and B are
filled only on the first row of an office (merged cells): carried down. About 300 offices. No phone, email or officer names.
Read with the standard library (zipfile + ElementTree); no spreadsheet package. The workbook shows no date.
Record ids: dept:sro_gj:GJ-SRO-<district slug>-<first 10 hex of sha1 of the SRO name>.
"""
import hashlib
import re
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from dforms import _esw

MODULE = "sro_gj"
URL = "https://garvi.gujarat.gov.in/Download/HelpFile/gARVI_SRO_Office_list.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
# district cells as the sheet spells them (Gujarati, short forms, English, one in a legacy font) -> district name
DIST = {"પંચમહાલ": "Panchmahal", "અરવલ્લી": "Aravalli", "VZJ<,L": "Aravalli", "પોરબંદર": "Porbandar", "ભરૂચ": "Bharuch",
        "DEV BHUMI-DWARKA": "Devbhumi Dwarka", "દેવભૂમિ-દ્રારકા": "Devbhumi Dwarka", "દેવભૂમિ દ્રારકા": "Devbhumi Dwarka",
        "મોરબી": "Morbi", "ગાંધીનગર": "Gandhinagar", "મહેસાણા": "Mehsana", "પાટણ": "Patan", "બોટાદ": "Botad",
        "સુરેન્દ્રનગર": "Surendranagar", "સુ.નગર": "Surendranagar", "વલસાડ": "Valsad", "SABARKANTHA": "Sabarkantha",
        "સાબરકાંઠા": "Sabarkantha", "સા.કા": "Sabarkantha", "ભાવનગર": "Bhavnagar", "તાપી": "Tapi", "કચ્છ": "Kachchh",
        "કચ્છ-ભુજ": "Kachchh", "ગીર સોમનાથ(વેરાવળ)": "Gir Somnath", "જૂનાગઢ": "Junagadh", "જુનાગઢ": "Junagadh",
        "ખેડા-નડીયાદ": "Kheda", "સુરત": "Surat", "મહીસાગર": "Mahisagar", "છોટાઉદેપુર": "Chhota Udaipur", "NAVSARI": "Navsari",
        "રાજકોટ": "Rajkot", "અમરેલી": "Amreli", "અમદાવાદ": "Ahmedabad", "અમદાવદ": "Ahmedabad", "નર્મદા": "Narmada",
        "NARMADA": "Narmada", "આણંદ": "Anand", "જામનગર": "Jamnagar", "દાહોદ": "Dahod", "વડોદરા": "Vadodara",
        "બનાસકાઠા": "Banaskantha", "બનાસકાંઠા": "Banaskantha"}
OFFICE_WORDS = re.compile(r"(સબ[\s.-]*રજીસ્[^\s,]*\s*(કચેરી)?|સ\.\s*ર\.\s*(કચેરી)?|S\.?\s*R\.?\s*O\.?\s*-?|કચેરી|,)")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "GJ", "india_only": True}}]


def sheet_rows(content):
    """[{column letter: text}] of the first sheet."""
    z = zipfile.ZipFile(BytesIO(content))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        ss = ["".join(t.text or "" for t in si.iter(NS + "t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si")]
    root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    out = []
    for r in root.find(NS + "sheetData"):
        d = {}
        for c in r.findall(NS + "c"):
            col = re.match(r"[A-Z]+", c.get("r", "")).group()
            if c.get("t") == "inlineStr":
                d[col] = "".join(t.text or "" for t in c.iter(NS + "t"))
                continue
            v = c.find(NS + "v")
            if v is None or v.text is None:
                continue
            d[col] = ss[int(v.text)] if c.get("t") == "s" else v.text
        out.append({k: v for k, v in d.items() if _esw.clean(v)})
    return out


def district(cell):
    c = _esw.clean(cell)
    if c in DIST:
        return DIST[c]
    first = c.split(" ")[0] if c else ""
    return DIST.get(first, c)


def short(name):
    """The place in an office name: "સ.ર.કચેરી અંકલેશ્વર" -> "અંકલેશ્વર", "S.R.O - KALYANPUR" -> "KALYANPUR"."""
    s = _esw.clean(OFFICE_WORDS.sub(" ", name)).strip(" -")
    return s or _esw.clean(name)


def parse(content, url=URL):
    rows = sheet_rows(content)
    offices, cur, dist_cell = [], None, ""
    for d in rows:
        if any("સ.ર.કચેરીનું" in (v or "") for v in d.values()):
            continue                                    # header row
        if d.get("A"):
            dist_cell = d["A"]
        b = _esw.clean(d.get("B"))
        if b and (cur is None or b != cur["name"] or district(dist_cell) != cur["district"]):
            cur = {"name": b, "district": district(dist_cell), "address": _esw.clean(d.get("C")), "address_gu": _esw.clean(d.get("D")),
                   "villages": []}
            offices.append(cur)
        if cur is None:
            continue
        if not cur["address"] and d.get("C"):
            cur["address"] = _esw.clean(d["C"])
        if not cur["address_gu"] and d.get("D"):
            cur["address_gu"] = _esw.clean(d["D"])
        en, gu = _esw.clean(d.get("E")).rstrip(". "), _esw.clean(d.get("F"))
        if en or gu:
            v = {k: x for k, x in (("en", en), ("gu", gu), ("note", _esw.clean(d.get("G")))) if x}
            cur["villages"].append(v)
    recs, seen = [], set()
    for o in offices:
        h = hashlib.sha1(o["name"].encode()).hexdigest()[:10]
        oid = f"GJ-SRO-{_esw.slug(o['district']) or 'x'}-{h}"
        if oid in seen:                                 # the same office listed again further down: add its villages
            prev = next(r for r in recs if r[0] == f"dept:{MODULE}:{oid}")
            prev[1].setdefault("villages", []).extend(o["villages"])
            prev[1]["village_count"] = len(prev[1]["villages"])
            continue
        seen.add(oid)
        place = short(o["name"])
        recs.append(_esw.record(MODULE, oid, dept="registration", level="subdistrict", area=place, area_regional=place,
                                post="Sub Registrar", office_regional=o["name"], address=o["address"], address_regional=o["address_gu"],
                                state="GJ", district=o["district"], office_id=oid, villages=o["villages"],
                                village_count=len(o["villages"]), source=url))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "gARVI_SRO_Office_list", r.content, "xlsx")]
    try:
        recs = parse(r.content, p.get("url", URL))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
        return [], files, f"not a readable xlsx: {type(e).__name__}"
    return recs, files, "" if recs else "no rows"
