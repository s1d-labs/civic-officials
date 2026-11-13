"""Division-level officers for divisions that had none (2026-11-13, seeds/dept_div3_<st>.json): dforms/st_div_pages.py with
"sections" / "keep" / "division_col" on the FULL saved pages (tests/data/st_div_pages/div3/*.html.gz: archive.s1d.me copies of
2026-11-05..11, live copies of 2026-11-13 for rdcsdbmp.nic.in and gad.assam.gov.in), and dforms/st_div_postlist.py on the
layout text of the three posting lists (pdftotext -layout; pypdf layout gave the same records on 2026-11-13)."""
import gzip
import json
from pathlib import Path

import pytest

from dforms import st_div_pages as P
from dforms import st_div_postlist as L

HERE = Path(__file__).resolve().parent
D = HERE / "data" / "st_div_pages" / "div3"
SEEDS = {i["payload"]["key"]: i["payload"] for f in sorted((HERE.parent / "seeds").glob("dept_div3_*.json"))
         for i in json.loads(f.read_text())}


def page(name):
    return gzip.open(D / name, "rt", encoding="utf-8", errors="replace").read()


# seed key -> (saved page, url, exact records, {post: (post_kind, dept)} that must be there)
PAGES = {
    "div3-jh-santhal-pargana": ("jh_dumka_whos_who.html.gz", 3, {
        "Divisional Commissioner S.P. Division Dumka": ("divisional_commissioner", "revenue"),
        "Inspector General of Police, S.P. Division Dumka": ("igp", "police"), "Deputy Inspector General(DIG)": ("dig", "police")}),
    "div3-jh-north-chotanagpur": ("jh_hazaribag_whos_who.html.gz", 1, {
        "Commissioner, North Chotanagpur Division, Hazaribag": ("divisional_commissioner", "revenue")}),
    "div3-jh-palamu": ("jh_palamu_directory.html.gz", 4, {
        "Commissioner Palamu": ("divisional_commissioner", "revenue"), "I.G. Palamu Zone": ("igp", "police"),
        "D.I.G. Palamu Range": ("dig", "police")}),
    "div3-jh-south-chotanagpur": ("jh_ranchi_whos_who.html.gz", 1, {"Divisional Commissioner": ("divisional_commissioner", "revenue")}),
    "div3-br-bhagalpur": ("br_bhagalpur_directory.html.gz", 2, {
        "Commissioner": ("divisional_commissioner", "revenue"), "Inspector General of Police (IG / Range DIG)": ("dig", "police")}),
    "div3-cg-durg": ("cg_durg_whos_who.html.gz", 1, {"Commissioner, Durg Division": ("divisional_commissioner", "revenue")}),
    "div3-cg-raipur": ("cg_raipur_directory.html.gz", 1, {"Commissioner Raipur": ("divisional_commissioner", "revenue")}),
    "div3-pb-ferozepur": ("pb_ferozepur_contact_directory.html.gz", 2, {
        "Divisional Commissioner Ferozepur": ("divisional_commissioner", "revenue"), "D.I.G Ferozepur Range, FZR": ("dig", "police")}),
    "div3-pb-jalandhar": ("pb_jalandhar_whos_who.html.gz", 1, {
        "Commissioner, Jalandhar Division. Jalandhar": ("divisional_commissioner", "revenue")}),
    "div3-pb-jalandhar-range": ("pb_jalandhar_keycontacts.html.gz", 1, {"DIG Jalandhar Range": ("dig", "police")}),
    "div3-pb-faridkot": ("pb_faridkot_division.html.gz", 1, {"Commissioner, Faridkot Division.": ("divisional_commissioner", "revenue")}),
    "div3-hr-ambala": ("hr_ambala_whos_who.html.gz", 1, {"Commissioner Ambala Division": ("divisional_commissioner", "revenue")}),
    "div3-hr-faridabad": ("hr_faridabad_whos_who.html.gz", 1, {
        "Commissioner Faridabad Division": ("divisional_commissioner", "revenue")}),
    "div3-hr-karnal": ("hr_karnal_whos_who.html.gz", 3, {
        "Commissioner, Karnal Division": ("divisional_commissioner", "revenue"),
        "P.A. To Divisional Commissioner, Karnal Division": ("personal_staff", "revenue")}),
    "div3-hr-rohtak": ("hr_rohtak_whos_who.html.gz", 1, {"Commissioner Rohtak Div. Rohtak": ("divisional_commissioner", "revenue")}),
    "div3-hr-gurugram": ("hr_rewari_whos_who.html.gz", 1, {"Commissioner, Gurugram Division": ("divisional_commissioner", "revenue")}),
    "div3-ml-tura": ("ml_westgarohills_directory.html.gz", 1, {"DIG (WR)": ("dig", "police")}),
    "div3-wb-burdwan": ("wb_hooghly_phones.html.gz", 1, {
        "DIVISIONAL COMMISSIONER, BURDWAN DIVISION": ("divisional_commissioner", "revenue")}),
    "div3-od-southern": ("od_rdcsdbmp_whos_who.html.gz", 6, {"Secretary to RDC": ("secretary", "revenue")}),
    "div3-od-southern-rdc": ("od_rdcsdbmp_department_1.html.gz", 1, {
        "Revenue Divisional Commissioner": ("divisional_commissioner", "revenue")}),
    "div3-as-divisions": ("as_gad_divisions.html.gz", 5, {"Commissioner": ("divisional_commissioner", "revenue")}),
    "div3-hp-courts": ("hp_rms_courts.html.gz", 3, {"Divisional Commissioner-Kangra": ("divisional_commissioner", "revenue")}),
}


@pytest.mark.parametrize("key", sorted(PAGES))
def test_division_rows_on_full_page(key):
    p = SEEDS[key]
    name, n, want = PAGES[key]
    recs = P.parse_page(p, page(name), p["urls"][0])
    assert len(recs) == n
    got = {d["post"]: d for _, d in recs}
    for post, (pk, dept) in want.items():
        assert got[post]["post_kind"] == pk and got[post]["dept"] == dept, post
    for rid, d in recs:
        assert rid.startswith(f"dept:st_div_pages:{key}:")
        assert d["level"] == "division" and d["state"] == p["state"] and d["division"] and d["districts"]
        assert d["src_pos"].get("table") and d["cells"] and d["src_url"] == p["urls"][0]
    if p.get("kind") != "police":
        assert any(d["post_kind"] == "divisional_commissioner" for _, d in recs) or key in ("div3-od-southern", "div3-pb-jalandhar-range")


def test_rows_of_one_division_only():
    recs = P.parse_page(SEEDS["div3-jh-santhal-pargana"], page("jh_dumka_whos_who.html.gz"), "https://dumka.nic.in/about-district/whos-who/")
    assert {d["division"] for _, d in recs} == {"Santhal Pargana"}
    assert not any("Deputy Commissioner" in d["post"] for _, d in recs)      # the district's own table is not read
    d = {d["post"]: d for _, d in recs}["Divisional Commissioner S.P. Division Dumka"]
    assert d["name"] == "Sri SHAILENDRA KUMAR LAL" and d["email"] == "divcomm-spddumka@jharkhandmail.gov.in"


def test_palamu_office_phone_and_ig():
    recs = dict(P.parse_page(SEEDS["div3-jh-palamu"], page("jh_palamu_directory.html.gz"), "https://palamu.nic.in/directory/"))
    by = {d["post"]: d for d in recs.values()}
    assert by["Commissioner Palamu"]["phone"] == "06562-230100, 06562-230101, 9431142742"
    assert by["I.G. Palamu Zone"]["name"] == "Sri. Narendra Kumar Singh (IPS)" and by["I.G. Palamu Zone"]["body_kind"] == "police"


def test_assam_every_division_from_one_table():
    recs = P.parse_page(SEEDS["div3-as-divisions"], page("as_gad_divisions.html.gz"), "https://gad.assam.gov.in/divisions")
    by = {d["division"]: d for _, d in recs}
    assert set(by) == {"North Assam", "Lower Assam", "Central Assam", "Upper Assam", "Barak Valley"}
    assert by["Upper Assam"]["name"] == "Shri Siddharth Singh,IAS" and by["Upper Assam"]["phone"].startswith("0376-2360460")
    assert by["Lower Assam"]["email"] == "commr-lad-asm@nic.in" and by["Lower Assam"]["address"] == "Panbazar, Guwahati"
    assert len({tuple(d["districts"]) for d in by.values()}) == 5                # each row its own division's districts


def test_hp_courts_division_from_court_name():
    recs = P.parse_page(SEEDS["div3-hp-courts"], page("hp_rms_courts.html.gz"), "https://rms.hp.gov.in/CourtsList.aspx")
    by = {d["division"]: d for _, d in recs}
    assert set(by) == {"Kangra", "Mandi", "Shimla"}
    assert "Dharamshala" in by["Kangra"]["address"] and not by["Kangra"].get("name")


def test_template_name_and_sample_phone_dropped():
    recs = P.parse_page(SEEDS["div3-od-southern-rdc"], page("od_rdcsdbmp_department_1.html.gz"),
                        "https://rdcsdbmp.nic.in/department/department-1/")
    (_, d), = recs
    assert not d.get("name") and d["phone"] == "0680-2292755" and d["email"] == "rdcbmp@nic.in"


def lst(name):
    return gzip.open(D / name, "rt", encoding="utf-8").read().split("\f")


def test_wb_ias_postings():
    p = SEEDS["div3-wb-ias-postings"]
    pages = lst("wb_ias_postings_06112026.layout.txt.gz")
    assert len(L.entries(pages, p["first_rx"], p.get("break_rx"))) == 282
    recs = L.parse_pages(p, pages)
    assert len(recs) == 6
    head = {d["division"]: d for _, d in recs if d["post_kind"] == "divisional_commissioner"}
    assert set(head) == {"Presidency", "Burdwan", "Medinipur", "Jalpaiguri", "Malda"}
    assert head["Malda"]["name"] == "Dr. Asvini Kumar Yadav" and head["Malda"]["post"] == "Divisional Commissioner, Malda Division"
    assert "additional charge of Divisional Commissioner, Malda Division" in head["Malda"]["designation_full"]
    assert head["Burdwan"]["post"] == "Divisional Commissioner, Bardhaman Division" and head["Burdwan"]["as_on"] == "06.11.2026"
    asst = [d for _, d in recs if d["post"].startswith("Assistant")]
    assert len(asst) == 1 and asst[0]["post_kind"] == "officer"
    rid, d = recs[0]
    assert rid == "dept:st_div_postlist:div3-wb-ias-postings:10:jalpaiguri"
    assert d["src_pos"]["page"] == 1 and d["src_pos"]["entry"] == "10" and "Khalil Ahmed" in d["src_pos"]["line_text"]


def test_gj_ips_civil_list_range_igs():
    p = SEEDS["div3-gj-ips-civil-list"]
    pages = lst("gj_ips_civil_list_2026.layout.txt.gz")
    es = L.entries(pages, p["first_rx"], p["break_rx"])
    assert len(es) == 192 and not [e for e in es if e.get("unread")]
    assert {e["name"] for e in es if e["sno"] in ("45", "66")} == {"Shri Makrand Govindbhai Chauhan", "Shri Rajendrasinh Chudasama"}
    recs = L.parse_pages(p, pages)
    by = {d["division"]: d for _, d in recs}
    assert len(recs) == 9 and len(by) == 9
    r = by["Rajkot Range"]
    assert r["name"] == "Shri Ashok Kumar" and r["post"] == "Inspector General of Police, Rajkot Range"
    assert r["office_phone"] == "0281-2477511" and r["residence_phone"] == "0281-2477522" and r["mobile"] == "9978405368"
    assert r["fax"] == "0281-2474341" and r["email"] == "spigp-raj@gujarat.gov.in" and r["dept"] == "police"
    a = by["Ahmedabad Range"]                       # additional charge; the next officer's phones are not taken
    assert a["name"] == "Ms. Vidhi Choudhary" and a["office_phone"] == "079-25633939" and "23258513" not in a["phone"]
    assert by["Gandhinagar Range"]["post_kind"] == "dig" and by["Panchmahal-Godhra Range"]["districts"]


def test_mh_quarterly_list_amravati_range():
    p = SEEDS["div3-mh-ips-sps-quarterly"]
    recs = L.parse_pages(p, lst("mh_ips_sps_quarterly_06082026.layout.txt.gz"))
    (rid, d), = recs
    assert rid == "dept:st_div_postlist:div3-mh-ips-sps-quarterly:1:amravati-range"
    assert d["post"] == "IGP,Amravati Range" and d["name"] == "Shri Mahesh Patil SPS-IPS (2008)" and d["post_kind"] == "igp"
    assert d["phone"] == "0721-2663226, 0721-2663256" and d["division"] == "Amravati Range" and len(d["districts"]) == 5


def test_seeds_route_and_keys():
    assert len(SEEDS) == 25
    for k, p in SEEDS.items():
        assert p["route"] in ("abroad", "direct") and (p["route"] == "direct") == p["india_only"]
        if p["reader"] == "st_div_pages":
            assert p["all_division"] and p["district_names"]
