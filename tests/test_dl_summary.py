"""Delhi MCD 2022 Result Summary (cforms/dl.py, source "summary2022").
Sample: dl_summary2022_p1_8_12.pdf = pages 1, 8 and 12 of sec.delhi.gov.in/sites/default/files/SEC/universal-tab/
result_summary-ward_wise_1.pdf (saved 2026-11-12)."""
import pathlib

from cforms import dl

DATA = pathlib.Path(__file__).parent / "data"
P = {"url": "u", "source": "summary2022", "bye_wards": [35, 56, 65, 74, 76, 120, 128, 139, 163, 164, 173, 198]}


def recs():
    rows = dl.summary_rows(dl.runs(str(DATA / "dl_summary2022_p1_8_12.pdf")))
    return dict(x for x in (dl.summary_record(P, pg, c) for pg, c in rows) if x)


def test_summary_rows_and_numbers():
    r = recs()
    ids = "councillor:DL:municipal-corporation-of-delhi:"
    assert ids + "1" in r and ids + "250" in r
    w1 = r[ids + "1"]
    assert (w1["name"], w1["party"], w1["reservation"], w1["votes"], w1["runner_up"], w1["runner_up_party"], w1["runner_up_votes"],
            w1["margin"]) == ("Sweta Khatri", "Aam Aadmi Party", "Woman", "15929", "Keshrani Neel Daman Khatri", "Bharatiya Janata Party",
                              "10960", "4969")
    # the two wards MyNeta has no winner for
    assert r[ids + "162"]["name"] == "Jyoti Prakash Jarwal" and r[ids + "162"]["reservation"] == "SC Woman"
    assert r[ids + "178"]["name"] == "Sugandha" and r[ids + "178"]["party"] == "Aam Aadmi Party"
    assert r[ids + "163-2022"]["status"].startswith("seat filled again")
    for d in r.values():
        assert int(d["votes"]) - int(d["runner_up_votes"]) == int(d["margin"])
