"""Offline test of dforms/ulb_py.py (Puducherry: the Karaikal who's who names the municipal commissioner) on a 2-row sample."""
from esw_common import *  # noqa: F401,F403


def test_ulb_py():
    seed = json.loads((ROOT / "seeds" / "dept_ulb_py.json").read_text())
    assert mod("ulb_py").items() == seed
    p = seed[0]["payload"]
    recs, files, why = mod("ulb_py").fetch(p, fake_get({p["url"]: "ulb_py_karaikal.html"}))
    assert why == "" and files[0][0] == "depts/ulb_py/karaikal.html.gz"
    check_records(recs, "ulb_py", "town_body")
    recs = dict(recs)
    assert list(recs) == ["dept:ulb_py:PY-karaikal-karaikal-commissioner"]          # the SSP row names no municipality
    c = recs["dept:ulb_py:PY-karaikal-karaikal-commissioner"]
    assert c["area"] == "Karaikal" and c["name"] == "Mr. S. Subash" and c["phone"] == "04368-222427" and c["role"] == "head"
    assert c["email"] == "municpal.kkl@py.gov.in" and c["district"] == "Karaikal"
