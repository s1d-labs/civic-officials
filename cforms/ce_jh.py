"""Jharkhand: elected ward councillors, mayors / chairpersons (direct) and deputy mayors / vice chairpersons (indirect) of the
48 urban bodies of the Municipal (General) Election 2026 (poll 23.02.2026, count 27.02.2026).

The State Election Commission (sec.jharkhand.gov.in, MElection.aspx) lists no results for 2026 (category "Results" is empty;
its "NagarPalika Nirvachan Report 2026" has statistics only, no names). The results are on the district sites (S3WaaS,
<district>.nic.in): each District Election Officer (Municipality) publishes the result as a district gazette, "Prapatra-23"
of the Jharkhand Municipal Election Rules 2012, rule 105:
- 23 (क): ward councillors. Ruled table: name | post (वार्ड पार्षद) | reserved / unreserved | women / other |
  "XXIII <district>/<no><body> (वर्ग-ख)/वार्ड संख्या -NN".
- 23 (ख): mayor / chairperson, and later (March 2026) deputy mayor / vice chairperson: the same columns, without the ward.
The files are scans (HP Scan, NAPS2): read by OCR (Tesseract hin+eng, cforms/hr.py grid reader: lines found and erased, one
image per column). Some districts post other result tables ("Result (Chas Mayor and Wards ...)", "Result of elected
candidates ..."): the columns are found from the header words; a file without a readable member table gives one record
"ce_jh_file:<key>" (type councillor_source_file, the OCR text of its first pages) so that it can be checked by hand.

Item kinds:
- {"kind": "seed", "module": "ce_jh"}: items(get) visits the 24 district sites (known election pages; else the home page menu
  links about the 2026 municipal election) and lists the result files (link text about Prapatra 23 / gazette / result, or a
  file uploaded after the count on such a page, minus affidavits, voter lists, Form 3/5 ...). One item per file.
- {"kind": "form-ce_jh", "url", "district", "link_text", "page_url", "body"?, "lgd_code"?, "post"?}: one result file.
Record id councillor:JH:<LGD code or body slug>:<ward no | "chair" | "vice">. The district sites answer outside India.
"""
import concurrent.futures
import hashlib
import os
import re
import subprocess
import tempfile
import unicodedata
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from cforms import hr
from cforms.tn import stored
import provenance

METHOD = "ocr tesseract hin+eng (ruled grid of the Prapatra-23 district gazette, one image per column)"
ELECTION = "Jharkhand Municipal (General) Election 2026 (poll 23.02.2026, count 27.02.2026; district gazette Prapatra-23)"
LANG = "hin+eng"
MAX_PAGES = 15

# district host -> (district, election pages seen on 2026-11-12; empty = find them from the home page menu). Gap round 2026-11-14:
# the 7 districts that had none got the election pages of their archive.s1d.me copies (2026-11-05/06); the home page menus of
# Koderma and Jamtara did not lead to their result files (Koderma "Form 23 Gazette Notification for Chairperson/Ward", Jamtara
# "जिला गजट अधिसूचना ... परिणाम प्रकाशन"), and the Sahebganj site is sahibganj.nic.in.
DISTRICTS = {
    "bokaro.nic.in": ("Bokaro", ["https://bokaro.nic.in/municipality-general-election-2026/"]),
    "chatra.nic.in": ("Chatra", ["https://chatra.nic.in/municipal-election-2026/"]),
    "deoghar.nic.in": ("Deoghar", ["https://deoghar.nic.in/district-election-portal/"]),
    "dhanbad.nic.in": ("Dhanbad", ["https://dhanbad.nic.in/hi/नगरपालिका-चुनाव-2026/"]),
    "dumka.nic.in": ("Dumka", ["https://dumka.nic.in/nagarpalika-election-2026/"]),
    "jamshedpur.nic.in": ("East Singhbum", ["https://jamshedpur.nic.in/departments/district-election-office/"]),
    "garhwa.nic.in": ("Garhwa", ["https://garhwa.nic.in/hi/नगरपालिका-आम-निर्वाचन-2026/"]),
    "giridih.nic.in": ("Giridih", ["https://giridih.nic.in/municipality-election-2022-23/"]),
    "godda.nic.in": ("Godda", ["https://godda.nic.in/municipal-general-election-2026/"]),
    "gumla.nic.in": ("Gumla", ["https://gumla.nic.in/election/municipal-election/"]),
    "hazaribag.nic.in": ("Hazaribagh", ["https://hazaribag.nic.in/hi/नगरपालिका-आम-निर्वाचन-2026/"]),
    "jamtara.nic.in": ("Jamtara", ["https://jamtara.nic.in/hi/नगरपालिका-निर्वाचन-2025/"]),
    "khunti.nic.in": ("Khunti", ["https://khunti.nic.in/municipal-election-2026/"]),
    "koderma.nic.in": ("Koderma", ["https://koderma.nic.in/election-department/municipal-election/"]),
    "latehar.nic.in": ("Latehar", ["https://latehar.nic.in/hi/नगरपालिका-चुनाव-2026/"]),
    "lohardaga.nic.in": ("Lohardaga", ["https://lohardaga.nic.in/nagar-palika-election-2026-voter-list-final-roll/"]),
    "pakur.nic.in": ("Pakur", ["https://pakur.nic.in/municipal-general-election-2026/"]),
    "palamu.nic.in": ("Palamu", ["https://palamu.nic.in/municipal-election-2020-3/"]),
    "ramgarh.nic.in": ("Ramgarh", ["https://ramgarh.nic.in/नगरपालिका-चुनाव-2025/"]),
    "ranchi.nic.in": ("Ranchi", ["https://ranchi.nic.in/election-2/"]),
    "sahibganj.nic.in": ("Sahebganj", ["https://sahibganj.nic.in/municipal-general-election-2026/"]),   # the site is sahibganj.nic.in
    "seraikela.nic.in": ("Saraikela Kharsawan", ["https://seraikela.nic.in/municipal-general-election-2026/"]),
    "simdega.nic.in": ("Simdega", ["https://simdega.nic.in/en/municipal-general-elections-2026/"]),
    "chaibasa.nic.in": ("West Singhbhum", ["https://chaibasa.nic.in/municipal-election-2026/"]),
}

# LGD code -> (district, English name, body type, spellings seen on the sites and in the gazettes)
BODIES = {
    "248056": ("Bokaro", "Chas", "Municipal Corporation", ["चास", "chas"]),
    "248136": ("Bokaro", "Phusro", "Municipal Council", ["फुसरो", "phusro", "fusro"]),
    "248129": ("Chatra", "Chatra", "Municipal Council", ["चतरा", "chatra"]),
    "248049": ("Deoghar", "Deoghar", "Municipal Corporation", ["देवघर", "deoghar"]),
    "248050": ("Deoghar", "Madhupur", "Municipal Council", ["मधुपुर", "madhupur"]),
    "248055": ("Dhanbad", "Chirkunda", "Municipal Council", ["चिरकुण्डा", "चिरकुंडा", "chirkunda"]),
    "250378": ("Dhanbad", "Dhanbad", "Municipal Corporation", ["धनबाद", "dhanbad"]),
    "250352": ("Dumka", "Basukinath", "Nagar Panchayat", ["बासुकीनाथ", "बासुकिनाथ", "वासुकिनाथ", "basukinath"]),
    "248054": ("Dumka", "Dumka", "Municipal Council", ["दुमका", "dumka"]),
    "250445": ("East Singhbum", "Chakulia", "Nagar Panchayat", ["चाकुलिया", "chakulia"]),
    "250435": ("East Singhbum", "Jugsalai", "Municipal Council", ["जुगसलाई", "jugsalai"]),
    "250433": ("East Singhbum", "Mango", "Municipal Corporation", ["मानगो", "mango"]),
    "248128": ("Garhwa", "Garhwa", "Municipal Council", ["गढ़वा", "गढवा", "garhwa"]),
    "253228": ("Garhwa", "Manjhiaon", "Nagar Panchayat", ["मझिआंव", "मझिंआव", "मझियांव", "manjhiaon", "majhiaon"]),
    "274815": ("Garhwa", "Shri Banshidhar Nagar (Nagar Untari)", "Nagar Panchayat",
               ["श्री बंशीधर नगर", "बंशीधर नगर", "नगर उंटारी", "नगर उन्तरी", "banshidhar", "nagar untari"]),
    "290364": ("Giridih", "Badki Saraiya", "Nagar Panchayat", ["बड़की सरैया", "बडकी सरैया", "सरिया", "saraiya", "suriya", "sariya"]),
    "277138": ("Giridih", "Dhanwar", "Nagar Panchayat", ["धनवार", "dhanwar"]),
    "250349": ("Giridih", "Giridih", "Municipal Corporation", ["गिरिडीह", "giridih"]),
    "248051": ("Godda", "Godda", "Municipal Council", ["गोड्डा", "godda"]),
    "300370": ("Godda", "Mahagama", "Nagar Panchayat", ["महागामा", "mahagama"]),
    "248057": ("Gumla", "Gumla", "Municipal Council", ["गुमला", "gumla"]),
    "248130": ("Hazaribagh", "Hazaribag", "Municipal Corporation", ["हजारीबाग", "hazaribag"]),
    "248134": ("Jamtara", "Jamtara", "Nagar Panchayat", ["जामताड़ा", "जामताडा", "jamtara"]),
    "248135": ("Jamtara", "Mihijam", "Municipal Council", ["मिहिजाम", "mihijam"]),
    "250414": ("Khunti", "Khunti", "Nagar Panchayat", ["खूंटी", "खूँटी", "खुंटी", "khunti"]),
    "277135": ("Koderma", "Domchanch", "Nagar Panchayat", ["डोमचांच", "domchanch"]),
    "248132": ("Koderma", "Jhumri Telaiya", "Municipal Council", ["झुमरी तिलैया", "झुमरीतिलैया", "झुमरी तेलैया", "jhumri"]),
    "248131": ("Koderma", "Koderma", "Nagar Panchayat", ["कोडरमा", "koderma", "kodarma"]),
    "250326": ("Latehar", "Latehar", "Nagar Panchayat", ["लातेहार", "latehar"]),
    "248137": ("Lohardaga", "Lohardaga", "Municipal Council", ["लोहरदगा", "lohardaga"]),
    "248133": ("Pakur", "Pakur", "Municipal Council", ["पाकुड़", "पाकुड", "pakur"]),
    "253231": ("Palamu", "Bishrampur", "Municipal Council", ["बिश्रामपुर", "विश्रामपुर", "bishrampur"]),
    "300374": ("Palamu", "Chhatarpur", "Nagar Panchayat", ["छतरपुर", "chhatarpur"]),
    "300371": ("Palamu", "Hariharganj", "Nagar Panchayat", ["हरिहरगंज", "hariharganj"]),
    "250323": ("Palamu", "Hussainabad", "Nagar Panchayat", ["हुसैनाबाद", "हुस्सैनाबाद", "hussainabad", "husainabad"]),
    "250324": ("Palamu", "Medininagar", "Municipal Corporation", ["मेदिनीनगर", "medininagar", "daltonganj"]),
    "274814": ("Ramgarh", "Ramgarh", "Municipal Council", ["रामगढ़", "रामगढ", "ramgarh"]),
    "250415": ("Ranchi", "Bundu", "Nagar Panchayat", ["बुंडू", "बुण्डू", "bundu"]),
    "250413": ("Ranchi", "Ranchi", "Municipal Corporation", ["रांची", "राँची", "ranchi"]),
    "277137": ("Sahebganj", "Barharwa", "Nagar Panchayat", ["बरहरवा", "barharwa"]),
    "248053": ("Sahebganj", "Rajmahal", "Nagar Panchayat", ["राजमहल", "rajmahal"]),
    "248052": ("Sahebganj", "Sahibganj", "Municipal Council", ["साहिबगंज", "साहेबगंज", "sahibganj", "sahebganj"]),
    "253166": ("Saraikela Kharsawan", "Adityapur", "Municipal Corporation", ["आदित्यपुर", "adityapur"]),
    "276352": ("Saraikela Kharsawan", "Kapali", "Municipal Council", ["कपाली", "kapali"]),
    "250423": ("Saraikela Kharsawan", "Seraikela", "Nagar Panchayat", ["सरायकेला नगर", "सराइकेला", "seraikela nagar", "serikella"]),
    "248138": ("Simdega", "Simdega", "Municipal Council", ["सिमडेगा", "simdega"]),
    "250430": ("West Singhbhum", "Chaibasa", "Municipal Council", ["चाईबासा", "चाइबासा", "chaibasa"]),
    "250416": ("West Singhbhum", "Chakradharpur", "Municipal Council", ["चक्रधरपुर", "chakradharpur"]),
}

COUNT_EPOCH = 1772150000          # 27.02.2026 (count): S3WaaS file names are upload times in ms / 10 (17724545312707 = 02.03.2026)
WANT = re.compile(r"प्रपत्र\s*[-–—]?\s*23|form\s*[-–—]?\s*23|\b23\s*\(?\s*(क|ख|ka|kh)\b|23\s*KH|गजट|गज़ट|gaz[ae]t|gajat|"
                  r"result|परिणाम|निर्वाचित|विजयी|elected|up\s*mahap|deputy|उपमहापौर|उप\s*महापौर|उपाध्यक्ष", re.I)
NOT = re.compile(r"शपथ|affidavit|मतदाता|voter|booth|मतदान\s*केन्द्र|मतदान\s*केंद्र|polling|आरक्षण|reservation|"
                 r"(प्रपत्र|form)\s*[-–—]?\s*(3|5|24)\b|नाम\s*निर्देशन|nomination|training|प्रशिक्षण|helpline|press|"
                 r"व्यय|expenditure|panchayat\s*office|पंचायत\s*(चुनाव|निर्वाचन)|lok\s*sabha|vidhan|assembly|"
                 r"ro\s*(and|&)\s*aro|अधिसूचित|विज्ञापन|प्रचार|"
                 # files posted on the election pages after the count that are not results (gap round 2026-11-14: SIR FAQs on
                 # the Hazaribagh and Saraikela pages; Dhanbad's "Panchayat Election 2022 - Form - 23")
                 r"faq|frequently\s*asked|special\s*intensive|\bSIR\b|tender|\brfp\b|panchayat\s*election", re.I)
MENU = re.compile(r"(municipal|nagar\s*palika|nagarpalika|नगरपालिका|नगर\s*निकाय|नगर\s*पंचायत|nagar\s*nigam).*(2026|2025)|"
                  r"(2026|2025).*(municipal|nagarpalika|नगरपालिका)|municipality\s*election", re.I)


def norm(s):
    """Spelling key for Devanagari / Latin names: NFC, nukta, chandrabindu, anusvara and spaces dropped, lower case."""
    s = unicodedata.normalize("NFD", s or "")
    s = re.sub(r"[़ँं‌‍\s.\-–—_]", "", s)
    return unicodedata.normalize("NFC", s).lower()


def find_body(text, district=None):
    """The LGD code of the body a text names (longest spelling wins; bodies of the district first), else None."""
    t = norm(text)
    best = None
    for code, (dist, _, _, names) in BODIES.items():
        for n in names:
            k = norm(n)
            if k and k in t:
                score = (dist == district, len(k))
                if best is None or score > best[0]:
                    best = (score, code)
    return best[1] if best else None


def post_of(text):
    """Post words (Hindi / English) -> (position, ward key) for heads, (None, None) for a ward member."""
    t = norm(text)
    if re.search(norm("उपमहापौर") + "|" + norm("उप महापौर") + r"|deputymayor|upmahap", t):
        return "Deputy Mayor", "vice"
    if re.search(norm("उपाध्यक्ष") + r"|vicechair|deputychair|vicepresident|upadhyaksh", t):
        return "Vice Chairperson", "vice"
    if re.search(norm("महापौर") + "|" + norm("मेयर") + r"|mayor|mahapaur|mahapor", t):
        return "Mayor", "chair"
    if re.search(norm("अध्यक्ष") + r"|chair|adhyaksh|president", t):
        return "Chairperson", "chair"
    return None, None


def bodies_in(text, district=None):
    """LGD codes of all bodies a text names (spellings inside a longer matched spelling do not count twice)."""
    t, out = norm(text), set()
    for code, (_, _, _, names) in BODIES.items():
        if any(norm(n) and norm(n) in t for n in names):
            out.add(code)
    return out


def body_post(text, ctx, district):
    """(LGD code, head post) a result link names: no code when it names several bodies, no post when it is about wards."""
    both = f"{text} {ctx}"
    code = find_body(text, district) or find_body(ctx, district)
    if len(bodies_in(text) or bodies_in(ctx)) > 1:
        code = None
    post = None if re.search(r"वार्ड|ward|पार्षद", both, re.I) else post_of(both)[0]
    if post and re.search(r"mayor|महापौर|mahap", both, re.I) and re.search(r"chair|अध्यक्ष|adhyaksh", both, re.I):
        post = None           # one file for a mayor and a chairperson (Bokaro: Chas and Phusro): the post cell decides
    return code, post


def links(html, page_url):
    """Result-file links of one district election page: [(url, link text, row text)]."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["header", "footer", "nav", "script", "style"]):
        t.decompose()
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        url = urljoin(page_url, a["href"])
        if not re.search(r"\.pdf($|\?)", url, re.I) or url in seen:
            continue
        row = a.find_parent(["tr", "li", "p"])
        text = a.get_text(" ", strip=True)
        ctx = row.get_text(" ", strip=True) if row and len(row.find_all("a", href=True)) == 1 else text
        both = f"{text} {ctx}"
        m = re.search(r"/(17\d{8})\d{3,}\.pdf", url)
        after = bool(m and int(m.group(1)) >= COUNT_EPOCH) or bool(re.search(r"/uploads/2026/(0[3-9]|1[0-2])/", url))
        old = bool(re.search(r"/uploads/20(1\d|2[0-5])/", url) or m and int(m.group(1)) < COUNT_EPOCH - 90 * 86400)
        strong = bool(re.search(r"प्रपत्र\s*[-–—]?\s*23|form\s*[-–—]?\s*23|23\s*\(?\s*(क|ख)|\bresult", both, re.I))
        if after and (strong or WANT.search(both) or not NOT.search(both)) or strong and not old and not NOT.search(text):
            seen.add(url)
            out.append((url, text, ctx[:300]))
    return out


def menu_pages(html, base):
    """Links of a district home page that lead to its 2026 municipal election page."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        t = a.get_text(" ", strip=True)
        u = urljoin(base, a["href"])
        if urlsplit(u).hostname == urlsplit(base).hostname and MENU.search(f"{t} {a['href']}") and u not in out \
                and not re.search(r"\.(pdf|jpg|png)$", u, re.I):
            out.append(u)
    return out[:4]


def page_items(html, page, district):
    """Queue items for the result files of one district election page."""
    out = []
    for url, text, ctx in links(html, page):
        code, post = body_post(text, ctx, district)
        p = {"kind": "form-ce_jh", "state": "JH", "url": url, "district": district, "page_url": page, "link_text": text,
             "row_text": ctx if ctx != text else None, "election": ELECTION, "post": post}
        if code:
            p.update(lgd_code=code, body=BODIES[code][1])
        out.append({"key": "ce-jh26-" + hashlib.sha1(url.encode()).hexdigest()[:12], "payload": {k: v for k, v in p.items() if v}})
    return out


def items(get):
    out, seen = [], set()
    for host, (district, pages) in DISTRICTS.items():
        if not pages:
            r = get(f"https://{host}/")
            pages = menu_pages(r.text, r.url or f"https://{host}/") if r is not None else []
        for page in pages:
            r = get(page)
            if r is None:
                continue
            for it in page_items(r.text, page, district):
                if it["key"] not in seen:
                    seen.add(it["key"])
                    out.append(it)
    return out


# ---------------------------------------------------------------- one result file

ROLES = [("name", r"नाम|name|candidate|अभ्यर्थी|प्रत्याशी"), ("post", r"^पद$|^पद\b|post|designation"),
         ("reservation", r"आरक्षित|अनारक्षित|reserv|category|कोटि"), ("women", r"महिला|अन्य|gender|लिंग"),
         ("ward", r"वार्ड|ward"), ("party", r"दल|party"), ("votes", r"प्राप्त\s*मत|votes|मत$"),
         ("body", r"निकाय|body|क्षेत्र")]
FORM23 = ["name", "post", "reservation", "women", "body"]


def cols_of(cells):
    out = {}
    for i, c in enumerate(cells):
        t = hr.clean(c).lower()
        if not t:
            continue
        for role, rx in ROLES:
            if role not in out and re.search(rx, t, re.I):
                out[role] = i
                break
    return out


def ward_of(text):
    """Ward number after "वार्ड संख्या" / "Ward No" (Devanagari digits and OCR letter slips in the number fixed), else None."""
    t = text or ""
    m = re.search(r"(?:वार्ड|बार्ड|ward)", t, re.I)
    if not m:
        return None
    tail = t[m.end():m.end() + 24].translate(str.maketrans("०१२३४५६७८९OoIl|", "012345678900111"))
    d = re.search(r"\d{1,3}", tail)
    return str(int(d.group(0))) if d else None


def women(s):
    t = hr.clean(s)
    return True if "महिला" in t or re.search(r"(?i)women|female", t) else False if re.search(r"अन्य|other|general", t, re.I) else None


def body_cell(s):
    """'XXIII सरायकेला-खरसावाँ/08आदित्यपुर नगरनिगम (वर्ग-ख)/वार्ड संख्या -01' -> the body part."""
    parts = [x for x in re.split(r"/", s or "") if x.strip()]
    for x in parts:
        if re.search(r"नगर|nagar|निगम|परिषद|पंचायत", x, re.I):
            return hr.clean(re.sub(r"^\s*\d+\s*", "", x))
    return hr.clean(s)


def page_records(rows, p, page):
    """Grid rows of one page -> member records (empty for cover pages and pages without a member table)."""
    cols, recs = None, []
    district = p.get("district")
    for r in rows:
        cells = r["cells"]
        c = cols_of(cells)
        if "name" in c and len(c) >= 2:
            cols = {k: i for i, k in enumerate(FORM23)} if len(cells) == 5 and c.get("name") == 0 else c
            continue
        if cols is not None and len(c) >= 2 and not hr.clean(cells[cols.get("name", 0)] if cols.get("name", 0) < len(cells) else ""):
            for k, i in c.items():      # second header line (पद | आरक्षित/अनारक्षित | महिला/अन्य under "पद का विवरण")
                cols.setdefault(k, i)
            continue
        if not any(hr.clean(x) for x in cells) or all(re.fullmatch(r"[\d\s०-९]*", hr.clean(x)) for x in cells):
            provenance.skip_row(r, 'skip: not any(hr.clean(x) for x in cells) or all(re.fullmatch(r"[\\d\\s०-९]...')
            continue          # empty row or the column numbers row "1 2 3 4 5"
        use = cols or ({k: i for i, k in enumerate(FORM23)} if len(cells) == 5 else None)
        if not use:
            provenance.skip_row(r, 'skip: not use')
            continue
        at = lambda k: cells[use[k]] if k in use and use[k] < len(cells) else ""
        name = hr.clean(at("name"))
        if not name or len(name) < 3 or re.search(r"नाम|name of|योग|total", name, re.I):
            provenance.skip_row(r, 'skip: not name or len(name) < 3 or re.search(r"नाम|name of|योग|total", na...')
            continue
        row_text = " ".join(cells)
        position, head = post_of(at("post") or "")
        if not position and not at("post") and p.get("post"):
            position, head = post_of(p["post"])
        if position is None and not re.search(r"पार्षद|सदस्य|member|councillor|ward", at("post") or row_text, re.I) \
                and not ward_of(at("ward") or at("body")):
            provenance.skip_row(r, 'skip: position is None and not re.search(r"पार्षद|सदस्य|member|councillor...')
            continue
        btxt = body_cell(at("body"))
        code = find_body(btxt, district) or p.get("lgd_code") or find_body(row_text, district)
        ward = head or ward_of(at("ward")) or ward_of(at("body"))
        conf = [x for x in (r.get("conf") or []) if x is not None]
        d = {"type": "councillor", "state": "JH", "lgd_code": code,
             "body": BODIES[code][1] if code else (btxt or p.get("body")), "body_local": btxt or None,
             "body_type": BODIES[code][2] if code else None, "district": BODIES[code][0] if code else district,
             "ward_no": ward, "name": name, "position": position or "Member", "post_local": hr.clean(at("post")) or None,
             "reservation": hr.clean(at("reservation")) or None, "women_seat": women(at("women")),
             "party": hr.clean(at("party")) or None, "votes": re.sub(r"\D", "", at("votes")) or None,
             "election": p.get("election", ELECTION), "url": p["url"], "page_url": p.get("page_url"),
             "link_text": p.get("link_text"), "page": page, "read": "ocr",
             "src_pos": {"page": page, "row": r.get("row"), "y": r.get("y"), "conf": min(conf) if conf else None,
                         "cells": [hr.clean(x) for x in cells]}}
        if not d["ward_no"]:
            d["ward_no_missing"] = True
        recs.append(d)
    return recs


def record_id(d, n):
    key = d.get("lgd_code") or hr.slug(d.get("body") or "") or "unknown"
    return f"councillor:JH:{key}:{d.get('ward_no') or 'row' + str(n)}"


def ocr_page(pdf, page, tmp):
    return hr.table(pdf, page, tmp, LANG)


def plain_text(pdf, page, tmp):
    png = hr.render(pdf, page, tmp, dpi=200)
    return subprocess.run(["tesseract", png, "-", "-l", LANG, "--psm", "6"], capture_output=True, text=True).stdout


def fetch(p, get):
    if not hr.tools():
        return [], [], "tesseract not available"
    content = stored(p, get)
    r = None
    if content is None:
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    files = [] if p.get("stored") else [(f"councillors/JH/{key}.pdf", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        n = int(m.group(1)) if m else 1
        pages = list(range(1, min(n, MAX_PAGES) + 1))
        with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), (os.cpu_count() or 2) // 2))) as ex:
            tabs = dict(zip(pages, ex.map(lambda pg: ocr_page(pdf, pg, tmp), pages)))
        found = [d for pg in pages for d in page_records(tabs[pg], p, pg)]
        if not found:
            texts = [plain_text(pdf, pg, tmp)[:6000] for pg in pages[:4]]
    if not found:
        rec = {"type": "councillor_source_file", "state": "JH", "url": p["url"], "page_url": p.get("page_url"),
               "link_text": p.get("link_text"), "district": p.get("district"), "lgd_code": p.get("lgd_code"),
               "pages": n, "file": files[0][0] if files else p.get("stored"), "ocr_text": texts,
               "note": "no Prapatra-23 member table read: check by hand", "election": p.get("election", ELECTION),
               "src_pos": {"pages": list(range(1, len(texts) + 1))}, "method": "ocr tesseract hin+eng (page text)"}
        return [(f"ce_jh_file:{key}", {k: v for k, v in rec.items() if v not in (None, "")})], files, ""
    out, seen = [], {}
    for i, d in enumerate(found, 1):
        rid = record_id(d, i)
        k = seen[rid] = seen.get(rid, 0) + 1
        out.append((rid + (f"-{k}" if k > 1 else ""), {x: v for x, v in d.items() if v not in (None, "", [])}))
    return out, files, ""
