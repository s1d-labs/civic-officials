"""sec-new-south readers on saved answers: Tamil Nadu heads (cforms/tn_heads.py, tnurbantree WordPress search answers),
Tamil Nadu casual elections 2022 and Kadambur (cforms/tn_casual.py + cforms/tn_text.py, pdftotext -layout output and district
answers of tnsec.tn.gov.in)."""
import gzip
from pathlib import Path

from cforms import tn_casual, tn_heads, tn_text

DATA = Path(__file__).parent / "data"


def gz(name):
    return gzip.decompress((DATA / name).read_bytes()).decode("utf-8")


def test_tn_heads_coonoor_chair_and_vice():
    a = [(tn_heads.search_url("coonoor", "chair"), (DATA / "tn_heads/coonoor_chair.json").read_text())]
    recs = dict(tn_heads.parse(a, {"site": "coonoor", "name_en": "Coonoor", "lgd_code": "252639"}))
    assert set(recs) == {"councillor:TN:head:coonoor:chair", "councillor:TN:head:coonoor:vice-chair"}
    ch = recs["councillor:TN:head:coonoor:chair"]
    assert ch["name"] == "M. Suseela" and ch["position"] == "Chairperson" and ch["ward_no"] == "chair"
    assert ch["party"] == "DMK" and ch["phone"] == "6369729972" and ch["lgd_code"] == "252639"
    assert ch["src_pos"]["id"] == 1523 and ch["src_pos"]["rows"][0] == {"label": "name", "table": 1, "row": 0}
    assert not ch.get("old_page") and ch["page_modified"].startswith("2026-05-21")
    vc = recs["councillor:TN:head:coonoor:vice-chair"]
    assert vc["name"] == "M. Vasimraja" and vc["phone"] == "9940921212" and vc["position"] == "Vice Chairperson"


def test_tn_heads_avadi_mayor_from_two_searches():
    a = [(tn_heads.search_url("avadi", "chair"), (DATA / "tn_heads/avadi_chair.json").read_text()),
         (tn_heads.search_url("avadi", "mayor"), (DATA / "tn_heads/avadi_mayor.json").read_text())]
    recs = dict(tn_heads.parse(a, {"site": "avadi"}))
    assert set(recs) == {"councillor:TN:head:avadi:mayor", "councillor:TN:head:avadi:deputy-mayor"}
    m = recs["councillor:TN:head:avadi:mayor"]
    assert m["name"] == "G.Udhayakumar" and m["phone"] == "9710086560" and m["email"] == "commr.avadi@tn.gov.in"
    assert m["office_address"].startswith("N.M.Road") and m["position_local"] == "Mayor"
    assert recs["councillor:TN:head:avadi:deputy-mayor"]["name"] == "S.Suryakumar"


def test_tn_heads_titles():
    assert tn_heads.post_of("Deputy Mayor")[0] == "deputy-mayor"
    assert tn_heads.post_of("Vice-Chairman")[0] == "vice-chair"
    assert tn_heads.post_of("Chairperson")[0] == "chair"
    assert tn_heads.post_of("Standing Committee Chairman") is None
    assert tn_heads.post_of("Citizen Charter") is None
    items = tn_heads.items()
    assert len(items) == 154 and all(i["payload"]["kind"] == "form-tn_heads" for i in items)
    assert sum(1 for i in items if i["payload"]["lgd_code"]) == 153


def test_tn_casual_lists_urban_files():
    assert len(tn_casual.districts(gz("tn_casual/rulbe2022.html.gz"))) == 37
    assert tn_casual.files(gz("tn_casual/rulbe2022_kpm.html.gz")) == [("corp", "kpm", "corp_kpm.pdf")]
    assert tn_casual.files(gz("tn_casual/rulbe2022_mdu.html.gz")) == []          # rural files only (puwm, vpp, vpwm)


def test_tn_casual_kanchipuram_ward_36():
    it = tn_casual.item(tn_casual.CASUAL, "corp", "kpm", "காஞ்சிபுரம்", "corp_kpm.pdf", True)
    p = it["payload"]
    assert p["url"].endswith("/rulbe2022/corp_kpm.pdf") and p["bye_election"]
    recs = tn_text.records(tn_text.parse_text(gz("tn_casual/corp_kpm.txt.gz"), p), p)
    assert len(recs) == 1
    rid, d = recs[0]
    assert rid == "councillor:TN:tx:corp-kpm:காஞ்சிபுரம்:36:bye2022"
    assert d["bye_election"] and d["replaces"] == "councillor:TN:tx:corp-kpm:காஞ்சிபுரம்:36"
    assert d["replaces_also"] == "councillor:TN:corp-kpm:காஞ்சிபுரம்:36"
    assert d["party"] == "DMK" and d["votes"] == 1759 and d["election"].startswith("Tamil Nadu urban local bodies casual election 2022")
    assert d["src_pos"]["page"] == 1 and d["src_pos"]["serial"] == "4"


def test_tn_kadambur_all_wards():
    it = tn_casual.item(tn_casual.KADAMBUR, "tp", "tut", "தூத்துக்குடி", "tp_tut.pdf", False)
    p = it["payload"]
    assert "bye_election" not in p and p["url"].endswith("/ulbetp2022/tp_tut.pdf")
    recs = tn_text.records(tn_text.parse_text(gz("tn_casual/tp_tut_kadambur.txt.gz"), p), p)
    assert [d["ward_no"] for _, d in recs] == [str(i) for i in range(1, 13)]
    assert sum(1 for _, d in recs if d["unopposed"]) == 3
    assert all(d["election"].startswith("Tamil Nadu 2022 (Kadambur") for _, d in recs)
    assert recs[2][1]["name"] == "கனகமணி.மா" and recs[2][1]["party"] == "DMK"
