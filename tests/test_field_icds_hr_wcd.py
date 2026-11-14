"""Offline tests of dforms/field_icds_hr_wcd.py (Haryana DPOs and WCDPOs) on full saved files in tests/data/icds_hr/:
the Who's Who page of wcdhry.gov.in (archive.s1d.me copy of 2026-11-06) and the WCDPO lists of Ambala, Hisar and Karnal
(fetched from Mumbai on 2026-11-14)."""
import hashlib
import json

import pytest

from esw_common import DATA, ROOT, check_records, fake_get, mod

B = "https://cdnbbsr.s3waas.gov.in/s34c144c47ecba6f8318128703ca9e2601/uploads/2020/11/"
PDFS = {B + "2020110371.pdf": "icds_hr/wcdpo_ambala.pdf", B + "2020110334.pdf": "icds_hr/wcdpo_hisar.pdf",
        B + "2020110311.pdf": "icds_hr/wcdpo_karnal.pdf"}


def _run(m):
    p = json.loads((ROOT / "seeds" / "dept_field_icds_hr_wcd.json").read_text())[0]["payload"]
    get = fake_get({m.URL: "icds_hr/wcdhry_whos_who.html", **PDFS})
    return m.fetch(p, get), get


def test_page_dpos_and_links():
    m = mod("field_icds_hr_wcd")
    recs, pdfs = m.parse_page((DATA / "icds_hr" / "wcdhry_whos_who.html").read_text(encoding="utf-8"))
    assert len(recs) == 22 and len(pdfs) == 21
    assert ("Ambala", B + "2020110371.pdf") in pdfs and "Charkhi-Dadri" not in dict(pdfs)
    d = dict(recs)["dept:field_icds_hr_wcd:dpo:ambala"]
    assert d["name"] == "Smt Manisha Gagat" and d["phone"] == "0171-2974275, 8950170625" and d["email"] == "poamb.wcd@gmail.com"
    assert d["level"] == "district" and d["post"] == "District Programme Officer" and d["src_pos"]["table"] >= 1


@pytest.mark.parametrize("engine", ["pdftotext", "pypdf"])
def test_wcdpo_lists(engine, monkeypatch):
    m = mod("field_icds_hr_wcd")
    if engine == "pypdf":
        monkeypatch.setattr("shutil.which", lambda name: None)
    (recs, files, why), get = _run(m)
    assert len(get.calls) == 22 and len(files) == 1
    assert why.startswith("no WCDPO list for 18 districts")
    cd = [(r, d) for r, d in recs if d["level"] == "block"]
    assert len(recs) == 45 and len(cd) == 23
    check_records([x for x in recs if not x[1].get("vacant")], "field_icds_hr_wcd", "women_child")
    from collections import Counter
    assert Counter(d["district"] for _, d in cd) == {"Hisar": 10, "Ambala": 7, "Karnal": 6}
    by = dict(recs)
    d = by["dept:field_icds_hr_wcd:cdpo:ambala:ambala-r-1"]
    assert (d["name"], d["phone"], d["icds_project"]) == ("Smt. Vanita Mehta", "9467733133", "Ambala R-1")
    assert d["address"] == "Near ADC office court road, ambala city" and d["last_updated"] == "2020-06"
    assert d["src_url"] == B + "2020110371.pdf" and d["src_pos"]["page"] == 1 and d["src_pos"]["row"] == 1
    d = by["dept:field_icds_hr_wcd:cdpo:ambala:shahzadpur"]
    assert d["name"] == "Smt. Manisha Gagat" and d["additional_charge"] is True
    d = by["dept:field_icds_hr_wcd:cdpo:hisar:narnaund"]
    assert d["vacant"] is True and "name" not in d and "phone" not in d
    d = by["dept:field_icds_hr_wcd:cdpo:hisar:barwala"]
    assert d["name"] == "Smt. Kusum Sharma" and d["address"] == "Market Committee Building near Tehsil Office, Railway Road, Barwala"
    assert by["dept:field_icds_hr_wcd:cdpo:karnal:nissing"]["address"] == "BDPO Complex, Nissing at Chirao"
    assert by["dept:field_icds_hr_wcd:cdpo:hisar:hisar-u"]["name"] == "Smt. Kamlesh"
