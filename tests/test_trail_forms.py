"""Source trail (provenance.py) on the forms/ readers and the dforms readers of fork F2: METHOD, src_url, src_pos, src.
Saved fixtures only; no network."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "tests"))

import blo  # noqa: E402
from forms import blo2_ocr  # noqa: E402

DATA = Path(__file__).parent / "data"


class Hub:
    def __init__(self, files):
        self.files = files

    def read_urls(self, target, keys):
        return {k: "https://bucket/" + k for k in keys if k in self.files}


class Resp:
    def __init__(self, content, status=200, url=""):
        self.content, self.status_code, self.url = content, status, url

    def raise_for_status(self):
        pass


def test_blo2_ocr_rows_name_the_bucket_copy_page_row_and_conf(monkeypatch):
    d = json.loads((DATA / "blo2" / "ocr_mn_thangmeiband.json").read_text(encoding="utf-8"))
    pages, p = d["pages"], d["payload"]
    pdf = b"%PDF-1.4 scanned"
    monkeypatch.setattr(blo2_ocr, "tools", lambda lang: True)
    monkeypatch.setattr(blo2_ocr, "ocr_pages", lambda content, lang, first=1, last=None: pages)
    monkeypatch.setattr(blo2_ocr.requests, "get", lambda url, timeout=None: Resp(pdf))
    monkeypatch.delenv("SCRAPE_POOL_PROJECT", raising=False)

    def get(m, u, dd):
        raise AssertionError("no site request")
    get.hub = Hub({"civic-officials-blo2-in/blo/MN/abc.pdf"})
    item = {"key": "k", "payload": {**p, "kind": "form-blo2_ocr", "stored": "civic-officials-blo2-in/blo/MN/abc.pdf"}}
    recs, _, why = blo.run(item, get)
    assert why == ""
    rid, r = recs[0]
    assert rid == "blo:MN:9:1"
    assert r["src"] == {"sha256": hashlib.sha256(pdf).hexdigest(), "url": p["url"], "file": "civic-officials-blo2-in/blo/MN/abc.pdf"}
    assert r["src_pos"]["page"] == 1 and r["src_pos"]["row"] == 2
    assert r["method"] == "ocr tesseract eng (ruled grid reader of cforms/hr.py)"
    assert blo.reader_method(item["payload"]) == blo2_ocr.METHOD


def _pages(name):
    return (DATA / "blo2" / name).read_text(encoding="utf-8").split("\f")


def test_blo2_pdf_rows_give_page_and_line():
    from forms import blo2_pdf
    pg = _pages("up_gorakhpur_328.txt")
    p = {"state": "UP", "ac_no": 328, "district": "Gorakhpur", "url": "https://cdn.s3waas.gov.in/x.pdf"}
    rows = blo2_pdf.rows_from_pages(pg, p)
    for r in rows:
        sp = r["src_pos"]
        assert pg[sp["page"] - 1].splitlines()[sp["line"] - 1] == sp["line_text"]
    assert rows[0]["src_pos"]["page"] == 1 and "8601480995" in rows[0]["src_pos"]["line_text"] or rows[0]["src_pos"].get("line_end")
    assert rows[-1]["src_pos"]["page"] == 2 and rows[0]["method"] == "pdf text (pypdf layout)"
    recs = dict(blo.form_rows(p, rows))
    assert recs["blo:UP:328:1"]["src_pos"] == rows[0]["src_pos"] and recs["blo:UP:328:1"]["method"] == "pdf text (pypdf layout)"
    kd = blo2_pdf.rows_from_pages(_pages("up_kheri_139_kd.txt"), {"state": "UP", "ac_no": 139})
    assert kd and kd[0]["method"] == "pdf text (pypdf layout) + Kruti Dev map"


def test_sub2_rj_bdo_and_gj_name_the_pdf_page_and_row(monkeypatch):
    from esw_common import fake_get, mod
    m = mod("sub2_rj_bdo")
    p = m.items()[0]["payload"]
    get = fake_get({m.CONTACTS: "sub2/rj_contacts_pr_block.json", m.URL: "sub2/rj_bdo_list_p1.pdf"})
    recs, _, _ = m.fetch(p, get)
    b = dict(recs)["dept:sub2_rj_bdo:ajmer:bhinay"]
    assert b["src_url"] == m.URL and b["src_pos"]["page"] == 1 and b["src_pos"]["sn"] == b["list_no"] and b["src_pos"]["row"] >= 1
    # read from the bucket copy: src names the copy
    pdf = (DATA / "sub2" / "rj_bdo_list_p1.pdf").read_bytes()
    import requests
    monkeypatch.setattr(requests, "get", lambda url, timeout=None: Resp(pdf))
    get2 = fake_get({})
    get2.hub = Hub({"civic-officials-depts/depts/sub2_rj_bdo/vikas-adhikari-list.pdf"})
    recs, files, why = m.fetch({**p, "stored": "civic-officials-depts/depts/sub2_rj_bdo/vikas-adhikari-list.pdf"}, get2)
    assert why == "" and files == [] and get2.calls == [] and len(recs) == 23
    assert recs[0][1]["src"] == {"sha256": hashlib.sha256(pdf).hexdigest(), "url": m.URL,
                                 "file": "civic-officials-depts/depts/sub2_rj_bdo/vikas-adhikari-list.pdf"}
    g = mod("sub2_gj")
    url = g.SOURCES["tdo"][0]
    recs, _, _ = g.fetch({"kind": "tdo", "url": url}, fake_get({url: "sub2/gj_tdo_civil_list.pdf"}))
    t = dict(recs)["dept:sub2_gj:tdo:bhavnagar:shihor"]
    assert t["src_url"] == url and t["src_pos"]["page"] >= 1 and t["src_pos"]["sn"] == t["civil_list_no"]
