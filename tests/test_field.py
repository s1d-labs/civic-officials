"""Offline tests of the field-official readers (dforms/_field.py, dforms/field_<layer>_<xx>.py) and their seeds
(seeds/dept_field_*.json). Samples in tests/data/field_*: small cuts of the archive.s1d.me copies (HTML) and of the layout text
of sample PDFs (fetched once on 2026-11-11). No test touches the network."""
import json

import pytest

from esw_common import DATA, ROOT, check_records, fake_get, mod
from dforms import _field

MODULES = ["field_health_s3waas", "field_education_s3waas", "field_icds_s3waas", "field_revenue_s3waas", "field_food_s3waas",
           "field_health_tr", "field_food_dl"]


def run(module, url, sample, **payload):
    recs, files, why = mod(module).fetch(dict(url=url, **payload), fake_get({url: sample}))
    assert why == "" and files and files[0][0].startswith(f"depts/{module}/"), why
    return recs


def check_field(recs, module, dept, layer):
    check_records(recs, module, dept)
    for _, d in recs:
        assert d["layer"] == "field" and d["field_layer"] == layer, d
        assert d["level"] in ("state", "district", "subdistrict", "circle", "block", "section", "facility"), d


# ---- the engine ----
def test_header_kinds():
    hk = _field.header_kind
    assert hk("Name of Patwari") == ("name", "Patwari")
    assert hk("Name of Patwar Circle")[0] == "area"
    assert hk("Name of the Incharge Medical Officer/Mid Level Health Provider(MLHP)") == ("name", "Medical Officer")
    assert hk("VAO Contact Number")[0] == "phone"
    assert hk("No. of Anganwadi Centre Sanctioned") == (None, None)
    assert hk("Tehsil/Sub Tehsil")[0] == "tehsil"
    assert hk("Kanungo Circle")[0] == "circle"
    cols, post = _field.header_map(["S.No", "Name of the Block", "Name of AyushmanArogyaMandir", "Govt/ Rented",
                                    "Name of the Incharge Medical Officer/MLHP", "Contact No. of MO/MLHP"])
    assert (cols["name"], cols["area"], cols["phone"], cols["block"], post) == (4, 2, 5, 1, "Medical Officer")
    # the phone column after the name column wins
    cols, post = _field.header_map(["Name Of Kanungo", "Mobile", "Name Of Patwari", "Mobile No."])
    assert (cols["name"], cols["phone"], post) == (2, 3, "Patwari")


def test_name_that_is_a_post():
    assert _field.is_post_text("District Medical & Health Officer (87 PHC's incharge)")
    assert not _field.is_post_text("Dr. K Rajender")


def test_levels():
    assert _field.level_of("health", "PHC Ashtangoo Medical Officer") == "facility"
    assert _field.level_of("health", "Civil Surgeon Office") == "district"
    assert _field.level_of("revenue", "Patwari Halqa Keegam") == "section"
    assert _field.level_of("revenue", "Revenue Inspector Pudukottai firka") == "circle"
    assert _field.level_of("education", "Block Education Officer, Kuchaikote") == "block"
    assert _field.level_of("icds", "CDPO Tufanganj-I") == "block"
    assert _field.level_of("health", "Secretary, Health & Family Welfare Department, Tripura") == "state"


# ---- layer modules on district portal pages ----
def test_health_bandipore():
    u = "https://bandipore.nic.in/health/"
    recs = run("field_health_s3waas", u, "field_health_bandipore.html", state="JK")
    check_field(recs, "field_health_s3waas", "health", "health")
    assert len(recs) == 3
    d = recs[1][1]
    assert (d["area"], d["name"], d["phone"], d["block"], d["post"]) == ("PHC Ashtangoo", "Dr.SaboorSikander", "8899297402",
                                                                         "BANDIPORA", "Medical Officer")
    assert (d["level"], d["last_updated"], d["state"]) == ("facility", "2025-09-27", "JK")


def test_health_buxar_two_tables():
    u = "https://buxar.nic.in/health/"
    recs = run("field_health_s3waas", u, "field_health_buxar.html", state="BR")
    check_field(recs, "field_health_s3waas", "health", "health")
    assert len(recs) == 8
    d = dict(recs)["dept:field_health_s3waas:buxar.nic.in:health:01"]
    assert (d["post"], d["name"], d["phone"], d["area"]) == ("Civil Surgeon", "Dr. Shiv Kumar Prasad", "9470003162",
                                                            "Civil Surgeon Office")
    assert dict(recs)["dept:field_health_s3waas:buxar.nic.in:health:04-b"]["name"] == "Javed Abedi"


def test_revenue_vao_without_names():
    u = "https://perambalur.nic.in/vao-contact-directory/"
    recs = run("field_revenue_s3waas", u, "field_revenue_perambalur_vao.html", state="TN",
               post="Village Administrative Officer")
    check_field(recs, "field_revenue_s3waas", "revenue", "revenue")
    assert [d["area"] for _, d in recs] == ["Esanai", "Alankili Enam Village", "Kezhakarai", "Elambalur", "Sengunam"]
    d = recs[0][1]
    assert (d["phone"], d["post"], d["level"], d.get("name")) == ("9384830749", "Village Administrative Officer", "section", None)


def test_revenue_patwari_shopian():
    u = "https://shopian.nic.in/know-your-patwari/"
    recs = run("field_revenue_s3waas", u, "field_revenue_shopian.html", state="JK")
    check_field(recs, "field_revenue_s3waas", "revenue", "revenue")
    assert [d["post"] for _, d in recs] == ["Office Qanungo", "Girdawar Qanungo", "Patwari", "Patwari"]
    d = recs[3][1]
    assert (d["area"], d["name"], d["phone"], d["tehsil"], d["district"]) == ("Patwari Halqa Keegam", "Arshid Hussain Bhat",
                                                                               "7006784939", "Keegam", "Shopian")


def test_education_gopalganj():
    u = "https://gopalganj.nic.in/education/"
    recs = run("field_education_s3waas", u, "field_education_gopalganj.html", state="BR")
    check_field(recs, "field_education_s3waas", "education", "education")
    by = {d["post"]: d for _, d in recs}
    assert by["Block Education Officer, Kuchaikote"]["name"] == "Shri Ashok Kumar Singh"
    assert by["Block Education Officer, Kuchaikote"]["level"] == "block"
    assert by["District Education Officer"]["level"] == "district"


def test_icds_coochbehar():
    u = "https://coochbehar.gov.in/icds-2/"
    recs = run("field_icds_s3waas", u, "field_icds_coochbehar.html", state="WB")
    check_field(recs, "field_icds_s3waas", "women_child", "icds")
    assert len(recs) == 4
    d = recs[2][1]
    assert (d["area"], d["post"], d["name"], d["phone"], d["level"]) == ("Cooch Behar-II", "CDPO", "Bidur Ch. Roy", "8927800286",
                                                                          "block")


def test_health_tripura():
    u = "http://health.tripura.gov.in/who_is_who"
    recs = run("field_health_tr", u, "field_health_tr.html")
    check_field(recs, "field_health_tr", "health", "health")
    assert recs[0][1]["name"] == "Prof. (Dr.) Manik Saha" and recs[0][1]["state"] == "TR" and recs[0][1]["level"] == "state"


# ---- PDF lists (layout text of the sample files) ----
def pdf_text_records(sample, **payload):
    p = dict(layer_key="revenue", text_layout=True, state="XX", **payload)
    return _field.parse((DATA / sample).read_bytes(), f"https://cdn.example/{sample}", p, "field_revenue_s3waas")


def test_pdf_gurdaspur_three_line_header():
    recs = pdf_text_records("field_revenue_gurdaspur_layout.txt")
    assert len(recs) == 4
    d = recs[0][1]
    assert (d["area"], d["post"], d["name"], d["phone"], d["tehsil"], d["circle"], d["level"]) == (
        "KALA NANGAL", "Patwari", "Munish Gupta", "9888615315", "Gurdaspur", "Gurdaspur", "section")


def test_pdf_hoshiarpur_villages_without_serial():
    recs = pdf_text_records("field_revenue_hoshiarpur_layout.txt")
    assert [d["sub_area"] for _, d in recs] == ["Hoshiarpur", "Chaholi", "Bassi Jana", "Sukhiabaad", "Salwara", "Bassi Khwaju"]
    assert {(d["name"], d["phone"], d["post"]) for _, d in recs} == {("Daljit Singh", "9872133970", "Patwari")}


def test_pdf_thoothukudi_two_tables():
    recs = pdf_text_records("field_revenue_thoothukudi_layout.txt", post="Village Administrative Officer")
    vao = [d for _, d in recs if d["post"] == "Village Administrative Officer"]
    ri = [d for _, d in recs if d["post"] == "Revenue Inspector"]
    assert len(vao) == 5 and len(ri) == 4    # 3 villages have no VAO number: no record
    assert (vao[1]["area"], vao[1]["phone"], vao[1]["tehsil"], vao[1]["circle"]) == ("Melathattaparai", "9791915745",
                                                                                     "Thoothukudi", "Keelathattaparai")
    assert (ri[2]["circle"], ri[2]["phone"], ri[2]["level"]) == ("Pudukottai", "9384095030", "circle")


def test_scanned_pdf_says_ocr():
    class Blank:
        content = b"%PDF-1.4\n%%EOF"
    recs, files, why = mod("field_revenue_s3waas").fetch({"url": "https://cdn.example/a.pdf", "needs_ocr": True},
                                                          lambda *a, **k: Blank())
    assert recs == [] and "OCR" in why and files[0][0].endswith(".pdf.gz")


# ---- Delhi drugs and food safety ----
def test_food_dl_drugs_pincodes():
    u = "https://drugs.delhi.gov.in/drugs/whos-who"
    recs, files, why = mod("field_food_dl").fetch({"url": u, "source": "drugs"}, fake_get({u: "field_food_dl_drugs.html"}))
    check_field(recs, "field_food_dl", "health", "food")
    assert why == "" and len(recs) == 12
    d = recs[0][1]
    assert (d["name"], d["pincodes"], d["licensing_authority"], d["licensing_authority_rank"],
            d["licensing_authority_email"]) == ("Sh. Sanjay Kumar", ["110085", "110089", "110040", "110083"], "Sh. Rohit Bajpai",
                                                "DDC", "dirdcd@nic.in")
    assert recs[3][1]["area"] == "District North-West" and recs[3][1]["level"] == "district"
    assert recs[6][1]["function"] == "Blood Cell" and recs[6][1]["name"] == "Mrs. Yamini Kohli"


def test_food_dl_officials():
    recs = mod("field_food_dl").parse_food((DATA / "field_food_dl_officials_layout.txt").read_text(), "u")
    posts = [d["post"] for _, d in recs]
    assert posts.count("Food Safety Officer") == 10 and posts.count("Designated Officer (Food Safety)") == 3
    assert ("Food Safety Officer", "Isha Kaushik") in [(d["post"], d["name"]) for _, d in recs]
    assert recs[0][1]["last_updated"] == "2026-07-29"


# ---- seeds ----
@pytest.mark.parametrize("module", MODULES)
def test_seeds(module):
    items = mod(module).items()
    keys = [i["key"] for i in items]
    assert items and len(keys) == len(set(keys)) and all(k.startswith("field_") for k in keys)
    for it in items:
        p = it["payload"]
        assert p["reader"] == module and p["url"].startswith("http") and p.get("state"), it
    raw = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    assert raw == items
