"""Kerala: "Government Secretaries" of the Government of Kerala portal (kerala.gov.in/subdetail/MTIzOTc2NzU2LjY0/MTk5NjIzNTkuMTI=,
Laravel, checked 2026-11-13 from dev-vps-3, Mumbai; 180 KB).

The page answers in Malayalam by default. The portal's own language switch (GET /setbilingualval with X-Requested-With:
XMLHttpRequest, the call its language menu makes; it answers {"success": "successfully set"} and sets the session to English)
comes first, on the same session; then the page answers in English. If the switch fails, the Malayalam page is read the same way
(names and posts then go to name_regional / post_regional).
Three tables: (1) Chief Secretary: a heading row "Chief Secretary", then name | address; (2) Staff Officer(s), the same shape;
(3) Name & Designation | Department | Additional Charges | Address, header rows repeated per group (Additional Chief Secretaries,
Principal Secretaries, Secretaries, Special Secretaries ...). The address cell holds room, block, "Phone:", "Fax:", "E-mail:".
Records: level state, body "Government Secretariat, Thiruvananthapuram", body_kind secretariat, department = the Department
cell, additional_charges = the Additional Charges cell. Post: the text after the service tag in the name cell ("Shri. K.R.
Jyothilal IAS Additional Chief Secretary"), else the heading of the table. One queue item = the page (2 GETs).
Ids: dept:st_kl_secretaries:<n>.
"""
import re

from dforms import _esw, _state
from provenance import at
import provenance

METHOD = "html table (heading rows + Name & Designation | Department | Additional Charges | Address)"

MODULE = "st_kl_secretaries"
URL = "https://kerala.gov.in/subdetail/MTIzOTc2NzU2LjY0/MTk5NjIzNTkuMTI="
LANG = "https://kerala.gov.in/setbilingualval"
BODY = "Government Secretariat, Thiruvananthapuram"
TAG = re.compile(r"(?i)\b(I\.?\s?A\.?\s?S|I\.?\s?F\.?\s?S|I\.?\s?P\.?\s?S|IRS|IA&AS|IAAS|IRTS|IES)\b\.?,?|ഐ\.?\s?എ\.?\s?എസ്\.?")
POSTS = re.compile(r"(?i)(additional chief\s+secretary|principal secretary|special secretary|secretary|commissioner|staff officer|"
                   r"അഡീഷണൽ ചീഫ് സെക്രട്ടറി|പ്രിൻസിപ്പൽ സെക്രട്ടറി|സ്പെഷ്യൽ സെക്രട്ടറി|സെക്രട്ടറി).*$")
ML = re.compile(r"[ഀ-ൿ]")
ML_KINDS = [("acs", "അഡീഷണൽ ചീഫ് സെക്രട്ടറി"), ("chief_secretary", "ചീഫ് സെക്രട്ടറി"), ("principal_secretary", "പ്രിൻസിപ്പൽ സെക്രട്ടറി"),
            ("special_secretary", "സ്പെഷ്യൽ സെക്രട്ടറി"), ("additional_secretary", "അഡീഷണൽ സെക്രട്ടറി"),
            ("joint_secretary", "ജോയിന്റ് സെക്രട്ടറി"), ("deputy_secretary", "ഡെപ്യൂട്ടി സെക്രട്ടറി"), ("secretary", "സെക്രട്ടറി")]


def ml_kind(post):
    """Rank key of a Malayalam post (the page answered in Malayalam)."""
    return next((k for k, w in ML_KINDS if w in (post or "")), "")


def items(get=None):
    return [{"key": f"{MODULE}:page", "payload": {"reader": MODULE, "url": URL, "lang_url": LANG, "state": "KL",
                                                  "india_only": True, "route": "direct"}}]


def split_name(cell, heading):
    """(name, post) of a "Name & Designation" cell: the post is what follows the service tag, else the trailing post words."""
    t = _esw.clean(cell.replace("|", " ")).strip(" ,")
    m = TAG.search(t)
    if m and _esw.clean(t[m.end():]).strip(" ,"):
        return t[: m.end()].strip(" ,"), _esw.clean(t[m.end():]).strip(" ,")
    m = POSTS.search(t)
    if m and m.start() > 3:
        return t[: m.start()].strip(" ,"), m.group(0).strip(" ,")
    return t, heading


def field(addr, label):
    m = re.search(rf"(?i){label}\s*[:\-]?\s*(.*?)(?=(?:phone|fax|e-?\s?mail|mob(?:ile)?|ഫോൺ|ഫാക്സ്|ഇ-മെയിൽ)\s*[:\-]|$)", addr)
    return m.group(1).strip(" ,") if m else ""


def parse(html, url=URL):
    s = _esw.soup(html)
    recs, n = [], 0
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        heading, wide = "", False
        for row, sp in zip(rows, pos):
            vals = [x for x in row if x]
            if not vals:
                provenance.skip_row(row, 'skip: not vals')
                continue
            if len(set(vals)) == 1 and len(row) <= 2 and not re.search(r"\d|@", vals[0]):
                heading = vals[0]                      # "Chief Secretary", "Staff Officer"
                continue
            if re.match(r"(?i)name\s*&\s*designation|പേരും പദവിയും", row[0]):
                wide = True
                continue
            if wide and len(row) >= 4:
                namecell, dept, extra, addr = row[0], row[1], row[2], row[3]
            else:
                namecell, dept, extra, addr = row[0], "", "", row[-1] if len(row) > 1 else ""
            name, post = split_name(namecell, heading)
            if not name:
                provenance.skip_row(row, 'skip: not name')
                continue
            n += 1
            ml = bool(ML.search(name + post))
            phone_txt = field(addr, r"(?:phone|ഫോൺ)")
            recs.append(_state.rec(
                MODULE, str(n), state="KL", level="state", post="" if ml else post, post_regional=post if ml else None,
                name="" if ml else name, name_regional=name if ml else None, body=BODY, body_kind="secretariat",
                department=dept, additional_charges=extra or None, phone=_esw.phones(phone_txt), phone_raw=phone_txt or None,
                fax=_esw.phones(field(addr, r"(?:fax|ഫാക്സ്)")) or None, email=_esw.emails(addr), address=addr,
                section=heading or None, cells=row, list_no=str(n), src_url=url, src_pos=sp,
                **({"post_kind": ml_kind(post)} if ml and ml_kind(post) else {})))
    return recs


def fetch(p, get):
    if p.get("lang_url"):
        get(p["lang_url"], headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"})
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.status_code != 200:
        return [], [], f"http {r.status_code}"
    recs = [(k, {**d, **at(r, p["url"])}) for k, d in parse(r.text, p["url"])]
    return recs, [_esw.keep(MODULE, "secretaries", r.content)], "" if recs else "no rows"
