"""Odisha PRI 2022 (dforms/pri_od.py) on saved files: the PR&DW lists (ZP president, PS chairman / vice, ZP members) and two
pages each of the SEC sarpanch and P.S member lists (page 190 of the sarpanch file has names printed half a row off)."""
from pri_common import DATA, check_pri, fake_get, mod

M = mod("pri_od")


def recs(name, lst):
    return M.records((DATA / "pri" / name).read_bytes(), lst, "u")


def test_items():
    it = M.items()
    assert len(it) == 7 and len({i["key"] for i in it}) == 7 and M.METHOD
    assert all(i["payload"]["route"] == "proxy" for i in it)


def test_zp_president():
    r = recs("od_zp_president.pdf", "zp_president")
    check_pri(r, "pri_od", "OD")
    d = dict(r)
    assert len(r) == 30 and "pri:pri_od:zp_president:angul" in d     # the ABSTRACT table under the list is left out
    a = d["pri:pri_od:zp_president:angul"]
    assert a["name"] == "Smt. Babita Pradhan" and a["party"] == "BJD" and a["gender"] == "female" and a["district_lgd"] == "Anugul"
    assert a["level"] == "zp" and a["role"] == "head" and a["src_pos"]["page"] == 1


def test_ps_chairman():
    r = recs("od_ps_chairman.pdf", "ps_chairman")
    check_pri(r, "pri_od", "OD")
    d = dict(r)
    assert 620 <= len(r) <= 628
    assert d["pri:pri_od:ps_chairman:angul:athmallik:head"]["name"] == "Dushasan Roul"
    assert d["pri:pri_od:ps_chairman:angul:athmallik:deputy"]["name"] == "Mamata Mahakud"
    assert d["pri:pri_od:ps_chairman:sambalpur:naktideul:head"]["name"] == "Swarupa Rani Sahu"   # samiti printed above its row
    assert len({x["block"] for _, x in r}) > 300


def test_zp_member():
    r = recs("od_zp_member.pdf", "zp_member")
    check_pri(r, "pri_od", "OD")
    d = dict(r)
    assert 850 <= len(r) <= 855 and len({x["district"] for _, x in r}) == 30
    a = d["pri:pri_od:zp_member:angul:1"]
    assert a["name"] == "Kajal Pattanayak" and a["block"] == "Angul" and a["party"] == "BJD" and a["ward_no"] == "1"
    assert d["pri:pri_od:zp_member:angul:10"]["name"] == "Rasmita Behera"          # "10 Kaniha" split at the column start
    assert d["pri:pri_od:zp_member:angul:10"]["constituency"] == "Kaniha"
    assert dict(r)[r[-1][0]]["district"] == "Sundargarh"


def test_sarpanch_pages():
    r = recs("od_sarpanch_p1_p190.pdf", "sarpanch")
    check_pri(r, "pri_od", "OD")
    by = {x["body_name"]: x for _, x in r}
    assert by["Angarabandha"]["name"] == "Sujata Sahu" and by["Angarabandha"]["block"] == "Angul"
    assert by["Angarabandha"]["district"] == "Angul" and by["Angarabandha"]["src_pos"]["page"] == 1
    assert by["Halwa"]["name"] == "Tamarao Bidika" and by["Kutuli"]["name"] == "Adibari Miniaka"
    assert by["M.K.Rai"]["name"] == "Teyargrasmi Sabar" and by["Kadama"]["name"] == "Rama Chandra Muturanga"
    assert by["Karlaghati"]["name"] == "Kousalya Mabalaka" and by["Siriguda"]["name"] == "Bhrati Srambutika"
    assert by["Kadama"]["block"] == "Gudari" and by["Kadama"]["level"] == "gp" and by["Kadama"]["role"] == "head"


def test_ps_member_pages():
    r = recs("od_ps_member_p1_p56.pdf", "ps_member")
    check_pri(r, "pri_od", "OD")
    d = dict(r)
    a = d["pri:pri_od:ps_member:deogarh:reamal:adas"]
    assert a["name"] == "Dali Behera" and a["constituency"] == "Adas" and a["body_name"] == "Reamal" and a["level"] == "ps"
    assert d["pri:pri_od:ps_member:angul:angul:angarabandha"]["name"] == "Sujata Swain"


def test_fetch_sec_list():
    pdf = (DATA / "pri/od_sarpanch_p1_p190.pdf")
    get = fake_get({M.SEC_TABLE: "pri/od_sec_table57.json",
                    M.SEC + "/uploads/cmsfiles/7f8c3efe-8fbc-4150-8b41-051771737319_SARPANCH.pdf": str(pdf.relative_to(DATA))})
    p = next(i["payload"] for i in M.items() if i["payload"]["list"] == "sarpanch")
    r, files, why = M.fetch(p, get)
    assert why == "" and len(r) > 60
    assert r[0][1]["src_url"].endswith("_SARPANCH.pdf") and r[0][1]["source"].endswith("/Landing/ElectedSarpanchPSMember")


def test_seed_file():
    import json
    from pri_common import ROOT
    assert json.loads((ROOT / "seeds/dept_pri_od.json").read_text()) == M.items()
