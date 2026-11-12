"""cforms/ka.py member rows: the ward named in the post wins over a ward in the address; nominee rows get no ward."""
import importlib

from esw_common import DATA

ka = importlib.import_module("cforms.ka")


def test_ward_in_post_and_nominees():
    rows, admins, term, blank = ka.members((DATA / "ka" / "council_ward_in_post.html").read_text())
    by = {r["name"]: r for r in rows}
    assert ka._ward(by["Sri. Ramachandra S"]["ward_no"]) == "13"       # address says "Ward No.10": the member's house, not the seat
    assert ka._ward(by["Smt. Annapurna S"]["ward_no"]) == "15"
    assert ka._ward(by["Sri. Ananda Reddy"]["ward_no"]) == "10"
    assert ka._ward(by["Sri. Somebody"]["ward_no"]) == "11"             # "President": no number in the post, the address gives it
    assert by["ತೀರ್ಥ ಕುಮಾರ್"]["nominated"] and by["Shri. B. Maulali"]["nominated"]
    assert not by["Sri. Ananda Reddy"]["nominated"] and not admins


def test_administrator_only_gives_body_status(monkeypatch):
    from esw_common import Answer
    monkeypatch.setattr(ka, "_base", lambda p: "http://" + p["host"])
    p = {"host": "www.x.mrc.gov.in", "url": "http://www.x.mrc.gov.in/en/council-members", "slug": "x-city-corporation",
         "body": "X City Corporation", "body_type": "City Corporation", "district": "Mysuru", "lgd_code": "252045"}
    page = (DATA / "ka" / "council_admin_only.html").read_bytes()
    recs, files, why = ka.fetch(p, lambda url, **kw: Answer(page, url))
    assert why == "" and len(recs) == 1
    rid, d = recs[0]
    assert rid == "body_status:KA:x-city-corporation" and d["type"] == "body_status" and d["status"] == "administrator"
    assert d["lgd_code"] == "252045" and "Administrator" in d["administrator"] and d["url"].endswith("/en/council-members")
    assert d["src_pos"] == {"table": 1, "row": 2}
