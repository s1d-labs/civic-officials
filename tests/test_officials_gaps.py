"""Offline tests of the readers added for the gaps survey of 2026-11-12: Uttar Pradesh food department contact files
(dforms/food_up_fcs.py, layout text of the two PDFs fetched once on 2026-11-12) and the Assam district and department sites on
the Standardized Website Framework 2.0 (dforms/swf_as.py, pages fetched once on 2026-11-12). No test touches the network."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod

FOOD = DATA / "food"


# ---- Uttar Pradesh: food department contact files ----
def test_up_food_contacts():
    m = mod("food_up_fcs")
    recs = m.parse_contacts((FOOD / "up_fcs_contacts_layout.txt").read_text())
    check_records([r for r in recs if r[1].get("name") or r[1].get("phone")], "food_up_fcs", "food_supplies")
    by = {r: d for r, d in recs}
    dso = [d for d in by.values() if d["section"] == "dso"]
    assert len(dso) == 75 and len({d["district_code"] for d in dso}) == 75
    assert len([d for d in by.values() if d["section"] == "dfmo" and d.get("district_code")]) == 75
    d = by["dept:food_up_fcs:contacts:dso:meerut"]
    assert (d["name"], d["phone"], d["district_code"], d["level"]) == ("श्री विनय सिंह", "01212665277, 7839564767", "169", "district")
    assert d["post"] == "District Supply Officer" and d["post_regional"] == "जिला पूर्ति अधिकारी"
    # the district name broken over two lines around its row ("संतकबीर" / "नगर")
    assert by["dept:food_up_fcs:contacts:dso:sant-kabir-nagar"]["name"] == "श्री राजीव शुक्ला"
    # a name one space after the district ("जी0बी0नगर श्री चमन शर्मा")
    assert by["dept:food_up_fcs:contacts:dso:gautam-buddha-nagar"]["name"] == "श्री चमन शर्मा"
    jc = by["dept:food_up_fcs:contacts:jcdc:लखनऊ"]
    assert (jc["name"], jc["post"], jc["phone"]) == ("श्री सत्यदेव", "Joint Commissioner (Food)", "05222613893, 7839564587")
    acc = by["dept:food_up_fcs:contacts:accounts:लखनऊ"]
    assert acc["name"] == "श्री धीरेन्द्र प्रताप सिंह" and acc["post"] == "Divisional Senior Accounts Officer"
    assert by["dept:food_up_fcs:contacts:heads:7"]["phone"] == "0522-2288658"
    # a row without a name is a vacant post and keeps its CUG number
    v = by["dept:food_up_fcs:contacts:rfc:मुरादाबाद"]
    assert v.get("vacant") and v["phone"] == "7839564866" and not v.get("name")


def test_up_food_emails():
    m = mod("food_up_fcs")
    recs = m.parse_emails((FOOD / "up_fcs_emails_layout.txt").read_text())
    check_records(recs, "food_up_fcs", "food_supplies")
    dso = [d for _, d in recs if d["section"] == "dso"]
    assert len(dso) == 75 and len({d["district_code"] for d in dso}) == 75
    by = {r: d for r, d in recs}
    assert by["dept:food_up_fcs:emails:dso:140"]["email"] == "dsofaizabad11@gmail.com"
    assert by["dept:food_up_fcs:emails:dso:140"]["area"] == "Ayodhya"
    assert by["dept:food_up_fcs:emails:rfc:allahabad"]["email"] == "rfcallahabad58@gmail.com"


def test_up_food_fetch_and_seed():
    m = mod("food_up_fcs")
    seeds = json.loads((ROOT / "seeds" / "dept_food_up_fcs.json").read_text())
    assert [s["payload"]["source"] for s in seeds] == ["contacts", "emails"] and all(s["payload"]["india_only"] for s in seeds)
    recs, files, why = m.fetch(seeds[0]["payload"], fake_get({}))
    assert why == "no answer" and not recs
