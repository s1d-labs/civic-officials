"""Offline tests of the gap-round councillor readers (cforms/cr_*.py) on small saved samples in tests/data/cr_*."""
import json
from pathlib import Path

from cforms import cr_body, cr_pb, cr_up
from cforms.cr_common import digits, key, latin, table_members

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


def read(name):
    return (DATA / name).read_text(encoding="utf-8")


# ---- helpers

def test_latin_and_keys():
    assert latin("कासगंज") == "kasaganja" and key(latin("कासगंज")) == key("Kasganj")
    assert key(latin("खैराबाद")) == key("Khairabad")
    assert key("Amanpur") != key("Mohanpur")
    assert digits("૯૫૮૬૧૫૧૬૧૩") == "9586151613" and digits("१२") == "12"


# ---- Uttar Pradesh: SEC 2023 winner list (Wayback copy of 13 May 2023, cut to 5 rows of Agra)

def test_up_sec_rows():
    rows = cr_up.winners(read("cr_up_sec_winners.html"))
    assert len(rows) == 5
    recs = dict(cr_up.records(rows, "8"))
    r = recs["councillor:UP:249062:7"]                 # 249062 = Agra Municipal Corporation in LGD
    assert r["name"] == "विमलेश कुमारी" and r["ward_name"] == "जगदीशपुरा पूर्वी" and r["phone"] == "9557658437"
    assert r["party"] == "Bahujan Samaj Party" and r["district_en"] == "Agra" and r["votes"] == "2782"
    assert recs["councillor:UP:249062:94"]["unopposed"] is True


def test_up_lgd_tie():
    assert cr_up.lgd_code("खैराबाद", "सीतापुर", "Municipal Council") == ("249188", "Sitapur")
    assert cr_up.lgd_code("अमांपुर", "कासगंज", "Nagar Panchayat")[0] == "249088"      # Amanpur, not Mohanpur
    assert cr_up.lgd_code("मोहनपुर", "कासगंज", "Nagar Panchayat")[0] == "249089"
    assert cr_up.district_en("लखीमपुर खीरी") == "Kheri"


def test_up_lgd_gap_bodies():
    """The 23 SEC bodies without an LGD code in civic.councillor on 2026-11-14 (495 members): 22 now tie, Chaumukha (Gorakhpur)
    is not in LGD and stays open."""
    cases = {("झांसी", "झांसी", "Municipal Corporation"): "249314",           # not Jhansi Railway Settlement
             ("वृन्दावन-मथुरा", "मथुरा", "Municipal Corporation"): "249052",
             ("हापुड", "हापुड़", "Municipal Council"): "248991", ("नकुड", "सहारनपुर", "Municipal Council"): "248876",
             ("बडौत", "बागपत", "Municipal Council"): "248972", ("विसंवा", "सीतापुर", "Municipal Council"): "249193",
             ("गौरा बरहज", "देवरिया", "Municipal Council"): "249462",
             ("बक्शी का तालाब", "लखनऊ", "Nagar Panchayat"): "263351", ("बढ़नीचाफा", "सिद्धार्थनगर", "Nagar Panchayat"): "297056",
             ("जलालाबाद", "शामली", "Nagar Panchayat"): "248907", ("फतेहगंज पश्चिमी", "बरेली", "Nagar Panchayat"): "249142",
             ("फतेहगंज पूर्वी", "बरेली", "Nagar Panchayat"): "249155", ("बढापुर", "बिजनौर", "Nagar Panchayat"): "248916",
             ("दारा नगर कड़ाधाम", "कौशाम्बी", "Nagar Panchayat"): "297064", ("करहल", "मैनपुरी", "Nagar Panchayat"): "249107",
             ("कुरावली", "मैनपुरी", "Nagar Panchayat"): "249103", ("कोहंडौर", "प्रतापगढ़", "Nagar Panchayat"): "297042",
             ("कटरा मेदनीगंज", "प्रतापगढ़", "Nagar Panchayat"): "249355", ("हैदरगढ", "बाराबंकी", "Nagar Panchayat"): "249387",
             ("कौडियागंज", "अलीगढ़", "Nagar Panchayat"): "249027", ("बाबूगढ", "हापुड़", "Nagar Panchayat"): "248992",
             ("निवाडी", "गाजियाबाद", "Nagar Panchayat"): "248978", ("चौमुखा", "गोरखपुर", "Nagar Panchayat"): None}
    got = {c: cr_up.lgd_code(*c)[0] for c in cases}
    assert got == cases
    assert sum(v is not None for v in got.values()) == 22
    assert cr_up.nukta("हापुड बढ़नी") == "हापुड़ बढ़नी"


def test_up_items():
    items = json.loads((SEEDS / "councillors_cr_up.json").read_text())
    assert len(items) == 228 and len({i["key"] for i in items}) == 228
    assert all(i["key"].startswith("cr-") for i in items)
    assert {i["payload"]["post"] for i in items} == {"7", "8", "9", "10", "11", "12"}


def test_up_sec_paging():
    """Live answers of 2026-11-12 (view state cut): Lucknow corporators, post 8, district 47, 100 + 10 rows on two pages."""
    import gzip
    pages = {k: gzip.decompress((DATA / f"cr_up_sec_{k}.html.gz").read_bytes()).decode() for k in ("lko_p1", "lko_p2", "bothset")}
    assert cr_up.selected(pages["bothset"]) == ("12", "0")      # both lists in one postback: post for the whole state
    calls = []

    class R:
        def __init__(self, t):
            self.text = t

    def get(url, method="GET", data=None, headers=None):
        calls.append((data or {}).get("__EVENTTARGET", "$GET").split("$")[-1] + (data or {}).get("__EVENTARGUMENT", ""))
        return R(pages["lko_p2"] if data and data["__EVENTARGUMENT"] == "Page$Next" else pages["lko_p1"])

    recs, files, why = cr_up.fetch({"post": "8", "district_id": "47"}, get)
    assert why == "" and len(recs) == 110 and len(files) == 2
    assert calls == ["GET", "DropDownList1", "ddlDistrict", "winnerdetailPage$Next"]
    r = dict(recs)
    assert {d["lgd_code"] for d in r.values()} == {"249234"} and {d["ward_no"] for d in r.values()} == {str(i) for i in range(1, 111)}
    assert cr_up.fetch({"post": "8", "district_id": "5"}, get)[2].startswith("page shows post/district")


# ---- Punjab: e-Nigam Digital MC-House

def test_pb_cards():
    cs = cr_pb.cards(read("cr_pb_talwara_home.html"))
    assert len(cs) == 13
    assert cs[0]["code"] == 2884 and cs[0]["ward_no"] == "1" and cs[0]["name"] == "Sh. Rajneesh Kumar"
    assert cs[4]["position"] == "President" and cs[6]["position"] == "Vice President" and cs[6]["ward_no"] == "7"
    assert cs[0]["url"].endswith("CouncillorsDetail?mcid=1094&MemberCode=2884")


def test_pb_cards_ward_number():
    # Alawalpur (mcid 1041) writes "Councillor Ward Number-1", "President Ward Number-5" (fixture: the cards of its home page, 2026-11-12)
    cs = cr_pb.cards(read("cr_pb_alawalpur_home.html"))
    assert [c["ward_no"] for c in cs] == [str(i) for i in range(1, 12)]
    assert cs[4]["position"] == "President" and cs[4]["name"] == "Smt. Neelam Rani" and cs[0]["code"] == 2785
    assert cr_pb.post_ward("Councillor  Ward Number-11") == (None, "11")


def test_pb_detail():
    d = cr_pb.detail(read("cr_pb_patiala_687.html"))
    assert d["name"] == "Sh. Harvinder Shukla" and d["ward_no"] == "2" and d["phone"] == "9814357168"
    assert d["email"] == "harvindershukla@yahoo.com" and d["address"].startswith("# 95 Prem Nagar")


def test_pb_seed():
    items = json.loads((SEEDS / "councillors_cr_pb.json").read_text())
    bodies = {i["payload"]["body"]: i["payload"]["mcid"] for i in items}
    assert bodies["Ludhiana"] == 1010 and bodies["Patiala"] == 1002 and bodies["Phagwara"] == 1009 and bodies["Talwara"] == 1094
    assert all(i["key"].startswith("cr-") and i["payload"]["lgd_code"] for i in items)


# ---- body sites (header-mapped member tables)

def test_body_tables():
    m = table_members(read("cr_body_up_fatehpur.html"))
    assert m[0]["ward_no"] == "1" and m[0]["name"] == "श्री विवेक सिंह" and m[0]["ward_name"] == "अजगंवा" and m[0]["phone"] == "8318835039"
    f = table_members(read("cr_body_up_firozabad.html"))
    assert f[1]["ward_no"] == "2" and f[1]["ward_name"] == "विजय नगर" and f[1]["phone"] == "9897459954"
    k = table_members(read("cr_body_up_khairabad.html"))           # ward column holds ward names
    assert "ward_no" not in k[0] and k[0]["ward_name"] == "माखूपुर" and k[0]["phone"] == "8299726665"


def test_body_records_gujarati():
    p = {"state": "GJ", "slug": "chanasma", "body": "Chanasma", "lgd_code": "251062", "url": "https://chanasmanagarpalika.org/Members_List.html"}
    recs = dict(cr_body.records(read("cr_body_gj_chanasma.html"), p))
    r = recs["councillor:GJ:chanasma:6"]
    assert r["name"] == "પ્રતીક્ષાબેન મિતકુમાર પટેલ" and r["position"] == "President" and r["party"] == "ભાજપ"
    assert r["phone"] == "9586151613" and r["lgd_code"] == "251062"
    assert recs["councillor:GJ:chanasma:4"]["phone"] == "6352223762, 9998699994"


def test_body_name_with_post():
    p = {"state": "WB", "slug": "budge-budge", "body": "Budge Budge", "lgd_code": "250301", "note": "x",
         "url": "https://budgebudgemunicipality.org/board of councillors.php"}
    recs = dict(cr_body.records(read("cr_body_wb_budgebudge.html"), p))
    r = recs["councillor:WB:budge-budge:9"]
    assert r["name"] == "Sri Gautam Dasgupta" and r["position"] == "Chairman" and r["phone"] == "9830220417, 8017784024"
    assert recs["councillor:WB:budge-budge:6"]["position"] == "Vice Chairman"
    assert "position" not in recs["councillor:WB:budge-budge:1"] and r["note"] == "x"
    seeds = json.loads((SEEDS / "councillors_cr_body.json").read_text())
    assert len(seeds) == 7 and all(i["key"].startswith("cr-body-") for i in seeds)


def test_pb_heads_keep_the_member_list_mohali():
    """Mohali (mcid 1001, a 2026 body: heads_only), the vice president's detail page (full saved page). Its #tblDataList lists
    all 50 members with name, ward, address and mobile; LBPAMS (cforms/pb.py) has no mobiles, and before 2026-11-13 the reader
    kept only the head. Now: 1 head + 50 member-list records councillor:PB:mohali:site:<ward>."""
    import gzip

    class R:
        def __init__(self, t):
            self.text = t
    page = gzip.decompress((DATA / "cr_pb_mohali_vice_detail_full.html.gz").read_bytes()).decode("utf-8")
    ml = cr_pb.member_list(page)
    assert len(ml) == 50 and all(m["name"] and m["phone"] for m in ml)
    assert [m["ward_no"] for m in ml] == [str(i) for i in range(1, 51)]
    assert ml[0] == {"name": "Charanjit Kaur", "ward_no": "1", "address": "#1813, Phase-5, SAS Nagar", "phone": "9815122132",
                     "email": None, "card_no": 1}
    url = "https://mcpatiala.punjab.gov.in/Councilors/CouncillorsDetail?mcid=1001&MemberCode=3486"
    cs = [{"code": 3486, "url": url, "name": "x", "position": "Vice President", "ward_no": "2", "card": "Vice President 2"}]
    recs, _, err = cr_pb.heads({"body": "Mohali", "slug": "mohali"}, lambda u: R(page) if u == url else None, "home", cs, [])
    ids = [rid for rid, _ in recs]
    assert err == "" and ids[0] == "councillor:PB:mohali:vice" and len(recs) == 51
    assert ids[1:] == [f"councillor:PB:mohali:site:{i}" for i in range(1, 51)]
    d = dict(recs)["councillor:PB:mohali:site:1"]
    assert d["phone"] == "9815122132" and d["source_kind"] == "e-Nigam member list" and d["src_pos"]["card"] == 1


def test_body_mp_town_sites():
    """Madhya Pradesh town sites (archive.s1d.me copies, 2026-11-11), full pages: the four table layouts of the gap round."""
    def recs(town):
        return cr_body.records(read(f"cr_body_mp_{town}.html"), {"state": "MP", "slug": town, "body": town, "url": "u"})
    wards = lambda rs: sorted(int(d["ward_no"]) for _, d in rs if d.get("ward_no"))     # noqa: E731
    j = recs("joura")                     # क्र | वार्ड | नाम | मोबाइल: 18 of 18 wards
    assert len(j) == 18 and wards(j) == list(range(1, 19))
    i = dict(recs("isagarh"))             # नाम | "पद / वार्ड": अध्यक्ष, उपाध्यक्ष, "पार्षद — वार्ड क्र. 01"
    assert len(i) == 15 and wards(i.items()) == [1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15]
    assert i["councillor:MP:isagarh:s1"]["position"] == "Chairperson" and "position" not in i["councillor:MP:isagarh:01"]
    m = dict(recs("mauganj"))             # "नाम / पद" (post in brackets) | वार्ड | मोबाइल: 15 of 15
    assert len(m) == 15 and wards(m.items()) == list(range(1, 16))
    assert m["councillor:MP:mauganj:1"]["name"] == "श्री बृजवासी पटेल" and m["councillor:MP:mauganj:1"]["position"] == "Chairperson"
    b = dict(recs("birsinghpur"))         # नाम | पद ("पार्षद वार्ड नं 02") | मोबाइल
    assert len(b) == 15 and wards(b.items()) == [2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    assert b["councillor:MP:birsinghpur:02"]["phone"] == "7509146975"
