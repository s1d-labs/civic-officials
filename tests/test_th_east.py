"""town heads, east: Assam DMA Executive Officers list (dforms/th_as.py; rows read by eye from the scan, file checked by sha256)."""
import json
from pathlib import Path

from dforms import th_as

ROOT = Path(__file__).resolve().parents[1]


class Resp:
    def __init__(self, content, url=th_as.URL):
        self.content, self.url, self.status_code = content, url, 200


def test_th_as_rows_and_codes():
    rows = th_as.rows()
    assert len(rows) == 104
    assert [(r["page"], r["row"]) for r in rows][:2] == [(1, 1), (1, 2)]
    assert sorted({r["page"] for r in rows}) == [1, 2, 3, 4, 5]
    # every row but Fakiragram (no LGD body) has a code; no code twice
    codes = [th_as.LGD.get(f"{r['page']}:{r['row']}") for r in rows]
    assert codes.count(None) == 1 and rows[codes.index(None)]["body"] == "Fakiragram"
    got = [c for c in codes if c]
    assert len(got) == len(set(got)) == 103


def test_th_as_parse_records():
    recs = dict(th_as.parse({"src_url": th_as.URL, "src_sha256": th_as.SHA256}))
    assert len(recs) == 104
    gmc = [d for d in recs.values() if d.get("lgd_code") == "249854"]
    assert len(gmc) == 1
    d = gmc[0]
    assert d["name"] == "Smti Loni Borpatra Gohain" and d["phone"] == "9864307767" and d["rank"] == "JC"
    assert d["role"] == "head" and d["dept"] == "town_body" and d["type"] == "dept_office"
    assert d["src_pos"] == {"page": 3, "row": 12, "read": "by eye from the rendered scan"}
    assert d["method"] == th_as.METHOD and d["src_sha256"] == th_as.SHA256 and d["as_of"].startswith("2023-12-21")
    howly = [d for d in recs.values() if d["area"] == "Howly M.B."][0]
    assert howly["name_doubtful"] is True
    doom = [d for d in recs.values() if d["area"] == "Doom Dooma M.B."][0]
    assert doom["phone"].replace(" ", "") == "8723938058"


def test_th_as_fetch_checks_file():
    p = th_as.items()[0]["payload"]
    recs, files, why = th_as.fetch(p, lambda url, **k: Resp(b"%PDF-1.7 another file"))
    assert recs == [] and why.startswith("file changed") and len(files) == 1
    import hashlib
    body = b"%PDF-1.7 test"
    p2 = dict(p, sha256=hashlib.sha256(body).hexdigest())
    recs, files, why = th_as.fetch(p2, lambda url, **k: Resp(body))
    assert why == "" and len(recs) == 104
    assert th_as.fetch(p, lambda url, **k: None)[2] == "no answer"
    assert th_as.fetch(p, lambda url, **k: Resp(b"<html>"))[2] == "not a pdf"


def test_th_as_seed_matches_items():
    assert json.loads((ROOT / "seeds/dept_th_as.json").read_text()) == th_as.items()
