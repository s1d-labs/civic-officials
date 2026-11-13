"""Aligarh Nagar Nigam (nnaligarh.in/ASCL, the UP e-governance "CitizenHome" portal, as Prayagraj): "List Of Important Numbers"
(SectionInformation.html?editForm&rowId=7; live sample 2026-11-13 from Mumbai, not in archive.s1d.me; the portal sets a
JSESSIONID cookie with one redirect first). One table in Hindi: क्र0 सं0 | अधिकारी का नाम | पद नाम | मोबाइल, about 29 rows: the
commissioners, engineers (assistant and junior engineers of construction and water), the city health officer, the zonal
sanitary officer, the sanitary and food inspectors, tax officers. The portal publishes no zone or ward lists for Aligarh (its
section pages for zones do not exist), so the records are at level "body". The Mayor row and the "complaints" row (शिकायत
सम्बंधित, 1533) are left out (the Mayor is elected; 1533 is a helpline, not a person).
Record ids: dept:ward3_aligarh:<post slug>:<mobile or row>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_aligarh"
BODY, LGD, STATE, DISTRICT = "Aligarh Nagar Nigam", "249025", "UP", "Aligarh"
URL = "https://nnaligarh.in/ASCL/SectionInformation.html?editForm&rowId=7&page="
POSTS = ((r"महाप्रबंधक\s*\(?\s*जल", "General Manager (Water)"), (r"मुख्य\s*अभियंता", "Chief Engineer"),
         (r"सहायक\s*लेखा\s*अधिकारी", "Assistant Accounts Officer"), (r"पशु\s*चिकित्सा", "Veterinary and Welfare Officer"),
         (r"जोनल\s*स्व[छच]्?छ?ता\s*अधिकारी", "Zonal Sanitary Officer"), (r"नगर\s*स्वास्थ्य\s*अधिकारी", "City Health Officer"),
         (r"प्रवर्तन\s*दल", "Enforcement Squad Officer"), (r"स्टेनो", "Steno to the Municipal Commissioner"),
         (r"पी\.?\s*आर\.?\s*ओ", "Public Relations Officer"), (r"आई\.?\s*टी\.?\s*ओ", "IT Officer"),
         (r"जी\.?\s*आई\.?\s*एस", "GIS Expert"), (r"^नगर\s*आयुक्त", "Municipal Commissioner"))


def items(get=None):
    return [{"key": f"{MODULE}-important-numbers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def en_post(post):
    p = _ward.hi_norm(post)
    for rx, en in POSTS:
        if re.search(rx, p):
            return en
    en = _ward.hi_post(post)
    m = re.search(r",\s*(निर्माण|जल)$", p)            # "अवर अभियन्ता, जल" -> Junior Engineer (Water)
    if m and en != _esw.clean(post):
        en += " (Construction)" if m.group(1) == "निर्माण" else " (Water)"
    return en


def parse(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "नाम", "पद")[:1]:
        for r in rows:
            name, post, ph = _ward.col(r, "अधिकारी"), _ward.col(r, "पद"), _ward.col(r, "मोबाइल")
            if not post or re.search(r"मेयर|महापौर", post) or "शिकायत" in name:
                provenance.skip_row(r, 'skip: not post or re.search(r"मेयर|महापौर", post) or "शिकायत" in name')
                continue
            en = en_post(post)
            wing = "water" if re.search(r"जल", post) else ("sanitation" if re.search(r"स्व[छच]|सफाई", post) else None)
            recs.append(_ward.record(MODULE, f"{_esw.slug(en)}:{re.sub(r'[^0-9]', '', ph) or len(recs)}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="body", area=BODY, post=en, post_regional=post,
                                     name=name, name_regional=name, phone=ph, wing=wing or _ward.wing_of(en), source=p["url"],
                                     src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "important-numbers", r.content)]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no officers table"
