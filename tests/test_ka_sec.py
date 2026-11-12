"""cforms/ka_sec.py: Karnataka SEC press notes -> one body_election record per body of the round. Fixture: the press note of
06-09-2021 (karsec.karnataka.gov.in/FileDoc/PressRelease/All/70/20210906153501993.pdf, a 3-page scan, fetched 2026-11-13)."""
import json
from pathlib import Path

from cforms import ka_sec

D = Path(__file__).parent / "data" / "ka"
SEEDS = Path(__file__).parent.parent / "seeds" / "councillors_ka_sec.json"


class R:
    def __init__(self, content, url):
        self.content, self.url = content, url


def _item(rnd):
    return next(i["payload"] for i in json.loads(SEEDS.read_text()) if i["payload"]["round"] == rnd)


def test_ka_sec_sep_2021_note():
    p = _item("2021-09")
    body = (D / "ka_sec_2021_09.pdf").read_bytes()
    recs, files, why = ka_sec.fetch(p, lambda url: R(body, url))
    assert why == "" and len(recs) == 5 and files[0][0] == "councillors/KA/sec/2021-09.pdf"
    d = dict(recs)
    hd = d["body_election:KA:2021-09:251893"]
    assert hd["body"] == "Hubballi-Dharwad" and hd["wards"] == 82 and hd["result_date"] == "2021-09-06"
    assert hd["term_ends_not_before"] == "2026-09-06" and hd["src_pos"]["page"] == 2 and hd["src_pos"]["row"] == 2
    assert hd["src_sha256"] == p["sha256"] and hd["src_url"] == p["url"] and hd["method"] == ka_sec.METHOD
    assert d["body_election:KA:2021-09:251962"]["body"] == "Tarikere"


def test_ka_sec_refuses_other_file_and_short_file():
    p = _item("2021-09")
    recs, files, why = ka_sec.fetch(p, lambda url: R(b"%PDF-1.4 other", url))
    assert recs == [] and why.startswith("file changed")
    assert ka_sec.fetch(p, lambda url: R(b"<html>", url))[2] == "not a PDF"
    assert ka_sec.fetch(p, lambda url: None)[2] == "press note did not answer"


def test_ka_sec_seeds():
    items = json.loads(SEEDS.read_text())
    rows = [r for i in items for r in i["payload"]["rows"]]
    assert len(items) == 6 and len(rows) == 83
    codes = [r["lgd_code"] for r in rows if r["lgd_code"]]
    assert len(codes) == len(set(codes)) == 82          # Jali (Uttara Kannada) has no LGD code
    dec21 = _item("2021-12")
    assert len(dec21["rows"]) == 58 and ka_sec.plus5(dec21["result_date"]) == "2026-12-30"
    assert ka_sec.plus5("2024-02-29") == "2029-02-28" and ka_sec.plus5(None) is None
    no_code = [r for r in _item("2021-12")["rows"] if not r["lgd_code"]]
    assert ka_sec.records({**dec21, "rows": no_code}, None)[0][0] == "body_election:KA:2021-12:jali"
