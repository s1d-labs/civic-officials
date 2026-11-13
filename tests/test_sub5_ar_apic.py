"""Offline tests of the Arunachal block / circle / sub-division officers reader (dforms/sub5_ar_apic.py) on the FULL saved APIC
PIO list (apic.arunachal.gov.in/pio-list, archive copy of 2026-11-13, 527 rows; gzip in tests/data/sub/)."""
import gzip

import provenance
from esw_common import *  # noqa: F401,F403

PAGE = "sub/sub5_ar_apic_pio_list.html.gz"


def _recs():
    provenance.rows_reset()
    recs = mod("sub5_ar_apic").records(gzip.decompress((DATA / PAGE).read_bytes()).decode("utf-8"))
    return recs, provenance.rows(len(recs))


def test_counts():
    recs, rows = _recs()
    assert len(recs) == 52
    lv = {}
    for _, d in recs:
        lv[d["level"]] = lv.get(d["level"], 0) + 1
    assert lv == {"subdistrict": 25, "block": 15, "subdivision": 12}
    assert rows["rows_seen"] == 528 and rows["rows_used"] == 36
    assert rows["rows_filtered"] == {"not a block / circle / sub-division office": 489}
    assert rows["rows_skipped"] == {"no name or contact": 2} and rows["rows_not_data"] == {"header": 1}
    assert sum(1 for _, d in recs if d.get("district_code")) == 44
    assert len({d["subdistrict_code"] for _, d in recs if d.get("subdistrict_code")}) == 20
    assert len({d["lgd_block_code"] for _, d in recs if d.get("lgd_block_code")}) == 15


def test_records():
    recs, _ = _recs()
    for dept in ("administration", "rural_development"):
        check_records([r for r in recs if r[1]["dept"] == dept], "sub5_ar_apic", dept)
    r = dict(recs)
    a = r["dept:sub5_ar_apic:126:pio:adc"]                      # "Shri Likha Radh, ADC, Pania PIO Department: GA Mobile: ..."
    assert a["name"] == "Shri Likha Radh" and a["area"] == "Pania" and a["level"] == "subdivision"
    assert a["email"] == "lradh43@gmail.com" and a["rti_role"] == "PIO" and a["src_pos"]["row"] == 126
    co, bdo = r["dept:sub5_ar_apic:144:pio:co"], r["dept:sub5_ar_apic:144:pio:bdo"]     # "CO cum BDO", Yangte
    assert co["subdistrict_code"] == "1704" and bdo["lgd_block_code"] == "7083" and co["district"] == "Kra Daadi"
    assert bdo["dept"] == "rural_development" and co["dept"] == "administration" and co["phone"] == "9402950226"
    b = r["dept:sub5_ar_apic:32:pio:bdo"]                       # post in the DEPARTMENT cell "BDO, Lada, Block"
    assert b["name"] == "Shri Tiwan Dolo" and b["lgd_block_code"] == "7539" and b["post_from"] == "department cell"
    e = r["dept:sub5_ar_apic:14:pio:eac"]                       # phone and e-mail in the row's CONTACT / EMAIL columns
    assert e["phone"] == "8119069134" and e["email"] == "patodctirap@gmail.com" and e["area"] == "Khonsa HQ"
    # one CO for three circles listed in the DEPARTMENT cell
    assert [r[f"dept:sub5_ar_apic:130:pio:co:p{i}"]["area_as_written"] for i in (1, 2, 3)] == ["Tarak Lengdi", "Gangte", "Chambang"]
    # forest "Eastern Arunachal Circle (EAC)" and "yahoo.co.in" are not posts
    assert not any(k.startswith("dept:sub5_ar_apic:219:") or k.startswith("dept:sub5_ar_apic:320:") for k in r)


def test_fetch():
    get = fake_get({"https://apic.arunachal.gov.in/pio-list": "sub/sub5_ar_apic_pio_list.html.gz"})
    recs, files, why = mod("sub5_ar_apic").fetch(mod("sub5_ar_apic").items()[0]["payload"], lambda u, **k: _gunz(get(u)))
    assert why == "" and len(recs) == 52 and files[0][0] == "depts/sub5_ar_apic/pio_list.html.gz"


def _gunz(a):
    a.content = gzip.decompress(a.content)
    return a
