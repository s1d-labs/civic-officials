"""Offline tests of the gram panchayat secretary readers (dforms/gp_*.py) on saved pages in tests/data/gp/."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod  # noqa: F401


def _gj(label):
    m = mod("gp_gj_tcm")
    return m, next(i["payload"] for i in m.items() if i["key"] == f"gp_gj_tcm:{label}")


def _common(recs):
    check_records(recs, "gp_gj_tcm", "rural_development")
    for rid, d in recs:
        assert d["level"] == "gram_panchayat" and d["state"] == "GJ" and d.get("district") and d.get("area"), d
        assert d["src_pos"]["table"] >= 1 and d["src_pos"]["row"] >= 2 and d["src_url"] == d["source"], d
        assert d.get("cells"), d


def test_gp_gj_tcm_seeds():
    m = mod("gp_gj_tcm")
    seeds = json.loads((ROOT / "seeds" / "dept_gp_gj_tcm.json").read_text())
    assert seeds == m.items() and len(seeds) == 33 and len({s["key"] for s in seeds}) == 33
    assert {s["payload"]["district"] for s in seeds} >= {"Kheda", "Dangs", "Banas Kantha", "Panch Mahals", "Kachchh"}
    assert m.METHOD


def test_gp_gj_tcm_district_flow_tapi():
    m, p = _gj("tapidp")
    get = fake_get({p["url"]: "gp/gj_tapi_home.html",
                    "https://tapidp.gujarat.gov.in/gu/taluka/Vyara/home": "gp/gj_tapi_vyara_home.html",
                    "https://tapidp.gujarat.gov.in/gu/taluka/Vyara/tcm-list": "gp/gj_tapi_vyara_tcm.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 30
    _common(recs)
    urls = [u for _, u, _ in get.calls]
    assert len(urls) == 10 and urls.count("https://tapidp.gujarat.gov.in/gu/Tcm-List") == 1   # 7 taluka homes + 2 lists
    d = dict(recs)
    r = d["dept:gp_gj_tcm:tapi:vyara:1-2"]
    assert r["name"] == "ચૌધરી હર્ષાબેન એન." and r["phone"] == "6352348836" and r["sejo"] == "કરંજવેલ"
    assert r["villages"] == "કરંજવેલ, કાટકુઈ, કપડવણ" and r["taluka"] == "Vyara" and r["district"] == "Tapi"
    assert r["post"] == "Talati-cum-Mantri (Panchayat Secretary)" and "extra_charge" not in r      # "-" = none
    assert r["cells"]["સોમવાર"] == "કરંજવેલ"                                                     # visiting days kept
    assert files and files[0][0] == "depts/gp_gj_tcm/tapi/gu-taluka-vyara-tcm-list.html.gz"


def test_gp_gj_tcm_sarpanch_and_tcm_in_one_table():
    m, p = _gj("botaddp")
    url = "https://botaddp.gujarat.gov.in/gu/taluka/Botad/Botad-Elected-Sarpanch-TCM-Details"
    recs = m.records((DATA / "gp/gj_botad_sarpanch_tcm.html").read_text(), url, p, "Botad")
    _common(recs)
    assert len(recs) == 51
    r = dict(recs)["dept:gp_gj_tcm:botad:botad:1-2"]
    assert r["name"] == "શ્રી એ.એન.ચૌહાણ" and r["phone"] == "9904457087" and r["area"] == "ઢાંકણીયા"
    assert r["sarpanch_name"] == "જોગરાણા જાનાબેન નગાભાઇ" and r["sarpanch_phone"] == "9824450598"
    assert r["src_pos"] == {"table": 1, "row": 2}


def test_gp_gj_tcm_employee_list_with_designation():
    m, p = _gj("mahisagardp")
    url = "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/TCM-Details"
    recs = m.records((DATA / "gp/gj_mahisagar_balasinor_tcm.html").read_text(), url, p, "Balasinor")
    _common(recs)
    r = dict(recs)["dept:gp_gj_tcm:mahisagar:balasinor:1-3"]
    assert r["name"] == "શ્રીમતિ.પી.જે.અમીન" and r["phone"] == "9978415701" and r["designation"] == "ત.ક મંત્રી"


def test_gp_gj_tcm_ditto_taluka():
    m, p = _gj("ahmedabaddp")
    url = "https://ahmedabaddp.gujarat.gov.in/gu/taluka/Sanand/Talati-cum-Ministers-Info"
    recs = m.records((DATA / "gp/gj_ahmedabad_sanand_tcm.html").read_text(), url, p, "Sanand")
    _common(recs)
    d = dict(recs)
    r = d["dept:gp_gj_tcm:ahmedabad:sanand:1-3"]
    assert r["taluka_regional"] == "સાણંદ" and r["area"] == "હિરાપુર" and r["phone"] == "9724788595"     # " = the cell above
    assert all(x.get("name") for _, x in recs)


# ---- Karnataka: Zilla Panchayat gram panchayat pages ----
def _ka(label):
    m = mod("gp_ka_zp")
    return m, next(i["payload"] for i in m.items() if i["key"] == f"gp_ka_zp:{label}")


def test_gp_ka_zp_seeds():
    m = mod("gp_ka_zp")
    seeds = json.loads((ROOT / "seeds" / "dept_gp_ka_zp.json").read_text())
    assert seeds == m.items() and len(seeds) == 28 and all(s["payload"]["state"] == "KA" for s in seeds)
    assert m.METHOD


def test_gp_ka_zp_tumakuru_table():
    m, p = _ka("zptumakuru")
    gp = "https://zptumakuru.karnataka.gov.in/46/gram-panchayat/en"
    assert p["pages"] == [gp]
    get = fake_get({p["url"]: "gp/ka_tumakuru_home.html", gp: "gp/ka_tumakuru_gp.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 327 and len(get.calls) == 2       # the menu link is the known page: read once
    check_records(recs, "gp_ka_zp", "rural_development")
    d = dict(recs)
    r = d["dept:gp_ka_zp:tumakuru:46:3-2"]
    assert r["area"] == "BARAKANALU" and r["block"] == "Chikkanayakanahalli" and r["phone"] == "9480877201"
    assert r["post"] == "Panchayat Development Officer (PDO)" and r["designation"] == "PDO/Secretary"
    assert r["src_pos"] == {"table": 3, "row": 2} and r["src_url"] == gp and r["level"] == "gram_panchayat"
    assert d["dept:gp_ka_zp:tumakuru:46:3-330"]["area"] == "VADAVANAGHATTA"


def test_gp_ka_zp_names_only_page_gives_nothing():
    m, p = _ka("zpkalaburagi")
    recs, files, why = m.fetch(p, fake_get({p["pages"][0]: "gp/ka_kalaburagi_gps.html"}))
    assert recs == [] and why == "no PDO table"
