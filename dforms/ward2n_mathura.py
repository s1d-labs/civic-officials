"""Nagar Nigam Mathura-Vrindavan (nnmvonline.in): the field officers of the corporation and the zone each one serves where the page
names it. One page, /OfficerList.aspx ("Officers List"; saved in archive.s1d.me 2026-11-11): table dgUnitList, क्रमांक | नाम | पद |
मोबाइल नंबर | विभाग / कार्य. The zone is written in the name or the department cell: "Anoop Sood (Vrindavan)", "Shri Brijlal Saini ,
Aurangabad zone", "Tax City Zone" (zones: City, Bhuteshwar, Vrindavan, Aurangabad). Read: the field posts (AE / JE civil, Jal Kal
and light, executive and chief engineer, GM Jal Kal, ZSO, SI, NSA, RI, TS, KNA, CTAO) and every row that names a zone (also the
zone clerks for birth and death certificates). Head-office posts (Mayor, Nagar Ayukt, ANA, SNA, accounts, audit) are left out.
The page does not list wards. The older CUG list (/CUGNumberList.aspx) is not read (it names a former Nagar Ayukt).
Records: level "zone" when a zone is named, else "body"; area = the zone ("Vrindavan Zone") or the body. Record ids:
dept:ward2n_mathura:<post slug>:<mobile>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_mathura"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Mathura-Vrindavan", "249052", "UP", "Mathura"
URL = "http://nnmvonline.in/OfficerList.aspx"
ZONE = re.compile(r"(?i)\b(city|bhut[e]?shwar|bhuteswar|vrindavan|aurangabad)\b(?:\s*zone)?")
ZONES = {"city": "City", "bhuteshwar": "Bhuteshwar", "bhutshwar": "Bhuteshwar", "bhuteswar": "Bhuteshwar", "vrindavan": "Vrindavan",
         "aurangabad": "Aurangabad"}
FIELD = re.compile(r"(?i)^(ae|je|ex\.?\s*en|chief engineer|gm|zso|si|csi|nsa|ri|ts|kna|ctao)\b")
POSTS = {"ae": "Assistant Engineer", "ae jal": "Assistant Engineer (Jal Kal)", "je": "Junior Engineer", "je jal": "Junior Engineer (Jal Kal)",
         "je civil": "Junior Engineer (Civil)", "ex. en. civil": "Executive Engineer (Civil)", "gm": "General Manager (Jal Kal)",
         "zso": "Zonal Sanitary Officer", "si": "Sanitary Inspector", "nsa": "Nagar Swasthya Adhikari (City Health Officer)",
         "ri": "Revenue Inspector", "ts": "Tax Superintendent", "kna": "Kar Nirdharan Adhikari (Tax Assessment Officer)",
         "ctao": "Chief Tax Assessment Officer", "chief engineer": "Chief Engineer", "clerk": "Clerk"}
WINGS = {"jal": "water", "light": "electrical", "tax": "revenue", "sanitation": "sanitation", "health": "health", "civil": "engineering",
         "construction": "engineering", "nirman": "engineering", "birth": "administration"}


def items(get=None):
    return [{"key": f"{MODULE}-officer-list", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    t = _esw.soup(html).find("table", id="dgUnitList")
    seen, recs = set(), []
    for tr in (t.find_all("tr") if t else []):
        tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) < 5:
            provenance.skip_row(tr, 'skip: len(tds) < 5')
            continue
        name_raw, post_raw, mob, dept = tds[1], tds[2], tds[3], tds[4]
        zm = ZONE.search(name_raw) or ZONE.search(dept)
        zone = ZONES.get(re.sub(r"[^a-z]", "", zm.group(1).lower())) if zm else None
        if not (FIELD.match(post_raw) or zone):
            provenance.skip_row(tr, 'skip: not (FIELD.match(post_raw) or zone)')
            continue
        name = _esw.clean(re.sub(r"\(\s*[A-Za-z]+\s*\)|,?\s*\b(city|bhut\w*|vrindavan|aurangabad)\s*zone\b", " ", name_raw, flags=re.I))
        name = _esw.clean(re.sub(r"\(\s*\)", " ", name)).strip(" ,")
        post = POSTS.get(re.sub(r"\s+", " ", post_raw.lower().strip(" ,")), post_raw.strip(" ,"))
        wing = next((w for k, w in WINGS.items() if k in dept.lower()), None)
        phones = _esw.phones(mob.replace(")", " "))
        key = f"{_esw.slug(post)}:{re.sub(r'[^0-9]', '', phones.split(',')[0]) or _esw.slug(name)}"
        recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone" if zone else "body", area=f"{zone} Zone" if zone else BODY,
                                 zone=f"{zone} Zone" if zone else None, post=post, post_source=post_raw, name=name, phone=phones,
                                 department=dept, wing=wing, source=p["url"], src_pos=_ward.tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "officer-list", r.content)], "" if recs else "no officer table"
