"""Offline tests of the Uttarakhand and Himachal Pradesh PRI elected-member readers (dforms/pri_uk.py, pri_hp.py) on saved pages
in tests/data/pri/ (result pages trimmed to a few rows; view state cut)."""
import json

from pri_common import DATA, ROOT, check_pri, fake_get, mod  # noqa: F401

UK = "https://secresult.uk.gov.in/"


def test_pri_uk_seeds():
    m = mod("pri_uk")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_uk.json").read_text())
    assert seeds == m.items() and len(seeds) == 12 and "050" not in {s["payload"]["district_code"] for s in seeds}
    assert m.METHOD


def test_pri_uk_district_flow():
    m = mod("pri_uk")
    p = m.items()[0]["payload"]
    assert p["district_code"] == "045"

    def search(page, block=None):
        return lambda u, meth, d: (meth == "POST" and u == UK + page and isinstance(d, dict)
                                   and (block is None or d.get("ctl00$ContentPlaceHolder1$hdnBlockCode") == block))
    get = fake_get({("GET", UK + "WinnerListZP.aspx"): "pri/uk_zp_get.html",
                    search("WinnerListZP.aspx"): "pri/uk_zp_045.html",
                    ("POST", UK + "WinnerListCP.aspx/GetBlocksByDistrict"): "pri/uk_blocks_045.json",
                    ("GET", UK + "WinnerListGP.aspx"): "pri/uk_gp_get.html",
                    ("GET", UK + "WinnerListCP.aspx"): "pri/uk_cp_get.html",
                    search("WinnerListGP.aspx", "357"): "pri/uk_gp_045_357.html",
                    search("WinnerListCP.aspx", "357"): "pri/uk_cp_045_357.html",
                    search("WinnerListGP.aspx"): "pri/uk_norecord.html",
                    search("WinnerListCP.aspx"): "pri/uk_norecord.html"})
    recs, files, why = m.fetch(p, get)
    assert why == ""
    check_pri(recs, "pri_uk", "UK")
    lv = [d["level"] for _, d in recs]
    assert (lv.count("zp"), lv.count("gp"), lv.count("ps")) == (45, 31, 40)
    assert len(get.calls) == 2 + 1 + 2 + 2 * 11            # ZP get + search, block list, 2 page gets, 11 blocks x 2
    zp_search = get.calls[1][2]
    assert zp_search["ctl00$ContentPlaceHolder1$ddlDistrict"] == "045" and "__VIEWSTATE" in zp_search
    d = dict(recs)
    g = d["pri:pri_uk:045:gp:357:21182"]
    assert g["name"] == "देवेन्द्र सिंह" and g["lgd_code"] == "21182" and g["lgd_match"] == "source" and g["role"] == "head"
    assert g["body_name"] == "उसकोना" and g["votes"] == 106 and g["status"] == "won (contested)" and g["block"] == "हवालबाग"
    assert g["src_pos"] == {"table": 1, "row": 2} and g["src_sha256"] and g["cells"]["WardCode"] == "21182"
    u = d["pri:pri_uk:045:gp:357:21114"]
    assert u["status"] == "elected unopposed" and "votes" not in u
    z = d["pri:pri_uk:045:zp:-:1114"]
    assert z["lgd_code"] == "45" and z["ward"] == "1 - सुनौली" and z["ward_no"] == "1" and z["category"] == "अनुसूचित जाति (एससी) महिला"
    k = d["pri:pri_uk:045:ps:357:1677"]
    assert k["level"] == "ps" and k["sec_block_code"] == "357" and k["body_name"] == "हवालबाग" and "lgd_code" not in k


HP = "https://sechimachal.hp.gov.in/dpmis/repList.aspx"


def _hp_get(result):
    """Postbacks answer the saved form page; btnShow answers the saved list."""
    return fake_get({lambda u, meth, d: meth == "POST" and "ctl00$ContentPlaceHolder1$btnShow" in (d or {}): result,
                     ("GET", HP): "pri/hp_rep_get.html", ("POST", HP): "pri/hp_rep_zmode.html"})


def _hp(post):
    m = mod("pri_hp")
    return m, next(i["payload"] for i in m.items() if i["key"] == f"pri_hp:1312:{post}")


def test_pri_hp_seeds():
    m = mod("pri_hp")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_hp.json").read_text())
    assert seeds == m.items() and len(seeds) == 60 and len({s["key"] for s in seeds}) == 60


def test_pri_hp_pradhan_flow():
    m, p = _hp("P")
    get = _hp_get("pri/hp_una_p.html")
    recs, _, why = m.fetch(p, get)
    assert why == ""
    check_pri(recs, "pri_hp", "HP")
    assert len(recs) == 11 and [c[0] for c in get.calls] == ["GET", "POST", "POST", "POST"]      # term, district, show
    show = get.calls[-1][2]
    assert show["ctl00$ContentPlaceHolder1$ddlDis"] == "1312" and show["__EVENTTARGET"] == ""
    assert get.calls[1][2]["ctl00$ContentPlaceHolder1$ddlPriTerm"] == "2026-2031"
    d = dict(recs)
    r = d["pri:pri_hp:1312:P:अम्ब~अम्ब_टिल्ला"]
    assert r["name"] == "हंस राज" and r["phone"] == "9459007892" and r["gender"] == "male" and r["age"] == 75
    assert r["level"] == "gp" and r["role"] == "head" and r["body_name"] == "अम्ब टिल्ला" and r["block"] == "अम्ब"
    assert r["term_start"] == "28-05-2026" and r["src_pos"] == {"table": 3, "row": 2} and r["cells"]["मोबाइल नं."] == "9459007892"


def test_pri_hp_zp_flow_leaves_out_empty_select():
    m, p = _hp("Z")
    get = _hp_get("pri/hp_una_z.html")
    recs, _, why = m.fetch(p, get)
    check_pri(recs, "pri_hp", "HP")
    assert len(get.calls) == 4                               # GET, term, post (no district postback for Z), show
    assert get.calls[2][2]["__EVENTTARGET"] == "ctl00$ContentPlaceHolder1$rbPost$4"
    assert "ctl00$ContentPlaceHolder1$ddlConsWard" not in get.calls[-1][2]
    r = recs[0][1]
    assert r["level"] == "zp" and r["ward"] == "1 - मुबारिकपुर" and r["ward_no"] == "1" and r["phone"] == "7018517538"


def test_pri_hp_ward_members_and_ps():
    m, p = _hp("W")
    recs = m.records((DATA / "pri/hp_una_w.html").read_text(), HP, p)
    check_pri(recs, "pri_hp", "HP")
    r = recs[0][1]
    assert r["role"] == "member" and r["body_name"] == "अम्ब टिल्ला" and r["ward"] == "1 - वार्ड न0-1" and r["phone"] == "7018409572"
    m, p = _hp("S")
    recs = m.records((DATA / "pri/hp_una_s.html").read_text(), HP, p)
    check_pri(recs, "pri_hp", "HP")
    assert recs[0][1]["level"] == "ps" and recs[0][1]["body_name"] == "अम्ब" and recs[0][1]["ward_no"] == "1"
