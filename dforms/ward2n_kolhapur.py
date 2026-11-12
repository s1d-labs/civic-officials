"""Kolhapur Mahanagarpalika (web.kolhapurcorporation.gov.in): the officers that the contact page ties to a divisional office, a
ward group or a lettered ward. One page, /contact (Marathi; in archive.s1d.me, saved 2026-11-05), one table per department
("अ. क्र. | नाव | पदनाम | संपर्क क्रमांक | ई - मेल आयडी") under a heading (सामान्य प्रशासन विभाग, शहर अभियंता / पवडी विभाग,
आरोग्य आणि स्वच्छता, शहर पाणीपुरवठा विभाग, नगररचना, घरफाळा विभाग ...). The post cell names the area:
  - "(वि. का. १)" or "(वि. का. १ व २)": divisional office (vibhagiya karyalay) 1-4 -> level "zone", area "Divisional Office <n>";
  - "आरोग्य निरीक्षक (A1) (वॉर्ड क्र. ४७,५५,५६,५७,६९)": a health inspector's circle and its election wards -> level "ward",
    area "Wards 47, 55, ...", zone = the circle (A1);
  - "(वॉर्ड ए, बी)", "(प्रभाग सी, डी)", "(प्रभाग ई 1)": lettered administrative wards -> level "zone", area "Ward A" (one record each).
Rows without such a mark (headquarters posts) are left out: the directory reader (directories.json) has them already.
Posts in English (post_regional as written), names in Marathi (name and name_regional). Record ids:
dept:ward2n_kolhapur:<area slug>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_kolhapur"
BODY, LGD, STATE, DISTRICT = "Kolhapur Mahanagarpalika", "251625", "MH", "Kolhapur"
URL = "https://web.kolhapurcorporation.gov.in/contact"
POSTS = ((r"सहा\w*\.?\s*आयुक्त", "Assistant Commissioner"), (r"सहा\.?\s*आरोग्य\s*निर[िी]क्षक", "Assistant Health Inspector"),
         (r"आरोग्य\s*निर[िी]क्षक", "Health Inspector"), (r"कनिष्ठ\s*अभियंता", "Junior Engineer"),
         (r"शाखा\s*अभियंता", "Branch Engineer"), (r"उप\s*शहर\s*रचनाकार", "Deputy Town Planner"),
         (r"कर\s*अधीक्षक", "Tax Superintendent"), (r"अधीक्षक", "Superintendent"))
SECTIONS = (("स्वच्छता", "sanitation"), ("आरोग्य", "health"), ("पाणी", "water"), ("नगररचना", "planning"), ("घरफाळा", "revenue"),
            ("अभियंता", "engineering"), ("प्रशासन", "administration"), ("विद्युत", "electrical"))
LETTERS = {"ए": "A", "बी": "B", "सी": "C", "डी": "D", "ई": "E"}


def items(get=None):
    return [{"key": f"{MODULE}-contact", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def areas(post):
    """[(level, area, zone, wards)] that a post cell names."""
    p = _ward.hi_norm(post)
    out = []
    m = re.search(r"वि\.?\s*का\.?\s*(\d)(?:\s*(?:व|,)\s*(\d))?", p)
    if m:
        for n in (g for g in m.groups() if g):
            out.append(("zone", f"Divisional Office {n}", f"Divisional Office {n}", []))
    m = re.search(r"वॉर्ड\s*क्र\.?\s*([\d,\s]+)", p)
    if m:
        circle = re.match(r"[^(]*\(([A-Z]\d?(?:-\d)?)[^)]*\)", p)
        ws = _ward.wards_of(m.group(1))
        out.append(("ward", ("Ward " if len(ws) == 1 else "Wards ") + ", ".join(ws), circle.group(1) if circle else None, ws))
    for m in re.finditer(r"(?:वॉर्ड|प्रभाग)\s*(?![क\d])([^)]*)\)", p):
        for code in re.findall(r"(?<![\u0900-\u097f])(ए|बी|सी|डी|ई)(?![\u0900-\u097f])\s*(\d)?", m.group(1)):
            ward = LETTERS[code[0]] + code[1]
            out.append(("zone", f"Ward {ward}", f"Ward {ward}", []))
    return out


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for t in soup.find_all("table"):
        h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "strong", "b", "caption"])
        section = _esw.clean(h.get_text(" ")) if h else ""
        g = _esw.grid(t)
        if not g or "पदनाम" not in " ".join(g[0]):
            continue
        head = [_esw.clean(c) for c in g[0]]
        for row in g[1:]:
            r = dict(zip(head, [_esw.clean(c) for c in row]))
            post = _ward.hi_norm(_ward.col(r, "पदनाम"))
            for level, area, zone, wards in areas(post):
                en = next((e for rx, e in POSTS if re.search(rx, post)), _ward.hi_post(post))
                wing = _ward.wing_of(en)
                if wing in ("other", "administration", "engineering") and not re.search("आयुक्त", post):
                    wing = next((w for word, w in SECTIONS if word in section), wing)
                if "ड्रेनेज" in post:
                    wing = "sewerage"
                if "स्वच्छता" in section and wing == "health":
                    wing = "sanitation"
                if "घरफाळा" in section and en == "Superintendent":
                    en = "Tax Superintendent"
                name = _ward.col(r, "नाव")
                recs.append(_ward.record(MODULE, f"{_esw.slug(area)}:{_esw.slug(en)}", seen, body=BODY, lgd=LGD, state=STATE,
                                         district=DISTRICT, level=level, area=area, zone=zone, wards=wards, post=en,
                                         post_regional=post, name=name, name_regional=name,
                                         phone=_ward.hi_norm(_ward.col(r, "संपर्क")), email=_ward.col(r, "ई - मेल", "मेल"),
                                         wing=wing, section=section or None, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contact", r.content)], "" if recs else "no ward or division posts"
