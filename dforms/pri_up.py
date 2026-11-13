"""Uttar Pradesh: every elected member of the three-tier panchayat general election 2021, from the State Election Commission's
winner list "Panchayat General Election - 2021 / Winner List" (sec.up.nic.in/site/WinnerListPRI2021.aspx). India only: the host
answers dev-vps-3 (OVH Mumbai) and not the hub's proxies or runners abroad (cforms/cr_up.py), so route "direct"
(project civic-officials-up-direct). No captcha, no login.

The page is ASP.NET WebForms (measured 2026-11-13 from dev-vps-3). ddlPostTypes (auto-postback) = the post:
  1 जिला पंचायत अध्यक्ष (Zila Panchayat Adhyaksh)    state-wide, no district list      75 rows
  2 जिला पंचायत सदस्य (Zila Panchayat member)        ddlDistrictName                   Lucknow 25 rows
  3 क्षेत्र पंचायत प्रमुख (Kshetra Panchayat Pramukh) state-wide                        825 rows
  4 क्षेत्र पंचायत सदस्य (Kshetra Panchayat member)  ddlDistrictName + ddlBlockName     Gosaiganj 94 rows
  5 ग्राम पंचायत प्रधान (Gram Pradhan)                ddlDistrictName + ddlBlockName     Gosaiganj 76 rows
  6 ग्राम पंचायत सदस्य (Gram Panchayat member)       ddlDistrictName + ddlBlockName     Gosaiganj 952 rows
btnSubmit ("View Details") shows table ctl00_ContentPlaceHolder1_GridView1, all rows on one page (no pager). Posts 4-6 show
nothing without a block ("चुनी गई प्रक्रिया में कोई डेटा उपलब्ध नहीं है।"). Columns (header words -> fields): जनपद district,
विकास खण्ड / ब्लॉक block ("1 - गोसाईगंज"), ग्राम पंचायत GP ("1 - सलेमपुर"), जिला पंचायत वार्ड / क्षेत्र पंचायत वार्ड /
ग्राम पंचायत वार्ड ward ("24 - गोसाईगंज तृतीय" or "3"), पद का आरक्षण seat reservation, उम्मीदवार name, पिता/पति father or
husband, उम्मीदवार की जाति/वर्ग category, शैक्षिक योग्यता education, लिंग gender, आयु age, मोबाइल नं० mobile, पता address,
प्राप्त वैध मत votes, प्राप्त मत % vote share, मतदान % turnout, परिणाम result (सविरोध = won a contest, निर्विरोध = unopposed).
Steps (as a person takes them): GET; postback the post; postback the district; then "View Details" with each block of the
district's block list, from the district page's form (the same form is posted once per block; a block submit without its own
auto-postback was checked to answer 2026-11-13). About 2 + n_blocks requests per item (UP: 826 blocks in 75 districts).

Queue items (items()): post 1 and post 3 for the whole state (2 items), post 2 per district (75), posts 5, 4 and 6 per district
(3 x 75); 302 items, heads first in queue order (payload tier 'heads' = posts 1, 3, 5). Expected rows (UNCHECKED beyond the samples):
75 + 825 + ~3,050 ZP members + ~57,700 pradhans + ~75,000 KP members + ~730,000 GP members (SEC 2021 seat totals, unchecked).

LGD: dforms/pri_up_lgd.json.gz (dforms/pri_up_build.py, DB civic lgd.pri_local_bodies): the SEC district id gives the LGD Zilla
Panchayat code (exact); the block name (Hindi) is matched to an LGD Kshetra Panchayat of that ZP, and the GP name to an LGD Gram
Panchayat of that block, with the Devanagari-to-Latin key of cforms/cr_common.py (best_body: score >= 0.8 and a 0.08 margin).
lgd_match "sec district id" (ZP), "name" (block / GP); no lgd_code when the match is weak: body_name, block and district stay.
Note: the 2021 bodies' five-year terms end in 2026 (first meetings May-July 2021); the SEC shows no 2026 results on 2026-11-13.
Record ids: pri:pri_up:zp:<ZP code>[:w<ward>], ps:<ZP code>:<block slug> (pramukh), ps:<sec block id>:w<ward>,
gp:<sec block id>:<sec GP no>[:w<ward>].
"""
import gzip
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

import provenance
from cforms.cr_common import best_body, key, latin, sim
from dforms._pri import clean, digits, int_or_none, mobile, record
from forms.aspnet import hidden, options

METHOD = "html table (ASP.NET winner grid; post, district and block postbacks)"     # source trail (provenance.py)

MODULE = "pri_up"
URL = "https://sec.up.nic.in/site/WinnerListPRI2021.aspx"
P = "ctl00$ContentPlaceHolder1$"
GRID = "ctl00_ContentPlaceHolder1_GridView1"
ELECTION = "Uttar Pradesh Panchayat General Election 2021 (SEC Uttar Pradesh)"
NO_DATA = "कोई डेटा उपलब्ध नहीं"
# post -> (level, role, English post, Hindi post, needs district, needs block)
POSTS = {"1": ("zp", "head", "Zila Panchayat Adhyaksh", "जिला पंचायत अध्यक्ष", False, False),
         "2": ("zp", "member", "Zila Panchayat Member", "जिला पंचायत सदस्य", True, False),
         "3": ("ps", "head", "Kshetra Panchayat Pramukh", "क्षेत्र पंचायत प्रमुख", False, False),
         "4": ("ps", "member", "Kshetra Panchayat Member", "क्षेत्र पंचायत सदस्य", True, True),
         "5": ("gp", "head", "Gram Pradhan", "ग्राम पंचायत प्रधान", True, True),
         "6": ("gp", "member", "Gram Panchayat Member", "ग्राम पंचायत सदस्य", True, True)}
HEAD = [("district", r"^जनपद$|^जिला$"), ("block", r"विकास\s*ख[ण|ं]्?ड|ब्लॉक"), ("ward", r"वार्ड"), ("gp", r"^ग्राम\s*पंचायत$"),
        ("seat_reservation", r"आरक्षण"), ("name", r"^उम्मीदवार$"), ("father_name", r"पिता|पति"), ("category", r"जाति|वर्ग"),
        ("education", r"शैक्षिक|योग्यता"), ("gender", r"लिंग"), ("age", r"आयु"), ("phone", r"मोबाइल"), ("address", r"पता"),
        ("votes", r"वैध\s*मत"), ("vote_pct", r"प्राप्त\s*मत\s*%"), ("turnout_pct", r"मतदान"), ("result", r"परिणाम")]
GENDER = {"महिला": "female", "पुरुष": "male"}
RESULT = {"सविरोध": "won (contested)", "निर्विरोध": "elected unopposed"}
_LGD = None


def lgd():
    global _LGD
    if _LGD is None:
        _LGD = json.loads(gzip.decompress((Path(__file__).parent / "pri_up_lgd.json.gz").read_bytes()).decode("utf-8"))
    return _LGD


def num_name(s):
    """"24 - गोसाईगंज तृतीय" -> ("24", "गोसाईगंज तृतीय"); "3" -> ("3", ""); text without a number -> ("", text)."""
    s = clean(digits(s))
    m = re.match(r"^(\d+)\s*(?:[-–.]\s*(.*))?$", s)
    return (m.group(1), clean(m.group(2) or "")) if m else ("", s)


def roles(header):
    out = {}
    for i, h in enumerate(header):
        for role, rx in HEAD:
            if role not in out.values() and re.search(rx, h):
                out[i] = role
                break
    return out


def rows(html):
    """[(row dict by role, cells {header: text}, 1-based row number in the table)] of the winner grid; [] when it is empty."""
    t = BeautifulSoup(html, "lxml").find("table", id=GRID)
    trs = t.find_all("tr") if t else []
    if not trs:
        return []
    header = [clean(c.get_text(" ", strip=True)) for c in trs[0].find_all(["th", "td"])]
    rl = roles(header)
    out = []
    for ri, tr in enumerate(trs[1:], 2):
        c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) != len(header):
            continue
        out.append(({rl[i]: v for i, v in enumerate(c) if i in rl}, dict(zip(header, c)), ri))
    return out


def zp_of(district_hi):
    """(SEC district id, LGD district, ZP code) of a Hindi district name as the grid writes it."""
    ds = lgd()["districts"]
    for sid, (hi, en, zp) in ds.items():
        if clean(hi) == clean(district_hi):
            return sid, en, zp
    code, _ = best_body(district_hi, [(sid, en, "", "") for sid, (hi, en, zp) in ds.items()])
    return (code, ds[code][1], ds[code][2]) if code else (None, None, None)


def _keys(name, hindi):
    """Match keys of one name: the whole name (Devanagari to Latin when hindi), brackets dropped; "0" abbreviations ("मो0पुर")
    dropped; with a second key where every d is read as r (ड / ड़ and ढ / ढ़ are often written without the dot)."""
    s = re.sub(r"\([^)]*\)", " ", name or "")
    if hindi:
        s = latin(s.replace("ॉ", "ा").replace("ॅ", "े").replace("0", " "))
    k = key(s)
    return {x for x in (k, k.replace("d", "r")) if x}


def _soft(name, hindi):
    """A second, vowel-keeping form for ties of the consonant key: Latin letters, long vowels made short, w -> v."""
    s = re.sub(r"\([^)]*\)", " ", name or "")
    if hindi:
        s = latin(s.replace("ॉ", "ा").replace("ॅ", "े").replace("0", " "))
    s = re.sub(r"[^a-z]", "", s.lower()).replace("w", "v").replace("ee", "i").replace("oo", "u")
    s = re.sub(r"([aeiou])\1+", r"\1", s)
    return re.sub(r"([kgcjtdpb])h", r"\1", s)


def match(name_hi, bodies):
    """(LGD code, score) of the body in bodies [[code, name]] whose whole name is closest to name_hi: consonant-key score >= 0.8
    and a margin of 0.08 over the next body; when several bodies are within that margin (the key drops vowels and h: Hardoiya /
    Dhaurahra), the vowel-keeping form decides if it leads by 0.05. (None, best score) otherwise."""
    hk = _keys(name_hi, True)
    if not hk or not bodies:
        return None, 0.0
    sc = sorted(((max(sim(a, b) for a in hk for b in _keys(n, False)), c, n) for c, n in bodies), reverse=True)
    if sc[0][0] < 0.8:
        return None, round(sc[0][0], 3)
    close = [x for x in sc if sc[0][0] - x[0] < 0.08]
    if len(close) == 1:
        return sc[0][1], round(sc[0][0], 3)
    hs = _soft(name_hi, True)
    soft = sorted(((sim(hs, _soft(n, False)), c, s0) for s0, c, n in close), reverse=True)
    if soft[0][0] >= 0.75 and soft[0][0] - soft[1][0] >= 0.05:
        return soft[0][1], round(soft[0][2], 3)
    return None, round(sc[0][0], 3)


def block_of(zp, block_hi):
    return match(block_hi, lgd()["blocks"].get(zp, []))


def gp_of(block_code, gp_hi):
    return match(gp_hi, lgd()["gps"].get(block_code, []))


def slugl(s):
    return re.sub(r"[^a-z0-9]+", "-", latin(s).lower()).strip("-")[:50]


def records(html, post, src, district_id=None, block_id=None, block_name=None):
    """Records of one winner grid. src = provenance.at(response, URL) of the answer that showed it."""
    level, role, post_en, post_hi, _, _ = POSTS[post]
    recs, cache = [], {}
    for r, cells, ri in rows(html):
        if not r.get("name"):
            continue
        dist_hi = r.get("district") or (lgd()["districts"][district_id][0] if district_id else "")
        sid, dist_en, zp = zp_of(dist_hi) if dist_hi else (None, None, None)
        blk_no, blk_hi = num_name(r.get("block", "")) if r.get("block") else ("", "")
        blk_hi = blk_hi or (block_name or "")
        ward_no, ward_name = num_name(r["ward"]) if r.get("ward") else ("", "")
        gp_no, gp_hi = num_name(r["gp"]) if r.get("gp") else ("", "")
        d = {"state": "UP", "level": level, "role": role, "post": post_en, "post_regional": post_hi,
             "name": r["name"], "father_name": r.get("father_name"), "gender": GENDER.get(r.get("gender", ""), r.get("gender")),
             "category": r.get("category"), "seat_reservation": r.get("seat_reservation"), "education": r.get("education"),
             "age": int_or_none(r.get("age")), "phone": mobile(r.get("phone", "")), "address": r.get("address") if r.get("address") != "-" else None,
             "votes": int_or_none(r.get("votes")), "vote_pct": r.get("vote_pct") if re.fullmatch(r"\d+(\.\d+)?", r.get("vote_pct", "")) else None,
             "turnout_pct": r.get("turnout_pct") if re.fullmatch(r"\d+(\.\d+)?", r.get("turnout_pct", "")) else None,
             "status": RESULT.get(r.get("result", ""), r.get("result")), "status_regional": r.get("result"),
             "district": dist_en or dist_hi, "district_regional": dist_hi, "election": ELECTION, "election_year": 2021,
             "source": URL, "sec_post": post, "sec_district_id": district_id or sid, "sec_block_id": block_id,
             "src_pos": {"table": GRID, "row": ri}, "cells": cells, **src}
        if level == "zp":
            d.update({"body_name": dist_en or dist_hi, "body_name_regional": dist_hi, "lgd_code": zp,
                      "lgd_match": "sec district id" if zp else None})
            if ward_no or ward_name:
                d.update({"ward_no": ward_no, "ward": ward_name})
            key = f"zp:{zp or slugl(dist_hi)}" + (f":w{ward_no or slugl(ward_name)}" if role == "member" else "")
        else:
            if (zp, blk_hi) not in cache:
                cache[(zp, blk_hi)] = block_of(zp, blk_hi) if zp and blk_hi else (None, 0.0)
            bcode, _ = cache[(zp, blk_hi)]
            d.update({"block": blk_hi, "block_no": blk_no or None, "block_lgd_code": bcode, "zp_lgd_code": zp})
            if level == "ps":
                d.update({"body_name": blk_hi, "lgd_code": bcode, "lgd_match": "name" if bcode else None})
                if role == "member":
                    d.update({"ward_no": ward_no, "ward": ward_name})
                    key = f"ps:{block_id or slugl(blk_hi)}:w{ward_no or slugl(ward_name)}"
                else:
                    key = f"ps:{zp or slugl(dist_hi)}:{slugl(blk_hi)}"
            else:
                gcode, score = gp_of(bcode, gp_hi) if bcode and gp_hi else (None, 0.0)
                d.update({"body_name": gp_hi, "gp_no": gp_no or None, "lgd_code": gcode, "lgd_match": "name" if gcode else None,
                          "lgd_score": score if gp_hi and bcode else None})
                key = f"gp:{block_id or slugl(blk_hi)}:{gp_no or slugl(gp_hi)}"
                if role == "member":
                    d.update({"ward_no": ward_no or None, "ward": ward_name or None})
                    key += f":w{ward_no or slugl(ward_name)}"
        recs.append(record(MODULE, key, **d))
    # the same seat twice in one grid (it happens in SEC lists): keep both, the second with a row suffix
    seen, out = {}, []
    for rid, d in recs:
        if rid in seen:
            rid = f"{rid}:r{d['src_pos']['row']}"
        seen[rid] = 1
        out.append((rid, d))
    return out


def _post(get, html, fields, target=""):
    d = hidden(html)
    d.update({"__EVENTTARGET": target, "__EVENTARGUMENT": "", "__LASTFOCUS": ""})
    d.update({P + k: v for k, v in fields.items()})
    if not target:
        d[P + "btnSubmit"] = "View Details"
    return get(URL, method="POST", data=d)


def selected(html, name):
    sel = BeautifulSoup(html, "lxml").find("select", attrs={"name": P + name})
    o = sel.find("option", selected=True) if sel else None
    return o.get("value") if o else None


def fetch(p, get):
    post = p["post"]
    level, role, _, _, need_d, need_b = POSTS[post]
    r = get(URL)
    if r is None:
        return [], [], "no answer"
    r = _post(get, r.text, {"ddlPostTypes": post}, P + "ddlPostTypes")
    if r is None or selected(r.text, "ddlPostTypes") != post:
        return [], [], "post postback did not answer"
    if not need_d:
        r = _post(get, r.text, {"ddlPostTypes": post})
        if r is None:
            return [], [], "submit did not answer"
        recs = records(r.text, post, provenance.at(r, URL))
        return recs, [], "" if recs else "no winner rows"
    did = p["district_id"]
    r = _post(get, r.text, {"ddlPostTypes": post, "ddlDistrictName": did}, P + "ddlDistrictName")
    if r is None or selected(r.text, "ddlDistrictName") != did:
        return [], [], "district postback did not answer"
    if not need_b:
        r = _post(get, r.text, {"ddlPostTypes": post, "ddlDistrictName": did})
        if r is None:
            return [], [], "submit did not answer"
        recs = records(r.text, post, provenance.at(r, URL), district_id=did)
        return recs, [], "" if recs else "no winner rows"
    form = r.text
    blocks = options(form, "ddlBlockName")
    if not blocks:
        return [], [], "no blocks in the list"
    recs, empty = [], []
    for bid, bname in blocks:
        a = _post(get, form, {"ddlPostTypes": post, "ddlDistrictName": did, "ddlBlockName": bid})
        if a is None:
            return [], [], f"block {bid} did not answer"
        if selected(a.text, "ddlBlockName") != bid:
            return [], [], f"block {bid}: page shows block {selected(a.text, 'ddlBlockName')}"
        got = records(a.text, post, provenance.at(a, URL), district_id=did, block_id=bid, block_name=bname)
        if not got:
            empty.append(bname)
        recs += got
    for _, d in recs:
        d["blocks_listed"] = len(blocks)
        if empty:
            d["blocks_without_rows"] = empty
    return recs, [], "" if recs else "no winner rows"


def items(get=None):
    """The queue items (no request needed: the district ids are in pri_up_lgd.json.gz). Heads first."""
    base = {"reader": MODULE, "url": URL, "host": "sec.up.nic.in", "state": "UP", "india_only": True, "route": "direct"}
    out = [{"key": f"pri_up:p{x}", "payload": {**base, "post": x, "tier": "heads"}} for x in ("1", "3")]
    ds = sorted(lgd()["districts"].items(), key=lambda x: int(x[0]))
    for post in ("5", "2", "4", "6"):
        for did, (hi, en, zp) in ds:
            out.append({"key": f"pri_up:p{post}:d{did}",
                        "payload": {**base, "post": post, "tier": "heads" if post == "5" else "members", "district_id": did,
                                    "district": en, "district_regional": hi, "zp_lgd_code": zp}})
    return out
