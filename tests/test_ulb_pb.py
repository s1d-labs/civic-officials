"""Offline test of dforms/ulb_pb.py (Punjab mSeva tenant master) on a cut of the saved answer (9 tenants)."""
from esw_common import *  # noqa: F401,F403

M = "ulb_pb"


def _run():
    p = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())[0]["payload"]
    get = fake_get({("POST", p["url"]): "ulb_pb_tenants.json"})
    recs, files, why = mod(M).fetch(p, get)
    assert why == "" and files[0][0] == "depts/ulb_pb/tenants.json.gz"
    body = json.loads(get.calls[0][2])
    assert body["MdmsCriteria"]["moduleDetails"][0]["moduleName"] == "tenant"
    check_records(recs, M, "town_body")
    return dict(recs)


def test_ulb_pb_items_match_seed():
    assert mod(M).items() == json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_pb_rows():
    r = _run()
    ab = r["dept:ulb_pb:PB-fazilka-abohar-executive-officer"]
    assert ab["area"] == "ABOHAR" and ab["phone"] == "01634220233" and ab["email"] == "eomcabh@yahoo.in"
    assert ab["lgd_code"] == "248355" and ab["role"] == "head" and ab["post_from"] == "email" and "name" not in ab
    am = r["dept:ulb_pb:PB-amritsar-amritsar-commissioner"]
    assert am["email"] == "cmcasr@punjab.gov.in" and am["body_type"] == "Municipal Corporation"
    ah = r["dept:ulb_pb:PB-sangrur-ahmedgarh-office"]
    assert ah["post"] == "Office" and ah["role"] == "staff" and ah["address"] == "Near Civil Hospital"
    assert r["dept:ulb_pb:PB-jalandhar-adampur-executive-officer"]["email"] == "eo.mcadampur@punjab.gov.in"
    # Improvement Trust (pb.itabohar), the department, the water board, a test tenant: left out; Bhulath has only a cut email
    assert len(r) == 4
