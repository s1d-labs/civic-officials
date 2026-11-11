"""Offline test of dforms/ulb_ap.py (Andhra Pradesh APCMMS ULB profiles: commissioner of every body) on a 3-body sample."""
from esw_common import *  # noqa: F401,F403


def test_ulb_ap():
    seed = json.loads((ROOT / "seeds" / "dept_ulb_ap.json").read_text())
    assert mod("ulb_ap").items() == seed
    p = seed[0]["payload"]
    recs, files, why = mod("ulb_ap").fetch(p, fake_get({p["url"]: "ulb_ap_ulbprofiles.json"}))
    assert why == "" and files[0][0] == "depts/ulb_ap/ulbprofiles.json.gz"
    check_records(recs, "ulb_ap", "town_body")
    recs = dict(recs)
    assert len(recs) == 3
    a = recs["dept:ulb_ap:AP-prakasam-addanki-commissioner"]
    assert a["name"] == "RAVINDRA DEVARAPALLI" and a["phone"] == "8008559293" and a["body_type"] == "Nagar Panchayat"
    assert a["role"] == "head" and a["district"] == "Prakasam" and a["area"] == "Addanki" and "name_list" not in a
    # a twin name: the bracket tag goes, the district stays
    at = next(d for d in recs.values() if d.get("name_list") == "ATMAKUR(NLR)")
    assert at["area"] == "Atmakur" and at["district"] == "Sri Potti Sriramulu Nellore"
    r = next(d for d in recs.values() if d["area"] == "Rajamahendravaram")
    assert r["name"] == "Rahul Meena" and r["phone"] == "9866657600" and r["body_type"] == "Municipal Corporation"


def test_ulb_ap_not_json():
    p = json.loads((ROOT / "seeds" / "dept_ulb_ap.json").read_text())[0]["payload"]
    recs, files, why = mod("ulb_ap").fetch(p, fake_get({p["url"]: "ulb_tn_tp.html"}))
    assert recs == [] and why == "not json" and files
