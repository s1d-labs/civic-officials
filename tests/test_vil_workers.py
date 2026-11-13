"""Offline tests of the village-worker readers (dforms/_vilwork.py, vil_kl_asha, vil_s3waas_workers, vil_mn_awc) on saved
copies in tests/data/vil_*: archive.s1d.me copies (Siaha pages, Manipur AWC PDF cut to pages 1, 150 and 332) and pages of
Kerala local body sites fetched once on 2026-11-13. No test touches the network."""
import collections
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod
from dforms import _vilwork


def check(recs, module):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids))
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:")
        assert d["type"] == "dept_office" and d["layer"] == "village_worker" and d["level"] in ("village", "section")
        assert d["dept"] in ("health", "women_child", "police") and d.get("source") and d.get("state") and d.get("post")
        assert d.get("name") or d.get("phone")
        assert d.get("src_pos") and d.get("src_url")


def test_roles():
    r = _vilwork.role_of
    assert r("Name of the ANM") == ("person", ("ANM", "health", "village"))
    assert r("Name of the ASHA")[1][0] == "ASHA"
    assert r("Name of Anganwadi Centre")[0] == "centre"
    assert r("Name of Anganwadi Worker")[1][0] == "Anganwadi Worker"
    assert r("Anganwadi Helper Name")[1][0] == "Anganwadi Helper"
    assert r("Name & Mobile No. of MO")[0] == "doctor"
    assert r("Mobile No.")[0] == "phone" and r("Phone Number")[0] == "phone"
    assert r("Village Name")[0] == "village" and r("Ward No")[0] == "ward_no" and r("CHC/PHC")[0] == "centre"
    assert r("Name") == ("person", None) and r("S.No")[0] == "sno"


def test_siaha_health_two_posts_per_row():
    url = "https://siaha.nic.in/health-dept/"
    recs, files, why = mod("vil_s3waas_workers").fetch({"url": url, "state": "MZ", "district": "Siaha"},
                                                      fake_get({url: "vil_siaha_health.html"}))
    assert why == "" and files[0][0].startswith("depts/vil_s3waas_workers/")
    check(recs, "vil_s3waas_workers")
    c = collections.Counter(d["post"] for _, d in recs)
    assert c == {"ASHA": 75, "ANM": 34}
    d = dict(recs)["dept:vil_s3waas_workers:siaha.nic.in:health-dept:t5-r2:asha"]
    assert (d["name"], d["phone"], d["village"], d["centre"]) == ("LC Sozi", "8413017646", "Tuisumpui", "Siaha Main Centre")
    a = dict(recs)["dept:vil_s3waas_workers:siaha.nic.in:health-dept:t5-r2:anm"]
    assert (a["name"], a["phone"]) == ("B.Thangpuia", "8794688060")
    assert all("MO" not in d["post"] for _, d in recs)      # the doctor column is not a village post


def test_siaha_anganwadi():
    url = "https://siaha.nic.in/list-of-anganwadi-workers-centres/"
    recs, _, why = mod("vil_s3waas_workers").fetch({"url": url, "state": "MZ", "district": "Siaha"},
                                                  fake_get({url: "vil_siaha_aww.html"}))
    assert why == ""
    check(recs, "vil_s3waas_workers")
    assert len(recs) == 115 and {d["post"] for _, d in recs} == {"Anganwadi Worker"}
    assert recs[0][1]["name"] == "Nukhai" and recs[0][1]["centre"] == "Vengpui -I" and recs[0][1]["last_updated"] == "2019-10-23"


def test_kl_asha_follows_menu_link():
    home, page = "https://adatpanchayat.lsgkerala.gov.in/en", "https://adatpanchayat.lsgkerala.gov.in/en/page/asha-workers"
    get = fake_get({home: "vil_kl_adat_home.html", page: "vil_kl_adat_asha.html"})
    recs, files, why = mod("vil_kl_asha").fetch({"url": home, "state": "KL", "body": "Adat", "local_body_code": "221553",
                                                 "district": "Thrissur"}, get)
    assert why == "" and len(files) == 2
    check(recs, "vil_kl_asha")
    assert len(recs) == 23 and {d["post"] for _, d in recs} == {"ASHA"}
    d = recs[0][1]
    assert (d["name"], d["phone"], d["ward_no"], d["area"], d["body"]) == ("Liji T P", "9349154730", "1", "Ward 1", "Adat")
    assert d["dept"] == "health" and d["local_body_code"] == "221553"


def test_kl_asha_layouts():
    v = mod("vil_kl_asha")
    a = v.parse((DATA / "vil_kl_adimaly_asha.html").read_text(), "https://adimalypanchayat.lsgkerala.gov.in/en/page/asha-workers-list", {})
    assert len(a) == 42 and a[0][1]["centre"] == "Deviyarcolony" and a[0][1]["caption"] == "ASHA DETAILS OF FHC DEVIYAR COLONY"
    k = v.parse((DATA / "vil_kl_akathethara_asha.html").read_text(),
                "https://akathetharapanchayat.lsgkerala.gov.in/en/page/asha-worker-details", {})
    assert len(k) == 19 and k[-1][1]["name"] == "Ambika" and k[-1][1]["phone"] == "7034692299"


def test_kl_asha_no_page():
    home = "https://x.lsgkerala.gov.in/en"
    recs, files, why = mod("vil_kl_asha").fetch({"url": home}, fake_get({home: "vil_siaha_aww.html"}))
    assert recs == [] and why == "no ASHA page"
    assert mod("vil_kl_asha").fetch({"url": home}, fake_get({}))[2] == "no site"


def test_mn_awc_pdf():
    url = "https://socialwelfare.mn.gov.in/media/filer_public/c9/fa/c9fa4864-496d-4c94-bf18-03e62a839874/awc_in_manipur.pdf"
    recs, files, why = mod("vil_mn_awc").fetch({"url": url, "state": "MN"}, fake_get({url: "vil_mn_awc_cut.pdf"}))
    assert why == "" and files[0][0] == "depts/vil_mn_awc/awc_in_manipur.pdf.gz"
    check(recs, "vil_mn_awc")
    c = collections.Counter(d["post"] for _, d in recs)
    assert c == {"Anganwadi Worker": 70, "Anganwadi Helper": 66}       # 4 helper cells read "Vacant"
    d = dict(recs)
    w = d["dept:vil_mn_awc:14252010101:aww"]
    assert (w["name"], w["area"], w["project"], w["district"]) == ("Langpoklakpam Modhubala Devi", "Langpok Mamang Leikai",
                                                                   "Bishnupur", "Bishnupur")
    assert w["src_pos"]["page"] == 1 and "14252010101" in w["src_pos"]["line_text"]
    assert d["dept:vil_mn_awc:14717050435:awh"]["name"] == "Ramreila Konghar"
    assert not any(x.get("split_unsure") for x in d.values())


def test_mn_awc_split_pypdf_spacing():
    v = mod("vil_mn_awc")
    line = ("5231  Imphal West            Imphal West-01              Tera Lukram Leirak Makha                          "
            "14256011901      Nameirakpam Pyari Devi                Khuraijam  Sunita Devi")
    (r,) = v.rows(line)
    assert r[1:7] == ("Imphal West", "Imphal West-01", "Tera Lukram Leirak Makha", "14256011901", "Nameirakpam Pyari Devi",
                      "Khuraijam  Sunita Devi") and r[7]


def test_vil_seeds():
    for f in ("dept_vil_kl_asha.json", "dept_vil_s3waas_workers.json", "dept_vil_mn_awc.json"):
        items = json.loads((ROOT / "seeds" / f).read_text())
        keys = [i["key"] for i in items]
        assert items and len(keys) == len(set(keys))
        for i in items:
            p = i["payload"]
            assert p["reader"].startswith("vil_") and p["url"].startswith("https://") and p["state"] and p["route"]
            mod(p["reader"])
    assert len(json.loads((ROOT / "seeds" / "dept_vil_kl_asha.json").read_text())) > 1000
