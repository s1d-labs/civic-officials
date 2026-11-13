"""Bihar: elected Panchayati Raj members from the State Election Commission (SEC Bihar), panchayat general election 2021
(11 phases, Sep-Dec 2021), host sec2021.bihar.gov.in (linked from sec.bihar.gov.in "Panchayat Election 2021 Result"). No captcha,
no login, no party (Bihar panchayat polls are non-party). The host answered GitHub runners abroad (archive vantage "pool", 200).

Two kinds of item (payload "mode"):

1. "result" (direct posts; one item = one phase page + one district): /claim-objection/Result<phase>.aspx?D=0&PO=1 (ASP.NET).
   Postbacks: ddl_Post -> ddlDistrict -> ddlBlock (the blocks of this district that voted in this phase) -> then
     post 3 Mukhiya (gram panchayat head) / 4 Sarpanch (gram kachahri head): ddlPanchayat -> Show (1 request per panchayat);
     post 5 Panchayat Samiti member: ddlPanchayat postback -> ddl_PachayatSamitiNo -> Show per constituency;
     post 6 Zila Parishad member: ddl_DistNo (constituencies of the block) -> Show per constituency;
     post 1 Gram Panchayat ward member / 2 Gram Kachahri panch: ddlPanchayat postback -> ddlWard -> Show per ward
       (about 110,000 wards each: payload "posts" includes 1 / 2 only in the members seed file).
   The answer table #ctl00_ContentPlaceHolder1_RPDetails lists every candidate with votes; the winner's name carries "(विजेता)"
   (cforms/br.py winner(): marked, else the only candidate, else the single highest vote). One record per winner, with every
   candidate kept (name, votes).
2. "indirect" (one item = one post): /claim-objection/Indirect_Final_WinningList.aspx, the final list of winners of the indirect
   elections: 1 Zila Parishad Adhyaksh, 2 Upadhyaksh (whole state, one Show), 3 Pramukh, 4 Up-pramukh (per district),
   5 Up-mukhiya, 6 Up-sarpanch (not public: see INDIRECT_PUBLIC). Columns: Post, District, Block,
   Panchayat, Reservation Status, Candidate Name, Father/Husband Name, Gender, Age, Category, Address.

No source gives phone numbers (ePanchayat Bihar DSC report lists DSC holders without post or phone; not used).
LGD: the SEC uses its own codes (district value, block value, panchayat code like 330010010). lgd_code is set by a name match
within the district and block against dforms/pri_br_lgd.json (built from DB civic lgd.pri_local_bodies by
seeds/build_pri_br.py): Hindi names normalised (norm()), exact first, else the single best close match (ratio >= 0.84).
Record ids: pri:pri_br:<phase>:<district>:<block>:<panchayat or ->:<post>:<no or ->; pri:pri_br:ind:<post>:<row key>.
"""
import difflib
import json
import re
from pathlib import Path

import provenance
from cforms.br import WIN, ZW, _post, _result, _votes, winner
from dforms import _pri
from forms.aspnet import options

METHOD = "html table (ASP.NET result page, one POST per panchayat / constituency / ward; winner marked विजेता)"
MODULE = "pri_br"
HOST = "http://sec2021.bihar.gov.in/claim-objection/"
INDIRECT_URL = HOST + "Indirect_Final_WinningList.aspx"
ELECTION = "Bihar Panchayat General Election 2021"
HEAD_POSTS = ["3", "4", "5", "6"]
MEMBER_POSTS = ["1", "2"]

# SEC post value -> (level, role, post, post_regional, body_kind, select that lists the unit numbers or None)
POSTS = {
    "1": ("gp", "member", "Ward Member (Gram Panchayat)", "ग्राम पंचायत के सदस्य", "gram_panchayat", "ddlWard"),
    "2": ("gp", "member", "Panch (Gram Kachahri)", "ग्राम कचहरी के पंच", "gram_kachahri", "ddlWard"),
    "3": ("gp", "head", "Mukhiya", "ग्राम पंचायत के मुखिया", "gram_panchayat", None),
    "4": ("gp", "head", "Sarpanch (Gram Kachahri)", "ग्राम कचहरी के सरपंच", "gram_kachahri", None),
    "5": ("ps", "member", "Panchayat Samiti Member", "पंचायत समिति के सदस्य", "panchayat_samiti", "ddl_PachayatSamitiNo"),
    "6": ("zp", "member", "Zila Parishad Member", "जिला परिषद के सदस्य", "zila_parishad", "ddl_DistNo"),
}
INDIRECT = {
    "1": ("zp", "head", "Zila Parishad Adhyaksh", "अध्यक्ष", "zila_parishad"),
    "2": ("zp", "deputy", "Zila Parishad Upadhyaksh", "उपाध्यक्ष", "zila_parishad"),
    "3": ("ps", "head", "Pramukh (Panchayat Samiti)", "प्रमुख", "panchayat_samiti"),
    "4": ("ps", "deputy", "Up-pramukh (Panchayat Samiti)", "उपप्रमुख", "panchayat_samiti"),
    "5": ("gp", "deputy", "Up-mukhiya", "उपमुखिया", "gram_panchayat"),
    "6": ("gp", "deputy", "Up-sarpanch (Gram Kachahri)", "उपसरपंच", "gram_kachahri"),
}
# 5 / 6 (Up-mukhiya, Up-sarpanch): the public page shows no district list and answers "Please select district" (the
# district is set only for signed-in users: hidden fields hfDist / hfUser). Not queued.
INDIRECT_PUBLIC = ["1", "2", "3", "4"]
# phase -> SEC district values on Result<phase>.aspx (read 2026-11-13 from the 11 pages; 352 phase-district pairs)
PHASES = {
    1: "33 35 31 36 38 34 37 23 24 32",
    2: "7 33 35 10 31 21 36 15 38 34 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 18 6 19 12 17 16 4",
    3: "7 33 35 10 31 21 36 15 38 34 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 6 19 12 17 16 4",
    4: "7 33 35 10 31 8 21 36 15 38 34 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 6 19 12 17 16 4",
    5: "7 33 35 10 31 8 21 36 15 38 34 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 26 3 6 19 12 17 16 4",
    6: "7 35 10 31 8 21 36 15 38 34 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 26 3 6 19 12 17 16 4",
    7: "7 35 10 31 8 21 36 15 38 34 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 26 3 6 19 12 17 16 4",
    8: "7 35 10 31 8 21 36 15 38 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 26 3 6 19 12 17 16 4",
    9: "7 35 10 31 8 21 36 15 13 37 27 28 9 2 1 30 20 23 22 29 24 14 11 5 32 25 18 26 3 6 19 12 17 16 4",
    10: "7 35 10 31 8 21 36 15 13 37 27 28 9 2 1 30 20 23 22 29 14 11 5 32 25 18 26 3 6 19 12 17 16 4",
    11: "15 13 27 28 9 2 1 20 22 29 14 11 5 18 6 19 12 17 16 4",
}
DISTRICTS = {
    "1": "पश्चिम चम्पारण", "2": "पूर्वी चम्पारण", "3": "शिवहर", "4": "सीतामढ़ी", "5": "मधुबनी", "6": "सुपौल", "7": "अररिया",
    "8": "किशनगंज", "9": "पूर्णियां", "10": "कटिहार", "11": "मधेपुरा", "12": "सहरसा", "13": "दरभंगा", "14": "मुजफ्फरपुर",
    "15": "गोपालगंज", "16": "सिवान", "17": "सारण", "18": "वैशाली", "19": "समस्तीपुर", "20": "बेगूसराय", "21": "खगड़िया",
    "22": "भागलपुर", "23": "बांका", "24": "मुंगेर", "25": "लखीसराय", "26": "शेखपुरा", "27": "नालन्दा", "28": "पटना",
    "29": "भोजपुर", "30": "बक्सर", "31": "कैमूर (भभुआ)", "32": "रोहतास", "33": "अरवल", "34": "जहानाबाद", "35": "औरंगाबाद",
    "36": "गया", "37": "नवादा", "38": "जमुई",
}
# rows expected per phase-district item for the head posts (unchecked estimate: GPs x 2 + PS + ZP members over 352 items)
EXPECTED_HEADS = 75


def items(get=None):
    out = []
    for ph, ds in PHASES.items():
        for d in ds.split():
            out.append({"key": f"pri_br:p{ph}:d{d}", "payload": {
                "reader": MODULE, "mode": "result", "url": f"{HOST}Result{ph}.aspx?D=0&PO=1", "phase": ph,
                "district_value": d, "district": DISTRICTS[d], "posts": HEAD_POSTS, "state": "BR", "route": "abroad",
                "india_only": False, "expected": EXPECTED_HEADS}})
    for post in INDIRECT_PUBLIC:
        out.append({"key": f"pri_br:ind:{post}", "payload": {
            "reader": MODULE, "mode": "indirect", "url": INDIRECT_URL, "post": post, "state": "BR", "route": "abroad",
            "india_only": False, "expected": {"1": 38, "2": 38, "3": 534, "4": 534}[post]}})
    return out


def member_items():
    """Ward members and panches (posts 1, 2): one item per phase-district-post; about 220,000 requests in all (one per ward)."""
    out = []
    for it in items():
        p = it["payload"]
        if p["mode"] != "result":
            continue
        for post in MEMBER_POSTS:
            out.append({"key": f"pri_br:m{post}:p{p['phase']}:d{p['district_value']}",
                        "payload": {**p, "posts": [post], "expected": 300}})
    return out


# ---- LGD name match -------------------------------------------------------------------------------------------------------
_LGD = None
_N = [("\u095c", "ड"), ("\u095d", "ढ"), ("\u095b", "ज"), ("\u095e", "फ"), ("\u0958", "क"), ("\u095a", "ग"), ("\u093c", ""), ("ं", ""), ("ँ", ""), ("ः", ""), ("्", ""), ("ब", "व"), ("ी", "ि"), ("ू", "ु"),
      ("ण", "न"), ("श", "स"), ("ष", "स"), ("ङ", "न"), ("ञ", "न"), ("ै", "े"), ("ौ", "ो"), ("ऐ", "ए"), ("औ", "ओ"), ("ई", "इ"),
      ("ऊ", "उ"), ("ऋ", "रि"), ("ृ", "रि")]


def norm(s):
    """Hindi place name -> a loose key: no 'पंचायत' / 'ग्राम', no spaces or marks, common spelling pairs folded."""
    s = ZW.sub("", s or "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"ग्राम\s*पंचायत|पंचायत|ग्राम|प्रखंड|प्रखण्ड", "", s)
    s = s.replace("क्ष", "छ")
    for a, b in _N:
        s = s.replace(a, b)
    return re.sub(r"[\s.\-,]+", "", s)


def lgd():
    global _LGD
    if _LGD is None:
        _LGD = json.loads((Path(__file__).with_name("pri_br_lgd.json")).read_text())
    return _LGD


def _pick(name, table):
    """table {norm key: value}: exact key, else the single best close key (ratio >= 0.84, 0.04 ahead of the next)."""
    k = norm(name)
    if not k:
        return None
    if k in table:
        return table[k]
    sc = sorted(((difflib.SequenceMatcher(None, k, x).ratio(), x) for x in table), reverse=True)
    if sc and sc[0][0] >= 0.84 and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 0.04):
        return table[sc[0][1]]
    return None


def lgd_codes(district_value=None, district=None, block=None, panchayat=None):
    """(zp code, block code, gp code) or None for the parts not matched. district_value = SEC district value."""
    m = lgd()
    zp = m["sec_district"].get(str(district_value or "")) or _pick(district or "", m["zp_by_name"])
    if not zp:
        return None, None, None
    blocks = m["zp"][zp]["blocks"]
    b = _pick(block, {k: k for k in blocks}) if block else None
    if not b:
        return zp, None, None
    bl = blocks[b]
    g = _pick(panchayat, bl["gps"]) if panchayat else None
    return zp, bl["code"], g


# ---- result pages -----------------------------------------------------------------------------------------------------------
def _name(s):
    return " ".join(ZW.sub("", WIN.sub(" ", s or "")).split())


def _status(c):
    t = c.get("प्रत्याशी का नाम", "")
    return "elected unopposed" if "निर्विरोध" in t else "won"


def _record(p, post, form, rows, c, how, resp, url, unit_no, names):
    level, role, en, hi, kind, _ = POSTS[post]
    d_name = c.get("जिला") or names.get("district") or p.get("district")
    b_name = c.get("प्रखंड") or names.get("block")
    g_name = c.get("पंचायत") or names.get("panchayat")
    zp, bc, gc = lgd_codes(p["district_value"], d_name, b_name, g_name if level == "gp" else None)
    code = {"zp": zp, "ps": bc, "gp": gc}[level]
    votes = _votes(c.get("कुल प्राप्त मत"))
    others = sorted((_votes(x.get("कुल प्राप्त मत")) or 0 for x in rows if x is not c), reverse=True)
    ri = next(i for i, x in enumerate(rows) if x is c)
    key = ":".join(str(x) for x in (p["phase"], p["district_value"], form.get("ddlBlock", "-"), form.get("ddlPanchayat", "-"),
                                    post, unit_no or "-"))
    return _pri.record(
        MODULE, key, state="BR", level=level, role=role, post=en, post_regional=c.get("पद") or hi, body_kind=kind,
        name=_name(c.get("प्रत्याशी का नाम")), votes=votes, candidates=[{"name": _name(x.get("प्रत्याशी का नाम")),
                                                                        "votes": _votes(x.get("कुल प्राप्त मत"))} for x in rows],
        n_candidates=len(rows), margin=votes - others[0] if votes is not None and others else None,
        winner_by=None if how == "marked" else how, status=_status(c),
        district=d_name, block=b_name if level != "zp" else (b_name or None),
        body_name={"zp": d_name, "ps": b_name, "gp": g_name}[level], panchayat=g_name if level != "gp" else None,
        ward_no=unit_no if post in ("1", "2") else None, constituency=unit_no if post in ("5", "6") else None,
        lgd_code=code, lgd_match="name" if code else None, lgd_zp=zp, lgd_block=bc, lgd_gp=gc,
        sec_district=p["district_value"], sec_block=form.get("ddlBlock"), sec_panchayat=form.get("ddlPanchayat"),
        election=f"{ELECTION}, phase {p['phase']}", election_year=2021, phase=p["phase"], source=url,
        **provenance.at(resp, url),
        src_pos={"table_id": "ctl00_ContentPlaceHolder1_RPDetails", "row": ri + 2,
                 "form": {k: v for k, v in form.items()}},
        cells=c)


def _show(get, url, h, form, p, post, unit_no, names, recs, why):
    r, resp = _post(get, url, h, "", form, resp=True)
    if r is None:
        why.append(f"no answer {form}")
        return h
    msg, rows, _ = _result(r)
    rows = [x for x in rows if x.get("जिला") and x.get("प्रत्याशी का नाम") != "कुल मत"]     # the "कुल मत" (total) row
    if not rows:
        if msg:
            why.append(f"{form.get('ddlPanchayat', form.get('ddlBlock'))}/{unit_no}: {msg[:60]}")
        return r
    c, how = winner(rows)
    if c is not None:
        recs.append(_record(p, post, dict(form), rows, c, how, resp, url, unit_no, names))
    return r


def fetch_result(p, get):
    url = p["url"]
    r0 = get(url)
    if r0 is None:
        return [], [], "no answer"
    recs, why = [], []
    for post in p.get("posts", HEAD_POSTS):
        unit_sel = POSTS[post][5]
        f = {"ddl_Post": post}
        h = _post(get, url, r0.text, "ddl_Post", f)
        f["ddlDistrict"] = p["district_value"]
        h = h and _post(get, url, h, "ddlDistrict", f)
        if not h:
            why.append(f"post {post}: district postback did not answer")
            continue
        blocks = [b for b in options(h, "ddlBlock") if not p.get("blocks") or b[0] in p["blocks"]]
        if not blocks:
            why.append(f"post {post}: no blocks")
        for bv, bn in blocks:
            fb = {**f, "ddlBlock": bv}
            hb = _post(get, url, h, "ddlBlock", fb)
            if not hb:
                why.append(f"block {bv}: no answer")
                continue
            names = {"district": p.get("district"), "block": bn}
            if post == "6":
                for no, _ in options(hb, unit_sel):
                    hb = _show(get, url, hb, {**fb, unit_sel: no}, p, post, no, names, recs, why)
                continue
            pans = [x for x in options(hb, "ddlPanchayat") if not p.get("panchayats") or x[0] in p["panchayats"]]
            for pv, pn in pans:
                fp = {**fb, "ddlPanchayat": pv}
                nm = {**names, "panchayat": pn}
                if unit_sel is None:
                    hb = _show(get, url, hb, fp, p, post, None, nm, recs, why)
                    continue
                hp = _post(get, url, hb, "ddlPanchayat", fp)
                if not hp:
                    why.append(f"panchayat {pv}: no answer")
                    continue
                for no, _ in options(hp, unit_sel):
                    hp = _show(get, url, hp, {**fp, unit_sel: no}, p, post, no, nm, recs, why)
    return recs, [], "" if recs else ("; ".join(why[:5]) or "no winners")


# ---- indirect winners ---------------------------------------------------------------------------------------------------------
def _grid(html):
    """The winners table: [(row number, {header: text})]."""
    s = _pri.soup(html)
    for t in s.find_all("table"):
        trs = t.find_all("tr")
        if not trs:
            continue
        head = [_pri.clean(c.get_text(" ")) for c in trs[0].find_all(["th", "td"])]
        if "Candidate Name" not in head:
            continue
        out = []
        for i, tr in enumerate(trs[1:], start=2):
            c = [_pri.clean(td.get_text(" ")) for td in tr.find_all("td")]
            if len(c) == len(head) and any(c):
                out.append((i, dict(zip(head, c))))
        return out
    return []


def indirect_records(html, resp, p, form):
    post = p["post"]
    level, role, en, hi, kind = INDIRECT[post]
    out = []
    for i, c in _grid(html):
        d_name, b_name, g_name = c.get("District"), c.get("Block"), c.get("Panchayat")
        zp, bc, gc = lgd_codes(form.get("ddlDistrict"), d_name, b_name, g_name if level == "gp" else None)
        code = {"zp": zp, "ps": bc, "gp": gc}[level]
        key = ":".join(["ind", post, form.get("ddlDistrict", "-"), norm(b_name) or "-", norm(g_name) or "-",
                        norm(c.get("Candidate Name")) or str(i)])
        out.append(_pri.record(
            MODULE, key, state="BR", level=level, role=role, post=en, post_regional=c.get("Post") or hi, body_kind=kind,
            name=c.get("Candidate Name"), father_name=c.get("Father/Husband Name"), gender=c.get("Gender"),
            age=_pri.int_or_none(c.get("Age")), category=c.get("Category"), reservation=c.get("Reservation Status"),
            address=c.get("Address"), district=d_name, block=b_name, panchayat=g_name,
            body_name={"zp": d_name, "ps": b_name, "gp": g_name}[level],
            lgd_code=code, lgd_match="name" if code else None, lgd_zp=zp, lgd_block=bc, lgd_gp=gc,
            election=f"{ELECTION}, indirect election (final winning list)", election_year=2021, status="won",
            source=p["url"], **provenance.at(resp, p["url"]),
            src_pos={"table": "Indirect winning list", "row": i, "form": dict(form)}, cells=c))
    return out


def fetch_indirect(p, get):
    url = p["url"]
    r0 = get(url)
    if r0 is None:
        return [], [], "no answer"
    f = {"ddl_Post": p["post"]}
    h = _post(get, url, r0.text, "ddl_Post", f)
    if not h:
        return [], [], "post postback did not answer"
    recs, why = [], []

    def show(h, f):
        r, resp = _post(get, url, h, "", f, resp=True)
        if r is None:
            why.append(f"no answer {f}")
            return h
        got = indirect_records(r, resp, p, f)
        if not got:
            why.append(f"no rows {f}")
        recs.extend(got)
        return r

    dists = [d for d in options(h, "ddlDistrict") if not p.get("districts") or d[0] in p["districts"]]
    if not dists:
        show(h, f)
    for dv, _ in dists:
        fd = {**f, "ddlDistrict": dv}
        hd = _post(get, url, h, "ddlDistrict", fd)
        if not hd:
            why.append(f"district {dv}: no answer")
            continue
        blocks = options(hd, "ddlBlock")
        if not blocks:
            show(hd, fd)
        for bv, _ in blocks:
            show(hd, {**fd, "ddlBlock": bv})
    ids = {}
    for rid, d in recs:            # the same winner shown twice (a page that ignores the block) is kept once
        ids.setdefault(rid, d)
    recs = list(ids.items())
    return recs, [], "" if recs else ("; ".join(why[:5]) or "no winners")


def fetch(p, get):
    return fetch_indirect(p, get) if p.get("mode") == "indirect" else fetch_result(p, get)
