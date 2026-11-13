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


def test_kl_heads_members_page_adoor():
    from cforms import kl_heads
    p = {"kind": "form-kl_heads", "url": "https://adoormunicipality.lsgkerala.gov.in/en", "body": "Adoor", "code": "M030100",
         "body_type": "Municipality", "district": "Pathanamthitta", "name_list": "Adoor Municipality", "lgd_code": "252262"}
    url = p["url"] + "/members"
    recs = kl_heads.from_members(gz("kl_heads/adoor_members.html.gz"), p, url)
    heads = {k for k in recs if ":head:" in k}
    assert heads == {"councillor:KL:head:M030100:chair", "councillor:KL:head:M030100:vice"}
    # every one of the 29 member cards is also a member record (wards 1-29)
    assert {k for k in recs if ":site:" in k} == {f"councillor:KL:site:M030100:w{i}" for i in range(1, 30)} and len(recs) == 31
    m = recs["councillor:KL:site:M030100:w13"]
    assert m["name"] == "Reena Samuel" and m["position"] == "Councillor" and m["source_kind"] == "body website"
    c = recs["councillor:KL:head:M030100:chair"]
    assert c["name"] == "Reena Samuel" and c["own_ward"] == "13" and c["own_ward_name"] == "Nethaji" and c["ward_no"] == "chair"
    assert c["src_pos"] == {"selector": "div.member-card", "index": 12} and c["url"].endswith("/en/member/6cd6cace-31ad-490c-a02d-689a4402856b")
    v = recs["councillor:KL:head:M030100:vice"]
    assert v["name"] == "Sasikumar D" and v["own_ward"] == "12" and v["position"] == "Vice Chairperson"
    # standing committee chairmen are not heads
    assert kl_heads.post_of("Works Standing Committee Chairman") is None
    assert kl_heads.post_of("Vice Chairperson & Chairman Standing Committee for Finance")[0] == "vice"


def test_kl_heads_keeps_every_member_koyilandy():
    """Koyilandy (quilandymunicipality.lsgkerala.gov.in/en/members, the full saved page): 46 member cards, wards 1-46. No SEC
    member page holds this body (2 records), so before 2026-11-13 the reader kept 2 of 46 people; now 2 heads + 46 members."""
    from cforms import kl_heads
    url = "https://quilandymunicipality.lsgkerala.gov.in/en/members"
    recs = kl_heads.from_members(gz("kl_heads/koyilandy_members.html.gz"), {"code": "M110300", "body": "Koyilandy"}, url)
    members = {k: d for k, d in recs.items() if ":site:" in k}
    assert len(recs) == 48 and len(members) == 46
    assert set(members) == {f"councillor:KL:site:M110300:w{i}" for i in range(1, 47)}
    assert all(d["name"] and d["list_url"] == url and d["position_local"] for d in members.values())


def test_kl_heads_home_page_fallback():
    from cforms import kl_heads
    pala = (DATA / "ulb_kl_pala.html").read_text()
    recs = kl_heads.from_home(pala, {"code": "M050800", "body": "Pala"}, "https://palamunicipality.lsgkerala.gov.in/en")
    assert recs["councillor:KL:head:M050800:chair"]["name"] == "MAYA RAHUL"
    assert recs["councillor:KL:head:M050800:chair"]["phone"] == "9526968579"
    kochi = (DATA / "ulb_kl_kochi.html").read_text()
    recs = kl_heads.from_home(kochi, {"code": "C070100", "body": "Kochi"}, "https://kochicorporation.lsgkerala.gov.in/en")
    assert recs["councillor:KL:head:C070100:mayor"]["name"] == "Adv. Minimol V. K."
    assert recs["councillor:KL:head:C070100:deputy-mayor"]["position"] == "Deputy Mayor"


def test_kl_heads_seeds():
    import json
    items = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_kl_heads.json").read_text())
    assert len(items) == 93 and len({i["payload"]["lgd_code"] for i in items}) == 93
    assert sum(1 for i in items if i["payload"]["code"].startswith("C")) == 6


def test_tg_heads_adilabad():
    from cforms import tg_heads
    url = "https://adilabadmunicipality.telangana.gov.in/pages/chairman-details"
    recs = dict(tg_heads.parse(gz("tg_heads/adilabad_chairman.html.gz"), {"body": "Adilabad", "lgd_code": "248083", "slug": "adilabad"}, url))
    c, v = recs["councillor:TG:head:adilabad:chair"], recs["councillor:TG:head:adilabad:vice"]
    assert (c["name"], c["position"], c["phone"]) == ("ANUSHA BANDARI", "Chairperson", "9951590999")
    assert (v["name"], v["position"], v["phone"]) == ("MOHAMMAD ROHITH", "Vice Chairperson", "8374483733")
    assert c["src_pos"] == {"table": 1, "row": 2} and c["lgd_code"] == "248083"
    assert tg_heads.post_of("Mayor") == ("chair", "Mayor") and tg_heads.post_of("Deputy Mayor") == ("vice", "Deputy Mayor")
    assert len(tg_heads.items()) == 123


def test_ap_heads_mayors_2026():
    from cforms import ap_heads
    bodies = ap_heads.parse_text(gz("ap_heads/mayors_2026.txt.gz"), "Mayor")
    assert len(bodies) == 13 and all(b["elected"] and b["votes_check"] for b in bodies)
    recs = dict(ap_heads.records(bodies, {"post": "Mayor", "url": ap_heads.FILES["Mayor"]}))
    t = recs["councillor:AP:head:tirupati:tirupati"]
    assert t["name"] == "MANNEM SREENIVASSA PRASAD (JB SREENIVAS)" and t["party"] == "TDP" and t["votes"] == 94937
    assert t["position"] == "Mayor" and t["ward_no"] == "chair" and t["direct"] and len(t["candidates"]) == 11
    assert t["src_pos"]["page"] == 1 and "94937" in t["src_pos"]["line_text"]
    k = recs["councillor:AP:head:y-s-r-kadapa:kadapa"]
    assert k["name"] == "MATLI SHUVARNA" and k["poll_date"] == "01.11.2026 & 02.11.2026"
    assert recs["councillor:AP:head:kurnool:kurnool"]["name"] == "BOLLEDDULA VIJAYA PRATHYUSHA"


def test_ap_heads_chairpersons_2026():
    from cforms import ap_heads
    bodies = ap_heads.parse_text(gz("ap_heads/chairpersons_2026.txt.gz"), "Chairperson")
    assert len(bodies) == 86 and all(b["elected"] for b in bodies)
    assert sum(1 for b in bodies if b["unopposed"]) == 17
    assert not [b["body"] for b in bodies if b["votes_check"] is False]
    recs = dict(ap_heads.records(bodies, {"post": "Chairperson", "url": ap_heads.FILES["Chairperson"]}))
    assert recs["councillor:AP:head:ananthapuramu:tadipatri"]["name"] == "YERRAGUDI RESHMA PARVEEN"
    assert recs["councillor:AP:head:prakasam:chimakurthy"]["district"] == "Prakasam"          # not Chirala's wrapped row
    assert recs["councillor:AP:head:dr-b-r-ambedkar-konaseema:amalapuram"]["name"] == "NALLA SRIDHAR"
    assert recs["councillor:AP:head:annamayya:punganur"]["name"] == "P. NAYAUM TEJ"
    assert recs["councillor:AP:head:annamayya:madanapalle"]["name"] == "GUNDLAPALLI SRIRAMA KUMAR@ SRIRAM KUMAR"
    assert [c["name"] for c in recs["councillor:AP:head:nandyal:dhone"]["candidates"]][1] == "CHAITANYA BOAY ALIAS VALLE CHAITANYA"


def test_tn_heads_tiruppur_mayor_in_charge_two_mobiles():
    a = [(tn_heads.search_url("tiruppur", "mayor"), (DATA / "tn_heads/tiruppur_mayor.json").read_text())]
    recs = dict(tn_heads.parse(a, {"site": "tiruppur"}))
    m = recs["councillor:TN:head:tiruppur:mayor"]
    assert m["in_charge"] and m["position_local"] == "Honourable Mayor Incharge" and m["name"] == ".R. Balasubramaniam".lstrip(".")
    assert m["phones"] == ["7305712227", "9363042912"] and m["phone"] == "7305712227"
    assert recs["councillor:TN:head:tiruppur:deputy-mayor"]["name"] == m["name"]
