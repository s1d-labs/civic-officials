"""Madhya Pradesh: the state government's own diary (diary.mp.gov.in, "Madhya Pradesh Diary And Calendar", Jansampark /
GAD). One page per section: https://diary.mp.gov.in/home/index?id=<n>, one HTML table each (class "table table-bordered"),
header row th.tabHead, group rows th.tabSubHead (one or more <b>: department, then the body), data rows <td>; a cell with
several values separates them with <br>. Checked from the archive copies (2026-11-06) and live from dev-vps-3 (2026-11-13):
the host sends an incomplete certificate chain (the task's insecure retry is needed: records get tls_unverified); answers
from Mumbai, abroad unchecked.

Sections read (SECTIONS below): Chief Minister, CM office, CM house office, Mantralaya officers by department (id 9: Chief
Secretary, ACS, PS, Secretaries, Additional / Deputy Secretaries of every department), corporations and boards (10),
council of ministers (11), MP government offices in New Delhi (15), heads of departments (16), zila panchayat presidents and
CEOs (20), mayors and municipal commissioners (21), commissions (23: PSC, SEC, information, human rights, women, child rights
...), universities (24), industrial court (25), Lokayukta (26), Speaker / Assembly secretariat / Deputy Speaker / Leader of
Opposition (27-29, 32), Governor and Raj Bhavan (30, 31), the division grid (46: per division the office and residence
phones of the Divisional Commissioner, IG, Additional Commissioner, DIG, CCF, Deputy Commissioners, Chief Engineers, Joint
Directors) and the district grid (48: per district the Collector, SP, District Judge, ADM, ZP CEO, DFO, municipal
commissioner, CMHO, EEs, Deputy Director Agriculture, DEO). Left out: MLAs (2) and MPs (33) (other readers), central
government pages (37-45, 51), MP cadre officers posted in Delhi (17-19).

Records (_state.rec): level state for the secretariat, HoDs, commissions, boards, ministers; division for the grid of id 46
(division, LGD districts from dforms/st_div_mp.json); district for ids 20, 21, 48 (district + LGD code). Names, posts and
departments in Hindi as the page writes them (post_regional = post); post_kind from the Hindi post (KINDS); post_en for the
grid columns. Phones: phone = office phones, phone_residence, fax, epabx, staff; residence address in residence_address
(public on the page: kept). Every cell in "cells". src_pos {"table", "row"} (+ "col" for the grid cells).
Ids: dept:st_mp_diary:<section id>:<row no>[:<column no>].
One queue item = one section page (1 GET).
"""
import re

from dforms import _esw, _state, _trail
import provenance

METHOD = "html table (diary.mp.gov.in section page: header th.tabHead, group rows th.tabSubHead)"
MODULE = "st_mp_diary"
BASE = "https://diary.mp.gov.in/home/index?id="

# section id -> (mode, level, body_kind, body when the page has no group rows)
SECTIONS = {
    3: ("people", "state", "other", "मध्यप्रदेश उच्च न्यायालय"),
    6: ("people", "state", "cm_office", "मुख्यमंत्री"),
    7: ("people", "state", "cm_office", "मुख्यमंत्री कार्यालय"),
    8: ("people", "state", "cm_office", "मुख्यमंत्री निवास कार्यालय"),
    9: ("people", "state", "secretariat", "मंत्रालय"),
    10: ("people", "state", "other", ""),
    11: ("people", "state", "cm_office", "मंत्रि-परिषद्"),
    15: ("people", "state", "department", "नई दिल्ली स्थित मध्यप्रदेश शासन के कार्यालय"),
    16: ("people", "state", "directorate", "विभागाध्यक्ष"),
    20: ("stacked", "district", "other", "जिला पंचायत"),
    21: ("stacked", "district", "other", "नगरपालिक निगम"),
    23: ("people", "state", "commission", ""),
    24: ("people", "state", "other", ""),
    25: ("people", "state", "other", "औद्योगिक न्यायालय मध्यप्रदेश"),
    26: ("people", "state", "commission", "लोकायुक्त कार्यालय, मध्यप्रदेश"),
    27: ("people", "state", "other", "विधान सभा"),
    28: ("people", "state", "other", "विधान सभा सचिवालय"),
    29: ("people", "state", "other", "विधान सभा"),
    30: ("people", "state", "governor", "राजभवन"),
    31: ("people", "state", "governor", "राज्यपाल का सचिवालय"),
    32: ("people", "state", "other", "विधान सभा"),
    46: ("grid", "division", "division", ""),
    48: ("grid", "district", "other", ""),
}

# header words -> field (first match wins)
COLS = [
    (r"निवास स्थान\s*का पता|निवास स्थान", "residence_address"),
    (r"कार्यालय का पता", "address"),
    (r"निवास दूरभाष", "phone_residence"),
    (r"कार्यालय दूरभाष", "phone_office"),
    (r"विधान सभा दूरभाष", "phone_assembly"),
    (r"ईपीएबीएक्स", "epabx"),
    (r"निजी स्टाफ", "staff"),
    (r"फैक्स", "fax"),
    (r"ई-?\s*मेल", "email"),
    (r"वेबसाइट", "website"),
    (r"कक्ष", "room"),
    (r"मंत्रिपरिषद विभाग|विभाग का नाम", "portfolio"),
    (r"^पद$", "post"),
    (r"नाम", "name"),
]

# Hindi post -> rank key (_state.RANK), longest / most specific first
KINDS = [
    (r"राज्यपाल", "governor"), (r"मुख्यमंत्री", "chief_minister"), (r"मंत्री", "minister"),
    (r"अपर मुख्य सचिव", "acs"), (r"मुख्य सचिव", "chief_secretary"), (r"प्रमुख सचिव", "principal_secretary"),
    (r"विशेष सचिव", "special_secretary"), (r"अपर सचिव", "additional_secretary"), (r"संयुक्त सचिव", "joint_secretary"),
    (r"उप सचिव", "deputy_secretary"), (r"अवर सचिव", "under_secretary"),
    (r"अपर पुलिस महानिदेशक|अति(?:रिक्त)?\.? पुलिस महानिदेशक", "adgp"), (r"पुलिस महानिदेशक", "dgp"),
    (r"पुलिस उप महानिरीक्षक", "dig"), (r"पुलिस महानिरीक्षक", "igp"), (r"पुलिस आयुक्त", "cp"),
    (r"संभागीय आयुक्त", "divisional_commissioner"), (r"राज्य निर्वाचन आयुक्त", "state_election_commissioner"),
    (r"मुख्य सूचना आयुक्त", "chief_information_commissioner"), (r"सूचना आयुक्त", "information_commissioner"),
    (r"सचिव", "secretary"), (r"उपाध्यक्ष", "vice_chairperson"), (r"अध्यक्ष|सभापति", "chairperson"), (r"सदस्य", "member"),
    (r"महानिदेशक|प्रबंध संचालक|प्रबन्ध संचालक|संचालक|आयुक्त|नियंत्रक|पंजीयक|रजिस्ट्रार|प्रमुख अभियंता|मुख्य अभियंता|"
     r"मुख्य कार्यपालन अधिकारी|कुलपति|लोकायुक्त", "head_of_department"),
]
_KINDS = [(re.compile(rx), k) for rx, k in KINDS]

# Hindi department words -> TAGGING.md dept key (first match wins); else _state.dept_key on the English post
HI_DEPTS = [
    ("police", r"गृह|पुलिस|जेल"), ("elections", r"निर्वाचन"), ("revenue", r"राजस्व|भू-?अभिलेख|आपदा|पंजीयन"),
    ("water", r"जल संसाधन|लोक स्वास्थ्य यांत्रिकी|नर्मदा घाटी|(?<![ऀ-ॿ])जल(?![ऀ-ॿ])"),
    ("health", r"स्वास्थ्य|चिकित्सा|आयुष"), ("education", r"शिक्षा|विश्वविद्यालय|तकनीकी"),
    ("agriculture", r"कृषि|उद्यानिकी|पशुपालन|मत्स्य|सहकारिता|किसान"), ("food_supplies", r"खाद्य"),
    ("rural_development", r"पंचायत|ग्रामीण"), ("town_body", r"नगरीय|नगर निगम|आवास|नगर तथा ग्राम"),
    ("public_works", r"लोक निर्माण"), ("electricity", r"ऊर्जा|विद्युत"), ("women_child", r"महिला|बाल"),
    ("sports_culture", r"खेल|संस्कृति|पर्यटन"), ("courts", r"विधि|न्याय|महाधिवक्ता|लोकायुक्त|अधिकरण"),
    ("social_welfare", r"सामाजिक|जनजातीय|जनजाति|अनुसूचित|पिछड़ा|पिछडा|अल्पसंख्यक|दिव्यांग|कल्याण"),
    ("transport", r"परिवहन"), ("forest", r"(?<![ऀ-ॿ])वन(?![ऀ-ॿ])|वन मण्|पर्यावरण"),
    ("treasury", r"वित्त|कोष"), ("excise_tax", r"वाणिज्यिक कर|आबकारी"),
    ("labour_industry", r"श्रम|उद्योग|द्योग|उद्यम|खनिज|कौशल|रोजगार|औद्योगिक"),
    ("planning", r"योजना|सांख्यिकी"), ("information", r"जनसंपर्क|जनसम्पर्क"),
]
_HI_DEPTS = [(k, re.compile(rx)) for k, rx in HI_DEPTS]


def dept_of(*texts):
    t = " ".join(_esw.clean(x) for x in texts if x)
    for k, rx in _HI_DEPTS:
        if rx.search(t):
            return k
    return None

# grid column headers -> (English post, rank key)
GRID_POSTS = [
    (r"संभागीय आयुक्त", "Divisional Commissioner", "divisional_commissioner"),
    (r"पुलिस उप महानिरीक्षक", "Deputy Inspector General of Police", "dig"),
    (r"पुलिस महानिरीक्षक", "Inspector General of Police", "igp"),
    (r"अपर आयुक्त", "Additional Commissioner", ""),
    (r"वन संरक्षक", "Chief Conservator / Conservator of Forests", ""),
    (r"उपायुक्त \(राजस्व\)", "Deputy Commissioner (Revenue)", ""),
    (r"उपायुक्त \(विकास\)", "Deputy Commissioner (Development)", ""),
    (r"लो\.?नि\.?वि", "Chief Engineer / Superintending Engineer PWD", ""),
    (r"जल संसाधन", "Chief Engineer / Superintending Engineer Water Resources", ""),
    (r"लो\.?स्वा\.?यां", "Chief Engineer / Superintending Engineer PHED", ""),
    (r"संयुक्त संचालक कृषि", "Joint Director Agriculture", ""),
    (r"संयुक्त संचालक लोक शिक्षण", "Joint Director Public Instruction", ""),
    (r"कलेक्टर", "Collector", ""),
    (r"पुलिस अधीक्षक", "Superintendent of Police", ""),
    (r"जिला एवं सत्र न्यायाधीश", "District and Sessions Judge", ""),
    (r"ए\.?डी\.?एम", "Additional District Magistrate", ""),
    (r"मुख्य कार्यपालन अधिकारी", "Chief Executive Officer, Zila Panchayat", ""),
    (r"वन मण्\S*ल अधिकारी", "Divisional Forest Officer", ""),
    (r"आयुक्त नगर निगम", "Municipal Commissioner / CMO", ""),
    (r"मुख्य चिकित्सा", "Chief Medical and Health Officer", ""),
    (r"कार्य\.? यंत्री लो\.?नि\.?वि", "Executive Engineer PWD", ""),
    (r"कार्य\.? यंत्री लो\.?स्वा", "Executive Engineer PHED", ""),
    (r"उप संचालक कृषि", "Deputy Director Agriculture", ""),
    (r"जिला शिक्षा अधिकारी", "District Education Officer", ""),
    (r"विश्राम भवन", "Rest House", ""),
]

# Hindi district names (letters only, see key()) -> (LGD code, LGD name)
MP = {"श्योपुर": ("431", "Sheopur"), "मुरैना": ("417", "Morena"), "भिण्ड": ("395", "Bhind"), "भिंड": ("395", "Bhind"),
      "ग्वालियर": ("407", "Gwalior"), "शिवपुरी": ("432", "Shivpuri"), "गुना": ("406", "Guna"), "अशोकनगर": ("391", "Ashoknagar"),
      "अशोक नगर": ("391", "Ashoknagar"), "दतिया": ("401", "Datia"), "भोपाल": ("396", "Bhopal"), "रायसेन": ("421", "Raisen"),
      "राजगढ": ("422", "Rajgarh"), "राजगढ़": ("422", "Rajgarh"), "सीहोर": ("427", "Sehore"), "विदिशा": ("437", "Vidisha"),
      "नर्मदापुरम": ("409", "Narmadapuram"), "होशंगाबाद": ("409", "Narmadapuram"), "हरदा": ("408", "Harda"),
      "बैतूल": ("394", "Betul"), "इन्दौर": ("410", "Indore"), "इंदौर": ("410", "Indore"), "धार": ("403", "Dhar"),
      "झाबुआ": ("412", "Jhabua"), "अलीराजपुर": ("639", "Alirajpur"), "खरगोन": ("414", "Khargone (West Nimar)"),
      "खरगौन": ("414", "Khargone (West Nimar)"), "बड़वानी": ("393", "Barwani"), "बडवानी": ("393", "Barwani"),
      "खण्डवा": ("405", "Khandwa (East Nimar)"), "खंडवा": ("405", "Khandwa (East Nimar)"), "बुरहानपुर": ("397", "Burhanpur"),
      "उज्जैन": ("435", "Ujjain"), "देवास": ("402", "Dewas"), "शाजापुर": ("430", "Shajapur"), "आगर": ("667", "Agar-Malwa"),
      "आगर मालवा": ("667", "Agar-Malwa"), "रतलाम": ("423", "Ratlam"), "मंदसौर": ("416", "Mandsaur"), "मन्दसौर": ("416", "Mandsaur"),
      "नीमच": ("419", "Neemuch"), "जबलपुर": ("411", "Jabalpur"), "कटनी": ("413", "Katni"), "नरसिंहपुर": ("418", "Narsimhapur"),
      "छिंदवाड़ा": ("399", "Chhindwara"), "छिंदवाडा": ("399", "Chhindwara"), "छिन्दवाड़ा": ("399", "Chhindwara"),
      "पांढुर्णा": ("785", "Pandhurna"), "पांढुरना": ("785", "Pandhurna"), "सिवनी": ("428", "Seoni"), "बालाघाट": ("392", "Balaghat"),
      "मण्डला": ("415", "Mandla"), "मंडला": ("415", "Mandla"), "डिण्डौरी": ("404", "Dindori"), "डिंडौरी": ("404", "Dindori"),
      "डिण्डोरी": ("404", "Dindori"), "सागर": ("425", "Sagar"), "दमोह": ("400", "Damoh"), "पन्ना": ("420", "Panna"),
      "छतरपुर": ("398", "Chhatarpur"), "टीकमगढ़": ("434", "Tikamgarh"), "टीकमगढ": ("434", "Tikamgarh"), "निवाड़ी": ("722", "Niwari"),
      "निवाडी": ("722", "Niwari"), "रीवा": ("424", "Rewa"), "मऊगंज": ("766", "MAUGANJ"), "सतना": ("426", "Satna"),
      "मैहर": ("784", "Maihar"), "सीधी": ("433", "Sidhi"), "सिंगरौली": ("638", "Singrauli"), "शहडोल": ("429", "Shahdol"),
      "अनूपपुर": ("390", "Anuppur"), "उमरिया": ("436", "Umaria")}
# divisions as the grid writes them -> st_div_mp.json name
DIVS = {"चम्बल": "Chambal", "ग्वालियर": "Gwalior", "उज्जैन": "Ujjain", "इन्दौर": "Indore", "इंदौर": "Indore", "भोपाल": "Bhopal",
        "नर्मदापुरम": "Narmadapuram", "होशंगाबाद": "Narmadapuram", "सागर": "Sagar", "जबलपुर": "Jabalpur", "रीवा": "Rewa",
        "शहडोल": "Shahdol"}


def key(s):
    """Letters only (Devanagari consonants and vowels, U+0905-U+0939): spellings with and without nukta, anusvara, halant
    or doubled vowel signs meet ("ग्‍वाालियर" = "ग्वालियर", "भि‍ण्‍ड" = "भिण्ड")."""
    return "".join(c for c in (s or "") if 0x905 <= ord(c) <= 0x939)


_MPK = {}
for _k, _v in MP.items():
    _MPK.setdefault(key(_k), _v)
_DIVK = {key(k): v for k, v in DIVS.items()}


def district_of(s):
    """(LGD code, LGD name) of a district cell ("श्‍योपुर 07530", "मुरैना </br>07532"); ("", "") when not known."""
    t = re.sub(r"[\d|().-]+", " ", _esw.clean(s)).strip()
    return _MPK.get(key(t)) or _MPK.get(key(t.split(" ")[0]) if t else "", ("", ""))


def kind_of(post):
    t = _esw.clean(post)
    for rx, k in _KINDS:
        if rx.search(t):
            return k
    return _state.post_kind(t)


def std_of(s):
    m = re.search(r"\b(0\d{2,4})\b", s or "")
    return m.group(1) if m else ""


def col_field(h):
    h = _esw.clean(h)
    for rx, f in COLS:
        if re.search(rx, h):
            return f
    return ""


def cells_of(tr):
    return [_esw.cell_text(td) for td in tr.find_all("td", recursive=False)]


def nodash(v):
    """A cell value without the page's "-" placeholders ("- | -" -> "")."""
    parts = [p.strip() for p in (v or "").split("|")]
    return " | ".join(p for p in parts if p and not re.fullmatch(r"[-–—.]+", p))


def parse(html, sec, url):
    mode, level, body_kind, body0 = SECTIONS[sec]
    # the page closes line breaks as "</br>", which lxml drops (the lines of a cell ran together): make them <br>
    soup = _esw.soup(re.sub(r"(?i)</br\s*>", "<br/>", html))
    table = soup.find("table")
    if table is None:
        return []
    head, groups, out, n = [], [], [], 0
    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table:
            continue
        ths = tr.find_all("th", recursive=False)
        if ths and "tabHead" in (ths[0].get("class") or []):
            head = [_esw.clean(th.get_text(" ")) for th in ths]
            continue
        if ths and "tabSubHead" in (ths[0].get("class") or []):
            groups = [_esw.clean(b.get_text(" ")) for b in ths[0].find_all("b")] or [_esw.clean(ths[0].get_text(" "))]
            groups = [g for g in groups if g]
            continue
        blocks = blocks_of(tr) if mode == "stacked" else None
        cells = cells_of(tr)
        if not cells or not head:
            provenance.skip_row(tr, 'skip: not cells or not head')
            continue
        n += 1
        pos = _trail.tr_pos(tr)
        if mode == "grid":
            out += grid_row(sec, level, head, cells, n, pos, url)
        elif mode == "stacked":
            out += stacked_row(sec, head, cells, blocks, n, pos, url)
        else:
            out.append(person_row(sec, level, body_kind, body0, head, groups, cells, n, pos, url))
    return out


def fields(head, cells):
    f = {}
    for h, v in zip(head, cells):
        k = col_field(h)
        v = nodash(v)
        if k and v:
            f[k] = (f[k] + " | " + v) if k in f else v
    return f


def person_row(sec, level, body_kind, body0, head, groups, cells, n, pos, url):
    f = fields(head, cells)
    post = f.get("post", "")
    if sec == 11:                     # ministers: the group row is the rank ("मंत्रिमण्‍डल के सदस्‍य", "राज्य मंत्री ...")
        post = (groups[0] if groups else "मंत्री")
    department = body = ""
    if sec == 9:                      # Mantralaya: the group row is the department
        department = groups[0] if groups else ""
        body = "मंत्रालय, मध्यप्रदेश" + (f" - {department}" if department else "")
    elif sec == 10:                   # boards: department, then the body
        department = groups[0] if groups else ""
        body = groups[1] if len(groups) > 1 else department
    elif groups and sec in (23, 24, 15, 3, 8, 25, 26, 30):
        body = groups[0]
    body = body or body0
    if sec == 16:                     # HoDs: "महानिदेशक, <body>" in the post cell
        m = re.match(r"^(.*?),\s*(.+)$", post)
        if m:
            body = m.group(2)
    email = _esw.emails(f.get("email", "") + " " + f.get("phone_office", "") + " " + " ".join(groups[1:] if sec == 23 else []))
    return _state.rec(
        MODULE, f"{sec}:{n}", state="MP", level=level, dept=dept_of(department, body, post, f.get("portfolio", "")), post=post or f.get("portfolio", ""), post_regional=post or None,
        post_kind=kind_of(post) or None, name=f.get("name", ""), name_regional=f.get("name") or None, body=body,
        body_kind=body_kind, department=department or (groups[0] if sec in (23, 24) and groups else ""),
        portfolio=f.get("portfolio") if sec == 11 else None, section=" / ".join(groups) or None,
        phone=_esw.phones(f.get("phone_office", "")), phone_residence=_esw.phones(f.get("phone_residence", "")) or None,
        phone_assembly=_esw.phones(f.get("phone_assembly", "")) or None, fax=f.get("fax"), epabx=f.get("epabx"),
        staff=f.get("staff"), email=email, website=f.get("website"), room=f.get("room"), address=f.get("address", ""),
        residence_address=f.get("residence_address"), diary_section=sec, cells=cells, source=url, src_url=url,
        src_pos=pos)


def grid_row(sec, level, head, cells, n, pos, url):
    """Division (46) or district (48) grid: one record for the unit (its own office / residence phones) and one per post
    column that has a phone or an e-mail. "232900 | 232660" = office | residence."""
    unit = cells[0]
    std = std_of(unit)
    name = _esw.clean(re.sub(r"\b0\d{2,4}\b|\|", " ", unit))
    out, kw = [], {}
    if level == "division":
        div = DIVS.get(name) or _DIVK.get(key(name)) or name
        kw = {"division": div, "division_regional": name}
    else:
        code, en = district_of(unit)
        kw = {"district": en or name, "district_code": code, "district_regional": name}
    for j, (h, v) in enumerate(zip(head, cells)):
        if j == 0:
            continue
        v = nodash(v)
        if not v:
            continue
        hpost = _esw.clean(h)
        if re.search(r"^कार्यालय दूरभाष$|^निवास दूरभाष$|^फैक्स", hpost):
            continue
        post_en, pk = next(((en, k) for rx, en, k in GRID_POSTS if re.search(rx, hpost)), ("", ""))
        parts = [p.strip() for p in v.split("|")]
        email = _esw.emails(v)
        nums = [p for p in parts if not _esw.emails(p)]
        office = _esw.phones(nums[0]) if nums else ""
        res = _esw.phones(" ".join(nums[1:])) if len(nums) > 1 else ""
        out.append(_state.rec(
            MODULE, f"{sec}:{n}:{j}", state="MP", level=level, post=post_en or hpost, post_regional=hpost,
            post_en=post_en or None, post_kind=pk or None, body=post_en or hpost,
            body_kind="division" if level == "division" else "other", phone=office, phone_residence=res or None, email=email,
            std_code=std or None, cells=cells, source=url, src_url=url, src_pos={**pos, "col": j + 1}, **kw))
    f = {}
    for h, v in zip(head, cells):
        hh = _esw.clean(h)
        if re.search(r"^कार्यालय दूरभाष$|^निवास दूरभाष$|^फैक्स", hh) and nodash(v):
            f[hh] = nodash(v)
    if f:
        office = f.get("कार्यालय दूरभाष", "")
        res = f.get("निवास दूरभाष", "")
        fax = next((v for k, v in f.items() if k.startswith("फैक्स")), "")
        out.append(_state.rec(
            MODULE, f"{sec}:{n}:unit", state="MP", level=level,
            post="Divisional Commissioner (office)" if level == "division" else "Collector (office)",
            post_regional="संभागीय आयुक्त कार्यालय" if level == "division" else "कलेक्टर कार्यालय",
            post_kind="divisional_commissioner" if level == "division" else None, body="unit office",
            body_kind="division" if level == "division" else "other", phone=_esw.phones(office),
            phone_residence=_esw.phones(res) or None, fax=fax or None, std_code=std or None, cells=cells, source=url,
            src_url=url, src_pos=pos, **kw))
    return out


def blocks_of(tr):
    """Per cell, its blocks (split on an empty line: two <br> in a row), each block a list of its lines."""
    out = []
    for td in tr.find_all("td", recursive=False):
        for br in td.find_all("br"):
            br.replace_with("\n")
        t = td.get_text().replace("\r", "")
        out.append([[_esw.clean(x) for x in b.split("\n") if _esw.clean(x)] for b in re.split(r"\n\s*\n", t)])
    return out


POST_LINE = re.compile(r"अध्\S*यक्ष|मु\S*ख्\S*य\s*कार्यपालन|महापौर|आयुक्\S*त|प्रशासक")


def stacked_row(sec, head, cells, blocks, n, pos, url):
    """Zila panchayat (20) and municipal corporation (21) rows: the name cell holds two people, each block "name / post"
    (a vacant seat: the post alone), the other cells hold their values block by block in the same order."""
    unit = cells[0]
    code, en = district_of(unit)
    std = std_of(unit)
    city = _esw.clean(re.sub(r"\b0\d{2,4}\b|\|", " ", unit))
    people, cur = [], []
    for b in blocks[1]:
        for ln in b:
            if re.fullmatch(r"[-–—.]+", ln):
                continue
            cur.append(ln)
            if POST_LINE.search(ln):
                people.append(cur)
                cur = []
        if cur:
            people.append(cur)
            cur = []
    out = []
    for i, b in enumerate(people):
        post = re.sub(r"^[-–—.\s]+|[-–—.\s]+$", "", b[-1])
        name = " ".join(x for x in b[:-1])
        cols = {}
        for h, cb in zip(head[2:], blocks[2:]):
            v = " | ".join(cb[i]) if i < len(cb) else ""
            cols[col_field(h) or h] = nodash(v)
        body = (f"जिला पंचायत {city}" if sec == 20 else f"नगर निगम {city}")
        out.append(_state.rec(
            MODULE, f"{sec}:{n}:{i + 1}", state="MP", level="district", post=post, post_regional=post,
            post_kind=kind_of(post) or None, name=name, name_regional=name or None, body=body, body_kind="other",
            dept="rural_development" if sec == 20 else "town_body", district=en or city, district_code=code,
            district_regional=city, phone=_esw.phones(cols.get("phone_office", "")),
            phone_residence=_esw.phones(cols.get("phone_residence", "")) or None,
            residence_address=cols.get("residence_address") or None, email=_esw.emails(cols.get("email", "")),
            website=cols.get("website") or None, fax=cols.get("fax") or None, std_code=std or None, cells=cells,
            source=url, src_url=url, src_pos={**pos, "person": i + 1}))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{s}", "payload": {"reader": MODULE, "url": BASE + str(s), "section": s, "state": "MP",
                                                  "india_only": True, "route": "direct"}} for s in sorted(SECTIONS)]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    html = r.text if hasattr(r, "text") else r.content.decode("utf-8", "replace")
    files = [_esw.keep(MODULE, f"section-{p['section']}", r.content)]
    recs = parse(html, int(p["section"]), p["url"])
    return recs, files, "" if recs else "no rows"
