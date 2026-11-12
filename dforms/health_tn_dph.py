"""Tamil Nadu: Deputy Directors of Health Services (DDHS, head of each of the 45 health unit districts, HUD) from the
Directorate of Public Health and Preventive Medicine (DPH&PM): "Telephone/Fax/ Mobile numbers of Deputy Directors of Health
Services", tnhealth.tn.gov.in/tngovin/dph/notification/2021-22/distdec2021.pdf (66 KB, 2 pages, text layer; PDF made 2022-03-05).
The DPH page tnhealth.tn.gov.in/tngovin/dph/dphpm.php still links it as "List of Officers at District Level" (2026-11-12).
The list is old (Dec 2021): records carry last_updated 2021-12 and the reader of the site should check them.
The newer DPH site www.tndphpm.com is an Angular page whose contact API (live.tndphpm.com/admin/api/contacts) needs a key from the
page's code: not used.

Columns (x of the header words): Sl.No | District (the HUD: Aranthangi, Athur, Koilpatti, Palani ... besides the revenue
districts) | Name of the Deputy Director of Health Services | Office Tele.No | Office Fax No | Mobile No. Cells wrap and are centred on the
serial line: a column that has text on the serial line is read from that line only; an empty one from the lines just above and
below (Coimbatore's phones, Tenkasi's and Mayiladuthurai's names). Notes printed on a neighbour line of a filled cell ("Vacant,
Dr. S.Chitrasena," above Kancheepuram) are therefore not read.

Records (depts.py contract): dept health, level district, area = the HUD, district = the LGD revenue district of the HUD,
post "Deputy Director of Health Services", name (with "(i/c)" and the in-charge note as printed; "Vacant" -> vacant=true),
phone = mobile, office phone and fax (fax also in "fax"). Ids dept:health_tn_dph:ddhs:<slug of HUD>. src_pos = page + line of
the serial number. archive.s1d.me has the file (vantage IN-proxy, 2026-11-06); the host answers only Indian addresses (unchecked
from abroad).
"""
import re

import provenance
from dforms import _esw, _field

METHOD = "pdf text (pdftotext -layout, else pypdf layout): rows by serial number, columns by the x of the header words"

MODULE = "health_tn_dph"
URL = "https://tnhealth.tn.gov.in/tngovin/dph/notification/2021-22/distdec2021.pdf"
LIST_DATE = "2021-12"
# health unit district -> LGD revenue district (2024)
HUD = {
    "aranthangi": "Pudukkottai", "ariyalur": "Ariyalur", "athur": "Salem", "attur": "Salem", "chengalpat": "Chengalpattu",
    "chengalpattu": "Chengalpattu", "cheyyar": "Tiruvannamalai", "coimbatore": "Coimbatore", "cuddalore": "Cuddalore",
    "dharmapuri": "Dharmapuri", "dindigul": "Dindigul", "erode": "Erode", "kallakurichi": "Kallakurichi",
    "kancheepuram": "Kancheepuram", "karur": "Karur", "koilpatti": "Thoothukkudi", "kovilpatti": "Thoothukkudi",
    "krishnagiri": "Krishnagiri", "madurai": "Madurai", "nagapattinam": "Nagapattinam", "nagercoil": "Kanniyakumari",
    "namakkal": "Namakkal", "nilgiris": "The Nilgiris", "palani": "Dindigul", "paramakudi": "Ramanathapuram",
    "perambalur": "Perambalur", "poonamallee": "Thiruvallur", "pudukottai": "Pudukkottai", "pudukkottai": "Pudukkottai",
    "ramnad": "Ramanathapuram", "ramanathapuram": "Ramanathapuram", "salem": "Salem", "tenkasi": "Tenkasi",
    "sivaganga": "Sivaganga", "sivakasi": "Virudhunagar", "thanjavur": "Thanjavur", "theni": "Theni",
    "tiruchirapalli": "Tiruchirappalli", "tiruchirappalli": "Tiruchirappalli", "tirunelveli": "Tirunelveli",
    "tirupathur": "Tirupathur", "tiruppur": "Tiruppur", "tiruvallur": "Thiruvallur", "tiruvannamalai": "Tiruvannamalai",
    "tiruvarur": "Thiruvarur", "tuticorin": "Thoothukkudi", "thoothukudi": "Thoothukkudi", "vellore": "Vellore",
    "villupuram": "Viluppuram", "viluppuram": "Viluppuram", "virudhunagar": "Virudhunagar", "ranipet": "Ranipet",
    "mayiladuthurai": "Mayiladuthurai", "chennai": "Chennai",
}
SERIAL = re.compile(r"^(\s{0,3})(\d{1,2})(?=\s+\S)")
MOBILE = re.compile(r"^(?:\+?91)?[6-9]\d{9}$")


def cols(lines):
    """x where the name, office phone, fax and mobile columns start (from the header words)."""
    x = {"name": 23, "tele": 57, "fax": 73, "mobile": 89}
    for ln in lines:
        for key, rx in (("name", r"Name of the Deputy"), ("fax", r"Office Fax"), ("mobile", r"Mobile No"), ("tele", r"Tele\.?\s*No")):
            m = re.search(rx, ln)
            if m:
                x[key] = m.start() - (2 if key in ("name", "tele") else 0)
    return x


def parse(text, url=URL):
    recs, seen = [], set()
    for pno, page in enumerate(text.split("\f"), 1):
        lines = page.split("\n")
        x = cols(lines)
        kinds = []
        for ln in lines:
            if not ln.strip():
                kinds.append("blank")
            elif re.search(r"(?i)^\s*(sl\.?n|o\s*$)|name of the deputy|office fax|tele\.?no|directorate of|telephone/fax|^\s*district\s", ln):
                kinds.append("head")
            elif SERIAL.match(ln):
                kinds.append("serial")
            else:
                kinds.append("text")
        for s, k in enumerate(kinds):
            if k != "serial":
                continue
            sn = SERIAL.match(lines[s]).group(2)
            per_line = {}
            for i in (s - 1, s, s + 1):
                if 0 <= i < len(lines) and (i == s or kinds[i] == "text"):
                    ln = lines[i] if i != s else " " * len(SERIAL.match(lines[s]).group(0)) + lines[s][len(SERIAL.match(lines[s]).group(0)):]
                    got = {}
                    for m in re.finditer(r"\S+(?: \S+)*", ln):
                        c = m.start()
                        col = ("district" if c < x["name"] else "name" if c < x["tele"] - 1 else "tele" if c < x["fax"] - 2
                               else "fax" if c < x["mobile"] - 2 else "mobile")
                        got.setdefault(col, []).append(m.group())
                    per_line[i] = got
            # a column filled on the serial line is read from that line only; an empty one from the lines just above and below
            # (cells of 2-3 lines are centred on the serial line)
            cell = {}
            for col in ("district", "name", "tele", "fax", "mobile"):
                own = per_line.get(s, {}).get(col)
                cell[col] = own if own else [w for i in (s - 1, s + 1) for w in per_line.get(i, {}).get(col, [])]
            hud = _esw.clean(" ".join(cell["district"]))
            name = _esw.clean(" ".join(cell["name"]))
            if not hud:
                continue
            district = HUD.get(hud.lower())
            vacant = bool(re.match(r"(?i)vacant", name))
            nums = {k: " ".join(cell[k]) for k in ("tele", "fax", "mobile")}
            phone = _esw.phones(nums["mobile"], nums["tele"])
            fax = _esw.phones(re.sub(r"(?i)fax", " ", nums["fax"] + (" " + nums["tele"] if "FAX" in nums["tele"].upper() else "")))
            key = f"ddhs:{_esw.slug(hud)}"
            if key in seen:
                key += f"-{sn}"
            seen.add(key)
            recs.append(_esw.record(
                MODULE, key, dept="health", level="district", area=f"{hud} Health Unit District", post="Deputy Director of Health Services",
                name=name or None, vacant=True if vacant else None, phone=phone or None, fax=fax or None, state="TN",
                district=district, hud=hud, office_phone=nums["tele"] or None, mobile=nums["mobile"] or None,
                last_updated=LIST_DATE, source=url, src_url=url, list_no=sn,
                src_pos=provenance.line_pos(pno, s + 1, lines[s]),
                list_title="Telephone/Fax/ Mobile numbers of Deputy Directors of Health Services (DPH&PM)"))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:ddhs", "payload": {"reader": MODULE, "url": URL, "state": "TN", "india_only": True, "route": "proxy", "expected": 45}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    text, engine = _field.pdf_text_engine(r.content)
    recs = parse(text, url)
    for _, d in recs:
        d["method"] = f"pdf text ({engine}): rows by serial number, columns by the x of the header words"
    return recs, [(f"depts/{MODULE}/ddhs-list.pdf", r.content, "application/pdf")], "" if recs else "no rows"
