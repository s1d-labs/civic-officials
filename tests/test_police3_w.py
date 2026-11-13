"""West / central police readers of branch police-sho-w (dforms/police3_cg, police3_gj, police3_mh, police3_ga, police3_tab) on saved
pages (tests/data/police3_*): no network. FakeGet answers each url from a file, as get() does on the pool."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from test_police2n import FakeGet  # noqa: E402

from dforms import police3_cg, police3_ga, police3_gj, police3_mh  # noqa: E402


def by_id(recs):
    return dict(recs)


def test_cg_mahasamund_sections_and_units():
    url = "https://mahasamund.gov.in/en/about-district/administrative-setup/police/"
    get = FakeGet({url: "police3_cg/mahasamund.html"})
    recs, files, why = police3_cg.fetch({"url": url, "district": "Mahasamund"}, get)
    d = by_id(recs)
    assert why == "" and len(recs) == 27 and files
    r = d["dept:police3_cg:mahasamund:thana-tumgaon"]
    assert r["level"] == "police_station" and r["phone"] == "9479192311" and r["subdivision"] == "Mahasamund"
    assert r["src_pos"] == {"table": 0, "row": 3} and r["src_url"] == url
    assert d["dept:police3_cg:mahasamund:chauki-sirpur"]["office_type"] == "police post"
    assert d["dept:police3_cg:mahasamund:control-room"]["office_type"] == "control_room"
    assert d["dept:police3_cg:mahasamund:traffic"]["level"] == "district"
    assert d["dept:police3_cg:mahasamund:ajaak"]["office_type"] == "women"
    assert d["dept:police3_cg:mahasamund:thana-basna"]["subdivision"] == "Saraipali"


def test_cg_bijapur_janjgir_sukma():
    u1 = "https://bijapur.gov.in/en/police/"
    recs, _, _ = police3_cg.fetch({"url": u1, "district": "Bijapur"}, FakeGet({u1: "police3_cg/bijapur.html"}))
    d = by_id(recs)
    assert len(recs) == 21
    assert d["dept:police3_cg:bijapur:gangalur"]["email"] == "sho-gangaloor.cg@gov.in"
    assert d["dept:police3_cg:bijapur:gangalur"]["phone"] == "9479194413"
    u2 = "https://janjgir-champa.gov.in/en/about-district/administrative-setup/police/"
    recs, _, _ = police3_cg.fetch({"url": u2, "district": "Janjgir-Champa"}, FakeGet({u2: "police3_cg/janjgir-champa.html"}))
    d = by_id(recs)
    assert d["dept:police3_cg:janjgir-champa:akaltara"]["pin_code"] == "495552"
    assert d["dept:police3_cg:janjgir-champa:ajk-janjgir-champa"]["office_type"] == "women"
    u3 = "https://sukma.gov.in/en/police/"
    recs, _, _ = police3_cg.fetch({"url": u3, "district": "Sukma"}, FakeGet({u3: "police3_cg/sukma.html"}))
    d = by_id(recs)
    assert d["dept:police3_cg:sukma:sp"]["name"] == "Sunil Sharma" and d["dept:police3_cg:sukma:sp"]["level"] == "district"
    assert len(recs) == 2          # counts ("No. of Thanas") are not offices


def test_gj_ips_register():
    url = police3_gj.URL
    recs, files, why = police3_gj.fetch({"url": url}, FakeGet({url: "police3_gj/ips_cadre_register.html"}))
    d = by_id(recs)
    assert why == "" and len(recs) == 190
    m = d["dept:police3_gj:s-p-morbi"]
    assert m["name"] == "Shri Mukesh Patel" and m["district"] == "Morbi" and m["level"] == "district"
    assert m["phone"] == "9978405975, 02822-243470, 02822-243471" and m["email"] == "sp-morbi@gujarat.gov.in"
    assert m["dob"] == "25-08-1981" and m["pay_level"] == "Level-12" and m["src_pos"] == {"index": 116, "id": "121"}
    sp = {r["district"] for r in d.values() if r["level"] == "district" and r["office_type"] == "office"}
    assert len(sp) == 34                    # every Gujarat district has its SP or CP
    assert d["dept:police3_gj:s-p-aravalli-modasa"]["district"] == "Arvalli"
    assert d["dept:police3_gj:s-p-east-kutch-gandhidham"]["district"] == "Kachchh"
    cp = d["dept:police3_gj:commissioner-of-police-surat-city"]
    assert cp["additional_charge"] is True and cp["district"] == "Surat"
    assert d["dept:police3_gj:d-c-p-zone-7-surat-city"]["level"] == "zone"
    assert d["dept:police3_gj:i-g-p-surat-range-surat"]["level"] == "range"


def test_mh_jalna_tables():
    url = "https://jalnapolice.gov.in/impcon.html"
    recs, _, why = police3_mh.fetch({"url": url, "district": "Jalna"}, FakeGet({url: "police3_mh/jalna_impcon.html"}))
    d = by_id(recs)
    assert why == "" and len(recs) == 40
    r = d["dept:police3_mh:jalna:ambad"]
    assert (r["level"], r["rank"], r["name"], r["phone"]) == ("police_station", "PI", "Shri Santosh Ghodke", "9657478003, 8459610784")
    sp = d["dept:police3_mh:jalna:superintendent-of-police-jalna"]
    assert sp["level"] == "district" and sp["phone"] == "02482-225601" and sp["name"].startswith("Shri Teghbir")
    assert d["dept:police3_mh:jalna:sdpo-ambad"]["level"] == "subdivision"
    assert d["dept:police3_mh:jalna:bharosa-cell"]["office_type"] == "women"
    assert d["dept:police3_mh:jalna:control-room"]["office_type"] == "control_room"
    assert d["dept:police3_mh:jalna:cyber-cell"]["office_type"] == "cyber"


def test_mh_raigad():
    home = police3_mh.RAIGAD
    items = police3_mh.items(FakeGet({home: "police3_mh/raigad_home.html"}))
    assert len(items) == 28 and items[0]["payload"]["contacts"] is True
    url = items[0]["payload"]["url"]
    recs, _, _ = police3_mh.fetch(items[0]["payload"], FakeGet({url: "police3_mh/raigad_alibag.html"}))
    d = by_id(recs)
    st = d["dept:police3_mh:raigad:alibag-police-station"]
    assert st["name"] == "Kishor Popat Sale" and st["rank"] == "Police Inspector" and st["phone"] == "9684706123, 02141-222098"
    assert d["dept:police3_mh:raigad:control-room"]["phone"] == "02141-222100"


def test_ga_phone_directory():
    url = police3_ga.URL
    recs, _, why = police3_ga.fetch({}, FakeGet({url: "police3_ga/phone.html"}))
    d = by_id(recs)
    assert why == "" and len(recs) == 240
    sp = d["dept:police3_ga:superintendent-of-police-north-goa"]
    assert sp["level"] == "district" and sp["district"] == "North Goa" and sp["phone"] == "7875756016, 0832-2416100"
    assert sp["email"] == "spn-pol.goa@nic.in"
    op = d["dept:police3_ga:aldona-outpost-op-mapusa"]
    assert op["office_type"] == "police post" and op["parent_station"] == "Mapusa" and op["phone"] == "0832-2293233"
    tr = d["dept:police3_ga:pi-traffic-cell-margao"]
    assert tr["level"] == "district" and tr["office_type"] == "traffic" and tr["district"] == "South Goa"
