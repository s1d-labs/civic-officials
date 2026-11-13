"""Jharkhand: Who's Who of the state portal (jharkhand.gov.in, NIC), one card per post: name, designation, department.

Pages (checked 2026-11-13 from dev-vps-3, Mumbai; archive copies of 2026-11-05/10 for 33 departments):
- /PDepartment/WebDirectory?department=<hash>: every post of one department's secretariat (Minister, Secretary, Additional /
  Joint / Deputy / Under Secretaries, OSDs, directors). 34 departments (the hash list is the department <select> of
  /Home/WebDirectory?rbCategory=2). 10-30 cards each.
- /Home/WebDirectory?rbCategory=1&department=<id>: every holder of one designation across the government (Governor 13, Chief
  Minister 14, Chief Secretary 15, Development Commissioner 16, ACS to CM 63, Secretary to CM 173, Principal Secretary cum
  L.R. 64).
Card: <b class="namefont">name</b>, <h5 class="dptdsc">designation</h5>, <h6 class="dptdsc"><b>department</b></h6>; some
cards add phone / e-mail lines below: kept when present. The portal gives no phone for most posts.
Records: level state, body = the department as the card names it, body_kind department (secretariat posts). Record id
dept:st_jh_whoswho:<department slug>:<post slug>:<name slug>, the same for both page kinds (a post seen on both is one record).
src_pos = {"card": n} (1-based place of the card on the page). One item = one page, one GET; the page is kept in the bucket.
Route: direct or proxy (answers from Mumbai); abroad unchecked.
"""
import re

from dforms import _esw, _state

METHOD = "html cards (NIC state portal Who's Who)"
MODULE = "st_jh_whoswho"
BASE = "https://jharkhand.gov.in"

DEPTS = {
    "d5cbf528f740b502b79241ff873ce6c5": "Department of Agriculture, Animal Husbandry & Co-operative",
    "b3460c056d63af44fe66bd92c961a144": "Department of Building Construction",
    "22d164d469bfc0bc0f2aefe67dd2806e": "Department of Cabinet Election",
    "fda7f226bff2b2df5da2e703f84bab11": "Department of Cabinet Secretariat and Vigilance",
    "b7ca9b1c84b0669f89357ee7bafb1274": "Department of Commercial Taxes",
    "0d86b2d838d51e9ae5d1720054578f16": "Department of Drinking Water and Sanitation",
    "89dcc06341a2e25e573a26d0e780fbbb": "Department of Energy",
    "a7a81ba176b755a597b776604940a2c5": "Department of Excise and Prohibition",
    "44ebd68a8460176fbe9ec6071af32506": "Department of Finance",
    "f6cce92549c349a9953bd877f4860f32": "Department of Food, Public Distribution & Consumer Affairs",
    "0f9d76428568fcad70cb130b20f4638e": "Department of Forest, Environment & Climate Change",
    "d5e4effc166af7f050089416e7e53b57": "Department of Health, Medical Education & Family Welfare",
    "e66e21ac2b0dbf5f42a77ae8373e789e": "Department of Higher and Technical Education",
    "1bc964f6f1e70dcba774fd80fe1118e0": "Department of Home, Jail & Disaster Management",
    "420c0ede70cff1d160c862004a7bfee0": "Department of Industries",
    "6ebf47a103a0bad887014cce9fe81960": "Department of Information & Public Relations",
    "5cedfc034ccdad75d58a0fa1875d396a": "Department of Information Technology & e-Governance",
    "447f299d2ed46a403af8ec2b9cfff194": "Department of Labour, Employment, Training and Skill Development",
    "62cc46459284fd62c0ad61eb117f1645": "Department of Law",
    "5e78d6d7d6b97e07863f2b2ac6c72c49": "Department of Mines & Geology",
    "8cc054261ce69fc6f8fa34acf567ed34": "Department of Panchayati Raj",
    "0bfb179af3c357296c35d64d10a7c0b3": "Department of Personnel, Administrative Reforms & Rajbhasha",
    "32d5e36f384bebd5d3753a04a0302eec": "Department of Planning & Development",
    "13c802aa19ff6d9acf1bd501d7fc9943": "Department of Revenue, Registration & Land Reforms",
    "f2da24cc2c612a0002eb7f07ec02801b": "Department of Road Construction",
    "cb756d3448ad467033846e84017824f3": "Department of Rural Development",
    "7bdf081dc5e322c3da257e565ba540e5": "Department of Rural Works",
    "9b4444362f0552972f13bf5536751e75": "Department of Scheduled Tribe, Scheduled Caste, Minority and Backward Class Welfare",
    "c2921c13fa62065c8d28c85aae51497e": "Department of School Education & Literacy",
    "ec6d0d0555498e764280158310986e87": "Department of Tourism, Arts, Culture, Sports & Youth Affairs",
    "b7ea2ca01a87777825bc151ebf8f8e2b": "Department of Transport",
    "299be138d615ca9d4dd0d382a642e96c": "Department of Urban Development & Housing",
    "fcc8fa0ea88d370507a094126bd40fae": "Department of Water Resources",
    "01f00daeed1418fb5cf6d8988d8a8fab": "Department of Women, Child Development & Social Security",
}
DESIGNATIONS = {"13": "Governor", "14": "Chief Minister", "15": "Chief Secretary", "16": "Development Commissioner",
                "63": "Additional Chief Secretary to Honourable CM", "173": "Secretary to Honourable CM",
                "64": "Principal Secretary cum L.R."}


def kind_of(post, dept):
    t = f"{post} {dept}"
    if re.search(r"(?i)\bgovernor\b", post):
        return "governor"
    if re.search(r"(?i)chief minister|to honou?rable cm|\bto cm\b", t) and not re.search(r"(?i)minister\b", dept or ""):
        return "cm_office"
    return "department"


def kind(post):
    """_state.post_kind, except "Secretary to (Hon'ble) Chief Minister / CM" -> secretary (the generic minister pattern takes it)."""
    import re as _re
    if _re.search(r"(?i)^(special |additional |joint |deputy |under |private )?secretary\s+to\b", post or ""):
        return _state.post_kind(_re.sub(r"(?i)\s+to\b.*$", "", post))
    return _state.post_kind(post)


def parse(html, url):
    s = _esw.soup(html)
    out, seen = [], set()
    for n, b in enumerate(s.find_all("b", class_="namefont"), 1):
        card = b.find_parent("div", class_="item_list") or b.find_parent("div")
        name = _esw.clean(b.get_text(" "))
        h5 = card.find("h5") if card else None
        h6 = card.find("h6") if card else None
        post = _esw.clean(h5.get_text(" ")) if h5 else ""
        dept = _esw.clean(h6.get_text(" ")) if h6 else ""
        rest = _esw.clean(card.get_text(" | ")) if card else ""
        phone, email = _esw.phones(rest.replace(name, " ")), _esw.emails(rest)
        k = f"{_esw.slug(dept)[:60] or 'gov'}:{_esw.slug(post)[:50]}:{_esw.slug(name)[:40]}"
        if k in seen:
            continue
        seen.add(k)
        out.append(_state.rec(MODULE, k, state="JH", level="state", post=post, name=name, post_kind=kind(post) or None, body=dept or "Government of Jharkhand",
                              body_kind=kind_of(post, dept), department=dept, phone=phone, email=email, source=url,
                              src_url=url, src_pos={"card": n}))
    return out


def items(get=None):
    out = [{"key": f"{MODULE}:dept:{h}", "payload": {"reader": MODULE, "url": f"{BASE}/PDepartment/WebDirectory?department={h}",
                                                     "label": d, "state": "JH", "india_only": True, "route": "direct"}}
           for h, d in DEPTS.items()]
    out += [{"key": f"{MODULE}:post:{i}", "payload": {"reader": MODULE, "url": f"{BASE}/Home/WebDirectory?rbCategory=1&department={i}",
                                                      "label": d, "state": "JH", "india_only": True, "route": "direct"}}
            for i, d in DESIGNATIONS.items()]
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    html = r.content.decode("utf-8", "replace")
    recs = parse(html, p["url"])
    name = re.sub(r"[^A-Za-z0-9]+", "-", p["url"].split("?", 1)[-1])[:80]
    return recs, [_esw.keep(MODULE, name, r.content)], "" if recs else "no cards"
