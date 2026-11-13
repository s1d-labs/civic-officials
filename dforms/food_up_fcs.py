"""Uttar Pradesh: officers of the Food and Civil Supplies Department (Khadya evam Rasad Vibhag), from the department's own two
contact files, linked on fcs.up.gov.in (home page, "Contact Us"):

1. https://fcs.up.gov.in/PDF/contacts/contact_details.pdf (11 pages, "Microsoft: Print To PDF", text layer in Kruti Dev 010,
   converted with dforms/_ward_kd.py): one table per group of posts, each under a Hindi heading:
   ministers, heads of the department (state), Regional Food Controllers (18 divisions), Regional Food Marketing Officers
   (18), District Food Marketing Officers (75 districts), Joint / Deputy Commissioners (Food) (18 divisions), District Supply
   Officers (75 districts: name, office phone, CUG mobile) and the divisional accounts officers. Columns: serial | division
   (only on a division's first row) | district | name | office phone | CUG mobile. A vacant post has no name.
2. https://fcs.up.gov.in/PDF/contacts/email_id.pdf (10 pages, English): e-mail of each RFC, RFMO, JC/DC (Food), DSO, DFMO
   and accounts office ("1   dsofaizabad11@gmail.com   DSO Faizabad").

Records (depts.py contract, dept food_supplies): level state / division / district; area = the division or district (English
LGD name for districts, Hindi as the file gives it in area_regional), district + district_code (LGD) on district rows, post in
English and post_regional in Hindi, name in Hindi (the file gives no English names), phone = office phone and CUG mobile.
The e-mail of each office goes on its contact row (districts by LGD code, divisions by name); an e-mail without a contact row
stays a record of its own. One queue item = both files (2 GETs). Ids: dept:food_up_fcs:<contacts|emails>:<section>:<area or n>.
Both files are kept in the bucket. pdftotext / pypdf layout text, a few pages: light work.
"""
import re

from dforms import _esw, _field, _ward_kd as kd
import provenance

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "food_up_fcs"
CONTACTS = "https://fcs.up.gov.in/PDF/contacts/contact_details.pdf"
EMAILS = "https://fcs.up.gov.in/PDF/contacts/email_id.pdf"

# Hindi heading (after conversion) -> (section key, English post or None = the row's own post, level, columns before the name)
SECTIONS = [
    (r"माननीय मंत्री", ("ministers", None, "state", 0)),
    (r"शीर्ष अधिकारी", ("heads", None, "state", 0)),
    (r"सम्भागीय खाद्य नियंत्रक", ("rfc", "Regional Food Controller", "division", 1)),
    (r"सम्भागीय खाद्य विपणन", ("rfmo", "Regional Food Marketing Officer", "division", 1)),
    (r"जिला खाद्य विपणन", ("dfmo", "District Food Marketing Officer", "district", 2)),
    (r"संयुक्त आयुक्त\s*/\s*उपायुक्त", ("jcdc", None, "division", 0)),
    (r"जिला पूर्ति अधिकारी", ("dso", "District Supply Officer", "district", 2)),
    (r"लेखाधिकारी", ("accounts", None, "division", 0)),
]
HONORIFIC = re.compile(r"^(श्री|श्रीमती|सुश्री|डा0|डॉ0|डा\.|कु0|प्र0\s*श्री)")
JCDC_POST = re.compile(r"\s*((?:प्र0\s*)?(?:संयुक्त आयुक्त|उपायुक्त)\s*\(खाद्य\))\s*$")
POSTS_EN = [(r"संयुक्त आयुक्त", "Joint Commissioner (Food)"), (r"उपायुक्त", "Deputy Commissioner (Food)"),
            (r"सं0\s*व0\s*ले0\s*अ0|वरिष्ठ लेखाधिकारी", "Divisional Senior Accounts Officer"),
            (r"सं0\s*ले0\s*अ0|स0\s*ले0\s*अ0|लेखाधिकारी", "Divisional Accounts Officer")]

# district names as the file spells them (Hindi, after conversion; letters only) -> (LGD code, LGD name)
UP = {"आगरा": ("118", "Agra"), "अलीगढ": ("119", "Aligarh"), "अम्बेडकरनगर": ("121", "Ambedkar Nagar"), "अमेठी": ("640", "Amethi"),
      "अमरोहा": ("154", "Amroha"), "जेपीनगर": ("154", "Amroha"), "औरैया": ("122", "Auraiya"), "फैजाबाद": ("140", "Ayodhya"),
      "अयोध्या": ("140", "Ayodhya"), "आजमगढ": ("123", "Azamgarh"), "बागपत": ("124", "Baghpat"), "बहराइच": ("125", "Bahraich"),
      "बलिया": ("126", "Ballia"), "बलरामपुर": ("127", "Balrampur"), "बांदा": ("128", "Banda"), "बाँदा": ("128", "Banda"),
      "बाराबंकी": ("129", "Bara Banki"), "बरेली": ("130", "Bareilly"), "बस्ती": ("131", "Basti"), "भदोही": ("179", "Bhadohi"),
      "संतरविदासनगर": ("179", "Bhadohi"), "सन्तरविदासनगर": ("179", "Bhadohi"), "बिजनौर": ("132", "Bijnor"),
      "बदायूं": ("133", "Budaun"), "बदायूँ": ("133", "Budaun"), "बुलन्दशहर": ("134", "Bulandshahr"), "बुलंदशहर": ("134", "Bulandshahr"),
      "चन्दौली": ("135", "Chandauli"), "चंदौली": ("135", "Chandauli"), "चित्रकूट": ("136", "Chitrakoot"), "देवरिया": ("137", "Deoria"),
      "एटा": ("138", "Etah"), "इटावा": ("139", "Etawah"), "फर्रूखाबाद": ("141", "Farrukhabad"), "फर्रुखाबाद": ("141", "Farrukhabad"),
      "फतेहपुर": ("142", "Fatehpur"), "फिरोजाबाद": ("143", "Firozabad"), "गौतमबुद्धनगर": ("144", "Gautam Buddha Nagar"),
      "जी0बी0नगर": ("144", "Gautam Buddha Nagar"), "जीबीनगर": ("144", "Gautam Buddha Nagar"), "गाजियाबाद": ("145", "Ghaziabad"),
      "गाजीपुर": ("146", "Ghazipur"), "गोण्डा": ("147", "Gonda"), "गोंडा": ("147", "Gonda"), "गोरखपुर": ("148", "Gorakhpur"),
      "हमीरपुर": ("149", "Hamirpur"), "हापुड": ("661", "Hapur"), "हरदोई": ("150", "Hardoi"), "हाथरस": ("163", "Hathras"),
      "जालौन": ("151", "Jalaun"), "जौनपुर": ("152", "Jaunpur"), "झांसी": ("153", "Jhansi"), "झाँसी": ("153", "Jhansi"),
      "कन्नौज": ("155", "Kannauj"), "कानपुरदेहात": ("156", "Kanpur Dehat"), "कानपुरनगर": ("157", "Kanpur Nagar"),
      "कासगंज": ("633", "Kasganj"), "कांशीरामनगर": ("633", "Kasganj"), "कौशाम्बी": ("158", "Kaushambi"), "खीरी": ("159", "Kheri"),
      "लखीमपुरखीरी": ("159", "Kheri"), "कुशीनगर": ("160", "Kushinagar"), "ललितपुर": ("161", "Lalitpur"), "लखनऊ": ("162", "Lucknow"),
      "महोबा": ("165", "Mahoba"), "महराजगंज": ("164", "Mahrajganj"), "महाराजगंज": ("164", "Mahrajganj"), "मैनपुरी": ("166", "Mainpuri"),
      "मथुरा": ("167", "Mathura"), "मऊ": ("168", "Mau"), "मेरठ": ("169", "Meerut"), "मिर्जापुर": ("170", "Mirzapur"),
      "मुरादाबाद": ("171", "Moradabad"), "मुजफ्फरनगर": ("172", "Muzaffarnagar"), "पीलीभीत": ("173", "Pilibhit"),
      "प्रतापगढ": ("174", "Pratapgarh"), "इलाहाबाद": ("120", "Prayagraj"), "प्रयागराज": ("120", "Prayagraj"),
      "रायबरेली": ("175", "Rae Bareli"), "रामपुर": ("176", "Rampur"), "सहारनपुर": ("177", "Saharanpur"), "सम्भल": ("659", "Sambhal"),
      "संभल": ("659", "Sambhal"), "संतकबीरनगर": ("178", "Sant Kabir Nagar"), "सन्तकबीरनगर": ("178", "Sant Kabir Nagar"),
      "शाहजहांपुर": ("180", "Shahjahanpur"), "शाहजहाँपुर": ("180", "Shahjahanpur"), "शामली": ("660", "Shamli"),
      "श्रावस्ती": ("181", "Shrawasti"), "सिद्धार्थनगर": ("182", "Siddharthnagar"), "सीतापुर": ("183", "Sitapur"),
      "सोनभद्र": ("184", "Sonbhadra"), "सुल्तानपुर": ("185", "Sultanpur"), "उन्नाव": ("186", "Unnao"), "वाराणसी": ("187", "Varanasi")}
# English spellings of the e-mail file -> LGD (the rest match LGD names letter for letter)
UP_EN = {"faizabad": "140", "allahabad": "120", "jpnagaramroha": "154", "jpnagar": "154", "noida": "144", "gbnagar": "144",
         "gbnagarnoida": "144", "kasganj": "633", "kanshiramnagarkasganj": "633", "bhadohi": "179", "santravidasnagarbhadohi": "179",
         "srnagarbhadohi": "179", "ramabainagar": "156", "raebareilly": "175", "chandoli": "135", "balliya": "126", "bulandshahar": "134", "aurraiya": "122",
         "siddharthanagar": "182", "gazipur": "146", "lakhimpurkheri": "159", "kheri": "159", "barabanki": "129", "raebareli": "175",
         "maharajganj": "164", "siddharthnagar": "182", "shravasti": "181", "kanpurnagar": "157", "kanpurdehat": "156",
         "santkabirnagar": "178", "skn": "178", "badaun": "133", "ambedkarnagar": "121", "hapur": "661", "panchsheelnagarhapur": "661"}


def hindi(s):
    """Kruti Dev text -> Unicode Devanagari; Latin capitals in brackets ("¼ADM½", "¼SP½") stay Latin; "]" is the print's comma."""
    s = (s or "").strip()
    if not s or re.search(r"[ऀ-ॿ]", s):
        return _esw.clean(s)
    keep = re.findall(r"¼([A-Z]{2,5})½", s)
    s = re.sub(r"¼[A-Z]{2,5}½", "\x01", s).replace("pkS", "\x00")
    out = kd.convert(s).replace("\x00", "चौ").replace("¼", "(").replace("½", ")").replace("]", ",")
    for k in keep:
        out = out.replace("\x01", f"({k})", 1)
    return _esw.clean(out.strip(" ,"))


def key(s):
    """District key: the consonants and vowel letters only (code points 0x905-0x939: no vowel signs, halant, nukta, digits,
    spaces or brackets), so the file's spellings match ("बदाॅयू" = "बदायूं", "झाॅसी" = "झांसी", "मुजफफरनगर" = "मुजफ्फरनगर",
    "अम्ेबडकरनगर" = "अम्बेडकरनगर")."""
    return "".join(c for c in re.sub(r"\(.*?\)", "", s or "") if 0x905 <= ord(c) <= 0x939)


SKEL = {}
for _k, _v in UP.items():
    SKEL.setdefault(key(_k), _v)


def lgd(name):
    return SKEL.get(key(name), ("", ""))


def phones_of(raw):
    """Office phone(s) and CUG mobile(s) in a raw row (after the serial): "05212665277", "0522-2288658", "0522   2789523"."""
    out = []
    for m in re.finditer(r"(?<!\d)(0\d{2,4})(?:\s{1,4}|-)(\d{6,8})(?!\d)|(?<!\d)(0\d{9,10})(?!\d)|(?<!\d)([6-9]\d{9})(?!\d)", raw):
        if m.group(1):
            out.append(f"{m.group(1)}-{m.group(2)}")
        else:
            out.append(m.group(3) or m.group(4))
    return list(dict.fromkeys(out))


def strip_numbers(raw):
    raw = re.sub(r"(?<!\d)0\d{2,4}(?:\s{1,4}|-)\d{6,8}(?!\d)", " ", raw)
    raw = re.sub(r"(?<!\d)\d{6,11}(?!\d)", " ", raw)
    return raw


def chunks(raw):
    """Text cells of a layout line (two or more spaces apart), numbers and "--" taken out."""
    return [c for c in (x.strip() for x in re.split(r"\s{2,}", strip_numbers(raw))) if c and not re.fullmatch(r"[-–.]+|\d{1,4}", c)]


def section_of(line_hi):
    for rx, sec in SECTIONS:
        if re.search(rx, line_hi):
            return sec
    return None


def lines_of(text):
    """(page, line, raw line) of a layout text with pages split by form feeds (source trail: 1-based page and line)."""
    for pg, ptext in enumerate(text.split("\f"), 1):
        for n, raw in enumerate(ptext.split("\n"), 1):
            yield pg, n, raw


def parse_contacts(text, url=CONTACTS):
    """Records of the contact file, from its layout text."""
    rows, sec, division, pre, last = [], None, "", [], None
    for pg, n_line, raw in lines_of(text):
        if not raw.strip():
            provenance.skipped("empty")
            continue
        m = re.match(r"^\s*(\d{1,3})\s+(.*)$", raw)
        hi = hindi(raw)
        if not m:
            s = section_of(hi)
            if s and not re.search(r"क्रमांक|अधिकारी का नाम\s", hi):
                sec, division, pre, last = s, "", [], None
                continue
            if sec is None or re.search(r"क्रमांक|नम्बर|नंबर|^नं0|^का नाम|टेलीफोन", hi):
                provenance.skipped('skip: sec is None or re.search(r"क्रमांक|नम्बर|नंबर|^नं0|^का नाम|टेलीफोन"...')
                continue
            cs = chunks(raw)
            if len(cs) != 1:
                provenance.skipped('skip: len(cs) != 1')
                continue
            frag = hindi(cs[0])
            if last is not None and last.get("_frag_district"):
                last["district"] = _esw.clean(last["district"] + " " + frag)
                last["_frag_district"] = False
            else:
                pre.append((frag, raw))
            continue
        if sec is None:
            provenance.skipped('skip: sec is None')
            continue
        body = m.group(2)
        if re.fullmatch(r"[\d\s]+", body):        # the column-number row "1 2 3 4 5 6"
            provenance.skipped('skip: re.fullmatch(r"[\\d\\s]+", body)')
            continue
        cs = []
        for c in (hindi(c) for c in chunks(body)):
            mm = re.search(r"\s((श्री|श्रीमती|सुश्री|डा0|डॉ0|कु0)\s.*)$", c)
            if mm and not HONORIFIC.match(c):      # "जी0बी0नगर श्री चमन शर्मा": district and name one space apart
                cs += [c[: mm.start()].strip(), mm.group(1)]
            else:
                cs.append(c)
        r = {"sec": sec, "sn": m.group(1), "phones": phones_of(body), "district": "", "division": "", "name": "", "post": "",
             "_pos": {"page": pg, "line": n_line, "line_text": raw}}
        name_i = next((i for i, c in enumerate(cs) if HONORIFIC.match(c)), None)
        lead = cs[:name_i] if name_i is not None else cs[: sec[3]] if sec[3] else []
        rest = cs[name_i:] if name_i is not None else cs[len(lead):]
        if sec[3] == 2:                        # division | district | name
            lead = [c for c in lead if not re.fullmatch(r"\(.*\)", c)]
            if len(lead) >= 2:
                division = lead[0]
                r["district"] = lead[1]
            elif len(lead) == 1:
                r["district"] = lead[0]
            r["division"] = division
            if pre and not r["district"]:
                r["district"] = pre[-1][0]
                r["_frag_district"] = True
            elif pre and last is not None:
                last["name"] = _esw.clean(last["name"] + " " + " ".join(f for f, _ in pre))
            r["name"] = rest[0] if rest else ""
        elif sec[3] == 1:                      # division | name
            if lead:
                r["division"] = lead[0]
            r["name"] = rest[0] if rest else ""
        else:                                  # name | post | (division)
            if pre and last is not None:
                last["name"] = _esw.clean(last["name"] + " " + " ".join(f for f, _ in pre))
            cells = cs
            if sec[0] == "jcdc":
                if cells and HONORIFIC.match(cells[0]):
                    mm = JCDC_POST.search(cells[0])
                    if mm:
                        cells = [cells[0][: mm.start()], mm.group(1)] + cells[1:]
                else:
                    cells = [""] + cells
                r["name"], r["post"] = (cells + ["", ""])[:2]
                r["division"] = cells[2] if len(cells) > 2 else ""
            elif sec[0] == "accounts":         # "name, post" | division (the post may be on the next line)
                r["name"] = cells[0] if cells else ""
                r["division"] = cells[1] if len(cells) > 1 else ""
            else:
                r["name"] = cells[0] if cells else ""
                r["post"] = cells[1] if len(cells) > 1 else ""
        pre = []
        rows.append(r)
        last = r
    return build(rows, url)


def post_en(sec, post_hi):
    if sec[1]:
        return sec[1]
    for rx, en in POSTS_EN:
        if re.search(rx, post_hi or ""):
            return en
    return None


def build(rows, url):
    recs, seen = [], set()
    for r in rows:
        sec = r["sec"]
        name = _esw.clean(r["name"])
        if sec[0] == "accounts":
            mm = re.search(r"[, ]\s*((?:सं0|स0)\s*(?:व0)?\s*ले0\s*अ0)\s*$", name)
            if mm:
                r["post"], name = mm.group(1), name[: mm.start()].strip(" ,")
        if re.search(r"रिक्त|vacant", name, re.I):
            name = ""
        area_hi = r["district"] if sec[2] == "district" else r["division"]
        code, en = lgd(r["district"]) if sec[2] == "district" else ("", "")
        k = f"{sec[0]}:{_esw.slug(en) or re.sub(r'[\s()]+', '-', area_hi).strip('-') or r['sn']}"
        if k in seen or not (en or area_hi):
            k = f"{sec[0]}:{r['sn']}"
        seen.add(k)
        post_hi = r["post"] or {"rfc": "सम्भागीय खाद्य नियंत्रक", "rfmo": "सम्भागीय खाद्य विपणन अधिकारी",
                                "dfmo": "जिला खाद्य विपणन अधिकारी", "dso": "जिला पूर्ति अधिकारी"}.get(sec[0], "")
        recs.append(_esw.record(
            MODULE, f"contacts:{k}", dept="food_supplies", level=sec[2], area=en or area_hi or "Uttar Pradesh",
            area_regional=area_hi or None, district=en or None, district_code=code or None,
            division_regional=r["division"] if sec[2] == "district" else None, state="UP",
            post=post_en(sec, post_hi) or post_hi, post_regional=post_hi, name=name, phone=", ".join(r["phones"]),
            vacant=True if not name and sec[0] not in ("ministers", "heads") else None, section=sec[0],
            office_id=k, list_no=r["sn"], source=url, src_url=url, src_pos=r.get("_pos")))
    return recs


EMAIL_SECTIONS = [(r"regional food controller", ("rfc", "Regional Food Controller", "division")),
                  (r"regional food marketing", ("rfmo", "Regional Food Marketing Officer", "division")),
                  (r"joint commissioner|deputy commissioner", ("jcdc", "Joint / Deputy Commissioner (Food)", "division")),
                  (r"district supply officer", ("dso", "District Supply Officer", "district")),
                  (r"district food marketing", ("dfmo", "District Food Marketing Officer", "district")),
                  (r"accounts officer", ("accounts", "Divisional Accounts Officer", "division"))]
LGD_EN = {re.sub(r"[^a-z]", "", en.lower()): code for code, en in set(UP.values())}


def parse_emails(text, url=EMAILS):
    """Records of the e-mail file: one per office ("1  dsofaizabad11@gmail.com   DSO Faizabad"); a bracket line under a row
    ("(NOIDA)", "(Kasganj)") belongs to the row above."""
    recs, sec, last, n = [], None, None, 0
    for pg, n_line, raw in lines_of(text):
        t = _esw.clean(raw)
        if not t:
            provenance.skipped("empty")
            continue
        s = next((v for rx, v in EMAIL_SECTIONS if re.search(rx, t, re.I) and "@" not in t), None)
        if s:
            sec, last = s, None
            continue
        if sec is None:
            provenance.skipped('skip: sec is None')
            continue
        em = _esw.emails(t)
        label = _esw.clean(re.sub(r"^\d{1,3}\s*|\S+@\S+|,", " ", t))
        if not em:
            if last is not None and label:
                last["label"] = _esw.clean(last["label"] + " " + label)
            continue
        if not re.match(r"^\s*\d", raw) and last is not None:          # a second address of the row above
            last["email"] = last["email"] + ", " + em
            continue
        last = {"sec": sec, "email": em, "label": label, "_pos": {"page": pg, "line": n_line, "line_text": raw}}
        recs.append(last)
    out, seen = [], set()
    for r in recs:
        sec = r["sec"]
        area = re.sub(r"^(rfc|rmo|rfmo|dso|dfmo|drmo|dmfo|dc|jc|ac|addl\.?|jc/dc|srao|rao|ao)\b\.?\s*", "", r["label"], flags=re.I).strip()
        code = ""
        if sec[2] == "district":
            ks = [re.sub(r"[^a-z]", "", x.lower()) for x in [area, re.sub(r"\(.*?\)", "", area)] + re.findall(r"\((.*?)\)", area)]
            code = next((LGD_EN.get(k) or UP_EN.get(k) for k in ks if LGD_EN.get(k) or UP_EN.get(k)), "")
        n += 1
        k = f"{sec[0]}:{code or _esw.slug(area) or n}"
        if k in seen:
            k = f"{k}:{n}"
        seen.add(k)
        en = next((e for c, e in set(UP.values()) if c == code), "") if code else ""
        out.append(_esw.record(MODULE, f"emails:{k}", dept="food_supplies", level=sec[2], area=en or area, district=en or None,
                               district_code=code or None, state="UP", post=sec[1], email=r["email"], label=r["label"],
                               section=sec[0], office_id=k, source=url, src_url=url, src_pos=r.get("_pos")))
    return out


# the 18 divisions (Hindi as the contact file spells them, any spelling with the same letters) -> English name of the e-mail file
DIVISIONS = {"मेरठ": "Meerut", "सहारनपुर": "Saharanpur", "मुरादाबाद": "Moradabad", "बरेली": "Bareilly", "लखनऊ": "Lucknow",
             "आगरा": "Agra", "अलीगढ": "Aligarh", "कानपुर": "Kanpur", "फैजाबाद": "Faizabad", "देवीपाटन": "Devipatan",
             "गोरखपुर": "Gorakhpur", "बस्ती": "Basti", "आजमगढ": "Azamgarh", "वाराणसी": "Varanasi", "विन्ध्याचल": "Mirzapur",
             "मिर्जापुर": "Mirzapur", "इलाहाबाद": "Allahabad", "झांसी": "Jhansi", "चित्रकूट": "Chitrakoot"}
DIV_SKEL = {key(k): v for k, v in DIVISIONS.items()}


def join_emails(recs, emails):
    """The e-mail of each office (e-mail file) on its row of the contact file: district rows by LGD code, division rows by the
    division name. Returns (contact records with emails, e-mail records that matched no contact row)."""
    by, used = {}, set()
    for rid, d in emails:
        sec = d["section"]
        k = (sec, d.get("district_code") or re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", d["area"]).lower()))
        by.setdefault(k, (rid, d))
    out = []
    for rid, d in recs:
        sec = d.get("section")
        if d.get("district_code"):
            k = (sec, d["district_code"])
        else:
            k = (sec, re.sub(r"[^a-z]", "", DIV_SKEL.get(key(d.get("area_regional") or ""), "").lower()))
        hit = by.get(k)
        if hit:
            d = dict(d, email=hit[1]["email"], email_source=hit[1]["source"])
            if hit[1].get("src_pos"):         # where the e-mail was read (the e-mail file), next to the contact row's own place
                d["src_pos"] = {**d.get("src_pos", {}), "email": hit[1]["src_pos"]}
            used.add(hit[0])
        out.append((rid, d))
    return out, [e for e in emails if e[0] not in used]


def items(get=None):
    return [{"key": f"{MODULE}:contacts", "payload": {"reader": MODULE, "url": CONTACTS, "emails_url": EMAILS, "state": "UP",
                                                      "india_only": True}}]


def fetch(p, get):
    """One item = the contact file + the e-mail file (2 GETs); the e-mails go on the contact rows, unmatched e-mails stay records
    of their own. Without the e-mail file the contact rows still go in."""
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    files = [(f"depts/{MODULE}/contacts.pdf", r.content, "application/pdf")]
    recs = parse_contacts(_field.pdf_text(r.content), p["url"])
    if p.get("emails_url"):
        e = get(p["emails_url"])
        if e is not None and e.content[:5] == b"%PDF-":
            files.append((f"depts/{MODULE}/emails.pdf", e.content, "application/pdf"))
            recs, rest = join_emails(recs, parse_emails(_field.pdf_text(e.content), p["emails_url"]))
            recs += rest
    return recs, files, "" if recs else "no rows"
