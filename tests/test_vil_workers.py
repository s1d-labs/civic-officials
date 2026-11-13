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
        assert d["type"] == "dept_office" and d["layer"] == "village_worker" and d["level"] in ("village", "section", "ward")
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
    for f in ("dept_vil_kl_asha.json", "dept_vil_s3waas_workers.json", "dept_vil_mn_awc.json", "dept_vil_uk_ddmp.json"):
        items = json.loads((ROOT / "seeds" / f).read_text())
        keys = [i["key"] for i in items]
        assert items and len(keys) == len(set(keys))
        for i in items:
            p = i["payload"]
            assert p["reader"].startswith("vil_") and p["url"].startswith("https://") and p["state"] and p["route"]
            mod(p["reader"])
    assert len(json.loads((ROOT / "seeds" / "dept_vil_kl_asha.json").read_text())) > 1000


UK = "https://cdn.s3waas.gov.in/s3f770b62bc8f42a0b66751fe636fc6eb0/uploads/2021/06/"


def uk(fmt, name):
    url = UK + name
    recs, files, why = mod("vil_uk_ddmp").fetch({"url": url, "format": fmt, "state": "UK"}, fake_get({url: f"vil_uk_ddmp_{fmt}.pdf"}))
    assert why == "" and files[0][0] == f"depts/vil_uk_ddmp/dehradun-{fmt}.pdf.gz"
    check(recs, "vil_uk_ddmp")
    return dict(recs)


def test_uk_aww_page1():
    d = uk("aww", "2021060969.pdf")
    assert collections.Counter(x["post"] for x in d.values()) == {"Anganwadi Worker": 26, "Anganwadi Helper": 17}
    w = d["dept:vil_uk_ddmp:aww:kalsi-1"]
    assert (w["name"], w["phone"], w["area"], w["awc_type"], w["project"], w["district_code"]) == (
        "kastura", "8755663467", "koti parihar", "Mini AWC", "Kalsi", "05060")
    assert not any(x.get("split_unsure") for x in d.values())


def test_uk_asha_ward_carried():
    d = uk("asha", "2021060975.pdf")
    assert len(d) == 49 and {x["post"] for x in d.values()} == {"ASHA"}
    m = d["dept:vil_uk_ddmp:asha:2"]
    assert (m["name"], m["phone"], m["ward_no"], m["area"], m["level"]) == ("Meena", "9411138943", "1", "Ward 1 Malsi", "ward")


def test_uk_gram_prahari_krutidev():
    d = uk("prahari", "2021060974.pdf")
    assert len(d) == 66 and {x["dept"] for x in d.values()} == {"police"}
    t = d["dept:vil_uk_ddmp:prahari:s1:1"]
    assert (t["name"], t["phone"], t["age"], t["tehsil"]) == ("श्री टीकम सिंह", "9805272602", "40", "त्यूनी")
    assert t["src_pos"]["page"] == 1 and "9805272602" in t["src_pos"]["line_text"]


def test_mn_awc_full_file_every_row():
    """The whole awc_in_manipur.pdf (332 pages, sha256 1267564c..., bucket civic-officials-depts/depts/vil_mn_awc/), as pypdf
    layout text (the engine the GitHub runners use). Serials 1-11,585, one AWC code each. Before 2026-11-13 the reader left
    out 201 rows without a word: a long AWC name that wraps (code and names on the next line), and a name that runs into the
    code ("Ward No.1114252011018", "Maning14252011611"): 11,384 rows / 20,658 records -> 11,585 / 21,034."""
    import gzip
    import provenance
    v = mod("vil_mn_awc")
    text = gzip.decompress((DATA / "vil_mn_awc_full_pypdf.txt.gz").read_bytes()).decode("utf-8")
    provenance.rows_reset()
    rows = v.rows(text)
    assert len(rows) == 11585 and sorted(int(r[0]) for r in rows) == list(range(1, 11586))
    assert len({r[4] for r in rows}) == 11585
    assert provenance.rows().get("rows_skipped") == {}          # no line with a digit is left out
    people = sum(1 for r in rows for nm in (r[5], r[6]) if v._esw.clean(nm) and not v.VACANT.match(v._esw.clean(nm)))
    assert people == 21034
    by = {r[0]: r for r in rows}
    assert by["138"][3:7] == ("Maibam Chingmang Mamang Khongnang Makhong", "14252010605", "Kongkham Sanahanbi Devi",
                              "Thounaojam Premila Devi")               # wrapped AWC name
    assert by["258"][3:5] == ("Bishnupur thiyam mamang Leikai Ward No.11", "14252011018")    # "No.11" + code glued
    assert by["394"][3:6] == ("Ningthoukhong Awang Khunou Maning Ward no 1(B)", "14252011521", "Laishram Ongbi Manorama Devi")
    assert by["8895"][3:5] == ("Kakching Wairi Khongnang Lamteiba Pareng 37 by 7", "14711010205")
    assert "Ward No.1114252011018" in by["258"][10]                    # line_text stays as the file writes it
