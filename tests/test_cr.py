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


def test_up_items():
    items = json.loads((SEEDS / "councillors_cr_up.json").read_text())
    assert len(items) == 228 and len({i["key"] for i in items}) == 228
    assert all(i["key"].startswith("cr-") for i in items)
    assert {i["payload"]["post"] for i in items} == {"7", "8", "9", "10", "11", "12"}


# ---- Punjab: e-Nigam Digital MC-House

def test_pb_cards():
    cs = cr_pb.cards(read("cr_pb_talwara_home.html"))
    assert len(cs) == 13
    assert cs[0]["code"] == 2884 and cs[0]["ward_no"] == "1" and cs[0]["name"] == "Sh. Rajneesh Kumar"
    assert cs[4]["position"] == "President" and cs[6]["position"] == "Vice President" and cs[6]["ward_no"] == "7"
    assert cs[0]["url"].endswith("CouncillorsDetail?mcid=1094&MemberCode=2884")


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
