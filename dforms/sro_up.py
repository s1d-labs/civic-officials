"""Uttar Pradesh: all Sub-Registrar offices (about 384) from the Stamp and Registration Department's officer list,
igrsup.gov.in/prernadoc/Adhiniyam/ContactUs/Contacts/officers_Name_No.pdf (linked from /igrsup/contactUs). Answers from Germany and
India. One GET of one 21-page Hindi PDF. Columns: क्रम सं., मण्डल (division), उप महानिरीक्षक निबंधन (DIG) + CUG, जनपद (district),
सहायक महानिरीक्षक निबंधन (AIG) + CUG, उप निबंधक कार्यालय (office), उप निबंधक का नाम (sub-registrar), मोबाइल, कार्यालय पता (address).
The PDF's font has a broken text map: the extracted text puts the i-matra before its consonant, writes conjuncts as Latin letters
(Ĥ = प्र, Û = न्, ¢ = क्ष ...) and the reph as "[". legacy() turns it back into normal Devanagari (map below, checked on the
names of this file). Each office is the line that carries the sub-registrar's mobile (the last 10-digit number on the line); the
DIG and AIG (with their CUG numbers) stand on the first line of their group. One record per office (level subdistrict); one per
DIG (division) and per AIG (district). "प्रभारी" in the name column = no regular holder (in charge). Names are in Hindi only
(name and name_regional carry the same text).
The PDF shows no date. Record ids: dept:sro_up:UP-SRO-<row no>, dept:sro_up:UP-DIG-<cug>, dept:sro_up:UP-AIG-<cug>.
"""
import re

import provenance
from dforms import _esw

METHOD = "pdf text (pypdf layout) + Devanagari font map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_up"
URL = "https://igrsup.gov.in/prernadoc/Adhiniyam/ContactUs/Contacts/officers_Name_No.pdf"

# legacy glyphs -> Devanagari (the i-matra variants and the reph are handled in legacy())
MAP = {"ȣ": "ी", "Ȥ": "ी", "ȧ": "ी", "Û": "न्", "Ö": "ण्", "à": "म्", "è": "स्", "ç": "ष्", "æ": "श्", "É": "ख्", "Ú": "ध्",
       "ã": "ल्", "Ü": "प्", "Ý": "फ्", "È": "क्", "×": "त्", "Þ": "ब्", "Ï": "ज्", "á": "य्", "å": "व्", "Í": "च्", "Ê": "ग्",
       "Ø": "थ्", "Ĩ": "म्र", "ɬ": "ड्", "ɪ": "ट्", "ɮ": "द्", "ƣ": "त्त", "ġ": "द्र", "ğ": "त्र", "Ě": "ट्र", "Ē": "ग्र", "Ĥ": "प्र",
       "Į": "श्र", "Ħ": "ब्र", "ħ": "भ्र", "ĕ": "च", "¢": "क्ष", "£": "ज्ञ", "Đ": "क्र", "Ǿ": "रु", "ǽ": "रु", "Ʌ": "ें", "ɇ": "ैं",
       "ɉ": "ों", "‚": ",", "⁄": "/", "◌": ""}
IMATRA = "ǓͧͪǐǑǒͩͬͫͨͯ"
C = "[क-हक़-य़]़?"
CL = f"{C}(?:्{C})*"
AK = f"{CL}[ा-ौँ-ःॢॣ]*"
MOBILE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
INCHARGE = "प्रभारी"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "UP"}}]


def legacy(s):
    """Text from this PDF's broken font map -> Devanagari."""
    for k in IMATRA:
        s = s.replace(k, "ि")
    for k, v in MAP.items():
        s = s.replace(k, v)
    s = re.sub(f"ि({CL})", r"\1" + "ि", s)            # i-matra after its consonant cluster
    s = re.sub(f"({CL})ȶ", "र्" + r"\1" + "े", s)           # ȶ = e-matra with a reph
    s = re.sub(f"({AK})\\[", "र्" + r"\1", s)                    # "[" = reph on the syllable before it
    return s.replace("द्तिीय", "द्वितीय")


def cols(line):
    """(x, text) of the cells on one line (cells are 2+ blanks apart)."""
    return [(m.start(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def parse_pages(pages, url=URL):
    lines = [legacy(l) for p in pages for l in p.split("\n")]
    # source trail: (page, line, raw text) of each line in `lines` (pages split at "\n")
    where = [(pn, ln, x) for pn, p in enumerate(pages, 1) for ln, x in enumerate(p.split("\n"), 1)]

    def lp(i):
        return provenance.line_pos(where[i][0], where[i][1], where[i][2])
    recs, offices, dig, aig = [], [], None, None
    addr_x = None
    for i, line in enumerate(lines):
        mobs = list(MOBILE.finditer(line))
        if not mobs or "क्रम" in line:
            continue
        last = mobs[-1]
        before, after = line[:last.start()], _esw.clean(line[last.end():])
        cells = cols(before)
        sr_no = None
        if cells and re.fullmatch(r"\d{1,3}", cells[0][1]) and cells[0][0] < 6:
            sr_no = int(cells.pop(0)[1])
        texts = [t for _, t in cells]
        if len(texts) < 3:
            continue
        name, office = texts[-1], texts[-2]
        mid = texts[1:-2]
        mandal = texts[0]
        # middle cells: [DIG, DIG CUG,] district [, AIG, AIG CUG]
        phones = [k for k, t in enumerate(mid) if MOBILE.fullmatch(t)]
        dist = next((t for k, t in enumerate(mid) if k not in phones and k + 1 not in phones), None)
        for k in phones:
            who, cug = (mid[k - 1] if k else ""), mid[k]
            if dist and mid.index(dist) > k:
                dig = {"name": who, "cug": cug, "mandal": mandal}
                recs.append(_esw.record(MODULE, f"UP-DIG-{cug}", dept="registration", level="division", area=mandal, area_regional=mandal,
                                        post="Deputy Inspector General (Registration)", name=who, name_regional=who, phone=cug, state="UP",
                                        office_id=f"UP-DIG-{cug}", source=url, src_pos=lp(i)))
            else:
                aig = {"name": who, "cug": cug, "district": dist}
                recs.append(_esw.record(MODULE, f"UP-AIG-{cug}", dept="registration", level="district", area=dist, area_regional=dist,
                                        post="Assistant Inspector General (Registration)", name=who, name_regional=who, phone=cug, state="UP",
                                        district=dist, office_id=f"UP-AIG-{cug}", source=url, src_pos=lp(i)))
        if after:
            addr_x = line.find(after[:6], last.end()) if addr_x is None else addr_x
        if sr_no is None:                     # the row number stands alone on the line above or below
            for j in (i + 1, i - 1):
                if 0 <= j < len(lines):
                    m = re.match(r"^\s{0,4}(\d{1,3})(?:\s|$)", lines[j])
                    if m and not MOBILE.search(lines[j]):
                        sr_no = int(m.group(1))
                        break
        offices.append({"i": i, "sr": sr_no, "mandal": mandal, "district": dist, "office": office, "name": name,
                        "mobile": last.group(1), "address": [after] if after else [], "dig": dig, "aig": aig})
    # address lines that wrap: the lines below an office line that have no mobile, text far right only
    for k, o in enumerate(offices):
        stop = offices[k + 1]["i"] if k + 1 < len(offices) else min(len(lines), o["i"] + 4)
        for j in range(o["i"] + 1, stop):
            t = lines[j]
            if not t.strip() or "क्रम" in t:
                continue
            for x, txt in cols(t):
                if addr_x and x >= addr_x - 15 and not re.fullmatch(r"\d{1,3}", txt):
                    o["address"].append(txt)
    seen = set()
    for n, o in enumerate(offices, 1):
        key = f"UP-SRO-{o['sr'] or n}"
        if key in seen:
            key = f"UP-SRO-{n}-{o['mobile']}"
        seen.add(key)
        incharge = o["name"].strip() == INCHARGE
        recs.append(_esw.record(MODULE, key, dept="registration", level="subdistrict", area=o["office"], area_regional=o["office"],
                                post="Sub Registrar", post_regional="उप निबंधक", name=None if incharge else o["name"],
                                name_regional=None if incharge else o["name"],
                                in_charge=True if incharge else None, phone=o["mobile"], address=" ".join(o["address"]),
                                state="UP", district=o["district"], division=o["mandal"], office_id=key, sr_no=o["sr"],
                                dig=(o["dig"] or {}).get("name"), aig=(o["aig"] or {}).get("name"), source=url,
                                src_pos=lp(o["i"])))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "officers_Name_No", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse_pages(pages, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
