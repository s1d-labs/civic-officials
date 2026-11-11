"""Offline test of the Arunachal reader (dforms/ulb_ar.py): Itanagar Municipal Corporation officers + committee members."""
from esw_common import *  # noqa: F401,F403

M = "ulb_ar"
SEED = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def _run(kind, sample):
    p = next(i["payload"] for i in SEED if i["payload"]["kind"] == kind)
    recs, files, why = mod(M).fetch(p, fake_get({p["url"]: sample}))
    assert why == "" and files[0][0] == f"depts/{M}/imc-{kind}.html.gz"
    check_records(recs, M, "town_body")
    return dict(recs)


def test_ulb_ar_items_match_seed():
    assert mod(M).items() == SEED and len(SEED) == 2


def test_ulb_ar_officers():
    recs = _run("officers", "ulb_ar_imc_officers.html")
    c = recs["dept:ulb_ar:AR-papum-pare-itanagar-municipal-corporation-commissioner"]
    assert c["role"] == "head" and c["name"] == "Shri Kego Jilen" and c["email"] == "imcitanagar@gmail.com"
    assert c["area"] == "Itanagar Municipal Corporation" and c["district"] == "Papum Pare" and c["last_updated"] == "2023-11-21"
    ao = recs["dept:ulb_ar:AR-papum-pare-itanagar-municipal-corporation-administrative-officer"]
    assert ao["name"] == "Shri Tayung Jerang" and ao["phone"] == "9436221498"
    assert len(recs) == 3


def test_ulb_ar_members_mayor_only():
    recs = _run("members", "ulb_ar_imc_members.html")
    mayor = recs["dept:ulb_ar:AR-papum-pare-itanagar-municipal-corporation-mayor"]
    assert mayor["role"] == "chair" and mayor["name"] == "Smti Likha Nari Tadar" and mayor["ward"] == "16"
    assert recs["dept:ulb_ar:AR-papum-pare-itanagar-municipal-corporation-deputy-mayor"]["name"] == "Shri Tok Tabin Camdir"
    assert len(recs) == 2                                                # the corporator card is left out
