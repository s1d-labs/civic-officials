"""Offline test of dforms/ulb_hr.py (Haryana DULB nodal officers page) on a cut of the saved page (10 rows)."""
from esw_common import *  # noqa: F401,F403

M = "ulb_hr"


def _run():
    p = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())[0]["payload"]
    get = fake_get({p["url"]: "ulb_hr_nodal.html"})
    recs, files, why = mod(M).fetch(p, get)
    assert why == "" and files[0][0] == "depts/ulb_hr/nodal-officers.html.gz"
    check_records(recs, M, "town_body")
    return dict(recs)


def test_ulb_hr_items_match_seed():
    assert mod(M).items() == json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_hr_rows():
    r = _run()
    am = r["dept:ulb_hr:HR-ambala-ambala-sadar-secretary"]
    assert am["area"] == "Ambala Sadar" and am["name"] == "Sh. Gulshan Kumar" and am["email"] == "eo-ambalasadar@ulbharyana.gov.in"
    assert am["role"] == "head" and am["district"] == "Ambala" and am["last_updated"] == "2025-08-21"
    ka = r["dept:ulb_hr:HR-kaithal-kaithal-executive-officer"]          # one officer for six bodies: the mailbox names Kaithal
    assert ka["area"] == "Kaithal" and ka["nodal_for"] == "Cheeka, Kalayat, Pundri, Rajaund, Siwan"
    yn = r["dept:ulb_hr:HR-yamunanagar-yamunanagar-additional-municipal-commissioner"]
    assert yn["role"] == "deputy" and yn["nodal_for"] == "Jagadhri"
    assert r["dept:ulb_hr:HR-sirsa-sirsa-executive-officer"]["name"] == "Smt. Suman Lata"
    # "Ellenabad, Kalanwali, Mandi Dabwali, Rania" with secymc.sirsa: no body fits, no record; each body has its own row
    assert len(r) == 9 and len({d["area"] for d in r.values()}) == 9
