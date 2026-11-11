"""Offline test of dforms/ulb_mh.py (Maharashtra district pages on municipal councils: Chandrapur and Pune tables, Satara cards)."""
from esw_common import *  # noqa: F401,F403


def _run(key, sample):
    seed = json.loads((ROOT / "seeds" / "dept_ulb_mh.json").read_text())
    p = next(i["payload"] for i in seed if i["key"] == key)
    recs, files, why = mod("ulb_mh").fetch(p, fake_get({p["url"]: sample}))
    assert why == "" and files and files[0][0].startswith("depts/ulb_mh/")
    check_records(recs, "ulb_mh", "town_body")
    return dict(recs)


def test_ulb_mh_items():
    assert mod("ulb_mh").items() == json.loads((ROOT / "seeds" / "dept_ulb_mh.json").read_text())


def test_ulb_mh_chandrapur():
    recs = _run("ulb_mh-chandrapur", "ulb_mh_chandrapur.html")
    assert len(recs) == 8
    co = recs["dept:ulb_mh:MH-chandrapur-ballaarapur-chief-officer"]
    assert co["area"] == "बल्लारपुर" and co["area_latin"] == "ballaarapur" and co["name"] == "श्री.विशाल वाघ" and co["role"] == "head"
    assert co["email"] == "municipalcouncilballarpur@gmail.com" and co["district"] == "Chandrapur" and co["level"] == "body"
    fire = recs["dept:ulb_mh:MH-chandrapur-ballaarapur-fire-department-head"]
    assert fire["name"] == "श्री. शुभम रत्नपारखी" and fire["designation"] == "अग्निशमन अधिकारी" and fire["phone"] == "7972523517"
    assert fire["role"] == "staff"
    # Devanagari digits in the mobile cell
    assert recs["dept:ulb_mh:MH-chandrapur-bramhapuri-fire-department-head"]["phone"] == "7385130977"


def test_ulb_mh_pune():
    recs = _run("ulb_mh-pune", "ulb_mh_pune.html")
    assert len(recs) == 2                                   # the table without officers gives nothing
    co = recs["dept:ulb_mh:MH-pune-baramati-chief-officer"]
    assert co["area"] == "Baramati" and co["name"] == "Pankaj Bhuse" and co["phone"] == "9763977233" and co["email"] == "baramatinp@gmail.com"
    assert co["body_class"] == "A"


def test_ulb_mh_satara_cards():
    recs = _run("ulb_mh-satara-2", "ulb_mh_satara.html")
    assert len(recs) == 2                                   # Patan: post only, no phone -> no record
    co = recs["dept:ulb_mh:MH-satara-municipal-council-phaltan-chief-officer"]
    assert co["area"] == "Municipal Council, Phaltan" and co["post"] == "Chief Officer" and not co.get("name")
    assert co["phone"] == "02166-222325" and co["role"] == "head" and co["last_updated"] == "2026-11-06"
