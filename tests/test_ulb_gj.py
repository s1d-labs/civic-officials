"""Offline test of dforms/ulb_gj.py (Gujarat COMA chief officer + pramukh lists) on two small saved pages (6 rows of each)."""
from esw_common import *  # noqa: F401,F403


def test_ulb_gj():
    p = json.loads((ROOT / "seeds" / "dept_ulb_gj.json").read_text())[0]["payload"]
    assert mod("ulb_gj").items() == json.loads((ROOT / "seeds" / "dept_ulb_gj.json").read_text())
    get = fake_get({p["url"]: "ulb_gj_list.html", p["url_pramukh"]: "ulb_gj_pramukh.html"})
    recs, files, why = mod("ulb_gj").fetch(p, get)
    assert why == "" and len(files) == 2 and files[0][0] == "depts/ulb_gj/listofmunicipalities.html.gz"
    check_records(recs, "ulb_gj", "town_body")
    recs = dict(recs)
    assert len(recs) == 12
    co = recs["dept:ulb_gj:GJ-ahmedabad-dholka-chief-officer"]
    assert co["area"] == "Dholka" and co["name"] == "Smt. Prarthanaben Rathod" and co["role"] == "head" and co["district"] == "Ahmedabad"
    assert co["status"] == "Regular" and co["body_class"] == "A" and co["last_updated"] == "2026-11-03" and co["level"] == "body"
    pr = recs["dept:ulb_gj:GJ-ahmedabad-dholka-pramukh-president"]
    assert pr["name"] == "Smt. Anamikaben Dilipbhai Bhatt" and pr["phone"] == "9106863860" and pr["role"] == "chair"
    # another spelling in the pramukh list: the chief officer still gets the district
    assert recs["dept:ulb_gj:GJ-kheda-mehmedabad-chief-officer"]["district"] == "Kheda"
    assert recs["dept:ulb_gj:GJ-kheda-mahemdavad-pramukh-president"]["phone"] == "9879216392"
    # "-" in the pramukh list: the body at the same Sr. No. of the chief officer list
    kadi = recs["dept:ulb_gj:GJ-mehsana-kadi-pramukh-president"]
    assert kadi["area"] == "Kadi" and kadi["name"] == "Shri Rajendrakumar Khodidas Gajjar"
    assert recs["dept:ulb_gj:GJ-mehsana-kadi-chief-officer"]["name"] == "Shri Siddharth R. Patel"
    # two Mandvi: Kutch (written "Mandvi (K)", district as LGD writes it) and Surat
    assert recs["dept:ulb_gj:GJ-kachchh-mandvi-k-chief-officer"]["name"] == "Shri Vaibhav K. Vyas (Mamlatdar)"
    assert recs["dept:ulb_gj:GJ-surat-mandvi-chief-officer"]["district"] == "Surat"
    assert recs["dept:ulb_gj:GJ-kachchh-mandvi-kutch-pramukh-president"]["area"] == "Mandvi (Kutch)"


def test_ulb_gj_without_pramukh_page():
    p = json.loads((ROOT / "seeds" / "dept_ulb_gj.json").read_text())[0]["payload"]
    recs, files, why = mod("ulb_gj").fetch(p, fake_get({p["url"]: "ulb_gj_list.html"}))
    assert why == "" and len(files) == 1 and len(recs) == 6 and all(d.get("district") is None for _, d in recs)
