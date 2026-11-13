"""cforms/pri_gj.py: Gujarat district / taluka / gram panchayat elected members from the district panchayat portals
(fixtures: archive.s1d.me copies 2026-11-05..11 and live pages 2026-11-13, tests/data/pri_gj/)."""
import json
import re
from pathlib import Path

from cforms import pri_gj

D = Path(__file__).parent / "data" / "pri_gj"
SEEDS = Path(__file__).parents[1] / "seeds" / "pri_gj.json"
MAHI = {"host": "mahisagardp.gujarat.gov.in", "district": "Mahisagar", "lgd_code": "274435"}
MAHI_T = ["Balasinor", "Kadana", "Khanpur", "Lunawada", "Santrampur", "Virpur"]


def page(name):
    return (D / name).read_text(encoding="utf-8")


class R:
    def __init__(self, body):
        self.content = body.encode("utf-8") if isinstance(body, str) else body


def test_taluka_members_seat_and_lgd():
    recs = pri_gj.table_records(page("mahisagar_balasinor_member_list.html"),
                                "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/member-list", MAHI, "x", pri_gj.Ids(), MAHI_T)
    assert len(recs) == 18 and all(d["level"] == "ps" and d["lgd_code"] == "4518" for _, d in recs)
    rid, d = recs[0]
    assert rid == "pri:GJ:ps:4518:w1-dp" and d["type"] == "pri_member" and d["ward_no"] == "1" and d["ward_name"] == "ભાંથલા"
    assert d["name"] == "ભારતીબેન ભવાનસિંહ સોલંકી" and d["phone"] == "7359380117" and d["post"] == "Member"
    assert d["src_pos"] == {"table": 1, "row": 2} and d["src_url"].endswith("/member-list") and d["cells"]


def test_sarpanch_list_maps_gram_panchayats():
    recs = pri_gj.table_records(page("mahisagar_balasinor_sarpanch.html"),
                                "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/Sarpanch-Details", MAHI, "x", pri_gj.Ids(), MAHI_T)
    assert len(recs) == 44 and all(d["level"] == "gp" and d["post"] == "Sarpanch" and d["head"] for _, d in recs)
    assert sum(1 for _, d in recs if d["lgd_code"]) >= 40
    rid, d = recs[0]
    assert rid == "pri:GJ:gp:160591:head-dp" and d["body"] == "જોરાપુરા" and d["block"] == "Balasinor" and d["ps_lgd_code"] == "4518"
    assert len({r for r, _ in recs}) == 44


def test_district_heads_and_english_sarpanch_table():
    tapi = {"host": "tapidp.gujarat.gov.in", "district": "Tapi", "lgd_code": "585"}
    recs = dict(pri_gj.table_records(page("tapi_president_members.html"),
                                     "https://tapidp.gujarat.gov.in/gu/President-Vice-President-Members", tapi, "x", pri_gj.Ids(), []))
    assert len(recs) == 26
    assert recs["pri:GJ:zp:585:head-dp"]["post"] == "President" and recs["pri:GJ:zp:585:head-dp"]["phone"] == "9316227724"
    assert recs["pri:GJ:zp:585:vice-dp"]["head_rank"] == 2
    dang = {"host": "dangdp.gujarat.gov.in", "district": "Dangs", "lgd_code": "403"}
    s = pri_gj.table_records(page("dang_sarpanch.html"), "https://dangdp.gujarat.gov.in/gu/Gram-Panchayat-Information-of-sarpanch",
                             dang, "x", pri_gj.Ids(), ["Ahwa", "Subir", "Waghai"])
    assert len(s) == 70 and s[0][1]["name"] == "REKHABEN JITESHBHAI PATEL" and s[0][1]["phone"] == "9913199094"
    assert "9426993365" not in json.dumps([d.get("phone") for _, d in s])      # the TCM's mobile is not the sarpanch's


def test_gujarati_digits_president_row():
    arv = {"host": "arvallidp.gujarat.gov.in", "district": "Arvalli", "lgd_code": "274433"}
    recs = dict(pri_gj.table_records(page("arvalli_bayad_members.html"), "https://arvallidp.gujarat.gov.in/gu/taluka/Bayad/list-of-members",
                                     arv, "x", pri_gj.Ids(), ["Bayad"]))
    d = recs["pri:GJ:ps:4581:head-dp"]
    assert d["phone"] == "9408591969" and d["ward_no"] == "21" and d["post_regional"] == "પ્રમુખ"
    assert recs["pri:GJ:ps:4581:w11-dp"]["post"] == "Chairman, Executive Committee"


def test_full_sarpanch_page_keys_apart_from_egramswaraj():
    """Kadana Sarpanch-Details, the full saved page (bucket copy b199e3b1..., 2026-11-13): 46 sarpanch rows, 46 records. Before,
    37 of them had the plain eGramSwaraj ids (pri:GJ:gp:<LGD>:head) and the later eGramSwaraj run replaced them: 9 were left."""
    import gzip
    html = gzip.decompress((D / "mahisagar_kadana_sarpanch_full.html.gz").read_bytes()).decode("utf-8")
    recs = pri_gj.table_records(html, "https://mahisagardp.gujarat.gov.in/gu/taluka/Kadana/Sarpanch-Details", MAHI, "x",
                                pri_gj.Ids(), MAHI_T)
    ids = [r for r, _ in recs]
    assert len(recs) == 46 and len(set(ids)) == 46 and all(d["phone"] for _, d in recs)
    coded = [r for r, d in recs if d["lgd_code"]]
    assert len(coded) == 37 and all(r.endswith(":head-dp") for r in coded)
    assert {r for r, d in recs if not d["lgd_code"]} == {r for r in ids if "~" in r}
    d = dict(recs)["pri:GJ:gp:162459:head-dp"]
    assert d["name"] == "મહેન્દ્રકુમાર વ્રજલાલ દરજી" and d["phone"] == "7621940965"


def test_about_president_box():
    anand = {"host": "ananddp.gujarat.gov.in", "district": "Anand", "lgd_code": "399"}
    (rid, d), = pri_gj.president_records(page("anand_about_president.html"), "https://ananddp.gujarat.gov.in/gu/About-President",
                                         anand, pri_gj.Ids(), [])
    assert rid == "pri:GJ:zp:399:head-p" and d["name"] == "જીલુભા પી. સિંધા" and d["phone"] == "9725027701"
    assert d["email"] == "pramukhdpanand@gmail.com" and d["phone_office"] == "02692-263092"


def test_fetch_one_district_with_fake_site():
    pages = {
        "https://mahisagardp.gujarat.gov.in/": page("mahisagar_home.html"),
        "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/home": page("mahisagar_balasinor_home.html"),
        "https://mahisagardp.gujarat.gov.in/gu/Information-of-office-bearers": page("mahisagar_office_bearers.html"),
        "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/member-list": page("mahisagar_balasinor_member_list.html"),
        "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/Sarpanch-Details": page("mahisagar_balasinor_sarpanch.html"),
        "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/About-President": page("mahisagar_balasinor_president.html"),
        "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/About-President/1019": page("mahisagar_balasinor_president.html"),
        "https://panchayat.gujarat.gov.in/mahisagar/documents/sarpanch%20details.pdf": b"%PDF-1.4 test",
    }
    asked = []

    def get(url, method="GET", data=None, headers=None):
        asked.append(url)
        return R(pages[url]) if url in pages else None
    items = json.loads(SEEDS.read_text())
    p = next(i["payload"] for i in items if i["key"] == "pri_gj:mahisagardp")
    recs, files, why = pri_gj.fetch(p, get)
    assert why == ""
    kinds = {}
    for _, d in recs:
        kinds[d.get("level") or d["type"]] = kinds.get(d.get("level") or d["type"], 0) + 1
    assert kinds == {"zp": 28, "ps": 19, "gp": 44, "source_file": 1}, kinds
    assert "https://mahisagardp.gujarat.gov.in/gu/taluka/Kadana/home" in asked       # every taluka is tried (no answer here)
    assert any(f[0].endswith(".pdf") for f in files) and len({r for r, _ in recs}) == len(recs)
    asked.clear()
    recs, _, why = pri_gj.fetch(dict(p, talukas=["Balasinor"]), get)       # one taluka only: no district pages, no other talukas
    assert why == "" and {d["level"] for _, d in recs} == {"ps", "gp"}
    assert "https://mahisagardp.gujarat.gov.in/gu/taluka/Kadana/home" not in asked


def test_seeds():
    items = json.loads(SEEDS.read_text())
    assert len(items) == 33 and len({i["key"] for i in items}) == 33
    for i in items:
        p = i["payload"]
        assert p["kind"] == "form-pri_gj" and p["state"] == "GJ" and p["lgd_code"] and p["route"] == "direct"
        assert p["url"] == f"https://{p['host']}/"


def test_full_member_page_keeps_gujarati_digit_in_names():
    """Manasa taluka panchayat members, the full saved page (bucket copy 8a809cd1..., 2026-11-13): 26 rows, 26 records. The
    typist writes ૫ (digit 5) for પ in 11 names ("૫ટેલ"); before, they became "5ટેલ" and did not match the page."""
    import gzip
    html = gzip.decompress((D / "gandhinagar_manasa_members_full.html.gz").read_bytes()).decode("utf-8")
    gnr = {"host": "gandhinagardp.gujarat.gov.in", "district": "Gandhinagar", "lgd_code": "406"}
    recs = pri_gj.table_records(html, "https://gandhinagardp.gujarat.gov.in/gu/taluka/Manasa/taluka-panchayat-manasa-details",
                                gnr, "x", pri_gj.Ids(), ["Manasa"])
    assert len(recs) == 26 and all(d["phone"] for _, d in recs)
    assert sum("૫" in d["name"] for _, d in recs) == 11 and not any(re.search(r"[0-9]", d["name"]) for _, d in recs)
    assert recs[0][1]["name"] == "શ્રીમતી.પ્રિયંકા હિરેનકુમાર ૫ટેલ"


def test_audit_leaves_out_portal_menus():
    """Sabarkantha About-President (full saved page): no table; the 32 menu blocks are left out, the one head is the record."""
    import gzip
    import audit
    body = gzip.decompress((D / "sabarkantha_about_president_full.html.gz").read_bytes())
    src = audit.read_source(body, "text/html", "x.html.gz")
    a = audit.audit_source(src, [("pri:GJ:zp:x:head-p", "x", "", "")], "cforms.pri_gj")
    assert a["rows_left_out"] == 32 and a["rows_visible"] == 0 and a["verdict"] == "not_tabular"
    sab = {"host": "sabarkanthadp.gujarat.gov.in", "district": "Sabarkantha", "lgd_code": "487"}
    assert len(pri_gj.president_records(body.decode("utf-8"), "https://sabarkanthadp.gujarat.gov.in/gu/About-President/1003",
                                        sab, pri_gj.Ids(), [])) == 1
