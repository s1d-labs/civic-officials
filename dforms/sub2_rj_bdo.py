"""Rajasthan: Vikas Adhikari (Block Development Officer, head of the panchayat samiti = block) of every panchayat samiti, from the
state list of the Panchayati Raj Department: "पंचायत समितियों में कार्यरत विकास अधिकारियों की सूची" (list of the Vikas Adhikaris
working in the panchayat samitis), dated 17 August 2026. The department's Jankalyan site attaches it as its "Block Office" contact
PDF (lsg.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail, row of "Panchayati Raj Department",
ContactCategoryName "Block Office", AttachmentUrl .../2026/Sep/DEPTContactDetail373745a5-....pdf). The file host
jankalyanfile.rajasthan.gov.in answers only from India; the /Files//Content/UploadFolder/ address moves to /WebMyWayFiles/.

One PDF, 15 landscape pages, about 370 rows, text layer set in Kruti Dev 010 for the Hindi columns (converted with
dforms/_ward_kd.py, imported). Columns, left to right (x borders in points, from the ruled pages): S.No | Name of the Vikas
Adhikari (Hindi; "रिक्त पद" = post vacant) | home district | panchayat samiti (Hindi) | posted district (English, capitals) |
panchayat samiti (English) | cadre (RDS-12, RRDS-PR ...) | order date | selection order date | mobile | STD code | office phone |
email (bdo.<dist>.<ps>@rajasthan.gov.in). A row starts at its serial number; pieces belong to the row whose serial number is
nearest in height. The mobile column also carries the STD code when the print runs them together ("8233443132 1466").

Records (dept rural_development, level block): area = the panchayat samiti in English as the list spells it ("Ajmer gramin",
"Payalakalan"), area_regional = its Hindi name, district = the posted district matched to LGD (Balotra, Didwana-Kuchaman ...),
name = the Hindi name (the list gives no English name), phone = the mobile and the office phone with its STD code
("01463-281123"), email. A vacant post keeps the office phone and email, with vacant=true and no name.
One queue item = 1 POST to the contact rows (payload "discover": the newest "Block Office" PDF of the department, so a new upload
is found; the payload url when the call fails) + 1 GET of the PDF (about 2 MB). The PDF is kept in the bucket; a payload "stored" (bucket key) reads that copy instead of the
site. Record ids: dept:sub2_rj_bdo:<slug of district>:<slug of panchayat samiti>[:n].
"""
import io
import re

import provenance
from dforms import _esw, _ward_kd as kd

METHOD = "pdf text pieces by position (pypdf, ruled columns) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_rj_bdo"
URL = ("https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/Department/PDF/DEPTContactDetail/2026/Sep/"
       "DEPTContactDetail373745a5-0193-41ea-9ee3-1629f3edf43a.pdf")
LIST_DATE = "2026-08-17"
# left borders of the columns (points); the ruled pages put double rules at 77/82, 203/208 ... 977/982
BORDERS = [0, 80, 205, 268, 350, 426, 502, 574, 624, 671, 741, 781, 833, 2000]
ROLES = ["sn", "name", "home", "ps_hi", "district", "ps", "cadre", "order", "selection", "mobile", "std", "office", "email"]
# posted district (letters only, lower case) -> (LGD code, LGD name)
LGD = {"ajmer": ("86", "Ajmer"), "alwar": ("87", "Alwar"), "balotara": ("775", "Balotra"), "balotra": ("775", "Balotra"),
       "banswara": ("88", "Banswara"), "baran": ("89", "Baran"), "barmer": ("90", "Barmer"), "beawar": ("774", "Beawar"),
       "bharatpur": ("91", "Bharatpur"), "bhilwara": ("92", "Bhilwara"), "bikaner": ("93", "Bikaner"), "bundi": ("94", "Bundi"),
       "chittorgarh": ("95", "Chittorgarh"), "chittaurgarh": ("95", "Chittorgarh"), "churu": ("96", "Churu"), "dausa": ("97", "Dausa"),
       "deeg": ("767", "Deeg"), "dholpur": ("98", "Dholpur"), "dhaulpur": ("98", "Dholpur"), "didwanakuchaman": ("768", "Didwana-Kuchaman"),
       "deedwanakuchaman": ("768", "Didwana-Kuchaman"), "dungarpur": ("99", "Dungarpur"), "ganganagar": ("100", "Ganganagar"),
       "sriganganagar": ("100", "Ganganagar"), "shriganganagar": ("100", "Ganganagar"), "hanumangarh": ("101", "Hanumangarh"),
       "jaipur": ("102", "Jaipur"), "jaisalmer": ("103", "Jaisalmer"), "jalore": ("104", "Jalore"), "jalor": ("104", "Jalore"),
       "jhalawar": ("105", "Jhalawar"), "jhunjhunu": ("106", "Jhunjhunu"), "jhunjhunun": ("106", "Jhunjhunu"), "jodhpur": ("107", "Jodhpur"),
       "karauli": ("108", "Karauli"), "khairthaltijara": ("770", "Khairthal-Tijara"), "khairthal": ("770", "Khairthal-Tijara"),
       "kota": ("109", "Kota"), "karoli": ("108", "Karauli"), "nagour": ("110", "Nagaur"), "kotputlibahror": ("782", "Kotputli-Behror"), "kotputlibehror": ("782", "Kotputli-Behror"), "nagaur": ("110", "Nagaur"), "pali": ("111", "Pali"),
       "phalodi": ("772", "Phalodi"), "pratapgarh": ("629", "Pratapgarh"), "rajsamand": ("112", "Rajsamand"),
       "salumbar": ("777", "Salumbar"), "salumber": ("777", "Salumbar"), "sawaimadhopur": ("113", "Sawai Madhopur"),
       "sikar": ("114", "Sikar"), "sirohi": ("115", "Sirohi"), "tonk": ("116", "Tonk"), "udaipur": ("117", "Udaipur")}
VACANT = re.compile(r"रिक्त")
CONTACTS = "https://lsg.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail"


def current_url(get):
    """The newest "Block Office" PDF of the Panchayati Raj Department in the Jankalyan contact rows (one POST, about 4.8 MB), so a
    new upload (new file name) is found without a code change; None when the call fails."""
    import json
    r = get(CONTACTS, method="POST", data=json.dumps({}), headers={"Content-Type": "application/json"})
    if r is None:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    rows = d.get("Data", {}).get("Data") if isinstance(d.get("Data"), dict) else d.get("Data")
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    def when(x):            # the upload month is in the file address (.../DEPTContactDetail/2026/Sep/...); row ids are not in order
        m = re.search(r"/(20\d\d)/([A-Za-z]{3})/", x.get("AttachmentUrl") or "")
        mon = months.index(m.group(2).lower()) + 1 if m and m.group(2).lower() in months else 0
        return (int(m.group(1)) if m else 0, mon, int(x.get("Id") or 0))
    best = None
    for x in rows or []:
        u = x.get("AttachmentUrl") or ""
        if x.get("IsPDF") and u.lower().endswith(".pdf") and re.match(r"(?i)\s*panchayati\s+raj\s+department", x.get("DepartmentTitle") or "") \
                and re.match(r"(?i)\s*block\s+office", x.get("ContactCategoryName") or ""):
            if best is None or when(x) > when(best):
                best = x
    if best is None:
        return None
    return best["AttachmentUrl"].replace("/Files//Content/UploadFolder/", "/WebMyWayFiles/").replace("/Files/Content/UploadFolder/", "/WebMyWayFiles/")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "discover": True, "state": "RJ", "india_only": True}}]


def stored(p, get):
    """(bytes, key) of the PDF from the bucket when the item names its saved copy (payload "stored": "<project>/<path>.pdf").
    The hub's signed url is read directly: the copy is in the bucket already; records name it in src (provenance.file_src)."""
    hub, k = getattr(get, "hub", None), p.get("stored")
    if not hub or not k:
        return None
    try:
        import requests
        url = hub.read_urls(k.split("/", 1)[0], [k])[k]
        r = requests.get(url, timeout=(20, 180))
        if r.status_code == 200 and r.content[:5] == b"%PDF-":
            return r.content, k
    except Exception:  # noqa: BLE001 - fall back to the site
        pass
    return None


def col(x):
    for k in range(len(BORDERS) - 1):
        if BORDERS[k] - 2 <= x < BORDERS[k + 1] - 2:
            return k
    return None


def page_rows(texts):
    """[{role: [pieces]}] for the rows of one page."""
    sns = sorted(((y, t.strip()) for x, y, t in texts if col(x) == 0 and re.fullmatch(r"\d{1,3}", t.strip())), reverse=True)
    if not sns:
        return []
    ys = [y for y, _ in sns]
    rows = []
    for i, (y0, sn) in enumerate(sns):
        top = (ys[i - 1] + y0) / 2 if i else y0 + 12
        bot = (ys[i + 1] + y0) / 2 if i + 1 < len(ys) else y0 - 30
        cells = {}
        for x, y, t in sorted(texts, key=lambda t: (-t[1], t[0])):
            k = col(x)
            if k is None or not (bot < y <= top) or not t.strip():
                continue
            cells.setdefault(ROLES[k], []).append(t)
        cells["sn"] = sn
        cells["_pos"] = {"row": i + 1, "sn": sn, "y": round(y0, 1)}   # row: 1-based on the page, top to bottom; y: PDF points
        rows.append(cells)
    return rows


def rows(content):
    from pypdf import PdfReader

    from dforms._util2_pdfgrid import page_parts
    reader = PdfReader(io.BytesIO(content))
    out = []
    for n, page in enumerate(reader.pages, 1):
        texts, _, _ = page_parts(reader, page)
        for r in page_rows(texts):
            r["_pos"] = {"page": n, **r.get("_pos", {})}
            out.append(r)
    return out


def text(parts, sep=" "):
    """Pieces of one cell as one text. A one-letter piece joins the text before it without a space: the print sets some names
    letter by letter ("e w y U ..." -> "ewyU...")."""
    out = ""
    for p in parts or []:
        p = p.replace("\n", " ").strip()
        if not p:
            continue
        out = out + p if (len(p) == 1 and out and sep == " " and not p.isdigit()) else (out + sep + p if out else p)
    return _esw.clean(out)


def hindi(parts):
    """Kruti Dev pieces -> Unicode ("vtesj xzkeh.k" -> "अजमेर ग्रामीण"); ¼ ½ are the print's brackets."""
    t = text(parts).replace("’", "'").replace("‘", "'")
    if not t or re.search(r"[\u0900-\u097f]", t):
        return t
    t = t.replace("pkS", "\x00")
    out = kd.convert(t).replace("\x00", "चौ").replace("¼", "(").replace("½", ")")
    return _esw.clean(re.sub(r"\(\s*", "(", re.sub(r"\s*\)", ")", out)))


def phones(mobile, std, office):
    m = text(mobile)
    mob = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", m.replace(" ", " "))
    rest = re.sub(r"(?<!\d)[6-9]\d{9}(?!\d)", " ", m)
    code = re.findall(r"(?<!\d)0?\d{2,4}(?!\d)", rest + " " + text(std))
    off = re.findall(r"(?<!\d)\d{5,8}(?!\d)", text(office))
    out = list(dict.fromkeys(mob))
    if off:
        c = code[0] if code else ""
        if c and not c.startswith("0"):
            c = "0" + c
        out.append(f"{c}-{off[0]}" if c else off[0])
    return ", ".join(out)


def build(rs, source=URL):
    recs, seen = [], set()
    for r in rs:
        ps_src = re.sub(r"\s*\(.*?\)\s*", " ", text(r.get("ps"))).strip(" ,.-")
        ps = re.sub(r"(?i)\s+gramin$", " Rural", ps_src)            # "Ajmer gramin" -> "Ajmer Rural" (the LGD block name)
        dist_raw = text(r.get("district"))
        if not ps or not dist_raw:
            continue
        code, district = LGD.get(re.sub(r"[^a-z]", "", dist_raw.lower()), ("", dist_raw.title()))
        name = hindi(r.get("name"))
        vacant = bool(VACANT.search(name))
        if vacant:
            name = ""
        email = _esw.emails(text(r.get("email"), ""))
        phone = phones(r.get("mobile"), r.get("std"), r.get("office"))
        base = f"{_esw.slug(district)}:{_esw.slug(ps_src)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="rural_development", level="block", area=ps, area_regional=hindi(r.get("ps_hi")),
                                district=district, district_code=code, state="RJ", name=name,
                                post="Vikas Adhikari (Block Development Officer)", phone=phone, email=email, source=source,
                                last_updated=LIST_DATE, vacant=True if vacant else None, cadre=hindi(r.get("cadre")),
                                home_district=text(r.get("home")), office=ps_src if ps_src != ps else None,
                                list_no=r.get("sn"), src_pos=r.get("_pos")))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    got = stored(p, get)
    content, key = got if got else (None, None)
    if content is None and p.get("discover"):
        url = current_url(get) or url
    files = []
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
        if content[:5] != b"%PDF-":
            return [], [], "not a pdf"
        files = [(f"depts/{MODULE}/vikas-adhikari-list.pdf", content, "application/pdf")]
    recs = build(rows(content), url)
    src = {"src": provenance.file_src(content, url, key)} if key else {"src_url": url}
    for _, d in recs:
        d.update(src)
    return recs, files, "" if recs else "no rows"
