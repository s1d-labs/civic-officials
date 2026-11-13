"""Offline tests of dforms/vil_kl_s3waas.py (Kerala village offices and grama panchayat secretaries on the district portals).
Samples in tests/data/vil_kl_*.html: archive.s1d.me copies (2026-11-05 .. 11-11), scripts / header / footer cut out.
No test touches the network."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod

M = mod("vil_kl_s3waas")


def run(name, district, kind="village_office", url=None):
    url = url or f"https://{name}.nic.in/en/villages/"
    recs, files, why = M.fetch({"url": url, "district": district, "kind": kind}, fake_get({url: f"vil_kl_{name}.html"}))
    assert why == "" and files and files[0][0].startswith("depts/vil_kl_s3waas/"), why
    check_records(recs, "vil_kl_s3waas", "rural_development" if kind == "gram_panchayat" else "revenue")
    return {d["area"]: d for _, d in recs if d["post"] != "Grama Panchayat President"}, recs


def test_alappuzha_office_and_officer_numbers():
    v, recs = run("alappuzha", "Alappuzha")
    assert len(recs) == 93
    d = v["Arookkutti"]
    assert (d["phone"], d["phone_mobile"], d["phone_office"], d["post"], d["level"], d["state"]) == (
        "8547612218, 04782187138", "8547612218", "04782187138", "Village Officer", "village", "KL")
    assert d["taluk"] == "Cherthala"          # taluk from the heading above the table
    assert v["Alappuzha West"]["taluk"] == "Ambalappuzha"
    assert d["src_pos"]["table"] >= 1 and d["src_pos"]["cells"][1] == "Arookkutti"


def test_kollam_village_officer_rows_only():
    v, _ = run("kollam", "Kollam", url="https://kollam.nic.in/en/revenue-officers/")
    assert len(v) == 104 and "Kollam West" in v and not any("Tahsildar" in a for a in v)
    assert (v["Kollam West"]["phone"], v["Kollam West"]["taluk"]) == ("8547610502", "Kollam")


def test_thrissur_taluk_by_table_order_and_email():
    v, recs = run("thrissur", "Thrissur", url="https://thrissur.nic.in/en/villages-255/")
    assert len(recs) == 255             # 3 village names repeat in two taluks
    d = v["Edathiruthy"]
    assert (d["phone"], d["email"], d["taluk"]) == ("8547614202", "votsr.edty@kerala.gov.in", "Kodungaloor")


def test_trivandrum_taluk_column():
    v, _ = run("trivandrum", "Thiruvananthapuram")
    d = v["Andoorkonam"]
    assert (d["taluk"], d["phone_mobile"], d["phone_office"]) == ("Thiruvananthapuram", "8547610120", "0471-2755944")


def test_wayanad_office_name_and_kozhikode():
    v, _ = run("wayanad", "Wayanad", url="https://wayanad.gov.in/en/village-panchayats/")
    assert len(v) == 49 and v["Nenmeni Village"]["email"] == "cru.nenmeni@kerala.gov.in"
    v, _ = run("kozhikode", "Kozhikode")
    assert v["BEYPORE"]["email"] == "vo-beypore.rev@kerala.gov.in" and v["BEYPORE"]["taluk"] == "Kozhikode"


def test_kasaragod_gp_secretary_and_president():
    v, recs = run("kasargod_gp", "Kasaragod", kind="gram_panchayat", url="https://kasargod.nic.in/en/village-panchayats/")
    d = v["Ajanur Grama Panchayat"]
    assert (d["post"], d["level"], d["phone"], d["email"]) == (
        "Grama Panchayat Secretary", "gram_panchayat", "9496049745, 04672266386", "secajanurgp@gmail.com")
    pres = [x for _, x in recs if x["post"] == "Grama Panchayat President" and x["area"] == "Ajanur Grama Panchayat"]
    assert pres and pres[0]["phone"] == "9496049744" and pres[0]["kind"] == "elected"


def test_seed():
    items = json.loads((ROOT / "seeds" / "dept_vil_kl_s3waas.json").read_text())
    assert len(items) == 11 and len({i["key"] for i in items}) == 11
    for i in items:
        p = i["payload"]
        assert p["reader"] == "vil_kl_s3waas" and p["state"] == "KL" and p["kind"] in ("village_office", "gram_panchayat")
