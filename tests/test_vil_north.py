"""Offline tests of the north India village-level readers: dforms/vil_rev_north.py (patwari / girdawar / tehsildar revenue
directories of J&K and Haryana district portals, J&K revenue department halqa pages, PDF lists) and dforms/vil_up_gp_contacts.py
(Uttar Pradesh gram panchayat contact lists). Samples in tests/data/vil_*: cuts of the archive.s1d.me copies (tables only) and
the pdftotext layout text of two PDFs fetched once on 2026-11-13. No test touches the network."""
import collections
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod
from dforms import vil_rev_north as rev, vil_up_gp_contacts as gpc

LEVELS = {"village", "circle", "subdistrict", "subdivision", "district"}


def html(name):
    return (DATA / name).read_text(encoding="utf-8")


def counts(recs):
    return collections.Counter(d["level"] for _, d in recs if d["type"] == "dept_office")


def offices(recs):
    return [(r, d) for r, d in recs if d["type"] == "dept_office"]


def test_kathua_cug():
    recs = rev.html_records(html("vil_rev_kathua.html"), "https://kathua.nic.in/revenue-contact-cug/", {"state": "JK", "district": "Kathua"})
    check_records(recs, "vil_rev_north", "revenue")
    c = counts(recs)
    assert len(recs) == 209 and c["village"] == 131 and c["subdistrict"] == 11 and set(c) <= LEVELS
    d = next(d for _, d in recs if d.get("phone") == "9484208518")
    assert (d["name"], d["post"], d["level"], d["area"], d["tehsil"]) == \
        ("Sh. Kulbir Singh", "Patwari", "village", "Patwari Halqua Malhar, Tehsil Lohai Malhar", "Lohai Malhar")
    assert d["src_pos"] == {"table": 1, "row": 13} and d["table_row"]["Designation"] == "Patwari"


def test_kulgam_directory_tables():
    recs = rev.html_records(html("vil_rev_kulgam.html"), "https://kulgam.nic.in/revenue-directory/", {"state": "JK", "district": "Kulgam"})
    check_records(recs, "vil_rev_north", "revenue")
    c = counts(recs)
    assert len(recs) == 104 and c["village"] == 61 and c["circle"] == 31
    d = next(d for _, d in recs if d.get("area") == "PATWARI HALQA AMNOO")
    assert d["post"] == "Patwari" and d["phone"] == "9484218158" and "name" not in d
    dc = next(d for _, d in recs if d["post"] == "Deputy Commissioner")
    assert dc["name"] == "Mr. Shahzad Alam" and dc["level"] == "district"


def test_ramban_name_and_post_in_one_cell():
    recs = rev.html_records(html("vil_rev_ramban.html"), "https://ramban.gov.in/revenue-official-directory/", {"state": "JK"})
    check_records(recs, "vil_rev_north", "revenue")
    assert len(recs) == 92 and counts(recs)["village"] == 50
    d = next(d for _, d in recs if d.get("area") == "Patwar Halqa Sana")
    assert (d["name"], d["post"], d["phone"]) == ("Melap Singh", "Patwari", "9484219153")
    dc = next(d for _, d in recs if d["post"] == "Deputy Commissioner")
    assert dc["name"] == "Sh. Mohammad Alyas Khan" and dc["phone"] == "9484219408"
    v = next(d for _, d in recs if d.get("area") == "Patwar Halqa Shagan")
    assert v["vacant"] is True and "name" not in v


def test_ambala_circles_with_villages_and_roster():
    recs = rev.html_records(html("vil_rev_ambala.html"), "https://ambala.gov.in/revenue/", {"state": "HR", "district": "Ambala"})
    off = offices(recs)
    check_records(off, "vil_rev_north", "revenue")
    roster = [d for _, d in recs if d["type"] == "staff_roster"]
    assert len(off) == 84 and len(roster) == 50
    assert sum(len(d["villages"]) for _, d in off) == 499
    d = next(d for _, d in off if d["area"] == "Anandpur Jalbera")
    assert d["name"] == "Sh. Gurpal Singh" and d["tehsil"] == "Ambala City" and d["level"] == "village"
    assert d["villages"][:2] == [{"village": "Anandpur Jalbera", "hb_no": "121", "area_acre": "1588", "src_pos": {"table": 4, "row": 3}},
                                 {"village": "Rawalan", "hb_no": "171", "area_acre": "410", "src_pos": {"table": 4, "row": 4}}]
    x = next(d for _, d in off if d["area"] == "Pilkhani")
    assert x["name"] == "Sh. Sukhchain Singh" and x["extra_charge"] is True
    r = next(d for d in roster if d.get("area") == "Mohra")
    assert r["post"] == "Patwari" and r["name"].startswith("Mahesh Kumar") and r["table_row"]["Date of Birth/"] == "18/09/1971"


def test_jkrevenue_halqa_phone_only():
    recs = rev.html_records(html("vil_rev_jkrevenue_j.html"), "https://jkrevenue.nic.in/patwarhalqaj.html", {"state": "JK", "post": "Patwari"})
    check_records(recs, "vil_rev_north", "revenue")
    assert len(recs) == 6 and all(d["post"] == "Patwari" and d["level"] == "village" for _, d in recs)
    assert recs[0][1]["area"] == "Sagoon" and recs[0][1]["district"] == "Jammu" and recs[0][1]["address"] == "Panchayat Ghar Sagoon"


def test_samba_and_srinagar_pdf_text():
    url = "https://cdn.s3waas.gov.in/s3a97da629b098b75c294dffdc3e463904/uploads/2022/09/2022090860.pdf"
    recs = rev.text_records((DATA / "vil_rev_samba_layout.txt").read_text(), url,
                            {"state": "JK", "district": "Samba", "columns": ["post", "area", "name"], "page": "https://samba.gov.in/x/"})
    check_records(recs, "vil_rev_north", "revenue")
    assert len(recs) == 93 and counts(recs)["village"] == 54
    d = recs[-1][1]
    assert (d["post"], d["area"], d["name"], d["phone"], d["source"], d["src_url"]) == \
        ("Patwari", "P/H Purmandal (BB)", "Parveen Kumar", "9484221507", "https://samba.gov.in/x/", url)
    assert d["src_pos"]["page"] == 2 and "Parveen Kumar" in d["src_pos"]["line_text"]
    recs = rev.text_records((DATA / "vil_rev_srinagar_layout.txt").read_text(), "https://x/2022091039.pdf",
                            {"state": "JK", "columns": ["district", "post", "area"]})
    check_records(recs, "vil_rev_north", "revenue")
    assert len(recs) == 86 and counts(recs)["village"] == 56
    d = next(d for _, d in recs if d.get("phone") == "9484001471")
    assert (d["area"], d["post"], d["district"], d["level"]) == ("Khonmoh", "Patwari", "Srinagar", "village")


def test_fetch_keeps_file_and_flags_scans():
    url = "https://kathua.nic.in/revenue-contact-cug/"
    recs, files, why = mod("vil_rev_north").fetch({"url": url, "state": "JK"}, fake_get({url: "vil_rev_kathua.html"}))
    assert why == "" and len(recs) == 209 and files[0][0] == "depts/vil_rev_north/kathua.nic.in-revenue-contact-cug.html.gz"
    scan = b"%PDF-1.4\n%%EOF\n"
    get = lambda u, **k: type("A", (), {"content": scan, "text": ""})()   # noqa: E731
    recs, files, why = rev.fetch({"url": "https://cdn.s3waas.gov.in/a/b.pdf", "state": "UP"}, get)
    assert recs == [] and len(files) == 1 and "needs OCR" in why


def test_up_gp_contacts_hathras():
    url = "https://hathras.nic.in/panchayat-sachivgram-pradhan-panchayat-sahayak-rojgar-sewak-ration-dealer-contact-list/"
    recs, files, why = mod("vil_up_gp_contacts").fetch({"url": url, "state": "UP", "district": "Hathras"}, fake_get({url: "vil_up_gp_hathras.html"}))
    assert why == "" and files
    for dept in ("rural_development", "food_supplies"):
        check_records([x for x in recs if x[1]["dept"] == dept], "vil_up_gp_contacts", dept)
    c = collections.Counter(d["role"] for _, d in recs)
    assert len(recs) == 2032 and c["sachiv"] == 462 and c["pradhan"] == 462 and c["rozgar"] == 196
    assert len({(d["block"], d["area"]) for _, d in recs}) == 462 and all(d["level"] == "gram_panchayat" for _, d in recs)
    s = next(d for _, d in recs if d["role"] == "sachiv" and d["area"] == "AMOSI")
    assert (s["name"], s["phone"], s["block"], s["post"], s["src_pos"]) == \
        ("MEENU BAGHEL", "8273574488", "HASAYAN", "Panchayat Secretary (Sachiv)", {"table": 1, "row": 3})
    p = next(d for _, d in recs if d["role"] == "pradhan" and d["area"] == "AMOSI")
    assert p["elected"] is True and p["name"] == "SAROJ DEVI" and p["last_updated"] == "2026-08-04"
    assert not any(d["role"] == "rozgar" and d["area"] == "AMOSI" for _, d in recs)      # "NA" = nobody


def test_seeds():
    for module in ("vil_rev_north", "vil_up_gp_contacts"):
        items = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
        assert items == mod(module).items()
        keys = [i["key"] for i in items]
        assert len(keys) == len(set(keys))
        for i in items:
            p = i["payload"]
            assert p["reader"] == module and p["url"].startswith("https://") and p["state"] and p["route"] in ("abroad", "proxy", "direct")
            assert p["india_only"] == (p["route"] != "abroad")
