"""Offline tests of the Meghalaya key-contacts reader (dforms/sub_ml.py) on small saved answers in tests/data/sub/ (cut from the pages of 2026-11-10/11)."""
from esw_common import *  # noqa: F401,F403


def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def test_sub_ml_key_contacts():
    items = {i["payload"]["page"]: i["payload"] for i in _seed("sub_ml")}
    p = items["dc"]
    recs, files, why = mod("sub_ml").fetch(p, fake_get({p["url"]: "sub/sub_ml_dc.html"}))
    assert why == "" and files[0][0] == "depts/sub_ml/dc.html.gz"
    check_records(recs, "sub_ml", "administration")
    r = dict(recs)
    egh = r["dept:sub_ml:ML-east-garo-hills:dc"]
    assert egh["name"] == "Shri. Raksin P. Marak, IAS" and egh["phone"] == "03658-220226" and egh["fax"] == "220272"
    assert egh["email"] == "dc-egh-meg@nic.in" and egh["district"] == "East Garo Hills" and egh["level"] == "district"
    ewkh = r["dept:sub_ml:ML-eastern-west-khasi-hills:dc"]
    assert ewkh["email"] == "dc.ewkh-mairang@meghalaya.gov.in" and "phone" not in ewkh
    assert r["dept:sub_ml:ML-west-garo-hills:dc"]["phone"] == "03651-223806, 03651-223835"
    p = items["sp"]
    recs, files, why = mod("sub_ml").fetch(p, fake_get({p["url"]: "sub/sub_ml_sp.html"}))
    check_records(recs, "sub_ml", "police")
    sp = dict(recs)["dept:sub_ml:ML-east-khasi-hills:sp"]
    assert sp["name"] == "Shri. Vivek Syiem, IPS" and sp["fax"] == "0364-2225675" and sp["email"] == "sp.ekh-meg@gov.in"
