"""Offline test of dforms/ulb_kl.py (Kerala: heads on each body's home page; the body list from the LSGD website index).
Samples: the index (5 rows, one municipality), Pala municipality (team cards + footer), Kochi corporation (older table template)."""
from esw_common import *  # noqa: F401,F403

INDEX = "https://lsgkerala.gov.in/en/website/web"


def test_ulb_kl_items():
    seed = json.loads((ROOT / "seeds" / "dept_ulb_kl.json").read_text())
    assert mod("ulb_kl").items() == seed and seed[0]["payload"]["kind"] == "seed"
    # on the hub: the index pages give one item per municipality / corporation (grama and block panchayats are left out)
    get = fake_get({INDEX: "ulb_kl_index.html"})
    items = mod("ulb_kl").items(get)
    assert items == [{"key": "ulb_kl-m030100", "payload": {
        "reader": "ulb_kl", "kind": "body", "url": "https://adoormunicipality.lsgkerala.gov.in/en", "state": "KL", "india_only": False,
        "body": "Adoor", "body_type": "Municipality", "code": "M030100", "district": "Pathanamthitta", "name_list": "Adoor Municipality"}}]
    assert [c[1] for c in get.calls] == [INDEX, INDEX + "?page=%2C%2C%2C1"]        # page 2 gives no answer here: the walk stops


def test_ulb_kl_pala():
    p = {"reader": "ulb_kl", "kind": "body", "url": "https://palamunicipality.lsgkerala.gov.in/en", "state": "KL", "body": "Pala",
         "body_type": "Municipality", "district": "Kottayam"}
    recs, files, why = mod("ulb_kl").fetch(p, fake_get({p["url"]: "ulb_kl_pala.html"}))
    assert why == "" and files[0][0] == "depts/ulb_kl/pala.html.gz"
    check_records(recs, "ulb_kl", "town_body")
    recs = dict(recs)
    assert len(recs) == 3
    s = recs["dept:ulb_kl:KL-kottayam-pala-secretary"]
    assert s["name"] == "AKASH M S" and s["phone"] == "9188955162" and s["role"] == "head" and s["last_updated"] == "2026-10-28"
    assert s["office_phone"] == "04822-212328" and s["office_email"] == "secretarypala@gmail.com"
    c = recs["dept:ulb_kl:KL-kottayam-pala-chairperson"]
    assert c["name"] == "MAYA RAHUL" and c["phone"] == "9526968579" and c["role"] == "chair"
    assert recs["dept:ulb_kl:KL-kottayam-pala-vice-chairperson"]["role"] == "deputy"


def test_ulb_kl_kochi_old_template():
    p = {"reader": "ulb_kl", "kind": "body", "url": "https://kochicorporation.lsgkerala.gov.in/en", "state": "KL", "body": "Kochi",
         "body_type": "Corporation", "district": "Ernakulam"}
    recs, _, why = mod("ulb_kl").fetch(p, fake_get({p["url"]: "ulb_kl_kochi.html"}))
    assert why == ""
    check_records(recs, "ulb_kl", "town_body")
    recs = dict(recs)
    assert recs["dept:ulb_kl:KL-ernakulam-kochi-mayor"]["name"] == "Adv. Minimol V. K."
    assert recs["dept:ulb_kl:KL-ernakulam-kochi-deputy-mayor"]["name"] == "V R Sudheer"
    s = recs["dept:ulb_kl:KL-ernakulam-kochi-secretary"]
    assert s["name"] == "P.S. Shibu" and s["role"] == "head" and s["office_phone"] == "91-484-2369007"


def test_ulb_kl_office_only():
    """A home page with no head cards: the office line becomes a "Secretary (office)" record."""
    html = ('<html><body><small class="ms-4"><i class="fa fa-envelope"></i>secretaryagly@gmail.com</small>'
            '<small class="ms-4"><i class="fa fa-phone-alt"></i>0484-2452367</small></body></html>')
    recs = dict(mod("ulb_kl").parse(html, {"body": "Angamaly", "district": "Ernakulam", "url": "https://x/en"}))
    o = recs["dept:ulb_kl:KL-ernakulam-angamaly-secretary-office"]
    assert o["email"] == "secretaryagly@gmail.com" and o["phone"] == "0484-2452367" and o["role"] == "head" and "name" not in o
