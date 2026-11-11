"""Offline test of dforms/ulb_rj.py (Rajasthan Jankalyan contact service) on a cut of the saved answer (27 rows)."""
from esw_common import *  # noqa: F401,F403

M = "ulb_rj"


def _run():
    p = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())[0]["payload"]
    get = fake_get({("POST", p["url"]): "ulb_rj_contacts.json"})
    recs, files, why = mod(M).fetch(p, get)
    assert why == "" and files[0][0] == "depts/ulb_rj/contacts.json.gz"
    assert get.calls[0][0] == "POST" and get.calls[0][2] == "{}"
    check_records(recs, M, "town_body")
    return dict(recs)


def test_ulb_rj_items_match_seed():
    assert mod(M).items() == json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_rj_town_sites():
    r = _run()
    tonk = r["dept:ulb_rj:RJ--tonk-commissioner-nagar-parishad"]
    assert tonk["area"] == "TONK" and tonk["name"] == "SHIKHAR CHAND JAIN" and tonk["phone"] == "01432-247246"
    assert tonk["email"] == "nptonk@gmail.com" and tonk["role"] == "head" and tonk["body_type"] == "Nagar Parishad"
    # three CHAIRMAN rows for Rajsamand: the newest entry (highest Id) wins
    ch = r["dept:ulb_rj:RJ--rajsamand-chairman"]
    assert ch["name"] == "Mr. Ashok Tak" and ch["phone"] == "9214432562" and ch["role"] == "chair"
    assert r["dept:ulb_rj:RJ--kapasan-executive-officer"]["name"] == "Lalit Singh Detha"
    assert r["dept:ulb_rj:RJ--nimbahera-staff"]["name"] == "Aasim Khan"
    assert "name" not in r["dept:ulb_rj:RJ--bayana-acp-dy-director"]          # "Nodal off" is no name


def test_ulb_rj_district_sites():
    r = _run()
    bk = r["dept:ulb_rj:RJ-dausa-bandikui-chairman"]
    assert bk["area"] == "Bandikui" and bk["district"] == "Dausa" and bk["name"] == "Mrs. Vinod Devi" and bk["phone"] == "9929745613"
    md = r["dept:ulb_rj:RJ-karauli-mandrayal-executive-officer"]
    assert md["name"] == "Sh. Jagram Meena" and md["email"] == "npmandrayal@gmail.com" and md["role"] == "head"
    assert r["dept:ulb_rj:RJ-anupgarh-anupgarh-commissioner-nagar-parishad"]["name"] == "Smt Kanchan Rathore"   # district HQ council
    assert r["dept:ulb_rj:RJ-hanumangarh-sangaria-executive-officer"]["name"] == "Sh. Pawan Kumar"
    areas = {d["area"] for d in r.values()}
    assert not areas & {"Sapotra", "Jodhpur", "Jaipur", "DUNGARPUR", "Balotra", "FATEHPUR"}   # supply EO, no-town Nigam, test site, ZP, UIT, DoIT
    assert len(r) == 14
