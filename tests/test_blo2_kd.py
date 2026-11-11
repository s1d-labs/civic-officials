"""forms/blo2_pdf.py on district BLO lists typed in the legacy Kruti Dev font (UP; hub items that ended with "no rows"):
the text layer has Latin letters, which the reader converts to Devanagari before it looks for the header.
Fixtures in tests/data/blo2/ (pypdf layout text of a few rows each, pages split by form feed; no network):
- up_kheri_139_kd.txt: 139 Gola, Kheri. Station names in Unicode, BLO names and the header in Kruti Dev.
- up_varanasi_388_kd.txt: 388 Varanasi North. All text in Kruti Dev; the header row is an image, so no header text.
- up_meerut_47_kd.txt: 47 Meerut Cantt. Kruti Dev and Mangal mixed in one cell; header on two lines; columns drift."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import blo  # noqa: E402
from forms import blo2_pdf  # noqa: E402

DATA = Path(__file__).parent / "data" / "blo2"


def pages(name):
    return (DATA / name).read_text(encoding="utf-8").split("\f")


def test_cells_convert_word_by_word():
    kd = blo2_pdf.kd_cell
    assert kd("ch0,y0vks0 dk uke@eksa0 u0") == "बी0एल0ओ0 का नाम/मों0 न0"
    assert kd("eksckbZy ua0") == "मोबाईल नं0"
    assert kd("Jherh izHkk vk;kZ] izk0fo0 eSykuh") == "श्रीमती प्रभा आर्या, प्रा0वि0 मैलानी"
    assert kd("47&esjB dSUV") == "47-मेरठ कैन्ट"
    assert kd("dfu’B lgk;d") == "कनिष्ठ सहायक" and kd("fjrs”k ;kno") == "रितेश यादव"
    # Unicode words next to Kruti Dev words: only the Latin words change; "%" in a Unicode cell is not a visarga
    assert kd("Jh ललत कुमार ys[kiky") == "श्री ललत कुमार लेखपाल"
    assert kd("पि$लक % कूल") == "पि$लक % कूल"
    # numbers, upper-case Latin and a few English words stay
    assert kd("8400245760]") == "8400245760,"
    assert kd("F:\\SPECIAL LIST") == "F:\\SPECIAL LIST" and kd("Page 1 of 14") == "Page 1 of 14"


def test_pypdf_sign_slips_are_repaired():
    kd = blo2_pdf.kd_cell
    assert kd("jsu wnsoh") == "रेनू देवी"             # space before a vowel sign
    assert kd("Jh jkosUn zdukSft;k") == "श्री रावेन्द्र कनौजिया"   # space before "z" (्र)
    assert kd("iq\"ik nos h") == "पुष्पा देवी"          # e-sign one letter too far right
    assert kd("foey's k flag") == "विमलेश सिंह"
    assert kd("vunq s'kd") == "अनुदेशक"                # u-sign one letter too far right
    # fields: a field that starts with a vowel sign joins the field before it; a short i "f" at a field end joins the next
    assert blo2_pdf.kd_fields([(0, 3, "j[s"), (5, 11, "kk nos"), (20, 21, "h"), (40, 46, "vk0ok0")]) == [
        (0, 21, "रेखा देवी"), (40, 46, "आ0वा0")]
    assert blo2_pdf.kd_fields([(0, 8, "cktkj f"), (20, 26, "'koiqj")])[-1][2] == "शिवपुर"


def test_kruti_dev_pages_are_found_and_english_pages_are_not():
    for name in ("up_kheri_139_kd.txt", "up_varanasi_388_kd.txt", "up_meerut_47_kd.txt"):
        assert all(blo2_pdf.kd_page(pg) for pg in pages(name)), name
    for name in ("up_gorakhpur_328.txt", "br_muzaffarpur_98.txt", "wb_ddinajpur.txt"):
        assert not any(blo2_pdf.kd_page(pg) for pg in pages(name)), name


def test_kheri_header_names_parts_and_mobiles():
    p = {"state": "UP", "ac_no": 139, "ac_name": "Gola Gokarannath", "district": "Kheri"}
    rows = blo2_pdf.rows_from_pages(pages("up_kheri_139_kd.txt"), p)
    assert [r["part_no"] for r in rows] == list(range(1, 14)) + [24, 25, 26]
    assert all(len(r["blo_phone"]) == 10 for r in rows)
    r = rows[0]
    assert (r["blo_name"], r["designation"], r["blo_phone"]) == ("श्रीमती प्रभा आर्या, प्रा0वि0 मैलानी", "स0अ0", "8808036962")
    assert set(r["cells"]) >= {"बूथ सं0", "मतदेय स्थल का नाम", "बी0एल0ओ0 का नाम/मों0 न0", "पदनाम", "मोबाईल नं0"}
    assert r["station"].startswith("Ĥा०ͪव० न0 पं0 मैलानी")     # Unicode cell kept as the PDF has it
    assert rows[3]["blo_name"].startswith("अर्जुन विश्वकर्मा") and rows[3]["designation"] == "अनुदेशक"
    assert rows[10]["blo_name"] == "श्री रावेन्द्र कनौजिया"
    # part 13: the designation and the mobile start a few columns left of the header; they still go to their columns
    assert (rows[12]["designation"], rows[12]["blo_phone"]) == ("शि0मि0", "7008948753")
    assert rows[-1]["blo_name"] == "मुकेश प्रजापति बिजुआ"
    recs = dict(blo.form_rows(dict(p, kind="form-blo2_pdf"), rows))
    assert len(recs) == len(rows) and "blo:UP:139:24" in recs


def test_varanasi_without_header_text_gets_named_columns():
    p = {"state": "UP", "ac_no": 388, "ac_name": "Varanasi North", "district": "Varanasi"}
    rows = blo2_pdf.rows_from_pages(pages("up_varanasi_388_kd.txt"), p)
    assert len(rows) == 20
    assert all(r["cells"]["_columns"] == blo2_pdf.GUESSED for r in rows)
    assert [r["blo_name"] for r in rows[:15]] == [
        "सुनील कुमार पाण्डेय", "शेख मोहम्मद अजीम", "इन्द्रावती देवी", "रितेश यादव", "मीरा देवी", "सुनीता भारती",
        "पुष्पा देवी", "विन्दू देवी", "हुबलाल", "मनीष कुमार सिंह", "कलावती देवी", "रीता देवी", "कुसुम सिंह",
        "शशिकला सिंह", "अनिता देवी"]
    r = rows[0]
    assert (r["station"], r["designation"], r["blo_phone"]) == (
        "गुरूनानक इग्लिश स्कूल भरलाई शिवपुर क0सं0 1", "शिक्षा मित्र प्रा0वि0 भरलाई", "9129454706")
    assert r["part_no"] == ""            # the part numbers are not in the text layer
    # a second mobile on the line below belongs to the row above, not to the next row
    assert rows[1]["blo_phone"] == "8840347451" and rows[1]["cells"]["Mobile"] == "8840347451 9555213903"
    assert rows[8]["cells"]["Mobile"] == "6306271575 7318189627" and rows[9]["blo_phone"] == "8004272770"
    assert len({r["blo_phone"] for r in rows}) == 20
    recs = dict(blo.form_rows(dict(p, kind="form-blo2_pdf"), rows))
    assert len(recs) == 20                 # ids by row index when there is no part number


def test_meerut_two_line_header_mixed_fonts():
    p = {"state": "UP", "ac_no": 47, "ac_name": "Meerut Cantt", "district": "Meerut"}
    rows = blo2_pdf.rows_from_pages(pages("up_meerut_47_kd.txt"), p)
    head = set().union(*(r["cells"] for r in rows))
    # "मतदेय" above "स्थल सं0", "भवन जिसमे ..." above nothing, "बी0एल0ओ0 का" above "नाम"
    assert {"मतदेय स्थल सं0", "भवन जिसमे यह अवस्थित होगा", "बी0एल0ओ0 का नाम", "पदनाम", "मोबाईल नम्बर"} <= head
    by_part = {r["part_no"]: r for r in rows}
    assert (by_part[10]["blo_name"], by_part[10]["designation"], by_part[10]["blo_phone"]) == (
        "श्री देशपाल वर्मा", "वरिष्ठ सहायक", "9690310957")
    assert by_part[11]["blo_name"] == "श्री अरविन्द कुमार" and by_part[15]["blo_name"] == "महेन्द्र सिंह"
    assert by_part[9]["blo_phone"] == "9759247179"     # not the supervisor's 7599000888 that ends the row
    assert by_part[7]["blo_phone"] == "9557009845"     # "7 | station | क0" and the next line are one row
    assert {1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16} <= set(by_part)


def test_helpers():
    assert blo2_pdf._numbering(["2", "3", "4", "5", "6", "8"]) and blo2_pdf._numbering(["1", "2", "3", "4"])
    assert not blo2_pdf._numbering(["12", "3", "4", "5"])
    head = [(0, 8, "स्थल सं0"), (60, 63, "नाम")]
    assert blo2_pdf._merge_above(head, [(1, 6, "मतदेय"), (11, 37, "भवन"), (54, 67, "बी0एल0ओ0 का")]) == [
        (0, 8, "मतदेय स्थल सं0"), (11, 37, "भवन"), (54, 67, "बी0एल0ओ0 का नाम")]
    assert blo2_pdf._merge_above(head, [(40, 60, "BLO LIST 2024")]) == head     # one field: a title, not a header part
    rows = [{"blo_phone": "7599000888", "cells": {"Mobile": "7599000888", "Supervisor": "x 98765432%02d" % i}}
            for i in range(6)] + [{"blo_phone": "91234567%02d" % i, "cells": {}} for i in range(10)]
    blo2_pdf._shared_phone(rows)
    assert [r["blo_phone"] for r in rows[:2]] == ["9876543200", "9876543201"]


def test_read_converts_a_kruti_dev_pdf(monkeypatch):
    monkeypatch.setattr(blo2_pdf, "pages_of", lambda content: pages("up_kheri_139_kd.txt"))

    class R:
        content = b"%PDF-1.7 test"

        def raise_for_status(self):
            pass

    class S:
        def get(self, url, timeout=None):
            return R()
    p = {"url": "https://cdn.s3waas.gov.in/s3a2557a7b2e94197ff767970b67041697/uploads/2023/08/2023081760.pdf",
         "state": "UP", "ac_no": 139, "district": "Kheri", "kind": "form-blo2_pdf"}
    rows, files, why = blo2_pdf.read(S(), p)
    assert why == "" and len(rows) == 16 and files[0][0] == blo2_pdf.store_path(p)
