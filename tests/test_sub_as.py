"""Offline tests of the Assam district and revenue-circle officer readers (dforms/sub_as.py, dforms/sub_as_asdma.py) on small saved answers in tests/data/sub/ (cut from the pages of 2026-11-10/11)."""
from esw_common import *  # noqa: F401,F403


def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def test_sub_as_pds_dc_offices():
    p = _seed("sub_as")[0]["payload"]
    assert p["india_only"] and p["state"] == "AS"
    recs, files, why = mod("sub_as").fetch(p, fake_get({p["url"]: "sub/sub_as_dc_offices.html"}))
    assert why == "" and files[0][0] == "depts/sub_as/dc-offices.html.gz"
    for rid, d in recs:
        assert rid.startswith("dept:sub_as:") and d["state"] == "AS" and d.get("source") and d["level"]
    r = dict(recs)
    dc = r["dept:sub_as:AS-bajali:deputy-commissioner"]
    assert dc["name"] == "Smti Cauvery Barkakati Sarma, Acs" and dc["dept"] == "administration" and dc["level"] == "district"
    assert dc["phone"] == "3666296999, 9864049559" and dc["email"] == "dcbajali@gmail.com" and dc["district"] == "Bajali"
    sdo = r["dept:sub_as:AS-bongaigaon:sub-divisional-officer-c"]
    assert sdo["level"] == "subdivision" and sdo["area"] == "NORTH SALMARA" and sdo["name"] == "Simi Karan"
    # two SDOs in one district: the name keeps the ids apart
    assert r["dept:sub_as:AS-golaghat:sub-divisional-officer-c:dr-neha-yadav-ias"]["area"] == "BOKAKHAT"
    # the page's KARIMGANJ is LGD's Sribhumi
    assert r["dept:sub_as:AS-sribhumi:deputy-commissioner"]["district"] == "Sribhumi"
    food = [d for d in r.values() if d["dept"] == "food_supplies"]
    assert food and all(d["level"] == "district" for d in food)
    # "(+91)0000000000" is no phone
    assert all("0000000000" not in d.get("phone", "") for d in r.values())


def test_sub_as_district_names():
    district = mod("sub_as").district
    assert district("N. C. HILLS") == "Dima Hasao" and district("Kamrup (M)") == "Kamrup Metro"
    assert district("Nagaon(Attached)") == "Nagaon" and district("SOUTH SALMARA") == "South Salmara Mancachar"
    assert district("Karbi – Anglong") == "Karbi Anglong" and district("D.C. Morigaon") == "Marigaon"


def test_sub_as_asdma_emergency():
    items = {i["payload"]["page"]: i["payload"] for i in _seed("sub_as_asdma")}
    p = items["emergency"]
    recs, files, why = mod("sub_as_asdma").fetch(p, fake_get({p["url"]: "sub/sub_as_asdma_emergency.html"}))
    assert why == "" and files[0][0] == "depts/sub_as_asdma/emergency.html.gz"
    r = dict(recs)
    dc = r["dept:sub_as_asdma:AS-barpeta:dc-office"]
    assert dc["phone"] == "03665-225129, 03665-252105" and dc["fax"] == "03665-223102" and dc["satellite_phone"] == "8991118973"
    assert dc["dept"] == "administration" and dc["post"] == "Deputy Commissioner" and "name" not in dc
    po = r["dept:sub_as_asdma:AS-darrang:ddma-po"]
    assert po["name"] == "Jagadish Bhattacharyya" and po["phone"] == "9864116646, 03713-222723"
    assert po["email"] == "jagadish.bhattacharyya@gmail.com" and po["dept"] == "revenue" and po["level"] == "district"
    assert r["dept:sub_as_asdma:AS-kamrup-metro:ddma-po"]["name"] == "Kaustav Talukdar"


def test_sub_as_asdma_field_officers():
    p = {i["payload"]["page"]: i["payload"] for i in _seed("sub_as_asdma")}["field"]
    recs, files, why = mod("sub_as_asdma").fetch(p, fake_get({p["url"]: "sub/sub_as_field_officers.xlsx"}))
    assert why == "" and files[0][0] == "depts/sub_as_asdma/field_officers.xlsx.gz"
    check_records(recs, "sub_as_asdma", "revenue")
    r = dict(recs)
    fo = r["dept:sub_as_asdma:AS-bajali:fo:sarupeta"]
    assert fo["name"] == "Satyajit Das" and fo["phone"] == "8402065980" and fo["email"] == "satyajit.das@gmail.com"
    assert fo["level"] == "subdistrict" and fo["area"] == "Sarupeta" and fo["district"] == "Bajali"
    assert r["dept:sub_as_asdma:AS-baksa:fo:baska"]["phone"] == "84862-85023"
    # two numbers in one cell, a line break inside the cell
    assert r["dept:sub_as_asdma:AS-majuli:fo:majuli-ujani-majuli"]["phone"] == "9101176940, 8256809982"
    assert r["dept:sub_as_asdma:AS-west-karbi-anglong:fo:donkamokam-revenue-officer"]["name"] == "Sri Hemphu Bey"
