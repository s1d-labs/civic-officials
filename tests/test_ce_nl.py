"""Nagaland ULB 2024 results (cforms/ce_nl.py): grid rows of the Kohima page typed from Gazette Ex. No. 179, page 51."""
import json
from pathlib import Path

from cforms import ce_nl

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


def test_kohima_rows():
    rows = json.loads((DATA / "ce_nl_kohima_rows.json").read_text())
    p = {"url": ce_nl.URL, "bodies": {"51": ["Kohima Municipal Council", "249722"]}}
    recs = dict(ce_nl.page_records(rows, p, 51))
    assert len(recs) == 19
    a = recs["councillor:NL:kohima-municipal-council:1"]
    assert a["name"] == "Kelhousenuo Khruomo" and a["gender"] == "F" and a["party"] == "NDPP" and a["unopposed"]
    assert a["reservation"] == "Reserved" and a["ward_name"] == "High School" and a["lgd_code"] == "249722"
    assert recs["councillor:NL:kohima-municipal-council:5"]["party"] == "IND"
    assert recs["councillor:NL:kohima-municipal-council:2"]["party"] == "NDPP"
    assert recs["councillor:NL:kohima-municipal-council:15"]["unopposed"]
    assert "unopposed" not in recs["councillor:NL:kohima-municipal-council:14"]
    w11 = recs["councillor:NL:kohima-municipal-council:11"]
    assert w11["name"] == "Neibodzelie Solo" and "ward_no_read" not in w11     # "l1" read as 11
    assert sum(1 for d in recs.values() if d["party"] == "NPP") == 3


def test_party_and_page_without_body():
    assert ce_nl.party("N.D.P.P") == "NDPP" and ce_nl.party("NPP") == "NPP" and ce_nl.party("1ND") == "IND"
    assert ce_nl.party("BJP") == "BJP" and ce_nl.party("NPF") == "NPF"
    assert ce_nl.page_records([], {"url": "x", "bodies": {}}, 51) == []


def test_main_bottom_cuts_summary_tables():
    w, h = 60, 900
    img = bytearray([255]) * (w * h)
    for y in range(50, 600):          # member table border
        img[y * w + 10] = 0
    for y in range(650, 800):         # summary table border (shorter)
        img[y * w + 30] = 0
    assert ce_nl.main_bottom(w, h, img, minrun=100) == 600


def test_seed():
    items = json.loads((SEEDS / "ocr_councillors_ce_nl.json").read_text())
    assert len(items) == 5
    pages = {k: v for i in items for k, v in i["payload"]["bodies"].items()}
    assert len(pages) == 25 and pages["51"][1] == "249722" and pages["75"][0] == "Chozuba Town Council"
    assert items[0]["payload"].get("save") and all(i["payload"].get("stored") for i in items[1:])
