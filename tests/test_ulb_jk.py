"""Offline test of the Kashmir reader (dforms/ulb_jk.py): DULB Kashmir key contacts PDF (layout text of a few rows)."""
from esw_common import *  # noqa: F401,F403

M = "ulb_jk"
SEED = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_jk_items_match_seed():
    assert mod(M).items() == SEED and SEED[0]["payload"]["india_only"] is True


def test_ulb_jk_rows():
    recs = mod(M).parse((DATA / "ulb_jk_key_contacts.txt").read_text())
    check_records(recs, M, "town_body")
    assert len(recs) == 6
    recs = dict(recs)
    a = recs["dept:ulb_jk:JK--achabal-executive-officer"]
    assert a["area"] == "Achabal" and a["body_type"] == "Municipal Committee" and a["role"] == "head"
    assert a["name"] == "Mirza Asif Ali" and a["charge"] == "Posted" and a["phone"] == "7006310020" and a["email"] == "eomc-achabal@jk.gov.in"
    b = recs["dept:ulb_jk:JK--beerwah-executive-officer"]
    assert b["name"] == "Jahangir Ahmad Shah" and b["charge"] == "BDO Soibugh"
    assert recs["dept:ulb_jk:JK--dooru-verinaag-executive-officer"]["name"] == "Mohammad Iqbal Bhat"
    s = recs["dept:ulb_jk:JK--sopore-ceo"]
    assert s["body_type"] == "Muncipa Council" and s["name"] == "Wali Mohammad Wani" and s["list_name"] == "Muncipa Council Sopore"


def test_ulb_jk_fetch_refuses_html():
    p = SEED[0]["payload"]
    assert mod(M).fetch(p, fake_get({p["url"]: "ulb_jk_key_contacts.txt"})) == ([], [], "not a PDF")
    assert mod(M).fetch(p, fake_get({})) == ([], [], "no answer")
