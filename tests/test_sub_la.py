"""Offline tests of the Ladakh UT directory reader (dforms/sub_la.py) on small saved answers in tests/data/sub/ (cut from the pages of 2026-11-10/11)."""
from esw_common import *  # noqa: F401,F403


def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def test_sub_la_directory():
    p = _seed("sub_la")[0]["payload"]
    recs, files, why = mod("sub_la").fetch(p, fake_get({p["url"]: "sub/sub_la_directory.html"}))
    assert why == "" and files[0][0] == "depts/sub_la/directory.html.gz"
    r = dict(recs)
    assert "dept:sub_la:LA-kargil:deputy-commissioner-and-chief-executive-officer-lahdc-kargil" not in r   # LAHDC table is not read
    leh = r["dept:sub_la:LA-leh:deputy-commissioner-leh"]
    assert leh["name"] == "Shri Romil Singh Donk, IAS" and leh["phone"] == "01982-252010" and leh["email"] == "dcleh-jk@nic.in"
    dc = r["dept:sub_la:LA-drass:deputy-commissioner-drass"]
    assert dc["name"] == "Sh. Imteeaz Kacho, JKAS" and dc["email"] == "dc-drass@ladakh.gov.in" and dc["district"] == "Drass"
    sp = r["dept:sub_la:LA-nubra:superintendent-of-police-district-nubra"]
    assert sp["dept"] == "police" and sp["level"] == "district" and sp["name"] == "Sh. Stanzin Losal, JKPS"
    assert all(d["state"] == "LA" and d["source"] == p["url"] for d in r.values())
