"""Nagar Nigam Kota (kotamc.org; one body again since the 2025 merger of Kota North and Kota South, LGD 303090): the officer and
employee list of the Kota North office ("Officer & Employee List" on the home page, shown through
UI/MstPdfViewer.aspx?PdfName=Kota_North.pdf; the file itself is /PDF/Kota_North.pdf; answers from Germany; live sample 2026-11-11,
not in archive.s1d.me). 7 pages, 262 rows, PDF made 2024-08-01, set in Kruti Dev 010 (converted with dforms/_ward_kd.py).
Columns: क्र.सं. | नाम अधिकारी/कर्मचारी | पद | मोबाइल नम्बर: commissioner, additional commissioner, deputy commissioners, executive /
assistant / junior engineers, town planners, revenue inspectors, health and sanitation staff, fire staff, drivers, clerks.
The list names no zone or ward of any post: records are level "body" (area "Kota North office"). A row whose cells wrap puts its
phone or the rest of its post on the lines just above and below the row number (the PDF centres the row); a post "-------"
repeats the post of the row above. Names and posts are Hindi: name and name_regional carry the same text (without श्री / श्रीमती /
सुश्री); post is English where the post is known (POSTS), post_regional as written.
rows() and post_en() are also used by dforms/ward2n_bikaner.py (the same site software and the same Kruti Dev lists).
Record ids: dept:ward2n_kota:<n> (the row number of the list).
"""
import re

from dforms import _esw, _ward, _ward_kd as kd

MODULE = "ward2n_kota"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Kota", "303090", "RJ", "Kota"
URL = "https://kotamc.org/PDF/Kota_North.pdf"

# Hindi posts of the Rajasthan corporations' lists (after Kruti Dev conversion and _ward.hi_norm) -> English. First match wins.
POSTS = (
    (r"^आयुक्त$", "Commissioner"), (r"^(अति(रिक्त)?\.?0?\s*आयुक्त)", "Additional Commissioner"),
    (r"^उपायु", "Deputy Commissioner"), (r"मुख्य\s*लेखाधिकारी", "Chief Accounts Officer"),
    (r"सहा(यक|0)\s*ले(खाधिकारी|0\s*अ0)", "Assistant Accounts Officer"), (r"^लेखाधिकारी", "Accounts Officer"),
    (r"संयुक्त\s*विधि\s*परामर्शी", "Joint Legal Adviser"), (r"उप\s*विधि\s*परामर्शी", "Deputy Legal Adviser"),
    (r"विधि\s*परामर्शी", "Legal Adviser"), (r"^सचिव", "Secretary"),
    (r"(अधि|अधी|अवि)\S*\s*अभियं?न?्?ता\s*(यांत्रिक|मैकेनिकल)", "Executive Engineer (Mechanical)"),
    (r"(अधि|अधी|अवि)\S*\s*अभियं?न?्?ता\s*विद्युत", "Executive Engineer (Electrical)"),
    (r"(अधि|अधी|अवि)\S*\s*अभियं?न?्?ता", "Executive Engineer"),
    (r"सहायक\s*अभियं?न?्?ता\s*विद्युत", "Assistant Engineer (Electrical)"), (r"सहायक\s*अभियं?न?्?ता", "Assistant Engineer"),
    (r"कनिष्ठ\s*अभियं?न?्?ता\s*विद्युत", "Junior Engineer (Electrical)"),
    (r"कनिष्ठ\s*अभियं?न?्?ता.*(मैकेनिकल|यांत्रिक)", "Junior Engineer (Mechanical)"), (r"कनिष्ठ\s*अभियं?न?्?ता", "Junior Engineer"),
    (r"सहायक\s*अग\S*\s*शमन\s*अधिकारी", "Assistant Fire Officer"), (r"अग\S*\s*शमन\s*अधिकारी|मुख्य\s*अग्नि", "Fire Officer"),
    (r"प्रभारी\s*(.+)\s*फायर\s*स्टेशन", "Fire Station Officer in charge"),
    (r"उप\s*नगर\s*नियोजक", "Deputy Town Planner"), (r"सहा(यक|0|\.)\s*नगर\s*नियोजक", "Assistant Town Planner"),
    (r"वरिष्ठ\s*प्रारूपकार", "Senior Draughtsman"), (r"प्रारूपकार", "Draughtsman"),
    (r"सहायक\s*राजस्व\s*निर[ीि]क्षक", "Assistant Revenue Inspector"), (r"राजस्व\s*निर[ीि]क्षक", "Revenue Inspector"),
    (r"राजस्व\s*अधिकारी", "Revenue Officer"), (r"सहायक\s*सां?ख्?यिकी", "Assistant Statistical Officer"),
    (r"सहायक\s*प्रशासनिक\s*अधिकारी", "Assistant Administrative Officer"), (r"अतिरिक्त\s*प्रशासनिक\s*अधिकारी", "Additional Administrative Officer"), (r"प्रशासनिक\s*अधिकारी", "Administrative Officer"),
    (r"स्वास्थ्य\s*अधिकारी", "Health Officer"), (r"स्वास्थ्य\s*निर[ीि]क्षक", "Health Inspector"),
    (r"मुख्य\s*(सफाई|स्वच्छता)\s*निर[ीि]क्षक", "Chief Sanitary Inspector"), (r"स्वच्छता\s*प्रभारी", "Sanitation In-charge"),
    (r"(सफाई|स्वच्छता)\s*निर[ीि]क्षक", "Sanitary Inspector"), (r"सफाई\s*जमादार|^जमादार", "Sanitation Jamadar"),
    (r"सहायक\s*प्रोग्रामर", "Assistant Programmer"), (r"प्रोग्रामर", "Programmer"), (r"सूचना\s*सहायक", "Information Assistant"),
    (r"पुलिस\s*उप\s*अधीक्षक", "Deputy Superintendent of Police"), (r"पुलिस\s*निर[ीि]क्षक", "Police Inspector"),
    (r"कांस्टेबल", "Constable"), (r"वरिष्ठ\s*(लिपिक|सहायक)", "Senior Assistant"), (r"कनिष्ठ\s*(लिपिक|सहायक)", "Junior Assistant"),
    (r"वाहन\s*चालक", "Driver"), (r"च0\s*श्रे0\s*क|चतुर्थ\s*श्रेणी", "Class IV Employee"), (r"गोताखोर", "Diver"),
    (r"इलेक्ट्रीशियन|वायरमैन", "Electrician"), (r"माली", "Gardener"), (r"हेल्पर", "Helper"), (r"चौकीदार", "Watchman"),
    (r"बेलदार", "Beldar (labourer)"), (r"मुंशी", "Munshi (record keeper)"), (r"ल[ीि]ड[ीि]?ं?ग\s*फायरम[ैे]न", "Leading Fireman"),
    (r"फायरम[ैे]न", "Fireman"), (r"चौकीदार", "Watchman"), (r"कुली", "Porter"), (r"^मेट$", "Mate (works supervisor)"),
    (r"मिस्त्री", "Mason"), (r"कारीगर", "Artisan"), (r"वायरम[ैे]न", "Wireman"), (r"प्याउ", "Water kiosk worker"),
)
# Latin abbreviations that the lists write next to the Kruti Dev text ("lgk;d vfHk;ark CIVIL AEN"): kept apart from the conversion.
LATIN = re.compile(r"(?<![A-Za-z])(?:IAS|RAS|RTS|RPS|CIVIL|LIGHT|XEN|AEN|JEN|AAO(?:-I{1,2})?|DLR|FO|ARI|RI|AO|EO|SI|II|III)(?![A-Za-z])|"
                   r"(?<=[a-z])(?:AAO(?:-I{1,2})?|XEN|AEN|JEN)(?![A-Za-z])")
NUM = re.compile(r"^\s*(\d{1,3})\s{1,}(?=\S)")
PHONE = re.compile(r"(?<!\d)([6-9]\d{9}|0\d{2,4}[-\s]?\d{6,8})(?!\d)")
HONOR = re.compile(r"^(श्रीमती|श्रीमति|श्री|सुश्री|डॉ0?\.?|डा0)\s*")


def items(get=None):
    return [{"key": f"{MODULE}-north-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def post_en(post):
    p = _ward.hi_norm(post)
    for rx, en in POSTS:
        if re.search(rx, p):
            return en
    en = _ward.hi_post(p)
    return en


def _cells(line):
    """[(start column, text)] of the runs of a line split by 2+ spaces."""
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def _split(seg):
    """(Kruti Dev text, [Latin abbreviations], [phones]) of one cell."""
    phones = PHONE.findall(seg)
    t = PHONE.sub(" ", seg)
    latin = LATIN.findall(t)
    t = LATIN.sub(" ", t)
    return _esw.clean(t), latin, phones


def kd_text(t):
    """Kruti Dev -> Unicode, with two fixes on top of dforms/_ward_kd.py: "pkS" is चौ (the helper gives चै), ¼ ½ are brackets."""
    t = (t or "").replace("pkS", "\x00")
    u = kd.convert(t).replace("\x00", "चौ").replace("¼", "(").replace("½", ")")
    return _esw.clean(_ward.hi_norm(u))


HONOR_KD = re.compile(r"^(Jh|Jherh|Jhefr|lqJh|Mk0|M‚0)\s")


def rows(pages):
    """Rows of a Kruti Dev staff list (pdftotext -layout pages): [{"n", "name", "service", "post", "post_latin", "phones", "note",
    "ditto"}] with name / post in Unicode Devanagari. Lines without a row number are given to the numbered line just above or below
    them when that line lacks a phone, a post or a name (the PDF centres a wrapped row on its number). A post "-------" repeats the
    post of the row above (ditto True; without its bracketed part: "कनिष्ठ अभियंता (मैकेनिकल)" -> "कनिष्ठ अभियंता")."""
    lines = []
    for pg in pages:
        for ln in pg.splitlines():
            if ln.strip() and not re.search(r"\\Users\\|^\s*\d{1,2}\s*$|Ø-?\s*l|uke\s+(vf/kdkjh|in\b)|^\s*la-\s*$|eksckbZy", ln):
                lines.append(ln)
    num_at = [i for i, ln in enumerate(lines) if NUM.match(ln)]
    claimed = set()
    out, last_post = [], ""
    for i in num_at:
        m = NUM.match(lines[i])
        cells = [seg for _, seg in _cells(" " * m.end() + lines[i][m.end():])]
        name, service, post_parts, latin, phones, notes, dash = "", [], [], [], [], [], False
        for k, seg in enumerate(cells):
            t, lat, ph = _split(seg)
            phones += ph
            if re.fullmatch(r"-{3,}", t):
                dash = True
                continue
            if k == 0 and t and (HONOR_KD.match(t) or len(cells) > 1):
                name, service = t, lat
            else:
                latin += lat
                if t:
                    post_parts.append(t)
        if not phones or not (post_parts or latin or dash) or not name:
            for j, above in ((i - 1, True), (i + 1, False)):
                if not (0 <= j < len(lines)) or j in claimed or NUM.match(lines[j]):
                    continue
                claimed.add(j)
                for seg in [seg for _, seg in _cells(lines[j])]:
                    t, lat, ph = _split(seg)
                    phones += ph
                    if not t or re.fullmatch(r"-{3,}", t):
                        continue
                    if re.fullmatch(r"¼.*½", t) and "fuyfEcr" in t:
                        notes.append(kd_text(t).strip("()"))
                    elif not name and HONOR_KD.match(t):
                        name, service = t, lat
                    else:
                        latin += lat
                        post_parts.insert(0, t) if above else post_parts.append(t)
        post = kd_text(" ".join(post_parts)) if post_parts else ""
        ditto = False
        if not post and not latin and (dash or last_post):
            post, ditto = re.sub(r"\s*\([^)]*\)$", "", last_post), True
        last_post = post or last_post
        nm = _esw.clean(HONOR.sub("", kd_text(name))) if name else ""
        out.append({"n": m.group(1), "name": nm, "service": " ".join(service), "post": post,
                    "post_latin": " ".join(dict.fromkeys(latin)), "phones": list(dict.fromkeys(phones)), "note": "; ".join(notes),
                    "ditto": ditto})
    return out


def record_of(module, r, seen, *, body, lgd, state, district, area, source, key=None, **extra):
    hi = _esw.clean(r["post"])
    en = post_en(hi) if hi else ""
    if not en or en == hi:
        en = r["post_latin"] or hi
    post_regional = " ".join(x for x in (hi, r["post_latin"]) if x) or None
    return _ward.record(module, key or r["n"], seen, body=body, lgd=lgd, state=state, district=district, level="body", area=area,
                        post=en or "Staff", post_regional=post_regional, name=r["name"], name_regional=r["name"] or None,
                        service=r["service"] or None, phone=", ".join(r["phones"]), notes=r["note"] or None,
                        post_from_row_above=True if r["ditto"] else None, vacant=None if r["name"] else True, source=source, **extra)


def parse(pages, p):
    seen, recs = set(), []
    for r in rows(pages):
        if not (r["name"] or r["phones"] or r["post"]):
            continue
        recs.append(record_of(MODULE, r, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, area="Kota North office",
                              source=p["url"], list_of="Nagar Nigam Kota North (before the 2025 merger)", file_date="2024-08-01"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "kota-north-officers", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no rows (pdftotext missing?)"
