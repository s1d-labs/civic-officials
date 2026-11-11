"""Offline test of the Jharkhand reader (dforms/ulb_jh.py): UDHD body pages, officer card + footer."""
from esw_common import *  # noqa: F401,F403

M = "ulb_jh"
SEED = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_jh_items_match_seed():
    assert mod(M).items() == SEED and len(SEED) == 48
    assert all(i["payload"]["india_only"] for i in SEED)


def test_ulb_jh_chas():
    p = next(i["payload"] for i in SEED if i["key"] == "ulb_jh-chas")
    recs, files, why = mod(M).fetch(p, fake_get({p["url"]: "ulb_jh_chas.html"}))
    assert why == "" and files[0][0] == f"depts/{M}/chas-municipal-corporation.html.gz"
    check_records(recs, M, "town_body")
    assert len(recs) == 1
    d = dict(recs)["dept:ulb_jh:JH-bokaro-chas-additional-municipal-commissioner"]
    assert d["area"] == "Chas" and d["body_type"] == "Municipal Corporation" and d["district"] == "Bokaro"
    assert d["name"] == "Shri ANIL KUMAR SINGH" and d["phone"] == "+91 9006083173" and d["email"] == "chasmunicipalcouncil@gmail.com"
    assert d["office_phone"] == "06542-265416" and d["office_email"] == "chasmunicipalcorporation@gmail.com"
    assert d["last_updated"] == "2026-10-31" and d["address"].endswith("Bokaro-827013 (Jharkhand)")


def test_ulb_jh_dc_card_skipped_and_office_record():
    html = (DATA / "ulb_jh_chas.html").read_text()
    dc = html.replace("Shri ANIL KUMAR SINGH", "Shri X (IAS)").replace("Additional Municipal Commissioner", "Deputy Commissioner")
    recs = dict(mod(M).parse(dc, "Chas Municipal Corporation", "Bokaro", "u"))
    assert list(recs) == ["dept:ulb_jh:JH-bokaro-chas-office"]                    # no body officer: the footer gives an Office record
    assert recs["dept:ulb_jh:JH-bokaro-chas-office"]["phone"] == "06542-265416"
    eo = html.replace("Additional Municipal Commissioner", "Executive Officer")
    assert dict(mod(M).parse(eo, "Chas Municipal Corporation", "Bokaro", "u"))["dept:ulb_jh:JH-bokaro-chas-executive-officer"]["role"] == "head"


def test_ulb_jh_split_type():
    st = mod(M).split_type
    assert st("Jamshedpur NAC") == ("Jamshedpur", "NAC") and st("Chakulia Nagar panchayat") == ("Chakulia", "Nagar panchayat")
