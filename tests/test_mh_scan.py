"""Thane-style sideways scans (cforms/mh_scan.py): the quarter turn, and rows of the grid reader to members. No OCR here:
the rows are given as cforms/hr.py table_pgm returns them (cells per column, "new" = the ruled line above crosses it)."""
from cforms import mh_scan

COLS = ["serial", "ward", "ward_name", "pop", "pop_sc", "pop_st", "seat", "reservation", "name", "gender", "party", "votes"]
P = {"cols": COLS, "url": "u", "slug": "thane-mc", "body": "Thane Municipal Corporation", "lgd_code": "251471"}


def test_rotate_quarter_turns():
    # 3 x 2 image: a b c / d e f
    w, h, d = mh_scan.rotate(3, 2, bytearray(b"abcdef"), 90)
    assert (w, h, bytes(d)) == (2, 3, b"daebfc")
    w, h, d = mh_scan.rotate(3, 2, bytearray(b"abcdef"), 270)
    assert (w, h, bytes(d)) == (2, 3, b"cfbead")
    assert mh_scan.rotate(*mh_scan.rotate(3, 2, bytearray(b"abcdef"), 90), 270)[2] == bytearray(b"abcdef")


def row(cells, new_ward):
    c = [""] * len(COLS)
    for k, v in cells.items():
        c[COLS.index(k)] = v
    return {"cells": c, "new": [True] * len(COLS) if new_ward else [True if k != "ward" and k != "ward_name" and k[:3] != "pop"
                                                                         else False for k in COLS]}


def test_merged_ward_blocks():
    rows = [row({"serial": "(१)", "ward": "(२)", "seat": "(७)", "name": "(९)"}, True),
            row({"serial": "१.", "seat": "अ", "reservation": "अनुसूचित जमाती", "name": "विक्रांत संजय तांडेल", "gender": "पुरुष",
                 "party": "शिवसेना", "votes": "२०४००"}, True),
            row({"serial": "२.", "ward": "१", "ward_name": "ओवळा, कासारवडवली,", "seat": "ब", "name": "अनिता राम ठाकूर",
                 "party": "भारतीय जनता पार्टी", "reservation": "नागरिकांचा मागासवर्ग प्रवर्ग - महिला"}, False),
            row({"serial": "३.", "seat": "क", "name": "नम्रता रवि घरत", "party": "शिवसेना"}, False),
            row({"serial": "५.", "seat": "अ", "name": "चौधरी कमल रमेश", "party": "भारतीय जनता पार्टी"}, True),
            row({"serial": "६.", "ward": "२", "seat": "ब", "name": "विकास सिताराम पाटील"}, False)]
    r = dict(mh_scan.records(rows, P))
    assert set(r) == {"councillor:MH:thane-mc:1-अ", "councillor:MH:thane-mc:1-ब", "councillor:MH:thane-mc:1-क",
                      "councillor:MH:thane-mc:2-अ", "councillor:MH:thane-mc:2-ब"}
    d = r["councillor:MH:thane-mc:1-अ"]
    assert d["name"] == "विक्रांत संजय तांडेल" and d["votes"] == 20400 and d["party"] == "SHS" and d["reservation"] == "ST"
    assert d["ward_name"] == "ओवळा, कासारवडवली," and d["lgd_code"] == "251471"
    assert r["councillor:MH:thane-mc:1-ब"]["reservation"] == "OBC woman"
