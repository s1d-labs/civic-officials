"""Assam Police, police.assam.gov.in (Government of Assam SWF 2.0 site): two public PDF lists on /about-us/our-branches-and-offices.
- form "landline": "All Districts Land Line Numbers" (/sites/default/files/public_utility/all_districts-land-line_number.pdf, an
  Excel print, 37 pages): one block per police district (heading "Nagaon", "Kamrup, Amingaon", "Commissioner of Police, Guwahati",
  "SRP, Pandu" ...), then "Sl. No. | Location | Number". Locations: "O.C. Nagaon P.S.", "I/C Morikalong TOP", "Dharamtul PS"
  (number "Not available"), "SP(N)", "Addl.SP(HQ) Office", "SDPO Office, KBR", "CI(W) BDA", "I/C Traffic", "Police Control Room",
  "CDR Cell", "ACP (Jalukbari)", "All Women P.S.". No officer names. A number in a cell of two or three lines is printed above
  and below the row line: each number-only line goes to the nearest row line of its block (ties: the row above). Numbers without
  the STD code (Guwahati: "2540278") get the block's STD code, taken from the block's full numbers or STD below.
- form "directory": "Directory of Police Officers in Assam" (/sites/default/files/public_utility/directory_ason-<ddmmyyyy>.pdf,
  15 pages): "SL No. | Name & Rank Of Officers | STD | Office | Fax | Mobile No. | E-mail ID", sections (headquarters, ranges,
  "Districts Superintendents of Police", battalions ...). One entry = a name line ("Shri Numal Mahatta, APS"), a post line
  ("Senior Supdt. of Police, Bongaigaon") and a serial line with the numbers; the lines come in any order around the serial
  line. Columns are taken from the section's header line positions. District SPs: level district, district from the post.
Both lists are read with pdftotext -layout (else pypdf layout) on the runner: text PDFs, no OCR. Answers from Mumbai
(2026-11-13); from abroad unchecked. items(get) reads the offices page for the current file names (the directory's name has
its date). Record ids: dept:police3_as:ll:<district>:<location>, dept:police3_as:dir:<serial>-<post>."""
import re
from collections import Counter

from dforms._field import pdf_text_engine
from dforms._police import clean, email, gz, phones, rec, slug, uniq
from dforms._police3e import kind, station_name
from provenance import line_pos

METHOD = "pdf text (pdftotext -layout, else pypdf layout), lines grouped by serial number"

M = "police3_as"
BASE = "https://police.assam.gov.in"
OFFICES = BASE + "/about-us/our-branches-and-offices"

DISTRICT = {   # block heading / post place -> LGD district name
    "nagaon": "Nagaon", "morigaon": "Marigaon", "marigaon": "Marigaon", "hailakandi": "Hailakandi", "cachar": "Cachar",
    "bongaigaon": "Bongaigaon", "sivasagar": "Sivasagar", "sivsagar": "Sivasagar", "karbi-anglong": "Karbi Anglong",
    "karbi anglong": "Karbi Anglong", "kanglong": "Karbi Anglong", "chirang": "Chirang", "goalpara": "Goalpara",
    "darrang": "Darrang", "kokrajhar": "Kokrajhar", "hojai": "Hojai", "barpeta": "Barpeta", "dhubri": "Dhubri",
    "golaghat": "Golaghat", "charaideo": "Charaideo", "jorhat": "Jorhat", "sonitpur": "Sonitpur", "dibrugarh": "Dibrugarh",
    "hamren": "West Karbi Anglong", "west karbi anglong": "West Karbi Anglong", "south salmara": "South Salmara Mancachar",
    "biswanath": "Biswanath", "udalguri": "Udalguri", "tinsukia": "Tinsukia", "nalbari": "Nalbari", "dima hasao": "Dima Hasao",
    "dhemaji": "Dhemaji", "sadiya": "Tinsukia", "majuli": "Majuli", "karimganj": "Sribhumi", "sribhumi": "Sribhumi",
    "lakhimpur": "Lakhimpur", "kamrup": "Kamrup", "baksa": "Baksa", "bajali": "Bajali", "tamulpur": "Tamulpur",
    "guwahati": "Kamrup Metro", "kamrup metro": "Kamrup Metro",
}
STD = {"Kamrup Metro": "0361", "Kamrup": "0361"}


def district_of(text):
    t = (clean(text) or "").lower()
    t = re.sub(r"\(.*?\)", " ", t)
    best = None
    for k, v in DISTRICT.items():
        m = re.search(r"\b" + re.escape(k) + r"\b", t)
        if m and (best is None or m.start() > best[0] or (m.start() == best[0] and len(k) > best[1])):
            best = (m.start(), len(k), v)
    return best[2] if best else None


def pages_lines(text):
    """[(page, line, text)] with 1-based page (form feed) and line numbers."""
    out = []
    for p, page in enumerate(text.split("\f"), 1):
        for i, ln in enumerate(page.split("\n"), 1):
            out.append((p, i, ln))
    return out


# ---------- land line list ----------
NUMLINE = re.compile(r"^[\d\s()/&,.\-OoRrWLlFfaxXTH]+$")
PAGE = re.compile(r"^\s*Page\s+\d+\s*$", re.I)
HEADROW = re.compile(r"^\s*Sl\.?\s*No", re.I)


def _is_numline(s):
    s = s.strip()
    return bool(s) and bool(re.search(r"\d{5}", s)) and bool(NUMLINE.match(s))


def _std_of(nums, district):
    """(std4, std5) of a block: the most common 4 / 5 digit prefixes of its 11-digit numbers; Guwahati / Kamrup 0361."""
    if district in STD:
        return STD[district], None
    full = [re.sub(r"\D", "", n) for n in nums]
    full = [d for d in full if len(d) == 11 and d.startswith("0")]
    s5 = Counter(d[:5] for d in full).most_common(1)
    s4 = Counter(d[:4] for d in full).most_common(1)
    return (s4[0][0] if s4 else None), (s5[0][0] if s5 else None)


def _fix(raw, std4, std5):
    """One published number cell -> a list of numbers ('0367824020f4' stays as printed in raw; phones() takes the digits)."""
    out = []
    for part in re.findall(r"\d[\d ]{4,12}\d", raw or ""):
        d = re.sub(r"\D", "", part)
        if len(d) == 7 and std4 and not d.startswith("0"):
            out.append(f"{std4}-{d}")
        elif len(d) == 6 and std5 and not d.startswith("0"):
            out.append(f"{std5}-{d}")
        elif len(d) == 11 and d.startswith("03"):
            # 0361 + 7 digits (Guwahati) or 03xxx + 6 digits: keep the STD code apart
            out.append(f"{d[:4]}-{d[4:]}" if d.startswith("0361") else f"{d[:5]}-{d[5:]}")
        else:
            out.append(part.replace(" ", ""))
    return out


def blocks_landline(text):
    """[(heading, [(page, line, line text, kind, serial, location, number text)])]."""
    pl = pages_lines(text)
    blocks, cur = [], None
    for idx, (p, i, ln) in enumerate(pl):
        s = ln.strip()
        if not s or PAGE.match(s) or s.lower().startswith("data :") or HEADROW.match(s):
            continue
        nxt = [x[2].strip() for x in pl[idx + 1: idx + 5] if x[2].strip() and not PAGE.match(x[2])]
        if not re.match(r"^\d", s) and nxt and HEADROW.match(nxt[0]) and not _is_numline(s):
            cur = (s, [])
            blocks.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^(\d{1,3})\s+(.*)$", s)
        if m:
            cells = re.split(r"\s{2,}", m.group(2).strip(), maxsplit=1)
            loc = cells[0]
            num = cells[1] if len(cells) > 1 else ""
            if re.search(r"\d{5}", loc) and not num:      # "1 2540278": no location
                loc, num = "", loc
            cur[1].append((p, i, ln, "row", m.group(1), loc, num))
        elif _is_numline(s):
            cur[1].append((p, i, ln, "num", None, None, s))
        else:
            cur[1].append((p, i, ln, "text", None, None, s))
    return blocks


def circle_area(loc):
    """'CI Laharighat' -> 'Laharighat'; 'CI(W) BDA' -> 'BDA'; 'C.I. Office, Lala' -> 'Lala'; 'ACP (Jalukbari)' -> 'Jalukbari'."""
    t = re.sub(r"^\s*(?:Circle Inspector|ACP|A\.C\.P\.?|C\.I\.?|CI\b)\s*[,.:-]?\s*", "", clean(loc) or "", flags=re.I)
    inner = re.fullmatch(r"\(\s*([^()]+?)\s*\)", t)
    if inner:
        return inner.group(1)
    t = re.sub(r"\([^()]*\)?", " ", t)
    t = re.sub(r"^\s*Office\s*,?\s*|\s*Office\s*$", "", t, flags=re.I)
    return clean(t).strip(" ,.-") or clean(loc)


def parse_landline(text, url, engine=None):
    recs = []
    for head, lines in blocks_landline(text):
        district = district_of(head)
        rows = [dict(page=p, line=i, line_text=ln, serial=sn, location=loc, number=[num] if num else [], extra=[], at=k)
                for k, (p, i, ln, kd, sn, loc, num) in enumerate(lines) if kd == "row"]
        if not rows:
            continue
        pos = [r["at"] for r in rows]
        for k, (p, i, ln, kd, sn, loc, num) in enumerate(lines):
            if kd == "row":
                continue
            j = min(range(len(pos)), key=lambda x: (abs(pos[x] - k), pos[x] > k))
            if kd == "num":
                rows[j]["number"].append(num)
            elif abs(pos[j] - k) <= 1:
                rows[j]["extra"].append(num)
        std4, std5 = _std_of([n for r in rows for n in r["number"]], district)
        hk = slug(head)
        for r in rows:
            loc = clean(" ".join([r["location"]] + r["extra"])) if r["location"] else clean(" ".join(r["extra"]))
            if not loc:
                continue
            level, otype, post = kind(loc)
            raw = " ; ".join(r["number"])
            ph = phones(*_fix(raw, std4, std5))
            area = station_name(loc) if level == "police_station" else (
                circle_area(loc) if level == "circle" else (district or clean(head)))
            d = dict(level=level, office_type=otype, area=area, post=post or loc, phone=ph, number_as_published=raw or None,
                     state="AS", district=district, unit=clean(head), list_no=r["serial"], source=url, src_url=url,
                     src_pos=line_pos(r["page"], r["line"], r["line_text"]), method=engine)
            if level != "police_station":
                d["office"] = loc
            recs.append(rec(M, f"ll:{hk}:{slug(loc)}", **d))
    return uniq(recs)


# ---------- officers directory ----------
HONOR = re.compile(r"^(?:Shri|Smti?|Sri|Ms|Mrs|Mr|Dr|Miss)\b\.?\s", re.I)
DIRHEAD = re.compile(r"\bSTD\b.*\b(?:Office|Fax|FAX)\b", re.I)
SKIPLINE = re.compile(r"LIST OF POLICE OFFICERS|^\s*SL\s*$|^\s*No\.\s*$", re.I)


def _cols(head):
    """Column starts from a header line: {'std','office','fax','mobile','email'} -> x."""
    c = {}
    for name, rx in (("std", r"\bSTD\b"), ("office", r"\bOffice\b"), ("fax", r"\bfax\b"), ("mobile", r"\bMobile"),
                     ("email", r"\bE-?mail")):
        m = re.search(rx, head, re.I)
        if m:
            c[name] = m.start()
    return c


def _left(ln, cols):
    """The text part of a line (left of the STD column) and the serial number in front of it."""
    edge = cols.get("std", 50) - 2
    left = ln[:edge] if len(ln) > edge else ln
    # a long post may run into the STD column: take text up to the first run of digits after a gap
    m = re.match(r"^(.*?)(?:\s{2,}\d|\s{2,}$|$)", ln)
    if m and len(m.group(1)) > len(left.rstrip()):
        left = m.group(1)
    sm = re.match(r"^\s*(\d{1,3})(?:\s+|$)(.*)$", left)
    if sm:
        return sm.group(1), clean(sm.group(2))
    return None, clean(left)


def _right(ln, cols, skip):
    """Tokens right of the text: [(column, token)]."""
    out = []
    for m in re.finditer(r"\S+", ln):
        if m.start() < skip:
            continue
        x, tok = m.start(), m.group()
        col = None
        for name in ("email", "mobile", "fax", "office", "std"):
            if name in cols and x >= cols[name] - 4:
                col = name
                break
        if "@" in tok:
            col = "email"
        elif re.fullmatch(r"[6-9]\d{9}", tok):
            col = "mobile"
        out.append((col or "std", tok))
    return out


def parse_directory(text, url, engine=None):
    pl = pages_lines(text)
    cols = {"std": 52, "office": 59, "fax": 69, "mobile": 79, "email": 90}
    section = None
    entries, cur = [], None

    def new():
        e = dict(names=[], posts=[], serial=None, tok=[], lines=[], section=section)
        entries.append(e)
        return e

    for p, i, ln in pl:
        s = ln.strip()
        if not s or PAGE.match(s) or SKIPLINE.search(s):
            continue
        if DIRHEAD.search(ln):
            cols = _cols(ln) or cols
            t = clean(ln[: cols.get("std", 50)])
            if t and not re.match(r"^(SL|Name)", t, re.I):
                section = t
            cur = None
            continue
        serial, left = _left(ln, cols)
        is_name = bool(left and HONOR.match(left))
        starts_text = len(ln) - len(ln.lstrip())
        if cur is None:
            cur = new()
        elif is_name and (cur["serial"] or cur["posts"] or cur["names"]):
            cur = new()
        elif serial and cur["serial"]:
            cur = new()
        elif left and not serial and not is_name and not cur["names"] and not cur["serial"] and cur["posts"] and \
                re.match(r"^[A-Z][a-z]", left) is None:
            pass
        if serial:
            cur["serial"] = serial
        if left:
            (cur["names"] if is_name else cur["posts"]).append(left)
        skip = len(ln) - len(ln.lstrip()) + (len(serial) + 1 if serial else 0) + len(left or "") + starts_text * 0
        cur["tok"] += _right(ln, cols, skip)
        cur["lines"].append((p, i, ln))
    recs = []
    for e in entries:
        if not e["serial"] or not (e["names"] or e["posts"]):
            continue
        name = clean(" ".join(e["names"])) if e["names"] else None
        post = clean(re.sub(r"\S+@\S+", " ", " ".join(e["posts"])))
        post = re.sub(r"^\d{3,5}\s+|\s+\d{3,5}$", "", post or "")
        if not post:
            continue
        by = {}
        for c, t in e["tok"]:
            by.setdefault(c, []).append(t)
        std = next((t for t in by.get("std", []) if re.fullmatch(r"0?\d{2,4}", t)), None)
        std = ("0" + std if std and not std.startswith("0") else std)
        offices = [t for t in by.get("office", []) + [t for t in by.get("std", []) if re.fullmatch(r"\d{6,8}", t)]
                   if re.fullmatch(r"\d{6,8}", t)]
        office_nums = [f"{std}-{t}" if std else t for t in offices]
        fax = [f"{std}-{t}" if std else t for t in by.get("fax", []) if re.fullmatch(r"\d{6,8}", t)]
        mobile = [t for t in by.get("mobile", []) if re.fullmatch(r"\d{10}", t)]
        mail = "".join(by.get("email", []))
        sec = e["section"] or ""
        dist = None
        if re.search(r"district", sec, re.I) and re.search(r"Supdt|Superintendent|\bSP\b|SSP", post, re.I):
            level, otype = "district", "office"
            dist = district_of(post)
        else:
            level, otype, _ = kind(post)
            if level == "police_station":
                level, otype = "district", "unit"
            dist = district_of(post) if re.search(r"Commissioner of Police|Commissionerate", post, re.I) else None
            if level in ("district",) and not dist:
                level = "state"
        p0, i0, l0 = e["lines"][0]
        d = dict(level=level, office_type=otype, area=dist or post, post=post, name=name,
                 phone=phones(*(mobile + office_nums)), fax=", ".join(fax) or None, email=email(mail), state="AS",
                 district=dist, section=sec or None, list_no=e["serial"], source=url, src_url=url,
                 src_pos=line_pos(p0, i0, l0, lines=[x[1] for x in e["lines"]]), method=engine)
        recs.append(rec(M, f"dir:{e['serial']}-{slug(post)[:60]}", **d))
    return uniq(recs)


# ---------- pool ----------
def links(html):
    """{'landline': url, 'directory': url} from the offices page."""
    out = {}
    for href in re.findall(r'href="([^"]+\.pdf)"', html or "", re.I):
        u = href if href.startswith("http") else BASE + href
        if re.search(r"land-?line", href, re.I):
            out.setdefault("landline", u)
        elif re.search(r"directory", href, re.I):
            out.setdefault("directory", u)
    return out


def items(get):
    r = get(OFFICES)
    if r is None:
        return []
    return [{"key": f"{M}:{form}", "payload": {"reader": M, "form": form, "url": u, "state": "AS"}}
            for form, u in sorted(links(r.text).items())]


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    text, engine = pdf_text_engine(r.content)
    form = p.get("form") or ("landline" if "land" in url else "directory")
    recs = parse_landline(text, url, engine) if form == "landline" else parse_directory(text, url, engine)
    return recs, [gz(M, form + ".pdf", r.content)], "" if recs else "no rows"
