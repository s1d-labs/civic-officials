"""Himachal Pradesh: elected representatives of the panchayats (term 2026-2031, PRI general election 2026) with mobile numbers,
from the State Election Commission's DPMIS page "Elected Representatives" (निर्वाचित प्रतिनिधि):
https://sechimachal.hp.gov.in/dpmis/repList.aspx (ASP.NET WebForms, Hindi; linked from sechimachal.hp.gov.in/En/index.html).

Form (measured 2026-11-13 from Mumbai): term ddlPriTerm (2026-2031, 2022-2027, 2020-2025), level rbPriPost (001 = PRI), post
rbPost (P प्रधान, U उप-प्रधान, W वार्ड सदस्य, S पंचायत समिति वार्ड सदस्य, Z जिला परिषद वार्ड सदस्य), district ddlDis (1301-1312),
block ddlBlk, button btnShow. Each select and radio posts back. The order that works: GET (session cookie) -> term postback ->
post postback (not for P) -> district postback (P, U, W only: for S and Z the district postback answers a redirect to
frmError.aspx) -> btnShow with the district. The empty select ddlConsWard (S, Z) must be left out of the form, else
frmError.aspx. A new GET starts each post (the session keeps the last choice).
Result table (one per page): पी आर आई कार्यकाल, कार्यकाल प्रारंभ तिथि, पंचायत समिति, ग्राम पंचायत, वार्ड, प्रतिनिधि का नाम, लिंग, आयु,
पता, मोबाइल नं. (columns present by post). A second, empty template table follows; it is skipped.
Sizes: Una (district 1312) P 250 rows, U 250, W ~1,500 (4.3 MB page), S 112, Z 19.
No captcha, no login. Heads of ZP / PS (chairman, elected indirectly) are not on this page.
One queue item per district and post (12 districts x 5 posts = 60 items; 4-5 requests each).
Records: pri:pri_hp:<district code>:<post>:<block>~<gram panchayat>~<ward> (Hindi, spaces as _; ~r<row> on a repeat). No LGD code in the source: the loader matches body_name (GP, Hindi) +
block (Hindi) + district to lgd.pri_local_bodies.local_body_name_local (Hindi for 3,861 of 3,862 HP bodies). Una Pradhans
2026-11-13: 138 of 249 GP names equal an LGD local name in the district (105 also with the block); the rest need a fuzzy match
(spelling variants, GPs formed in 2025-26).
"""
import re

import provenance
from dforms import _pri

METHOD = "html table (ASP.NET WebForms elected representatives list, header words -> columns)"     # source trail
MODULE = "pri_hp"
URL = "https://sechimachal.hp.gov.in/dpmis/repList.aspx"
TERM = "2026-2031"
ELECTION = "Himachal Pradesh Panchayati Raj General Election 2026 (term 2026-2031)"
DISTRICTS = {"1301": "Bilaspur", "1302": "Chamba", "1303": "Hamirpur", "1304": "Kangra", "1305": "Kinnaur", "1306": "Kullu",
             "1307": "Lahaul and Spiti", "1308": "Mandi", "1309": "Shimla", "1310": "Sirmaur", "1311": "Solan", "1312": "Una"}
# post -> (radio index, level, role, post, post_regional)
POSTS = {"P": (0, "gp", "head", "Pradhan", "प्रधान"), "U": (1, "gp", "deputy", "Up-Pradhan", "उप-प्रधान"),
         "W": (2, "gp", "member", "Gram Panchayat Ward Member", "वार्ड सदस्य"),
         "S": (3, "ps", "member", "Panchayat Samiti Member", "पंचायत समिति वार्ड सदस्य"),
         "Z": (4, "zp", "member", "Zila Parishad Member", "जिला परिषद वार्ड सदस्य")}
P = "ctl00$ContentPlaceHolder1$"
HEAD = (("कार्यकाल प्रारंभ", "term_start"), ("कार्यकाल", "term"), ("पंचायत समिति", "block"), ("ग्राम पंचायत", "gp"),
        ("वार्ड", "ward"), ("नाम", "name"), ("लिंग", "gender"), ("आयु", "age"), ("पता", "address"), ("मोबाइल", "phone"))
GENDER = {"पुरुष": "male", "महिला": "female"}


def items(get=None):
    return [{"key": f"{MODULE}:{c}:{post}", "payload": {"reader": MODULE, "url": URL, "district_code": c, "district": n, "post": post,
                                                       "term": TERM, "state": "HP", "india_only": True, "route": "direct"}}
            for c, n in DISTRICTS.items() for post in POSTS]


def form(html, **kw):
    """Form fields of the page: hidden/text inputs, checked radios, selected options (empty selects left out) + kw."""
    s = _pri.soup(html)
    d = {}
    for i in s.find_all("input"):
        n, t = i.get("name"), i.get("type")
        if not n or t in ("submit", "button", "image"):
            continue
        if t in ("radio", "checkbox"):
            if i.has_attr("checked"):
                d[n] = i.get("value", "")
            continue
        d[n] = i.get("value", "")
    for sel in s.find_all("select"):
        o = sel.find("option", selected=True) or sel.find("option")
        if sel.get("name") and o is not None:
            d[sel["name"]] = o.get("value", "")
    d.update(kw)
    return d


def records(html, url, p, r=None):
    idx, level, role, post, post_reg = POSTS[p["post"]]
    src = provenance.at(r, url) if r is not None else {"src_url": url}
    out, seen = [], set()
    for tn, t in enumerate(_pri.soup(html).find_all("table"), 1):
        g = _pri.grid(t)
        if not g or "कार्यकाल" not in _pri.clean(g[0][0] if g[0] else ""):
            continue
        head = [_pri.clean(c) for c in g[0]]
        col = {}
        for i, h in enumerate(head):
            k = next((k for w, k in HEAD if w in h), None)
            if k and k not in col:
                col[k] = i
        if "name" not in col:
            continue
        for rn, row in enumerate(g[1:], 2):
            cells = [_pri.clean(c) for c in row]
            if len(cells) < len(head) or not cells[col["name"]]:
                provenance.skip_row(row, 'skip: len(cells) < len(head) or not cells[col["name"]]')
                continue
            v = {k: cells[i] for k, i in col.items()}
            ward = v.get("ward", "")
            m = re.match(r"^(\d+)\s*-\s*(.+)$", _pri.digits(ward))
            age = _pri.int_or_none(v.get("age"))
            ts = re.search(r"\d{2}-\d{2}-\d{4}", v.get("term_start", ""))
            f = dict(state="HP", level=level, role=role, post=post, post_regional=post_reg, name=v["name"], name_regional=v["name"],
                     gender=GENDER.get(v.get("gender"), v.get("gender")), age=age, address=v.get("address"),
                     phone=_pri.mobile(v.get("phone")) or v.get("phone"), district=p["district"], district_code=p["district_code"],
                     block=v.get("block"), term=v.get("term") or p["term"], term_start=ts.group(0) if ts else v.get("term_start"),
                     election=ELECTION, election_year=2026, status="in office (term 2026-2031)", source=url, **src,
                     src_pos={"table": tn, "row": rn}, cells=dict(zip(head, cells)))
            if level == "gp":
                f.update(body_name=v.get("gp"), body_name_regional=v.get("gp"))
            elif level == "ps":
                f.update(body_name=v.get("block"), body_name_regional=v.get("block"))
            else:
                f.update(body_name=p["district"])
            if ward:
                f.update(ward=ward, ward_no=m.group(1) if m else None)
            key = "~".join(x for x in (v.get("block", ""), v.get("gp", ""), ward) if x).replace(" ", "_") or str(rn - 1)
            if key in seen:
                key = f"{key}~r{rn - 1}"
            seen.add(key)
            out.append(_pri.record(MODULE, f"{p['district_code']}:{p['post']}:{key}", **f))
    return out


def fetch(p, get):
    post, dc = p["post"], p["district_code"]
    idx = POSTS[post][0]
    r = get(URL)
    if r is None:
        return [], [], "no answer"
    r = get(URL, "POST", form(r.text, **{P + "ddlPriTerm": p.get("term", TERM), "__EVENTTARGET": P + "ddlPriTerm"}))
    if r is not None and post != "P":
        r = get(URL, "POST", form(r.text, **{P + "rbPost": post, "__EVENTTARGET": P + f"rbPost${idx}"}))
    if r is not None and post in "PUW":
        r = get(URL, "POST", form(r.text, **{P + "ddlDis": dc, "__EVENTTARGET": P + "ddlDis"}))
    if r is None:
        return [], [], "postback: no answer"
    r2 = get(URL, "POST", form(r.text, **{P + "ddlDis": dc, P + "btnShow": "View List", "__EVENTTARGET": ""}))
    if r2 is None:
        return [], [], "list: no answer"
    recs = records(r2.text, URL, p, r2)
    return recs, [], "" if recs else "no rows"
