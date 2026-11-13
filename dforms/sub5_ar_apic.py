"""Arunachal Pradesh: block, circle and sub-division officers from the PIO list of the Arunachal Pradesh Information Commission
(apic.arunachal.gov.in/pio-list): the First Appellate Authority (FAA), Public Information Officer (PIO) and Assistant PIO of every
public office that has sent its RTI officers to the Commission. Answers from Germany (archive capture of 2026-11-05 from
dev-vps-2) and from India (pool captures 2026-11-06..13). One page, one HTML table, 527 rows on 2026-11-13, no paging.

Columns: Sl. NO. | DEPARTMENT | FAA | PIO | APIO | CONTACT | EMAIL. Offices write their own rows, so the cells are free text:
"Shri Likha Radh, ADC, Pania PIO Department: GA Mobile: 84148461239 Email: ... Address: O/o ADC, Pania" or
"Talom Nalo, BDO, 7085679399, dapocdblock@gmail.com" or only "Circle Officer(GA) Email id:pemiya09@gmail.com".
The reader keeps the people of the FAA / PIO / APIO / CONTACT / EMAIL cells whose post is a sub-district post:
  BDO / Block Development Officer            -> dept rural_development, level block
  CO / Circle Officer, EAC / Extra Assistant Commissioner / Assistant Commissioner
                                             -> dept administration, level subdistrict (in Arunachal the LGD sub-districts
                                                are the administrative circles; an EAC or a CO heads a circle)
  ADC / Additional Deputy Commissioner, SDO / Sub-Divisional Officer
                                             -> dept administration, level subdivision
  "CO cum BDO" gives two records (circle and block). A PIO cell without a post in a row whose DEPARTMENT cell is a BDO office
  ("BDO, Lada, Block" | "Shri Tiwan Dolo, email, phone") is that BDO (post_from "department cell").
  A person with no phone and no e-mail in the cell takes the row's CONTACT / EMAIL columns when the row has one PIO only.
Rows of forest, works, power, water, industries, tourism and similar offices are left out (their "Circle", "EAC" and "SDO" are
not civil posts): provenance.filtered("not a block / circle / sub-division office"); so are rows without such a post.
A cell part without name, phone and e-mail ("Circle Officer, Longding HQ") is counted as skipped ("no name or contact").
The same person repeated in many rows (the Tezu CO is APIO of 6 offices) gives one record (first row).

Place: the words after the post ("ADC, Pania" -> Pania; "BDO, Ziro-I CD, Block" -> Ziro-I), else the place in the DEPARTMENT
cell ("Department RD-Yangte" -> Yangte; "Department: Rural Development,Niausa CD Block,Longding District" -> Niausa).
LGD: the place is matched to the Arunachal sub-districts (CO, EAC, ADC, SDO) or blocks (BDO) of dforms/sub5_ar_lgd.json
(civic.subdistrict and lgd.blocks, state 12) after removing "HQ", "ADC", "Circle", "SDO", "EAC", "CD", "Block"; a single
match gives district, district_code and subdistrict_code / lgd_block_code (the loader ties them by code).
Record ids: dept:sub5_ar_apic:<row no>:<column>:<kind>[:n]. One queue item = 1 GET (about 380 KB).
"""
import json
import re
from pathlib import Path

from dforms import _esw
import provenance

METHOD = "html table (APIC PIO list; free-text cells read by post words)"     # source trail (provenance.py)

MODULE = "sub5_ar_apic"
URL = "https://apic.arunachal.gov.in/pio-list"
COLS = ["sno", "department", "faa", "pio", "apio", "contact", "email"]
NOT_CIVIL = re.compile(r"(?i)forest|\bpwd\b|public works|power|electric|\bphe\b|water|\brwd\b|rural works|works division|"
                       r"industr|touris|transport|health|education|school|police|excise|tax|trade|agricultur|veterinar|"
                       r"\bplanning\b|election|information|\bipr\b|panchayati raj|\bdpdo\b|economics|statistic|sports|labour|"
                       r"\bccf\b|conservator")
# kind -> (dept, level, post as the reader writes it); order: the specific posts first
# abbreviations in capitals only ("co" is also in "yahoo.co.in"); e-mail addresses are removed before the search
KINDS = [
    ("co_bdo", re.compile(r"\bC\.?O\.?\s*-?\s*(?i:cum)\s*-?\s*B\.?D\.?O\b")),
    ("bdo", re.compile(r"\bB\.?D\.?O\b|(?i:block development officer)")),
    ("adc", re.compile(r"\bA\.?D\.?C\b|(?i:addi?t?i?onal\s+deputy\s+commissioner|addl\.?\s*dy\.?\s*commissioner)")),
    ("sdo", re.compile(r"\bS\.?D\.?O\b(?!\s*/)|(?i:sub[- ]?divisional officer)")),
    ("eac", re.compile(r"\bE\.?A\.?C\b|(?i:extra\s+ass(?:istan)?t\.?\s+commissioner|\basstt?\.?\s*commissioner|\bassistant\s+commissioner)")),
    ("co", re.compile(r"\bC\.?O\b(?![-\s]*(?i:cum))|(?i:circle officer)")),
]
EMAIL_TEXT = re.compile(r"(?i)(?:e-?mail\s*(?:id)?\s*[:;]?\s*)?[\w.+-]+\s*@\s*[\w-]+(?:\.[\w-]+)+")
POST = {"bdo": ("rural_development", "block", "Block Development Officer"),
        "co": ("administration", "subdistrict", "Circle Officer"),
        "eac": ("administration", "subdistrict", "Extra Assistant Commissioner"),
        "adc": ("administration", "subdivision", "Additional Deputy Commissioner"),
        "sdo": ("administration", "subdivision", "Sub-Divisional Officer")}
STOP = re.compile(r"(?i)\b(?:PIO|APIO|FAA|Department|Mobile|Email|E-mail|Address|Contact|Ph|Phone|Assistant|Public|Officer|"
                  r"cum|i/c)\b|[\d@:|]")
DEPT_WORDS = re.compile(r"(?i)\b(?:departe?ment|deptt?|dept|of|the|office|o/o|ga|rd|rural|development|cd|c\.d|block|blocks|"
                        r"district|administra\w*|general|bdo|circle|officer|additional|addl|deputy|dy|commiss\w*|dc|adc|eac|sdo|co|"
                        r"arunachal|pradesh|a\.p|hq|ind|independent|and|&)\b\.?")
LGD_NOISE = re.compile(r"(?i)\b(?:hq|h\.q|adc|circle|sdo|eac|cd|block|sub[- ]?division|headquarters?|sadar)\b")
DISTRICT_WORDS = re.compile(r"(?i)\b(?:east|west|upper|lower|siang|kameng|subansiri|valley|dibang|kurung|kumey|papum|pare|"
                            r"changlang|tirap|longding|lohit|anjaw|namsai|tawang|kra|daadi|kamle|leparada|shi[- ]yomi|"
                            r"pakke|kessang|keyi|panyor|bichom|lepa\s*rada)\b")
_LGD = None


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "AR"}}]


def _key(s):
    return re.sub(r"[^a-z]", "", LGD_NOISE.sub(" ", (s or "").lower()))


def lgd():
    global _LGD
    if _LGD is None:
        d = json.loads((Path(__file__).resolve().parent / "sub5_ar_lgd.json").read_text())
        _LGD = {}
        for kind in ("subdistricts", "blocks"):
            m = {}
            for code, name, dc, dn in d[kind]:
                m.setdefault(_key(name), []).append((code, name, dc, dn))
            _LGD[kind] = m
    return _LGD


def tie(place, level):
    """(code, LGD name, district code, district name) of a place, or None when it matches no or several units."""
    hits = lgd()["blocks" if level == "block" else "subdistricts"].get(_key(place)) or []
    return hits[0] if len(hits) == 1 else None


def parts(cell):
    """A cell with several people ("1. Dr. A, CO ... 2. Dr. B ...") as one text per person."""
    t = _esw.clean(cell)
    ps = [p.strip(" ,;") for p in re.split(r"(?:^|\s)\d{1,2}\s*[.)]\s+(?=\D)", t) if p.strip(" ,;")]
    return ps or ([t] if t else [])


def kinds_of(text):
    """Post kinds named in a person text, specific first ("CO cum BDO" -> ["co", "bdo"])."""
    for k, rx in KINDS:
        m = rx.search(text)
        if m:
            return (["co", "bdo"] if k == "co_bdo" else [k]), m
    return [], None


def name_of(text):
    """The person's name: the text before the first comma when it names no post and no contact ("Shri Likha Radh, ADC")."""
    head = re.split(r",|\s+-\s+|\s+PIO\b|\s+FAA\b", text, maxsplit=1)[0].strip()
    head = re.sub(r"(?i)^(PIO|APIO|FAA)\s*[-–:]\s*", "", head).strip()
    if not head or kinds_of(head)[0] or re.search(r"(?i)[\d@:]|\bemail\b|\bdepartment\b|\boffice\b|\bcommissioner\b", head):
        return ""
    if len(head.split()) > 6:
        return ""
    return head


def _places(t):
    """Places in a text: "Yachuli & Param Putu Circles" -> ["Yachuli", "Param Putu"]; district words are removed unless the
    place is nothing else ("Tezu Lohit" -> "Tezu"; "Tawang" stays)."""
    out = []
    for p in re.split(r"\s*(?:&|\band\b|/)\s*", t or ""):
        p = re.sub(r"(?i)\b(?:cd|block|circles?)\b\.?", " ", p)
        p = re.sub(r"\s+", " ", p).strip(" .,:;-–()")
        q = re.sub(r"\s+", " ", DISTRICT_WORDS.sub(" ", p)).strip(" .,-–")
        p = q if re.search(r"[A-Za-z]{3}", q) else p
        if p and re.search(r"[A-Za-z]{3}", p) and len(p) <= 40 and p not in out:
            out.append(p)
    return out


def place_after(text, m):
    """The places written after the post: "ADC, Pania PIO ..." -> ["Pania"]."""
    rest = text[m.end():]
    rest = re.sub(r"^\s*(?:\([^)]*\)\s*)?[,\-–]?\s*", "", rest)
    rest = STOP.split(rest, maxsplit=1)[0]
    cand = rest.split(",")[0]
    if re.fullmatch(r"(?i)\s*(hq|ga|rd)?[\s.]*", cand):
        return []
    return _places(cand)


def place_of_dept(dept):
    """The places in the DEPARTMENT cell: "Department RD-Yangte" -> [Yangte]; "BDO, Bameng Block, East Kameng" -> [Bameng];
    "O/o Circle Officer, Tarak Lengdi • O/o Circle Officer, Gangte" -> [Tarak Lengdi, Gangte]."""
    t = EMAIL_TEXT.sub(" ", dept or "")
    many = re.findall(r"(?i)circle officer\s*,\s*([A-Za-z][A-Za-z .-]*?)\s*(?:•|$)", t)
    if len(many) > 1:
        return [_esw.clean(x) for x in many]
    t = re.sub(r"(?i)^\s*departe?ment\s*[:\-–]?\s*", "", t)
    only_district = []
    for p in re.split(r"[,\-–•]|\s{2,}", t):
        q = DEPT_WORDS.sub(" ", re.sub(r"(?i)\s+and\s+", " & ", p))
        q = re.sub(r"\s+", " ", q).strip(" .:;()&")
        if q and DISTRICT_WORDS.sub(" ", q).strip(" .&") and re.search(r"[A-Za-z]{3}", q):
            return _places(q)
        if q and not only_district:
            only_district = [q]       # "Office Tawang": the district HQ, when the cell names no other place
    return only_district


def records(html, url=URL):
    soup = _esw.soup(html)
    recs, seen, ids = [], set(), set()
    table = next((t for t in soup.find_all("table") if "PIO" in t.get_text(" ")[:400]), None)
    if table is None:
        return recs
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            provenance.skipped("header")
            continue
        cells = [_esw.cell_text(td) for td in tds]
        cells += [""] * (len(COLS) - len(cells))
        row = dict(zip(COLS, cells))
        if not any(cells[1:]):
            provenance.skipped("empty")
            continue
        sno = re.sub(r"\D", "", row["sno"]) or str(len(ids) + 1)
        dept = row["department"]
        if NOT_CIVIL.search(dept):
            provenance.filtered("not a block / circle / sub-division office")
            continue
        dept_kinds, dept_m = kinds_of(EMAIL_TEXT.sub(" ", dept))
        people = [(col, pi, text, len(ps)) for col in ("faa", "pio", "apio") for ps in [parts(row[col])]
                  for pi, text in enumerate(ps)]
        got, posted = 0, 0
        for col, pi, text, n_in_cell in people:
            bare = EMAIL_TEXT.sub(" ", text)
            ks, m = kinds_of(bare)
            via = "cell"
            if not ks and dept_kinds == ["bdo"] and col == "pio" and not re.search(r"(?i)\b(?:DC|deputy commissioner)\b", bare):
                ks, via = dept_kinds, "department"        # "BDO, Lada, Block" | "Shri Tiwan Dolo, email, phone"
            if not ks:
                continue
            posted += 1
            name = name_of(text)
            phone = _esw.phones(bare)
            email = _esw.emails(text)
            if not (phone or email) and len(people) == 1 or (not (phone or email) and col == "pio"
                                                               and sum(1 for c, *_ in people if c == "pio") == 1):
                phone = phone or _esw.phones(EMAIL_TEXT.sub(" ", row["contact"]))      # the row's CONTACT / EMAIL columns
                email = email or _esw.emails(row["email"])
            if not (name or phone or email):
                continue
            places = (place_after(bare, m) if via == "cell" else []) or \
                (place_after(EMAIL_TEXT.sub(" ", dept), dept_m) if via == "department" else []) or place_of_dept(dept) or [""]
            for k in ks:
                dkey, level, post = POST[k]
                for ji, place in enumerate(places):
                    dup = (k, _key(place), name.lower(), email, phone)
                    if dup in seen:
                        continue
                    seen.add(dup)
                    t = tie(place, level) if place else None
                    key = f"{sno}:{col}:{k}" + (f":{pi + 1}" if n_in_cell > 1 else "") + (f":p{ji + 1}" if len(places) > 1 else "")
                    while key in ids:
                        key += "x"
                    ids.add(key)
                    recs.append(_esw.record(
                        MODULE, key, dept=dkey, level=level, area=t[1] if t else place, area_as_written=place or None,
                        post=post, designation=text[:200], name=name, phone=phone, email=email, body=dept,
                        post_from="department cell" if via == "department" else None,
                        rti_role=col.upper(), state="AR", state_code="12",
                        district=t[3] if t else None, district_code=t[2] if t else None,
                        subdistrict_code=t[0] if t and level != "block" else None,
                        lgd_block_code=t[0] if t and level == "block" else None,
                        tie_how="name in sub5_ar_lgd.json" if t else None, cells={c: v for c, v in row.items() if v},
                        source=url, src_url=url, src_pos={"table": _esw.table_no(table), "row": int(sno) if sno.isdigit() else None,
                                                          "col": col}))
                    got += 1
        if got:
            provenance.used(1)
        elif posted:
            provenance.skipped("no name or contact")
        else:
            provenance.filtered("not a block / circle / sub-division office")
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "pio_list", r.content)]
    recs = records(r.text, url)
    return recs, files, "" if recs else "no rows"
