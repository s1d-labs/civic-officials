"""Mira-Bhayandar Mahanagarpalika (mbmc.gov.in): the officers and staff of its 6 prabhag samiti (ward committee) offices. One page
per office, /ward-committee-no-<n>- (Marathi; answers from Germany; live sample 2026-11-11 of no. 1, the archive holds only
/ward-offices, the office addresses). Each page has:
  - the head table "विभाग प्रमुख | दूरध्वनी/भ्रमणध्वनी क्रमांक | पत्ता | ई-मेल": the ward officer (prabhag adhikari), mobile, office
    address, ward email;
  - the text "प्रभाग समिती क्र. 1 अंतर्गत निवडणूक प्रभाग क्र. 8,23 व 24": the election wards (prabhag) of the office;
  - the job chart: one table per section (आवक-जावक, अतिक्रमण, कर विभाग ...), rows "no | post | श्री . name | मो . क्र . mobile |
    duties"; a post cell can name a sub-office ("(राई-मुर्धे विभाग)"), a name cell can hold two people and a tax recovery zone.
Records: level "zone" (a prabhag samiti covers several election wards), area "Prabhag Samiti <n>", wards = its election wards;
post in English (post_regional as written), names in Marathi (name and name_regional the same text). The head row has role "head".
Record ids: dept:ward2n_mirabhayandar:ps<n>:<post slug>:<k>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_mirabhayandar"
BODY, LGD, STATE, DISTRICT = "Mira-Bhayandar Mahanagarpalika", "251470", "MH", "Thane"
URL = "https://mbmc.gov.in/ward-committee-no-{n}-"
N = 6

# Marathi posts -> English (first match wins, longer posts first)
MR_POSTS = (
    (r"प्रभाग\s*अधिकारी", "Ward Officer"), (r"सहा\w*\s*आयुक्त", "Assistant Commissioner"),
    (r"कार्यकारी\s*अभियंता", "Executive Engineer"), (r"उप\s*-?\s*अभियंता", "Deputy Engineer"),
    (r"सहा\w*\s*अभियंता", "Assistant Engineer"), (r"कनिष्ठ\s*अभियंता", "Junior Engineer"),
    (r"कर\s*निर[िी]क्षक", "Tax Inspector"), (r"वसुली\s*लिपि?ी?क", "Tax Recovery Clerk"),
    (r"स्वच्छता\s*निर[िी]क्षक", "Sanitary Inspector"), (r"आरोग्य\s*निर[िी]क्षक", "Health Inspector"),
    (r"मुकादम", "Sanitation Mukadam"), (r"फेरीवाला\s*पथ\w*\s*प्रमुख", "Hawker Squad Head"),
    (r"संगणक\s*चालक", "Computer Operator"), (r"लिपि?ी?क|टंकलेखक", "Clerk"), (r"शिपाई", "Peon"),
    (r"सफाई\s*कामगार", "Sanitation Worker"), (r"मजूर", "Labourer"), (r"रखवालदार", "Watchman"), (r"वाहन\s*चालक", "Driver"),
)
# section heading -> wing (for clerks and peons, whose post names no wing)
SECTIONS = (("कर", "revenue"), ("अतिक्रमण", "planning"), ("फेरीवाला", "planning"), ("आरोग्य", "sanitation"),
            ("स्वच्छता", "sanitation"), ("पाणी", "water"), ("बांधकाम", "engineering"), ("आवक", "administration"))
SECTION = re.compile(r"([^\s|:.,()][^|:.,()]{1,40}?)\s*:\s*-")
PERSON = re.compile(r"((?:श्रीमती|श्रीम|श्री|सौ|कु|डॉ)\s*\.?\s*[^|]*?)\s*(?:\|\s*)?मो\s*\.?\s*क्र\s*\.?\s*([\d\s]{6,14}\d)")


def items(get=None):
    return [{"key": f"{MODULE}-ps{n}", "payload": {"reader": MODULE, "url": URL.format(n=n), "state": STATE, "office": n}}
            for n in range(1, N + 1)]


def en_post(p):
    p = _ward.hi_norm(p)
    for rx, en in MR_POSTS:
        if re.search(rx, p):
            return en
    return _esw.clean(p)


def people(cell):
    """[(name, mobile, note)] of a name cell: one or two people, each "श्री . name मो . क्र . mobile"; a note in brackets
    ("( वसुलीझोन – B04, B06)") goes to the person before it."""
    c = _ward.hi_norm(cell)
    note = "; ".join(_esw.clean(x) for x in re.findall(r"\(([^)]*झोन[^)]*)\)", c))
    out = [(_esw.clean(m.group(1)).strip(" |"), re.sub(r"\s", "", m.group(2))) for m in PERSON.finditer(c)]
    if not out:
        nm = _esw.clean(re.sub(r"\(.*?\)", "", c)).strip(" |")
        out = [(nm, "")] if nm and len(nm) <= 40 and not re.search(r"\d|,", nm) else []
    return [(re.sub(r"\s*\.\s*", ". ", n).replace(" .", "."), ph, note) for n, ph in out]


def parse(html, p):
    soup = _esw.soup(html)
    n = p.get("office") or int(re.search(r"no-(\d+)", p["url"]).group(1))
    area = f"Prabhag Samiti {n}"
    text = _ward.hi_norm(soup.get_text(" "))
    m = re.search(r"निवडणूक\s*प्रभाग\s*क्र\s*\.?\s*([\d\s,]+(?:\s*(?:व|आणि|ते|-)\s*\d+)*)", text)
    wards = _ward.wards_of(re.sub(r"\s*(व|आणि)\s*", ",", m.group(1))) if m else []
    seen, recs, done, k = set(), [], set(), {}
    common = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=area, zone=area, wards=wards,
                  source=p["url"])
    for head, rows in _ward.header_tables(html, "विभाग प्रमुख", "ई-मेल", soup=soup)[:1]:
        for r in rows[:1]:
            name = _ward.col(r, "विभाग प्रमुख")
            recs.append(_ward.record(MODULE, f"ps{n}:ward-officer", seen, post="Ward Officer", post_regional="प्रभाग अधिकारी",
                                     name=name, name_regional=name or None, phone=_ward.col(r, "दूरध्वनी"),
                                     email=_ward.col(r, "ई-मेल"), address=_ward.col(r, "पत्ता"), wing="administration", **common))
            done.add(("ward officer", _esw.clean(name)))
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not any(len(r) >= 3 and re.fullmatch(r"\d{1,3}\.?", _esw.clean(r[0])) for r in g):
            continue
        before = _ward.hi_norm(" ".join(reversed(t.find_all_previous(string=True, limit=150))))
        section = ([_esw.clean(x) for x in SECTION.findall(before) if "JOB CHART" not in x] or [""])[-1]
        for r in g:
            if len(r) < 3 or not re.fullmatch(r"\d{1,3}\.?", _esw.clean(r[0])) or t.find("table"):
                continue
            pr = _ward.hi_norm(r[1])
            post_mr = _esw.clean(pr.split("|")[0])
            sub = "; ".join(_esw.clean(x).strip("() ") for x in pr.split("|")[1:] if _esw.clean(x))
            en = en_post(post_mr)
            wing = _ward.wing_of(en)
            if wing in ("other", "administration") and en not in ("Ward Officer", "Assistant Commissioner"):
                wing = next((w for word, w in SECTIONS if word in f"{section} {sub}"), wing)
            for name, phone, note in people(r[2]):
                if not name or (en.lower(), name) in done:
                    continue
                done.add((en.lower(), name))
                key = f"ps{n}:{_esw.slug(en)}"
                k[key] = k.get(key, 0) + 1
                recs.append(_ward.record(MODULE, f"{key}:{k[key]}", seen, post=en, post_regional=post_mr, name=name,
                                         name_regional=name, phone=phone, wing=wing, section=section or None,
                                         sub_area=sub or None, notes=note or None, **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"ps{p.get('office', 'x')}", r.content)], "" if recs else "no officer tables"
