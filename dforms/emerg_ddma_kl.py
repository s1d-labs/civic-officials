"""Kerala: the Kerala State Disaster Management Authority's DM Directory 2025 (sdma.kerala.gov.in/wp-content/uploads/2025/06/
DM-Directory-2025_23.pdf, 58 pages, no login). One PDF, one queue item. Parts, in order:
- emergency numbers (state helplines 1070 / 1079 / 112 / 1077 ...), KSDMA members, state level officers, armed forces, MHA and NDMA
  control rooms, VSAT and satellite phones: level state;
- "District Emergency Operation Center": one row per district, landline + mobile (14 rows): level district, post "District
  Emergency Operations Centre";
- "District Emergency Operation Centre- HOTLINES": DDMA hotline numbers, A end (SEOC) and B end (district);
- "TALUK EMERGENCY OPERATIONS CENTERS": one row per taluk under "<DISTRICT> DISTRICT" (78 taluks): level subdistrict;
- "DISTRICT WISE DETAILS": per district, sections Revenue (DEOC, Collector, ADM, RDOs, TEOCs), Police, Fire and Rescue service,
  Coast Guard, Fisheries, KSEB, Health Services, KSRTC ...: one row per post, mobile and landline.
The directory names posts, not people (a few rows carry a name). Rows are read from the page layout (pdftotext -layout or pypdf):
"<no>  <post>  <mobile>  <landline>", with continuation lines for long posts and extra numbers.
Record: dept from the section (Revenue -> disaster for EOC / control room rows, else revenue; Police -> police; Fire -> fire;
Health -> health; KSEB -> electricity; KSRTC -> transport; Fisheries, Coast Guard, armed forces -> other), layer emerg_ddma,
level, area (district or taluk), post, phone, helpline (short codes), section, part, district, state KL, source, last_updated
2025-05-25 (the cover: "Updated on 25th May 2025" on the taluk page). Record ids: dept:emerg_ddma_kl:<part>:<district>:<slug of post>.
"""
import re

from dforms import _emerg
from dforms._pdftext import layout_pages

MODULE = "emerg_ddma_kl"
URL = "https://sdma.kerala.gov.in/wp-content/uploads/2025/06/DM-Directory-2025_23.pdf"
DISTRICTS = ["Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha", "Kottayam", "Idukki", "Ernakulam", "Thrissur",
             "Palakkad", "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"]
DIST_ALIAS = {"kasargod": "Kasaragod", "trivandrum": "Thiruvananthapuram"}
PARTS = [  # (regex on a heading line, part key, level)
    (r"^emergency contact numbers$", "helplines", "state"),
    (r"^kerala state disaster management authority$", "ksdma", "state"),
    (r"^emergency contacts\s*-\s*state-?\s*level officers$", "state", "state"),
    (r"^armed forces$", "armed", "state"),
    (r"^government of india", "mha", "state"),
    (r"^national disaster management authority$", "ndma", "state"),
    (r"^vsat phone numbers$", "vsat", "state"),
    (r"^satellite phones? numbers$", "satphone", "state"),
    (r"^district emergency operation cent(er|re)$", "deoc", "district"),
    (r"hotlines$", "hotline", "district"),
    (r"^taluk emergency operations cent(er|re)s", "teoc", "subdistrict"),
    (r"^district wise details$", "district", "district"),
]
DEPTS = [(r"(?i)police|crime|vigilance|intelligence", "police"), (r"(?i)fire", "fire"),
         (r"(?i)health|ayurveda|homo?eopath|medical", "health"), (r"(?i)kseb|electricity", "electricity"),
         (r"(?i)ksrtc|transport", "transport"), (r"(?i)local self", "town_body"), (r"(?i)revenue", "revenue")]
SECTIONS = re.compile(r"(?i)^(revenue|police|ksrtc|fisheries|fire\s*(and|&)\s*rescue\s*service|fireandrescueservice|kseb|ksebl|"
                      r"kerala state electricity board|health( services)?|coast guard|homeopathy|ayurveda|navy|"
                      r"local self govt\.? department|coastal police|fire & rescue)$")
PHONE = re.compile(r"(?:\+91[\s-]*)?(?:\(?0\d{2,4}\)?[\s–-]*)?\d{6,}|\b1\d{2,3}\b(?=\s*$|[\s/;,])|\d{3,5}\s*[–-]\s*\d{6,8}|\d{4,5}\s\d{6,7}")
ROW = re.compile(r"^\s{0,6}(\d{1,2})\.?\s+(\S.*)$")


def district_of(text):
    t = _emerg.clean(re.sub(r"(?i)\bdistrict\b", "", text)).lower()
    if t in DIST_ALIAS:
        return DIST_ALIAS[t]
    return next((d for d in DISTRICTS if d.lower() == t), None)


def split(line):
    """(post text, phone text, column where the phones start) of one layout line."""
    m = PHONE.search(line)
    if not m:
        return line.strip(), "", None
    return line[:m.start()].strip(" -:;,"), line[m.start():].strip(), m.start()


def rows(pages):
    """[(part, level, district, section, no, post, phone text)] from the directory's pages."""
    out, part, level, district, section, cur = [], None, "state", None, "", None
    lines = [ln for pg in pages if "PAGE NO" not in pg for ln in pg.split("\n")]

    def nxt_row(i):
        for ln in lines[i + 1:i + 4]:
            if ln.strip():
                m = ROW.match(ln)
                return bool(m and m.group(1) == "1")
        return False

    for i, ln in enumerate(lines):
        s = _emerg.clean(ln)
        if not s:
            continue
        if re.fullmatch(r"\d{1,2}", s) and len(ln) - len(ln.lstrip()) > 12:
            continue  # page number
        if re.match(r"(?i)^(s[il]\.?\s*(no)?|no\.|sl\s*no|updated|address\b)", s) or "Landline/Mobile" in s or "TELENO" in s:
            continue
        low = s.lower()
        hit = next(((k, lv) for rx, k, lv in PARTS if re.search(rx, low)), None)
        if hit and not ROW.match(ln):
            part, level = hit
            section, cur = "", None
            district = None if level == "state" else district
            continue
        if part is None:
            continue
        d = district_of(s) if not re.search(r"\d", s) else None
        if d and part in ("teoc", "district") and not ROW.match(ln) and (len(ln) - len(ln.lstrip()) >= 10 or "DISTRICT" in s):
            district, section, cur = d, "", None
            continue
        m = ROW.match(ln)
        if m:
            post, ph, _ = split(m.group(2))
            cur = [part, level, district, section, int(m.group(1)), post, ph]
            out.append(cur)
            continue
        if part == "district" and not re.search(r"\d{3,}", s) and (SECTIONS.match(s) or nxt_row(i)) and len(s) < 60:
            section, cur = s, None
            continue
        if cur is not None:
            post, ph, _ = split(ln)
            if post:
                cur[5] = f"{cur[5]} {post}".strip()
            if ph:
                cur[6] = f"{cur[6]}, {ph}".strip(", ")
    return out


def dept_of(section, post, part):
    if part in ("deoc", "hotline", "teoc", "ksdma", "ndma", "mha", "vsat", "satphone", "helplines"):
        return "disaster"
    for rx, d in DEPTS:
        if re.search(rx, section or post or ""):
            if d == "revenue" and re.search(r"(?i)emergency|control|eoc|disaster|teoc", post):
                return "disaster"
            return d
    if re.search(r"(?i)emergency|eoc|disaster|control room", post):
        return "disaster"
    return "other"


def records(pages, url=URL):
    recs, seen = [], set()
    for part, level, district, section, no, post, ph in rows(pages):
        phone = _emerg.phones(ph)
        helpline = _emerg.short_codes(ph)
        if not (phone or helpline) or not post:
            continue
        area, lvl = district, level
        if part == "deoc":
            area = district_of(post) or post
            district, post = area, "District Emergency Operations Centre"
        elif part == "hotline":
            dd = district_of(re.sub(r"(?i)^ddma\s*", "", post))
            if dd:
                area = district = dd
            else:
                lvl = "state"
        elif part == "teoc":
            area, post = re.sub(r"(?i)\s*taluk$", "", post), "Taluk Emergency Operations Centre"
        elif part == "district" and re.match(r"(?i)teoc", post):
            area, lvl = re.sub(r"(?i)^teoc\s*[–-]\s*", "", post), "subdistrict"
        elif part == "district" and re.search(r"(?i)fire and rescue station|fire station|^frs\b", post):
            lvl = "facility"
            area = re.sub(r"(?i)^(fire\s*(and|&)\s*rescue\s*station|frs)[\s,–-]*", "", post) or district
        key = _emerg.unique(f"{part}:{_emerg.slug(district or 'state')}:{_emerg.slug(area if part == 'teoc' else post)[:60]}", seen)
        recs.append(_emerg.record(
            MODULE, key, "ddma", dept=dept_of(section, post, part), level=lvl, area=area or "Kerala", post=post, phone=phone,
            helpline=helpline, section=section, part=part, district=district, state="KL", office_id=key, source=url,
            last_updated="2025-05-25"))
    return recs


def items(get=None):
    return _emerg.seed(MODULE)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    files = [_emerg.keep(MODULE, "dm-directory-2025", r.content, ext="pdf")]
    pages, _ = layout_pages(r.content)
    recs = records(pages, url)
    return recs, files, "" if recs else "no rows"
