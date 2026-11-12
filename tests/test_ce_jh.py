"""Jharkhand Municipal Election 2026 (cforms/ce_jh.py): grid rows typed from the Seraikela-Kharsawan district gazettes
Prapatra-23 (क) page 3 (Adityapur wards 1-8) and 23 (ख) page 3 (Adityapur mayor); saved district election pages."""
import json
from pathlib import Path

from cforms import ce_jh

DATA = Path(__file__).parent / "data"
URL = "https://cdn.s3waas.gov.in/s3b337e84de8752b27eda3a12363109e80/uploads/2026/03/17726939225372.pdf"


def test_ward_rows():
    rows = json.loads((DATA / "ce_jh_adityapur_wards_rows.json").read_text())
    p = {"url": URL, "district": "Saraikela Kharsawan"}
    recs = ce_jh.page_records(rows, p, 3)
    assert len(recs) == 8
    a = recs[0]
    assert a["name"] == "बनमाली दास" and a["ward_no"] == "1" and a["lgd_code"] == "253166" and a["body"] == "Adityapur"
    assert a["position"] == "Member" and a["women_seat"] is False and a["reservation"] == "पिछड़ा वर्ग-II"
    assert a["src_pos"]["page"] == 3 and a["src_pos"]["row"] == 4 and a["src_pos"]["conf"] == 70
    assert recs[1]["women_seat"] is True and recs[7]["ward_no"] == "8" and recs[7]["name"] == "मोना बेसरा"
    assert ce_jh.record_id(a, 1) == "councillor:JH:253166:1"


def test_mayor_row():
    rows = json.loads((DATA / "ce_jh_adityapur_mayor_rows.json").read_text())
    recs = ce_jh.page_records(rows, {"url": URL, "district": "Saraikela Kharsawan"}, 3)
    assert len(recs) == 1
    m = recs[0]
    assert m["position"] == "Mayor" and m["ward_no"] == "chair" and m["name"] == "संजय सरदार" and m["lgd_code"] == "253166"


def test_posts_and_bodies():
    assert ce_jh.post_of("उपमहापौर") == ("Deputy Mayor", "vice")
    assert ce_jh.post_of("Up Mahapor 23 KH") == ("Deputy Mayor", "vice")
    assert ce_jh.post_of("उपाध्यक्ष") == ("Vice Chairperson", "vice")
    assert ce_jh.post_of("अध्यक्ष") == ("Chairperson", "chair")
    assert ce_jh.post_of("वार्ड पार्षद") == (None, None)
    assert ce_jh.find_body("18 सरायकेला नगर पंचायत अध्यक्ष जिला गजट", "Saraikela Kharsawan") == "250423"
    assert ce_jh.find_body("चिरकुण्डा नगर परिषद", "Dhanbad") == "248055"
    assert ce_jh.find_body("SURIYA", "Giridih") == "290364"
    assert ce_jh.ward_of("XXIII सरायकेला/08आदित्यपुर नगरनिगम (वर्ग-ख)/वार्ड संख्या -०७") == "7"


def test_links_seraikela():
    got = ce_jh.links((DATA / "ce_jh_seraikela_page.html").read_text(), "https://seraikela.nic.in/municipal-general-election-2026/")
    urls = {u for u, _, _ in got}
    assert len(got) == 9          # 3 bodies x (wards, head) + 3 deputy heads
    assert URL in urls
    assert not any("17697684588655" in u or "17700220047961" in u for u in urls)     # code of conduct, booth lists


def test_links_bokaro():
    got = ce_jh.links((DATA / "ce_jh_bokaro_page.html").read_text(), "https://bokaro.nic.in/municipality-general-election-2026/")
    assert [t for _, t, _ in got] == ["Result (Chas Mayor and Wards, Phusro Adhyaksh and Wards)", "Result (Deputy Mayor / Vice-Chairperson)"]


def test_menu_palamu():
    got = ce_jh.menu_pages((DATA / "ce_jh_palamu_home.html").read_text(), "https://palamu.nic.in/")
    assert got[0] == "https://palamu.nic.in/municipal-election-2020-3/"


def test_bodies_complete():
    assert len(ce_jh.BODIES) == 48 and len(ce_jh.DISTRICTS) == 24
    assert {b[0] for b in ce_jh.BODIES.values()} == {d for d, _ in ce_jh.DISTRICTS.values()}


def test_page_items_seraikela():
    its = ce_jh.page_items((DATA / "ce_jh_seraikela_page.html").read_text(), "https://seraikela.nic.in/municipal-general-election-2026/",
                           "Saraikela Kharsawan")
    got = {(i["payload"].get("lgd_code"), i["payload"].get("post")) for i in its}
    assert ("253166", "Mayor") in got and ("253166", "Deputy Mayor") in got and ("276352", "Vice Chairperson") in got
    assert ("250423", None) in got and ("276352", "Chairperson") in got
    assert all(i["key"].startswith("ce-jh26-") and i["payload"]["kind"] == "form-ce_jh" for i in its)
    b = ce_jh.page_items((DATA / "ce_jh_bokaro_page.html").read_text(), "https://bokaro.nic.in/x/", "Bokaro")
    assert [i["payload"].get("post") for i in b] == [None, None] and not any("lgd_code" in i["payload"] for i in b)


def test_seed_file():
    items = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_ce_jh26.json").read_text())
    assert len({i["key"] for i in items}) == len(items) >= 20
    assert items[-1]["payload"] == {"kind": "seed", "module": "ce_jh", "state": "JH", "url": "https://sec.jharkhand.gov.in/MElection.aspx"}
