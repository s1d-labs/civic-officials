"""Offline tests of the sub4 north readers (dforms/sub4_*.py) on saved answers in tests/data/sub4/.
J&K: RD&PR halqa directory (ajaxData.php selects + officersdirectory.php pages)."""
import json

from esw_common import *  # noqa: F401,F403


def test_sub4_jk_seeds():
    m = mod("sub4_jk_rdd")
    seeds = json.loads((ROOT / "seeds" / "dept_sub4_jk.json").read_text())
    assert seeds == m.items() and len(seeds) == 20 and len({s["key"] for s in seeds}) == 20
    assert all(s["payload"]["reader"] == "sub4_jk_rdd" and s["payload"]["state"] == "JK" for s in seeds)
    # the district select values of the saved answers are the seed districts
    for div, f in (("Kashmir", "jk_districts_kashmir.html"), ("Jammu", "jk_districts_jammu.html")):
        assert set(m.DIVISIONS[div]) <= set(m.options((DATA / "sub4" / f).read_text()))
    assert all(m.district_of(d)[0] for ds in m.DIVISIONS.values() for d in ds)


def test_sub4_jk_fetch_one_block():
    m = mod("sub4_jk_rdd")
    gps = m.options((DATA / "sub4" / "jk_gps_rafiabad.html").read_text())
    assert len(gps) == 16 and "Behrampora A" in gps and "Chanum" in gps
    routes = {lambda u, mt, d: mt == "POST" and d == {"district": "Baramulla"}: "sub4/jk_blocks_baramulla.html",
              lambda u, mt, d: mt == "POST" and d == {"block": "Rafiabad"}: "sub4/jk_gps_rafiabad.html",
              m.gp_url("Chanum", "Rafiabad"): "sub4/jk_gp_chanum.html",
              m.gp_url("Chatloora", "Rafiabad"): "sub4/jk_gp_chatloora.html"}
    p = {s["key"]: s["payload"] for s in m.items()}["sub4_jk_rdd-baramulla"]
    recs, files, why = m.fetch(p, fake_get(routes))
    assert why == "" and files == []
    by = dict(recs)
    assert len(recs) == 23 and len(by) == 23
    d = by["dept:sub4_jk_rdd:baramulla:rafiabad:chanum:2"]
    assert (d["dept"], d["level"], d["post"], d["name"], d["phone"], d["area"], d["block"], d["district_code"]) == \
        ("revenue", "gram_panchayat", "Patwari", "Noor Mohammad", "9906639171", "Chanum", "Rafiabad", "3")
    assert d["src_pos"] == {"table": 1, "row": 3} and d["src_url"] == m.gp_url("Chanum", "Rafiabad")
    # two people named BDO of Rafiabad by different halqa pages: one block record each
    b = by["dept:sub4_jk_rdd:baramulla:rafiabad:bdo:gauravdeep-kaur"]
    assert (b["level"], b["area"], b["post"], b["phone"], b["panchayats"]) == \
        ("block", "Rafiabad", "Block Development Officer", "8825073583", ["Chatloora"])
    assert "dept:sub4_jk_rdd:baramulla:rafiabad:bdo:irshad-ahmad-wani" in by
    assert by["dept:sub4_jk_rdd:baramulla:rafiabad:chatloora:6"]["dept"] == "electricity"
    assert not any("aadhaar" in k and k != "aadhaar_column_filled" for _, d in recs for k in d)
    for rid, d in recs:
        assert rid.startswith("dept:sub4_jk_rdd:") and d["type"] == "dept_office" and d["state"] == "JK" and d["source"]


def test_sub4_jk_other_block_rows_dropped():
    m = mod("sub4_jk_rdd")
    html = (DATA / "sub4" / "jk_gp_chanum.html").read_text()
    assert m.build("Baramulla", "Boniyar", [("Chanum", "u", html)]) == []
