"""cforms/mh.py on the whole saved Pune-division Part I-A supplement of 19 Jan 2026 (bucket copy db6a005f521c..., 48 pages).
The OCR cell texts of pages 27-33 (Tesseract mar, as the runner read them, 2026-11-13) stand in for Tesseract, so the test
needs no OCR; the cell borders and the text layer come from the PDF itself."""
import gzip
import shutil
import json
from pathlib import Path

import pytest

from cforms import gj, mh

DATA = Path(__file__).parent / "data" / "mh_gazette"
PDF = DATA / "pune_div_part1a_20260119.pdf"


def _parse(monkeypatch, first, last):
    cells = json.loads(gzip.decompress((DATA / "sangli_ocr_cells_p27_p33.json.gz").read_bytes()))
    monkeypatch.setattr(gj, "ocr_boxes", lambda pdf, page, boxes, tmp, lang, **k: cells[str(page)])
    p = {"kind": "form-mh", "slug": "sangli-miraj-kupwad-mc", "body": "Sangli-Miraj-Kupwad Municipal Corporation",
         "lgd_code": "251639", "url": "https://egazzete.mahaonline.gov.in/Forms/GazetteSearch.aspx", "first": first, "last": last}
    return mh.parse(str(PDF), p)


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext (poppler) not installed")
def test_sangli_ward_cells_in_brackets(monkeypatch):
    """The ward cell spans its seats and reads "(1) Kupwad, Prakash Nagar ...": no number column, so no ward was found and the
    67 rows of pages 27-32 collapsed into 4 record ids (x-अ .. x-ड): 4 records. Now 17 wards, 67 records; page 33: wards
    18-20, 11 records. 78 = the council's seats."""
    recs = _parse(monkeypatch, 27, 32)
    assert len(recs) == len({rid for rid, _ in recs}) == 67
    wards = {}
    for _, d in recs:
        wards[d["ward_no"]] = wards.get(d["ward_no"], 0) + 1
    assert sorted(wards, key=int) == [str(n) for n in range(1, 18)] and wards["13"] == 3
    d = dict(recs)
    assert d["councillor:MH:sangli-miraj-kupwad-mc:1-अ"]["name"] == "सदामते रविंद्र यशवंत"
    assert d["councillor:MH:sangli-miraj-kupwad-mc:2-ब"]["name"] == "मगदूम गजानन रामू"
    recs = _parse(monkeypatch, 33, 33)
    assert len(recs) == 11 and {d["ward_no"] for _, d in recs} == {"18", "19", "20"}



def _parse_ich(monkeypatch, first, last):
    cells = json.loads(gzip.decompress((DATA / "ichalkaranji_ocr_cells_p10_p16.json.gz").read_bytes()))
    monkeypatch.setattr(gj, "ocr_boxes", lambda pdf, page, boxes, tmp, lang, **k: cells[str(page)])
    p = {"kind": "form-mh", "slug": "ichalkaranji-mc", "body": "Ichalkaranji Municipal Corporation", "lgd_code": "251619",
         "url": "https://egazzete.mahaonline.gov.in/Forms/GazetteSearch.aspx", "first": first, "last": last}
    return mh.parse(str(PDF), p)


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext (poppler) not installed")
def test_ichalkaranji_ward_cells_with_kramank(monkeypatch):
    """Pages 10-16 (OCR cells read here, Tesseract 5.3.4 mar, 2026-11-14): the ward cell reads "प्रभाग क्रमांक १ (अ)", and
    "क्रमांक" is a head word, so every row was taken as a head row: 0 records (items mh-div-ichalkaranji-mc-p10, -p16).
    Now 65 records = 15 wards x 4 seats + ward 16 x 5 seats; the local front "शिव-शाहू विकास आघाडी" is the party."""
    recs = _parse_ich(monkeypatch, 10, 15) + _parse_ich(monkeypatch, 16, 16)
    assert len(recs) == len({rid for rid, _ in recs}) == 65
    wards = {}
    for _, d in recs:
        wards[d["ward_no"]] = wards.get(d["ward_no"], 0) + 1
    assert sorted(wards, key=int) == [str(n) for n in range(1, 17)] and wards["16"] == 5 and wards["1"] == 4
    d = dict(recs)
    a = d["councillor:MH:ichalkaranji-mc:1-अ"]
    assert a["name"] == "लोखंडे स्वाती राजेंद्र" and a["reservation"] == "SC woman" and a["party"] == "शिव-शाहू विकास आघाडी"
    assert d["councillor:MH:ichalkaranji-mc:2-क"]["name"] == "जाधव रणजीत गंगाराम"       # OCR lost "२ (क)": text layer
    assert d["councillor:MH:ichalkaranji-mc:16-इ"]["name"] == "सुनील शंकरराव तेलनाडे"
    assert sum(x["party"] == "BJP" for x in d.values()) == 43
