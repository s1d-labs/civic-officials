"""Madhya Pradesh: elected panchayat representatives (2022 panchayat general election and later bye-elections, as the department
keeps them) from MP Panchayat Darpan (mppanchayatdarpan.gov.in, Panchayat & Rural Development Department, NIC). Open pages,
no login, no captcha (measured 2026-11-13 from Mumbai). The MP State Election Commission host did not resolve from Mumbai.

Flow (ASP.NET WebForms, one session):
1. GET /panchayat/Search.aspx?TypeID=<type> (zila: no TypeID; janpad: Qri3376EFpjxJdBBauGZLg==; gram: +zEfuxGGQVK2FrsclPfLMg==)
   -> hidden fields (view state).
2. POST the same page with the district / janpad / gram panchayat ids (the selects are filled by script from
   /Handlers/localbodies_En.ashx?DistrictID=..&LBTypeID=6 and /Handlers/GpZones_En.ashx?LbId=..; event validation is off) and
   __EVENTTARGET=ctl00$ContentPlaceHolder1$btnView -> redirect to /Panchayat/Default.aspx?QS=..&ID=.. (the body's home page),
   whose hidden fields HdnOffietype (ZP / JP / GP), HdnID and HdnOffieID (office id) name the body.
3. GET /Panchayat/Handlers/Get_Representatives_Details_By_OfficeID.ashx?OID=<office>&QS=<type>&ID=<id> -> HTML cards:
   name (h3.card-title) + post (p.card-text): ZP "अध्यक्ष, जिला पंचायत" / "उपाध्यक्ष, जिला पंचायत" / "सदस्य, जिला पंचायत";
   JP "अध्यक्ष, जनपद पंचायत" / "उपाध्यक्ष ..." / "सदस्य ..."; GP "सरपंच" / "उप सरपंच" / "पंच". No phone numbers.
   Each card links a profile page (Representatives_Profile.aspx: name, post, ward); not fetched (one request per person).
Items: kind "district" (52): the zila panchayat and every janpad panchayat of the district (1 + 2 x (1 + janpads) requests);
kind "janpad" (313): every gram panchayat of one janpad (2 + 2 x GPs requests: about 150 on average, up to about 500).
Janpad ids and their LGD codes: dforms/pri_mp_lgd.json (made offline 2026-11-13 from the handler lists: LGD local name equal,
else sound match within the zila; 306 of 313 janpads, 52 of 52 zilas). GP LGD codes: the loader matches body_name (Hindi) to
lgd.pri_local_bodies.local_body_name_local within the janpad (16,718 of 23,011 MP GPs have a Hindi LGD name).
Record ids pri:pri_mp:<type>:<body id>:<card no> (body id = Darpan district id for ZP, janpad id for JP, GP zone id for GP).
"""
import json
import re
from html import unescape
from pathlib import Path

from dforms import _pri
import provenance

METHOD = "html cards (Panchayat Darpan representatives handler, card index)"
MODULE = "pri_mp"
BASE = "https://mppanchayatdarpan.gov.in"
TYPE = {"zp": "", "ps": "Qri3376EFpjxJdBBauGZLg%3d%3d", "gp": "%2bzEfuxGGQVK2FrsclPfLMg%3d%3d"}
LGD = json.loads(Path(__file__).with_name("pri_mp_lgd.json").read_text())
ELECTION = "Madhya Pradesh Panchayat General Election 2022 (Panchayat Darpan list)"
CARD = re.compile(r"<h3 class='card-title'[^>]*>(.*?)</h3>.*?<p class='card-text'>(.*?)</p>.*?href='([^']*)'", re.S)
HIDDEN = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
POSTS = [  # (pattern on the Hindi post, level, role, English post)
    (r"^अध्यक्ष.*जिला", "zp", "head", "Adhyaksh (Chairperson), Zila Panchayat"),
    (r"^उपाध्यक्ष.*जिला", "zp", "deputy", "Upadhyaksh (Vice-Chairperson), Zila Panchayat"),
    (r"सदस्य.*जिला", "zp", "member", "Member, Zila Panchayat"),
    (r"^अध्यक्ष.*जनपद", "ps", "head", "Adhyaksh (Chairperson), Janpad Panchayat"),
    (r"^उपाध्यक्ष.*जनपद", "ps", "deputy", "Upadhyaksh (Vice-Chairperson), Janpad Panchayat"),
    (r"सदस्य.*जनपद", "ps", "member", "Member, Janpad Panchayat"),
    (r"^सरपंच", "gp", "head", "Sarpanch"),
    (r"^उप\s*सरपंच", "gp", "deputy", "Up-Sarpanch"),
    (r"^पंच", "gp", "member", "Panch (Ward Member)"),
]


def items(get=None):
    out = []
    for did in sorted(LGD, key=int):
        d = LGD[did]
        out.append({"key": f"{MODULE}:district:{did}", "payload": {"reader": MODULE, "kind": "district", "url": BASE + "/panchayat/Search.aspx",
                    "district_id": int(did), "district": d["district"], "state": "MP", "route": "proxy", "india_only": True}})
        for jid in sorted(d["janpads"], key=int):
            out.append({"key": f"{MODULE}:janpad:{jid}", "payload": {"reader": MODULE, "kind": "janpad", "url": BASE + "/panchayat/Search.aspx",
                        "district_id": int(did), "district": d["district"], "janpad_id": int(jid),
                        "janpad": d["janpads"][jid]["name"], "state": "MP", "route": "proxy", "india_only": True}})
    return out


def text(s):
    return _pri.clean(unescape(re.sub(r"<[^>]+>", " ", s or "")))


def post_of(hindi):
    for rx, level, role, en in POSTS:
        if re.search(rx, hindi):
            return level, role, en
    return None


def cards(html):
    """[(card no, name, post in Hindi, profile url)] from the representatives handler."""
    return [(i, text(n), text(p), BASE + unescape(h) if h.startswith("/") else unescape(h))
            for i, (n, p, h) in enumerate(CARD.findall(html or ""), 1)]


def search_page(get, typ):
    url = BASE + "/panchayat/Search.aspx" + (f"?TypeID={TYPE[typ]}" if TYPE[typ] else "")
    r = get(url)
    return (url, dict(HIDDEN.findall(r.text))) if r is not None else (url, None)


def open_body(get, url, hidden, district, lb=0, gp=0):
    """POST View Details -> (home page url, type, id, office id) of the body, or None."""
    f = {k: v for k, v in hidden.items()}
    f.update({"__EVENTTARGET": "ctl00$ContentPlaceHolder1$btnView", "__EVENTARGUMENT": "",
              "ctl00$ContentPlaceHolder1$ddlDistrict_DD": str(district), "ctl00$ContentPlaceHolder1$hdnDistrict": str(district)})
    if lb:
        f.update({"ctl00$ContentPlaceHolder1$ddl_Localbody_JP": str(lb), "ctl00$ContentPlaceHolder1$hdnLBID": str(lb)})
    if gp:
        f.update({"ctl00$ContentPlaceHolder1$ddlgz": str(gp), "ctl00$ContentPlaceHolder1$hdnGp": str(gp)})
    r = get(url, method="POST", data=f)
    if r is None:
        return None
    h = dict(re.findall(r'name="ctl00\$ContentPlaceHolder1\$(HdnOffietype|HdnID|HdnOffieID)"[^>]*value="([^"]*)"', r.text))
    if not h.get("HdnOffieID") or h["HdnOffieID"] == "0":
        return None
    return r.url, h.get("HdnOffietype"), h.get("HdnID"), h["HdnOffieID"]


def body_records(get, body, ctx):
    """Records of one body from its representatives handler. body = (home url, type, id, office id)."""
    home, typ, bid, oid = body
    url = f"{BASE}/Panchayat/Handlers/Get_Representatives_Details_By_OfficeID.ashx?OID={oid}&QS={typ}&ID={bid}"
    r = get(url)
    if r is None:
        return None
    return records(r.text, url, home, typ, bid, oid, ctx)


def records(html, url, home, typ, bid, oid, ctx):
    out = []
    for no, name, post_hi, prof in cards(html):
        p = post_of(post_hi)
        if not p or not name:
            provenance.skipped('skip: not p or not name')
            continue
        level, role, post = p
        out.append(_pri.record(
            MODULE, f"{typ.lower()}:{bid}:{no}", state="MP", level=level, role=role, post=post, post_regional=post_hi, name=name,
            body_name=ctx.get("body_name"), district=ctx.get("district"), block=ctx.get("block"),
            lgd_code=ctx.get("lgd_code"), lgd_match="name" if ctx.get("lgd_code") else "", district_lgd=ctx.get("district_lgd"),
            block_lgd=ctx.get("block_lgd"), darpan_type=typ, darpan_id=bid, darpan_office_id=oid, profile_url=prof,
            election=ELECTION, election_year=2022, source=url, src_url=url, body_page=home, src_pos={"card": no}))
    return out


def fetch(p, get):
    did = p["district_id"]
    d = LGD.get(str(did), {})
    recs, why = [], []
    if p["kind"] == "district":
        url, hid = search_page(get, "zp")
        if hid is None:
            return [], [], "no search page"
        b = open_body(get, url, hid, did)
        if b:
            got = body_records(get, b, {"body_name": d.get("district"), "district": d.get("district"), "lgd_code": d.get("zp_lgd"),
                                        "district_lgd": d.get("zp_lgd")})
            recs += got or []
            if not got:
                why.append("zp: no cards")
        else:
            why.append("zp: no body page")
        url, hid = search_page(get, "ps")
        if hid is None:
            return recs, [], "no janpad search page"
        for jid, j in sorted(d.get("janpads", {}).items(), key=lambda kv: int(kv[0])):
            b = open_body(get, url, hid, did, lb=int(jid))
            got = body_records(get, b, {"body_name": j["name"], "district": d.get("district"), "block": j["name"],
                                        "lgd_code": j.get("lgd"), "district_lgd": d.get("zp_lgd"), "block_lgd": j.get("lgd")}) if b else None
            recs += got or []
            if not got:
                why.append(f"jp {jid}: no cards")
    else:
        jid = p["janpad_id"]
        j = d.get("janpads", {}).get(str(jid), {})
        r = get(f"{BASE}/Handlers/GpZones_En.ashx?LbId={jid}")
        try:
            gps = [(int(a), _pri.clean(b)) for a, b in r.json()["rows"]] if r is not None else []
        except (ValueError, KeyError, TypeError):
            gps = []
        if not gps:
            return [], [], "no gram panchayat list"
        url, hid = search_page(get, "gp")
        if hid is None:
            return [], [], "no search page"
        for gid, gname in gps:
            b = open_body(get, url, hid, did, lb=jid, gp=gid)
            got = body_records(get, b, {"body_name": gname, "district": d.get("district"), "block": p.get("janpad"),
                                        "district_lgd": d.get("zp_lgd"), "block_lgd": j.get("lgd")}) if b else None
            recs += got or []
            if not got:
                why.append(f"gp {gid}: no cards")
    reason = "" if recs else ("; ".join(why)[:200] or "no records")
    return recs, [], reason
