"""Offline test of dforms/ulb_tn.py (Tamil Nadu DTP town panchayat EO list + CMA commissioner e-mails) on two small saved pages."""
from esw_common import *  # noqa: F401,F403


def _seed():
    return json.loads((ROOT / "seeds" / "dept_ulb_tn.json").read_text())


def test_ulb_tn_items():
    assert mod("ulb_tn").items() == _seed()


def test_ulb_tn_town_panchayats():
    p = next(i["payload"] for i in _seed() if i["payload"]["kind"] == "tp")
    recs, files, why = mod("ulb_tn").fetch(p, fake_get({p["url"]: "ulb_tn_tp.html"}))
    assert why == "" and files[0][0] == "depts/ulb_tn/tp.html.gz"
    check_records(recs, "ulb_tn", "town_body")
    recs = dict(recs)
    assert len(recs) == 5
    eo = recs["dept:ulb_tn:TN-kancheepuram-sriperumbudur-executive-officer"]
    assert eo["area"] == "Sriperumbudur" and eo["district"] == "Kancheepuram" and eo["role"] == "head" and eo["level"] == "body"
    assert eo["phone"] == "8925809268" and eo["office_phone"] == "044 - 27162440" and eo["body_type"] == "Town Panchayat"
    # the district heading carries to the bodies below it; the department's spelling stays (LGD: Uthayendram)
    ud = recs["dept:ulb_tn:TN-thiruppathur-udayendiram-executive-officer"]
    assert ud["district"] == "Thiruppathur" and ud["phone"] == "8925809301"


def test_ulb_tn_commissioners():
    p = next(i["payload"] for i in _seed() if i["payload"]["kind"] == "cma")
    recs, files, why = mod("ulb_tn").fetch(p, fake_get({p["url"]: "ulb_tn_cma.html"}))
    assert why == "" and files[0][0] == "depts/ulb_tn/cma.html.gz"
    check_records(recs, "ulb_tn", "town_body")
    recs = dict(recs)
    assert len(recs) == 5
    c = recs["dept:ulb_tn:TN-chengalpattu-madhuranthagam-commissioner"]
    assert c["email"] == "commr.madhuranthagam@tn.gov.in" and c["grade"] == "Grade II" and c["role"] == "head"
    assert c["region"] == "Chengalpattu" and "name" not in c and "phone" not in c
    assert recs["dept:ulb_tn:TN-tiruvallur-thiruthani-commissioner"]["email"] == "commr.thiruthani@tn.gov.in"
