"""Uttarakhand: elected members of the three-tier panchayats, General Election 2025 (त्रिस्तरीय पंचायत सामान्य निर्वाचन 2025),
from the State Election Commission result site secresult.uk.gov.in (linked from sec.uk.gov.in; ASP.NET WebForms, Hindi).

Structure (measured 2026-11-13 from Mumbai; the server needs TLS legacy renegotiation, which get() retries):
  FrontDashboard.aspx: posts and counts: जिला पंचायत सदस्य 358 (358 declared), क्षेत्र पंचायत सदस्य 2,974 (2,973),
  प्रधान ग्राम पंचायत 7,499 (7,488). Haridwar (district 050) is not in this round (it votes on another cycle).
  WinnerListZP.aspx: district select (ddlDistrict, LGD district code with 3 digits) + Search -> one table of ZP ward winners.
  WinnerListGP.aspx / WinnerListCP.aspx: district + block; the block select is filled by the page method
  WinnerListCP.aspx/GetBlocksByDistrict (JSON {"districtCode"}) and the search reads the hidden field hdnBlockCode.
  Result table columns: क्रमांक, WardCode, <ward or gram panchayat> ("1 - उसकोना"), BlockName, पद का आरक्षण, विजयी उम्मीदवार का
  नाम, पता, प्राप्त वैध मत, प्राप्त मत %, परिणाम (सविरोध / निर्विरोध निर्वाचित), विवरण देखें.
LGD: the GP table's WardCode is the LGD gram panchayat code (5 of 5 checked by hand, all 7,817 UK GP codes in lgd.pri_local_bodies
are 5-digit); the district code is the LGD Zila Panchayat code (45-57 = LGD ZP codes). Kshetra panchayats: the SEC block code
(352 ...) is not the LGD code: records carry sec_block_code + block (Hindi); the loader takes the LGD code from the parent of the
block's GP codes.
No captcha, no login. Heads of ZP / KP (adhyaksh / pramukh, elected indirectly) are not on this site.
One queue item per district: 2 GETs + 1 search (ZP) + 1 block list + 2 GETs + 2 searches per block (8-15 blocks): 20-35 requests.
Records: pri:pri_uk:<district code>:<zp|ps|gp>:<block code>:<ward code>.
"""
import json
import re

import provenance
from dforms import _pri

METHOD = "html table (ASP.NET WebForms result list, header words -> columns)"     # source trail (provenance.py)
MODULE = "pri_uk"
BASE = "https://secresult.uk.gov.in/"
ELECTION = "Uttarakhand Panchayat General Election 2025"
DISTRICTS = {"045": "Almora", "046": "Bageshwar", "047": "Chamoli", "048": "Champawat", "049": "Dehradun", "051": "Nainital",
             "052": "Pauri Garhwal", "053": "Pithoragarh", "054": "Rudraprayag", "055": "Tehri Garhwal", "056": "Udham Singh Nagar",
             "057": "Uttarkashi"}
P = "ctl00$ContentPlaceHolder1$"
STATUS = {"सविरोध निर्वाचित": "won (contested)", "निर्विरोध निर्वाचित": "elected unopposed"}
LEVELS = {  # page -> (level, post, post_regional)
    "WinnerListZP.aspx": ("zp", "Zila Panchayat Member", "जिला पंचायत सदस्य"),
    "WinnerListCP.aspx": ("ps", "Kshetra Panchayat Member", "क्षेत्र पंचायत सदस्य"),
    "WinnerListGP.aspx": ("gp", "Pradhan (Gram Panchayat)", "प्रधान ग्राम पंचायत"),
}


def items(get=None):
    return [{"key": f"{MODULE}:{c}", "payload": {"reader": MODULE, "url": BASE + "FrontDashboard.aspx", "district_code": c,
                                                 "district": n, "state": "UK", "india_only": True, "route": "direct"}}
            for c, n in DISTRICTS.items()]


def form(html, **kw):
    """The page's form fields (hidden inputs, the selected option of each select, no buttons) + kw."""
    s = _pri.soup(html)
    d = {}
    for i in s.find_all("input"):
        if i.get("name") and i.get("type") not in ("submit", "button", "image", "radio", "checkbox"):
            d[i["name"]] = i.get("value", "")
    for sel in s.find_all("select"):
        o = sel.find("option", selected=True) or sel.find("option")
        if sel.get("name") and o is not None:
            d[sel["name"]] = o.get("value", "")
    d.update(kw)
    return d


def rows(html, url, page, p, block_code="", r=None):
    """Records from one result list page (r = the response, for the exact-bytes source trail)."""
    src = provenance.at(r, url) if r is not None else {"src_url": url}
    level, post, post_reg = LEVELS[page]
    s = _pri.soup(html)
    out = []
    for tn, t in enumerate(s.find_all("table"), 1):
        g = _pri.grid(t)
        hi = next((i for i, r in enumerate(g[:3]) if any("WardCode" in _pri.clean(c) for c in r)), None)
        if hi is None:
            continue
        head = [_pri.clean(c) for c in g[hi]]
        col = {}
        for i, h in enumerate(head):
            key = ("ward_code" if h == "WardCode" else "block" if h == "BlockName" else "category" if "आरक्षण" in h
                   else "name" if "उम्मीदवार" in h else "address" if h == "पता" else "pct" if "%" in h
                   else "votes" if "मत" in h else "result" if "परिणाम" in h else "sno" if "क्रमांक" in h
                   else "unit" if ("वार्ड" in h or "पंचायत" in h) else None)
            if key and key not in col:
                col[key] = i
        for rn, r in enumerate(g[hi + 1:], hi + 2):
            cells = [_pri.clean(c) for c in r]
            if len(cells) < len(head) or not cells[col["name"]]:
                continue
            v = {k: cells[i] for k, i in col.items()}
            unit = v.get("unit", "")
            m = re.match(r"^(\d+)\s*-\s*(.+)$", _pri.digits(unit))
            wcode = v.get("ward_code", "")
            if not wcode.isdigit():
                continue
            f = dict(state="UK", level=level, role="head" if level == "gp" else "member", post=post, post_regional=post_reg,
                     name_regional=v["name"], name=v["name"], category=v.get("category"), address=v.get("address"),
                     votes=_pri.int_or_none(v.get("votes")), vote_pct=v.get("pct"), status=STATUS.get(v.get("result"), v.get("result")),
                     status_regional=v.get("result"), district=p["district"], district_code=p["district_code"],
                     block=v.get("block"), election=ELECTION, election_year=2025, source=url, **src,
                     src_pos={"table": tn, "row": rn}, cells=dict(zip(head, cells)))
            if level == "gp":
                f.update(body_name=m.group(2) if m else unit, body_name_regional=m.group(2) if m else unit, sec_no=m.group(1) if m else None,
                         lgd_code=wcode, lgd_match="source", sec_block_code=block_code)
            elif level == "zp":
                f.update(body_name=p["district"], ward=unit, ward_no=m.group(1) if m else None, ward_code=wcode,
                         lgd_code=str(int(p["district_code"])), lgd_match="source")
            else:
                f.update(body_name=v.get("block"), body_name_regional=v.get("block"), ward=unit, ward_no=m.group(1) if m else None,
                         ward_code=wcode, sec_block_code=block_code)
            out.append(_pri.record(MODULE, f"{p['district_code']}:{level}:{block_code or '-'}:{wcode}", **f))
    return out


def fetch(p, get):
    dc = p["district_code"]
    recs, why = [], []
    # Zila Panchayat members: one search per district
    u = BASE + "WinnerListZP.aspx"
    r = get(u)
    if r is None:
        return [], [], "zp page: no answer"
    r2 = get(u, "POST", form(r.text, **{P + "ddlDistrict": dc, P + "btnSearch": "Search"}))
    if r2 is not None:
        recs += rows(r2.text, u, "WinnerListZP.aspx", p, r=r2)
    else:
        why.append("zp search: no answer")
    b = get(BASE + "WinnerListCP.aspx/GetBlocksByDistrict", "POST", json.dumps({"districtCode": dc}),
            {"Content-Type": "application/json; charset=utf-8"})
    try:
        blocks = [(x["Value"], x["Text"]) for x in b.json()["d"] if str(x.get("Value", "")).isdigit()] if b is not None else []
    except (ValueError, KeyError, TypeError):
        blocks = []
    if not blocks:
        why.append("no block list")
    for page in ("WinnerListGP.aspx", "WinnerListCP.aspx"):
        u = BASE + page
        r = get(u)
        if r is None:
            why.append(f"{page}: no answer")
            continue
        for code, _name in blocks:
            r2 = get(u, "POST", form(r.text, **{P + "ddlDistrict": dc, P + "ddlBlock": code, P + "hdnBlockCode": code,
                                                P + "btnSearch": "Search"}))
            if r2 is None:
                why.append(f"{page} {code}: no answer")
                continue
            recs += rows(r2.text, u, page, p, code, r=r2)
    return recs, [], "; ".join(why) if not recs or why else ""
