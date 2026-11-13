"""Offline tests of the sub4 readers for the southern states (dforms/sub4_*.py) on saved answers in tests/data/sub4/.
Kerala: block / grama panchayat staff pages and office blocks of the Information Kerala Mission body sites (sub4_kl_lsg)."""
import json

from esw_common import *  # noqa: F401,F403

KL = "https://adimalyblockpanchayat.lsgkerala.gov.in"
GP = "https://adatpanchayat.lsgkerala.gov.in"


def test_sub4_kl_seed_and_index():
    m = mod("sub4_kl_lsg")
    seeds = json.loads((ROOT / "seeds" / "dept_sub4_kl.json").read_text())
    assert seeds == m.items()
    rows, more = m.index_rows((DATA / "sub4" / "kl_index.html").read_text())
    assert more and len(rows) == 19 and all(c[0] in "BGD" for _, c, _ in rows)
    it = m.body_item(*rows[2])
    assert it["key"] == "sub4_kl_lsg-b060100"
    p = it["payload"]
    assert (p["body"], p["body_type"], p["district"], p["district_code"], p["url"]) == \
        ("Adimaly", "Block Panchayat", "Idukki", "556", f"{KL}/en")


def test_sub4_kl_index_walk():
    m = mod("sub4_kl_lsg")
    get = fake_get({m.INDEX: "sub4/kl_index.html"})        # page 2 answers None: the walk stops
    out = m.items(get)
    assert len(out) == 19 and len({i["key"] for i in out}) == 19


def test_sub4_kl_block_table():
    m = mod("sub4_kl_lsg")
    p = m.body_item("Adimaly Block Panchayat", "B060100", "http://adimalyblockpanchayat.lsgkerala.gov.in/")["payload"]
    staff_url = f"{KL}/en/page/officials-and-employees"
    get = fake_get({p["url"]: "sub4/kl_b060100_home.html", staff_url: "sub4/kl_b060100_staff.html",
                    f"{KL}/en/emails": "sub4/kl_b060100_emails.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(files) == 3
    check_records(recs, "sub4_kl_lsg", "rural_development")
    d = dict(recs)
    head = d["dept:sub4_kl_lsg:b060100:1"]
    assert (head["name"], head["post"], head["level"], head["phone"], head["office_phone"], head["office_email"]) == \
        ("Nissar C A", "Block Development Officer (Secretary, Block Panchayat)", "block", "9447825988", "04864222671",
         "bdoadimali@gmail.com")
    assert head["src_pos"] == {"table": 1, "row": 2} and head["src_url"] == staff_url and head["district_code"] == "556"
    jbdo = d["dept:sub4_kl_lsg:b060100:2"]
    assert (jbdo["post"], jbdo["section"], jbdo["joined"]) == ("JBDO (EGS)", "MGNREGA", "03.02.2025")
    staff = [x for x in d.values() if x["kind"] == "staff"]
    assert len(staff) == 29 and sum(1 for x in staff if x.get("is_head")) == 1
    subs = [x for x in d.values() if x["kind"] == "office_under_body"]
    assert len(subs) == 11 and subs[0]["post"] == "CHC Chithirapuram" and subs[0]["level"] == "office"


def test_sub4_kl_gp_cards_and_vacant():
    m = mod("sub4_kl_lsg")
    p = m.body_item("Adat Grama Panchayat", "G080601", "http://adatpanchayat.lsgkerala.gov.in/")["payload"]
    get = fake_get({p["url"]: "sub4/kl_g080601_home.html", f"{GP}/en/page/staff-details": "sub4/kl_g080601_staff.html",
                    f"{GP}/en/emails": "sub4/kl_g080601_emails.html"})
    recs, files, why = m.fetch(p, get)
    d = dict(recs)
    head = d["dept:sub4_kl_lsg:g080601:1"]
    assert (head["name"], head["post"], head["level"], head["phone"], head["section"], head["src_pos"]) == \
        ("Lima P S", "Panchayat Secretary", "gram_panchayat", "9496046075", "SEC", {"card": 1})
    vac = d["dept:sub4_kl_lsg:g080601:19"]
    assert vac.get("name") is None and vac["vacant"] is True and vac["post"] == "Junior Health Inspector"
    assert sum(1 for x in d.values() if x["kind"] == "staff") == 23


def test_sub4_kl_gp_emoji_headers_and_empty_page():
    m = mod("sub4_kl_lsg")
    pp = m.people((DATA / "sub4" / "kl_g060101_staff.html").read_text())
    assert len(pp) == 20 and pp[0][0]["name"] == "Nandakumar R" and pp[0][0]["designation"] == "Secretary"
    assert m.people((DATA / "sub4" / "kl_b070200_staff.html").read_text()) == []
    # no staff rows: the office block alone gives the Secretary (office) record
    p = m.body_item("Alangad Block Panchayat", "B070200", "http://alangadblockpanchayat.lsgkerala.gov.in/")["payload"]
    recs = m.build(p, [], {"phone": "0484 2603020", "email": "bdo@x.in"}, [], "https://alangadblockpanchayat.lsgkerala.gov.in/en/emails")
    assert [r for r, _ in recs] == ["dept:sub4_kl_lsg:b070200:office"] and recs[0][1]["district"] == "Ernakulam"


def test_sub4_kl_staff_links_skip_implementing_officers():
    m = mod("sub4_kl_lsg")
    html = ('<a href="/en/node/39">നിർവ്വഹണ ഉദ്യോഗസ്ഥർ</a><a href="/en/node/44">ജീവനക്കാർ</a>'
            '<a href="/en/page/implementing-officers">Implementing Officers</a><a href="https://other.in/staff">Staff</a>')
    assert m.staff_links(html, "https://x.lsgkerala.gov.in/en", "x.lsgkerala.gov.in") == ["https://x.lsgkerala.gov.in/en/node/44"]
