"""Gujarat: Taluka Development Officers (TDOs, head of the taluka panchayat = block), Mamlatdars (head of the taluka = sub-district)
and Prant Officers / Deputy Collectors (head of the prant = sub-division), from the three state civil lists that the Government of
Gujarat prints for these cadres. Each list is one PDF with a text layer (Government Photo Litho Press), one officer per table row:
  - tdo: "Civil List As On 01.01.2025, Taluka Development Officer, Class-2 Cadre" (Panchayats, Rural Housing and Rural Development
    Department), panchayat.gujarat.gov.in/panchayat/documents/Y-423-TDO-Civil-List-2025.pdf, 38 pages, about 250 officers.
    Columns: Sr. No | Photo | Name, education, (native), date of birth | Mode of recruitment | Present designation ("Taluka
    Development Officer, Shihor, Dist. Bhavnagar") and date of appointment | Contact details ("(M) 9925232344", email).
  - mamlatdar: "Civil List As On 01.11.2025, Mamlatdar, Class-2 Cadre" (Revenue Department),
    revenuedepartment.gujarat.gov.in/downloads/Mamlatdar_class_2.pdf, 54 pages, about 380 officers.
  - dycollector: "Civil List As On 01.11.2025, Deputy Collector, Class-1 Cadre GAS (Junior Scale)" (Revenue Department),
    revenuedepartment.gujarat.gov.in/downloads/Deputy_collector_1.pdf, 50 pages, about 330 officers.
    Columns of both revenue lists: No | District of posting | Photo | Name, education, (native) | Designation ("Mamlatdar, Unjha",
    "Prant Officer, Dhrangadhra") and date of appointment | Date of birth | Date of appointment to the cadre | Contact details
    ("(M)-9712288122", email, "(O)-02767-250970").
The table cells sit between vertical rule lines (the same x on every page); a row starts at the serial number in the first column.
pypdf gives every text piece with its position (dforms/_util2_pdfgrid.page_parts, imported, not changed); the reader puts each
piece in its column by x and in its row by y, and joins words that the print broke at a line end ("Of-" + "ficer").

The reader keeps only officers posted to one taluka / taluka panchayat / prant: posts "Taluka Development Officer, <taluka>",
"Mamlatdar, <taluka>" (not "Mamlatdar, Election / Supply / ..." or "Chitnis to Collector") and "Prant Officer, <prant>" or
"Sub Divisional Magistrate, <place>". Area = the taluka / prant as the list spells it; district = the "Dist." part of the post (TDO)
or the "District of posting" column (revenue lists). Phones and emails are the officer's own contact details.
One queue item per list = 1 GET (2.8 to 7.4 MB). The PDF is kept in the bucket; a payload "stored" (bucket key) reads that copy
instead of the site (cforms/tn.py stored() pattern). Record ids: dept:sub2_gj:<kind>:<slug of district>:<slug of area>[:n].
"""
import io
import re

from dforms import _esw

MODULE = "sub2_gj"
SOURCES = {
    "tdo": ("https://panchayat.gujarat.gov.in/panchayat/documents/Y-423-TDO-Civil-List-2025.pdf", "2025-01-01"),
    "mamlatdar": ("https://revenuedepartment.gujarat.gov.in/downloads/Mamlatdar_class_2.pdf", "2025-11-01"),
    "dycollector": ("https://revenuedepartment.gujarat.gov.in/downloads/Deputy_collector_1.pdf", "2025-11-01"),
}
# column roles left to right (one column between two vertical rules; rules closer than 9 points are one border)
ROLES = {
    "tdo": ["sn", "photo", "name", "mode", "post", "contact"],
    "mamlatdar": ["sn", "district", "photo", "name", "post", "dob", "cadre", "contact"],
    "dycollector": ["sn", "district", "photo", "name", "post", "dob", "cadre", "contact"],
}
# fixed borders (points) when a page has no rules: the same as on the ruled pages
BORDERS = {
    "tdo": [43, 67, 134, 275, 357, 471, 553],
    "mamlatdar": [43, 63, 117, 181, 301, 363, 408, 479, 553],
    "dycollector": [43, 63, 115, 183, 301, 363, 408, 479, 553],
}
NOT_PLACE = re.compile(r"(?i)\b(election|supply|disaster|land\s*reforms?|stamp|atvt|e-?dhara|vigilance|ceiling|recovery|reservation|"
                       r"rehabilitation|acquisition|tenancy|inam|chitnis|chitnish|protocol|training|leave|deputation|waiting|"
                       r"suspension|planning|revenue\s*inquiry|inquiry|appeal|r\.?t\.?s|n\.?a\.?|municipal|corporation|city\s*survey|"
                       r"collector|secretariat|sachivalaya|department|board|commission|cell|branch|officer\s*on|project|g\.?i\.?d\.?c|"
                       r"assistant|account|audit|deputy|additional|authority|spipa|mdm|alien|allot\w*|encroachment|non\s*agri\w*|rto|"
                       r"m[ae]ritime|iora|ric|ssrd|science|administration|office|health|medical|service|urban|development)\b")
OFFICER = r"of+i*c+e*r?"
# district as the lists spell it (letters only, lower case) -> (LGD code, LGD name)
LGD = {"ahmedabad": ("438", "Ahmedabad"), "amreli": ("439", "Amreli"), "anand": ("440", "Anand"), "arvalli": ("672", "Arvalli"),
       "aravalli": ("672", "Arvalli"), "banaskantha": ("441", "Banas Kantha"), "bharuch": ("442", "Bharuch"),
       "bhavnagar": ("443", "Bhavnagar"), "botad": ("676", "Botad"), "chhotaudepur": ("668", "Chhotaudepur"),
       "chotaudepur": ("668", "Chhotaudepur"), "chhotaudaipur": ("668", "Chhotaudepur"), "dahod": ("445", "Dahod"),
       "dang": ("444", "Dangs"), "dangs": ("444", "Dangs"), "devbhumidwarka": ("674", "Devbhumi Dwarka"),
       "gandhinagar": ("446", "Gandhinagar"), "girsomnath": ("675", "Gir Somnath"), "girsomanath": ("675", "Gir Somnath"),
       "jamnagar": ("447", "Jamnagar"), "jamanagar": ("447", "Jamnagar"), "junagadh": ("448", "Junagadh"), "kachchh": ("449", "Kachchh"),
       "kutch": ("449", "Kachchh"), "kachch": ("449", "Kachchh"), "kheda": ("450", "Kheda"), "mahesana": ("451", "Mahesana"),
       "mehsana": ("451", "Mahesana"), "mahisagar": ("669", "Mahisagar"), "morbi": ("673", "Morbi"), "narmada": ("452", "Narmada"),
       "navsari": ("453", "Navsari"), "panchmahal": ("454", "Panch Mahals"), "panchmahals": ("454", "Panch Mahals"),
       "patan": ("455", "Patan"), "porbandar": ("456", "Porbandar"), "rajkot": ("457", "Rajkot"), "sabarkantha": ("458", "Sabar Kantha"),
       "surat": ("459", "Surat"), "surendranagar": ("460", "Surendranagar"), "tapi": ("641", "Tapi"), "vadodara": ("461", "Vadodara"),
       "valsad": ("462", "Valsad"), "vavtharad": ("789", "Vav-Tharad")}
# talukas that left Banaskantha for the new Vav-Tharad district (2025); the TDO list of 01.01.2025 still puts them in Banaskantha
VAV_THARAD = {"vav", "wav", "tharad", "tharada", "deodar", "diyodar", "bhabhar", "suigam", "lakhani", "rah", "raah", "dharnidhar"}
DIST = re.compile(r"(?i),?\s*dist(?:rict)?\.?\s*[:\-]?\s*([A-Za-z][A-Za-z .\-]*?)\s*$")
DATE = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")


def items(get=None):
    return [{"key": f"sub2_gj_{k}", "payload": {"reader": MODULE, "url": url, "kind": k, "state": "GJ", "india_only": True}}
            for k, (url, _) in SOURCES.items()]


def stored(p, get):
    """The PDF from the bucket when the item names its saved copy (payload "stored": "<project>/<path>.pdf")."""
    hub, k = getattr(get, "hub", None), p.get("stored")
    if not hub or not k:
        return None
    try:
        import requests
        url = hub.read_urls(k.split("/", 1)[0], [k])[k]
        r = requests.get(url, timeout=(20, 180))
        if r.status_code == 200 and r.content[:5] == b"%PDF-":
            return r.content
    except Exception:  # noqa: BLE001 - fall back to the site
        pass
    return None


def _borders(vlines, kind):
    xs = sorted({round(x) for x, y0, y1 in vlines if y1 - y0 > 40})
    out = []
    for x in xs:
        if out and x - out[-1] < 9:
            out[-1] = (out[-1] + x) / 2
        else:
            out.append(x)
    return out if len(out) == len(ROLES[kind]) + 1 else BORDERS[kind]


def join_lines(parts):
    """Pieces of one cell, top to bottom, as one text: a line that ends in '-' joins the next one without the hyphen when the
    next one starts in lower case ("Of-" + "ficer" -> "Officer", "tdo.shankhesh-" + "war@gmail.com"), with it otherwise."""
    out = ""
    for t in parts:
        t = t.replace("\n", " ").strip()
        if not t:
            continue
        if t == "-":
            out += "-"
        elif out.endswith("-"):
            out = out[:-1] + t if t[:1].islower() or t[:1].isdigit() and "@" in t else out + t
        else:
            out = (out + " " + t) if out else t
    return _esw.clean(out)


def page_rows(texts, vlines, kind):
    """[{role: text}] for the officer rows of one page."""
    b = _borders(vlines, kind)
    roles = ROLES[kind]

    def col(x):
        for k in range(len(b) - 1):
            if b[k] - 3 <= x < b[k + 1] - 1:
                return k
        return None
    starts = sorted({y for x, y, t in texts if col(x) == 0 and re.match(r"\s*\d+\b(?!\s*\d)", t) and not re.match(r"\s*1 2 3", t)},
                    reverse=True)
    rows = []
    for i, y0 in enumerate(starts):
        y1 = starts[i + 1] if i + 1 < len(starts) else -1
        cells = {}
        for x, y, t in sorted(texts, key=lambda t: (-t[1], t[0])):
            k = col(x)
            if k is None or not (y1 + 4 < y <= y0 + 6):
                continue
            cells.setdefault(roles[k], []).append(t)
        row = {r: join_lines(v) for r, v in cells.items()}
        row["name_parts"] = [_esw.clean(t) for t in cells.get("name", []) if _esw.clean(t)]
        sn = re.match(r"\s*(\d+)\s*(.*)$", row.get("sn", ""))
        if not sn:
            continue
        row["sn"] = sn.group(1)
        if sn.group(2) and "district" in roles:
            row["district"] = join_lines([sn.group(2)] + cells.get("district", []))
        rows.append(row)
    return rows


def rows(content, kind):
    from pypdf import PdfReader

    from dforms._util2_pdfgrid import page_parts
    reader = PdfReader(io.BytesIO(content))
    out = []
    for page in reader.pages:
        texts, _, vlines = page_parts(reader, page)
        out += page_rows(texts, vlines, kind)
    return out


EDU = re.compile(r"(?i)\b(bachelor|master|diploma|graduat\w*|degree|pass(ed)?|engineer\w*|civil|ssc|hsc|ssce|brs|mrs|mba|mca|bba|bca|"
                 r"iti|bams|bhms|mbbs|ptc|matric\w*|llb|llm|phd|std|b\.?\s?ed|m\.?\s?ed|b\.?\s?com|m\.?\s?com|b\.?\s?sc|m\.?\s?sc|"
                 r"b\.?\s?tech|m\.?\s?tech|b\.?\s?e|m\.?\s?e|b\.?\s?a|m\.?\s?a|b\.?\s?pharm|m\.?\s?phil|pgd\w*|f\.?\s?y|s\.?\s?y|"
                 r"t\.?\s?y)\b|\d")
# education printed on the name line ("Nasib Janmamad Sumara New S.S.C", "Chintan Virambhai Chaudhari M. Pharm")
EDU_TAIL = re.compile(r"\s+(?:(?:New|Old)\s+)?(?:[BM]\.?\s*(?:Pharm\w*|Farm\w*|Physio\w*|Tech|Sc|Com|Ed|Arch|A|E)\b\.?|"
                      r"S\.?\s*S\.?\s*C\.?\w*|H\.?\s*S\.?\s*C\.?\w*)(?:[\s.].*)?$")
NAME_LINE = re.compile(r"(?:Dr\.?\s*|Smt\.?\s*|Shri\.?\s*)?(?:[A-Z][a-z]+|[A-Z]\.)(?:[\s.]*(?:[A-Z][a-z]+|[A-Z]\.))*\.?")


def name_of(parts):
    """The officer's name from the pieces of the name cell (top to bottom): the first line, and the next lines while they are
    capitalised words (a name that wraps: "Bhudarbhai Tobhanbhai" + "Savsani"); the education line ("B.A.", "New S.S.C.",
    "Bachelor of Rural Studies"), the native district "(Anand)" and the date of birth end it."""
    if isinstance(parts, str):
        parts = [parts]
    out = []
    for i, t in enumerate(parts):
        t = t.strip()
        if i and (not NAME_LINE.fullmatch(t) or EDU.search(t) or not re.search(r"[a-z]{2}", t)):
            break
        t = re.split(r"\(|\b\d{2}-\d{2}-\d{4}\b", t)[0]
        out.append(t)
        if t != parts[i].strip():
            break
    name = _esw.clean(" ".join(out))
    return EDU_TAIL.sub("", name).strip(" ,.")


def post_place(kind, post):
    """(clean post, area, district or '') for a post this reader keeps, else None.
    'Taluka Development Officer, Shihor, Dist.Bhavnagar 09-01-2025' -> ('Taluka Development Officer', 'Shihor', 'Bhavnagar')."""
    p = _esw.clean(DATE.sub(" ", post or "")).strip(" ,.")
    dist = ""
    m = DIST.search(p)
    if m:
        dist, p = m.group(1).strip(" .-"), p[:m.start()].strip(" ,.")
    if kind == "tdo":
        m = re.match(r"(?i)(?:in-?\s*charge\s+)?taluka\s+development\s+" + OFFICER + r"\s*[,:\-]?\s*(.+)$", p)
        post_name = "Taluka Development Officer"
    elif kind == "mamlatdar":
        m = re.match(r"(?i)mam[altdr]+r(?:\s*-\s*\d)?\s*[,:\-]?\s+(.+)$", p)
        post_name = "Mamlatdar"
    else:
        m = re.match(r"(?i)(?:prant\s+" + OFFICER + r"|sub[\s-]*divisional\s+(?:magistrate|" + OFFICER + r"))\s*[,:\-]\s*(.+)$", p)
        post_name = "Prant Officer (Sub-Divisional Magistrate)"
    if not m:
        return None
    area = m.group(1).strip(" ,.-")
    if not dist and kind == "tdo" and "," in area:          # "Lakhtar, Surendranagar"
        area, dist = (x.strip(" ,.-") for x in area.rsplit(",", 1))
    area = re.sub(r"(?i)^(taluka|ta\.?)\s+", "", area)
    unit = area
    area = re.sub(r"\s*,.*$", "", area)
    area = re.sub(r"\s*\([^)]*\)\s*$", "", area).strip(" ,.-")
    if not area or NOT_PLACE.search(unit) or len(area.split()) > 3 or len(area) > 30:
        return None
    return post_name, area, dist, unit


def contacts(cell):
    """(phones, emails) from the contact cell: '(M)-9712288122 mam-unjha@ gujarat.gov.in (O)-02767-250970'."""
    t = re.sub(r"\s*@\s*", "@", cell or "")
    t = re.sub(r"(\S)\s+(gujarat\.\s*gov\.\s*in|gmail\.\s*com|yahoo\.\s*(?:co\.\s*in|com|in)|nic\.\s*in|gov\.\s*in)\b", r"\1\2", t)
    t = re.sub(r"\.\s+(?=(?:gov|in|com|co)\b)", ".", t)
    mail = _esw.emails(t)
    rest = _esw.EMAIL.sub(" ", _esw.deob(t))
    ph = _esw.phones(re.sub(r"\((?:M|O|R)\)\s*-?", " ", rest).replace("/", " "))
    return ph, mail


DEPT = {"tdo": ("rural_development", "block"), "mamlatdar": ("revenue", "subdistrict"), "dycollector": ("administration", "subdivision")}


def build(kind, rs, source, upd):
    dept, level = DEPT[kind]
    recs, seen = [], set()
    for r in rs:
        pp = post_place(kind, r.get("post", ""))
        name = name_of(r.get("name_parts") or r.get("name", ""))
        if not pp or not name:
            continue
        post, area, dist, unit = pp
        district = _esw.clean(r.get("district") or dist)
        code, lgd = LGD.get(re.sub(r"[^a-z]", "", district.lower()), ("", ""))
        if code == "441" and re.sub(r"[^a-z]", "", area.lower()) in VAV_THARAD:
            code, lgd = LGD["vavtharad"]
        district = lgd or district
        phone, email = contacts(r.get("contact", ""))
        base = f"{kind}:{_esw.slug(district) or 'gj'}:{_esw.slug(unit)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept=dept, level=level, area=area, district=district, district_code=code, state="GJ", name=name, post=post,
                                designation=DATE.sub(" ", r.get("post", "")), office=unit if unit != area else "", phone=phone, email=email, source=source, last_updated=upd,
                                civil_list_no=r.get("sn", "")))
    return recs


def fetch(p, get):
    kind = p.get("kind", "tdo")
    url, upd = SOURCES[kind]
    url = p.get("url") or url
    content = stored(p, get)
    files = []
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
        if content[:5] != b"%PDF-":
            return [], [], "not a pdf"
        files = [(f"depts/{MODULE}/{kind}.pdf", content, "application/pdf")]
    recs = build(kind, rows(content, kind), url, upd)
    return recs, files, "" if recs else "no rows"
