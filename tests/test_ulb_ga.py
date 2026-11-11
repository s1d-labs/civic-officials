"""Offline test of dforms/ulb_ga.py (South Goa municipalities table: chief officer post + office phone) on a 3-row saved page."""
from esw_common import *  # noqa: F401,F403


def test_ulb_ga():
    seed = json.loads((ROOT / "seeds" / "dept_ulb_ga.json").read_text())
    assert mod("ulb_ga").items() == seed
    p = seed[0]["payload"]
    recs, files, why = mod("ulb_ga").fetch(p, fake_get({p["url"]: "ulb_ga_municipalities.html"}))
    assert why == "" and files[0][0] == "depts/ulb_ga/municipalities.html.gz"
    check_records(recs, "ulb_ga", "town_body")
    recs = dict(recs)
    assert len(recs) == 3
    co = recs["dept:ulb_ga:GA--municipal-council-canacona-chief-officer"]
    assert co["area"] == "Municipal Council Canacona" and co["post"] == "Chief Officer" and co["phone"] == "0832-2643358"
    assert co["role"] == "head" and not co.get("name") and co["last_updated"] == "2021-03-22" and co["level"] == "body"
    assert recs["dept:ulb_ga:GA--municipal-council-sanguem-chief-officer"]["phone"] == "0832-2604227"
