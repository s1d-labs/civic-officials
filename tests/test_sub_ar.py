"""Offline tests of the Arunachal returning officers reader (dforms/sub_ar.py) on small saved answers in tests/data/sub/ (cut from the pages of 2026-11-10/11)."""
from esw_common import *  # noqa: F401,F403


def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def test_sub_ar_returning_officers():
    pages = json.loads((DATA / "sub" / "sub_ar_ro_pages.json").read_text())   # layout text of the PDF, cut to 10 rows
    recs = mod("sub_ar").parse_pages(pages)
    check_records(recs, "sub_ar", "elections")
    r = dict(recs)
    assert len(r) == 10
    a = r["dept:sub_ar:AR-AC-12:ro"]
    assert a["name"] == "Sh. Kamin Darang" and a["subdivision"] == "Lemmi" and a["area"] == "12 - Pakke Kessang (ST)"
    assert a["office_id"] == "AR-AC-12" and a["level"] == "ac" and a["post"] == "Returning Officer"
    # wrapped cells: designation, name and email on two lines
    assert r["dept:sub_ar:AR-AC-6:ro"]["designation"] == "Additional Deputy Commissioner, Singchung"
    assert r["dept:sub_ar:AR-AC-25:ro"]["name"] == "Sh. Shashank Mani Tripathi, IAS"
    assert r["dept:sub_ar:AR-AC-25:ro"]["district"] == "Kamle"
    assert r["dept:sub_ar:AR-AC-17:ro"]["email"] == "himaniayushi@gmail.com, dc-lsuban-arn@nic.in"
    assert r["dept:sub_ar:AR-AC-41:ro"]["email"] == "deoanini-arn@nic.in, deoanini12@gmail.com"
    assert r["dept:sub_ar:AR-AC-57:ro"]["area"] == "57 - Borduria Bogapani (ST)"
    assert r["dept:sub_ar:AR-AC-29:ro"]["subdivision"] == "Basar"
