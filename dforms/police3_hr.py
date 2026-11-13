"""Haryana district police sites <district>.haryanapolice.gov.in: the "Contact Us" page (contactus.html / Contactus.html /
Contacts.html; India only, like the rest of haryanapolice.gov.in). Static HTML, no login, no captcha. One table of the
district's officers inside layout tables; the columns differ per district:
- Fatehabad: Sr. No. | Name of Office | Name of Police Officers | Phone No. | Mobile No. | Email-ids (SP, ASP, DSPs, SHOs,
  police post in-charges, CIA / ANC / AVT staff);
- Yamunanagar: Sr. No. | Name of Office | Email-ids | Name of Police Officers and Officials | Landline No. | Mobile No.;
- Charkhi Dadri, Hansi: Sr. No. | Rank | Office Tel. No. ("7419301104 220863": CUG mobile + landline) | Email (no names).
The leaf tables (no table inside) are read; the header row names the columns. The post decides the level:
SP / SSP / Superintendent / Addl. SP / ASP / CP / DCP -> district; DSP / ACP <place> -> subdivision (DSP HQ / Traffic / Crime
-> district unit); SHO / PS <station> -> police_station (Women, Traffic, Cyber stations keep office_type women / traffic /
cyber); PP <post> -> police_station, office_type police post; anything else (CIA, ANC, AVT, PO staff ...) -> district unit.
police_hr reads the statewide station list and the SHOContact.html pages; this reader adds the SP / DSP rows and the
districts whose sites have no SHOContact.html (Fatehabad, Charkhi Dadri, Hansi).
One queue item = one district page. Record id dept:police3_hr:<district>:<post slug>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police3_hr"

COLS = [("sno", r"^(sr|s)\.?\s*no"), ("email", r"e-?mail"), ("name", r"name of (the )?police officer|officer"),
        ("mobile", r"mobile|cug"), ("phone", r"phone|tel|landline"), ("post", r"name of office|rank|designation|office")]
DISTRICT = re.compile(r"\b(S\.?S\.?P|S\.?P|Superintendent|Superidentant|Addl\.?\s*S\.?P|A\.?S\.?P|C\.?P|D\.?C\.?P|"
                      r"Commissioner)\b", re.I)
DSP = re.compile(r"^(?:D\.?S\.?P|A\.?C\.?P)(?:[-\s]*[IVX0-9]+)?\b[\s,.-]*(.*)$", re.I)
DSP_UNIT = re.compile(r"\b(HQ|H\.Q|Traffic|Crime|Cyber|Head ?quarter|Security|Women|PCR)\b", re.I)
SHO = re.compile(r"^(?:SHO|S\.H\.O\.?)\s*(?:P\.?S\.?)?\s*[-,.]?\s*(.*)$|^P\.?S\.?\s+(.*)$", re.I)
PP = re.compile(r"^(?:I/?C\s+)?P\.?P\.?\s+(.*)$", re.I)
OTYPE = [(r"\bwomen|mahila", "women"), (r"traffic", "traffic"), (r"cyber", "cyber")]


def col_of(h):
    h = (clean(h) or "").lower()
    for k, pat in COLS:
        if re.search(pat, h):
            return k
    return None


def leaf_rows(html):
    """[(table no, row no, {col: text})] of every leaf table whose header row names a post column."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for ti, t in enumerate(soup.find_all("table")):
        if t.find("table"):
            continue
        trs = t.find_all("tr")
        head, cols = None, []
        for ri, tr in enumerate(trs):
            cells = [clean(c.get_text(" ", strip=True)) or "" for c in tr.find_all(["td", "th"])]
            if head is None:
                cols = [col_of(c) for c in cells]
                if "post" in cols and ("mobile" in cols or "phone" in cols):
                    head = ri
                continue
            if not any(cells) or len(cells) < len(cols) - 1:
                continue
            if len(cells) == len(cols) - 1 and cols[0] == "sno" and not re.fullmatch(r"\d+\.?", cells[0]):
                cells = [""] + cells          # a row without its serial number (rowspan)
            row = {}
            for k, v in zip(cols, cells):
                if k and v and k not in row:
                    row[k] = v
            if row.get("post"):
                out.append((ti, ri, row))
    return out


def strip_district(s, district):
    s = re.sub(r"[\s,]*\b" + re.escape(district) + r"\b\.?$", "", s, flags=re.I).strip(" ,.-")
    return s


def classify(post, district):
    p = clean(post) or ""
    m = SHO.match(p)
    if m:
        area = re.sub(r"\s*,\s*", " ", (m.group(1) or m.group(2) or "").strip(" ,.-")) or district     # as published
        otype = next((t for pat, t in OTYPE if re.search(pat, area, re.I)), "police station")
        return "police_station", "SHO", area, otype
    m = PP.match(p)
    if m:
        return "police_station", "Police post in-charge", strip_district(m.group(1), district), "police post"
    m = DSP.match(p)
    if m:
        place = strip_district(m.group(1), district)
        if not place or DSP_UNIT.search(place) or re.fullmatch(r"[IVX0-9-]+", place):
            return "district", p, district, "unit"
        return "subdivision", "DSP", place, "subdivision"
    if DISTRICT.search(p) and not re.search(r"\b(CIA|ANC|AVT|staff|cell|unit)\b", p, re.I):
        return "district", p, district, "office"
    return "district", p, district, "unit"


def split_tel(s):
    """'7419301104 220863' -> '7419301104, 220863' (CUG + landline written in one cell)."""
    return re.sub(r"(?<=\d)\s+(?=\d{5,})", ", ", s or "")


def parse(html, url, district, std=None):
    recs = []
    d = slug(district)
    for ti, ri, r in leaf_rows(html):
        level, post, area, otype = classify(r["post"], district)
        tel = split_tel(r.get("phone"))
        if std:
            tel = re.sub(r"(?<![\d-])([1-5]\d{5})(?!\d)", std + r"-\1", tel)
        mails = [e for e in (email(x) for x in re.split(r"[,;\s]+", (r.get("email") or "").replace("[at]", "@")
                                                                     .replace("[dot]", "."))) if e]
        ph = phones(r.get("mobile"), tel)
        name = r.get("name")
        if name and re.fullmatch(r"[-–\s.]*|vacant", name, re.I):
            name = None
        if not ph and not mails and not name:
            continue
        key = f"{d}:{slug(post)}-{slug(area)}" if level in ("police_station", "subdivision") else f"{d}:{slug(post)}"
        recs.append(rec(M, key, level=level, office_type=otype, post=post, area=area, office=r["post"], name=name,
                        phone=ph, telephone=r.get("phone"), mobile=phones(r.get("mobile")), email=", ".join(mails) or None,
                        state="HR", district=district, list_no=r.get("sno"), source=url, src_pos={"table": ti, "row": ri}))
    return uniq(recs)


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    district = p["district"]
    recs = parse(r.text, url, district, p.get("std"))
    return recs, [gz(M, slug(district), r.content)], "" if recs else "no rows"
