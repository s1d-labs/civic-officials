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


def test_sub3_mh_aero_ocr_line_positions():
    from esw_common import mod
    m = mod("sub3_mh_aero")
    pages = [(2, (DATA / "sub3" / "mh_aero_p002.ocr.txt").read_text()), (40, (DATA / "sub3" / "mh_aero_p040.ocr.txt").read_text())]
    d = dict(m.build(m.parse(pages), "u"))
    t = d["dept:sub3_mh_aero:AC-5:1"]
    sp = t["src_pos"]
    text = dict(pages)[sp["page"]]
    assert text.splitlines()[sp["line"] - 1] == sp["line_text"] and sp["page"] == t["page"]
    four = d.get("dept:sub3_mh_aero:AC-3:4")
    assert four is None or four["src_pos"].get("line_end", four["src_pos"]["line"]) >= four["src_pos"]["line"]


def test_police_ka_option_and_table_positions():
    from bs4 import BeautifulSoup
    from dforms import police_ka
    html = (DATA / "police_ka_17.html").read_text(encoding="utf-8")
    d = dict(police_ka.parse_options(html, "17", "Gadag"))
    b = d["dept:police_ka:17:betageri-ps"]
    opt = BeautifulSoup(html, "lxml").find_all("option")[b["src_pos"]["index"] - 1]
    assert "Betageri" in opt.get_text() and b["method"].startswith("html select options")
    recs = police_ka.parse_bcp((DATA / "police_ka_bcp.html").read_text(encoding="utf-8"))
    sp = recs[0][1]["src_pos"]
    assert sp["table"] >= 1 and sp["row"] >= 2 and recs[0][1]["method"] == "html table"


def test_food_up_fcs_contact_and_email_lines():
    from esw_common import mod
    m = mod("food_up_fcs")
    folder = DATA / "food"
    text = (folder / "up_fcs_contacts_layout.txt").read_text()
    by = dict(m.parse_contacts(text))
    d = by["dept:food_up_fcs:contacts:dso:meerut"]
    sp = d["src_pos"]
    assert text.split("\f")[sp["page"] - 1].split("\n")[sp["line"] - 1] == sp["line_text"] and "7839564767" in sp["line_text"]
    assert d["src_url"] == m.CONTACTS
    em = m.parse_emails((folder / "up_fcs_emails_layout.txt").read_text())
    joined, _ = m.join_emails(list(by.items()), em)
    j = dict(joined)["dept:food_up_fcs:contacts:dso:meerut"]
    assert j["src_pos"]["email"]["line_text"] and j["src_pos"]["line"] == sp["line"] and j["src_url"] == m.CONTACTS


def test_field_html_and_text_positions():
    from esw_common import fake_get, mod
    from dforms import _esw, _field
    u = "http://health.tripura.gov.in/who_is_who"
    recs, _, _ = mod("field_health_tr").fetch({"url": u}, fake_get({u: "field_health_tr.html"}))
    d = recs[0][1]
    assert d["src_url"] == u and d["method"] == "html table"
    soup = _esw.soup((DATA / "field_health_tr.html").read_text(encoding="utf-8"))
    t = soup.find_all("table")[d["src_pos"]["table"] - 1]
    tr = [x for x in t.find_all("tr") if x.find_parent("table") is t][d["src_pos"]["row"] - 1]
    assert "Manik Saha" in tr.get_text(" ")
    sample = "field_revenue_gurdaspur_layout.txt"
    text = (DATA / sample).read_text()
    p = dict(layer_key="revenue", text_layout=True, state="XX")
    recs = _field.parse(text.encode(), "https://cdn.example/x", p, "field_revenue_s3waas")
    sp = recs[0][1]["src_pos"]
    assert text.split("\f")[sp["page"] - 1].split("\n")[sp["line"] - 1] == sp["line_text"]
    assert recs[0][1]["method"].startswith("text layout")
    food = mod("field_food_dl").parse_food((DATA / "field_food_dl_officials_layout.txt").read_text(), "u")
    assert food[0][1]["src_pos"]["line_text"].strip() and food[0][1]["src_pos"]["page"] == 1


def _tr_of(html, pos):
    from dforms import _esw
    soup = _esw.soup(html)
    t = soup.find_all("table")[pos["table"] - 1]
    return [x for x in t.find_all("tr") if x.find_parent("table") is t][pos["row"] - 1] if "row" in pos else t


def test_court_central_health_positions():
    from esw_common import fake_get, mod
    m = mod("court_dcourts")
    base = "https://patna.dcourts.gov.in/"
    get = fake_get({base + "list-of-judges/": "court_dcourts_patna_judges.html",
                    base + "contact-us/": "court_dcourts_kabirdham_contact.html"})
    recs, _, _ = m.fetch({"url": base, "state": "BR", "district": "Patna"}, get)
    judge = next(d for _, d in recs if d["kind"] == "judge")
    office = next(d for _, d in recs if d["kind"] == "office")
    assert judge["src_url"] == base + "list-of-judges/" and office["src_url"] == base + "contact-us/"
    html = (DATA / "court_dcourts_patna_judges.html").read_text()
    assert "ANAMIKA" in _tr_of(html, judge["src_pos"]).get_text(" ") and judge["method"] == "html table"
    assert office["src_pos"].get("line_text") or office["src_pos"].get("row")
    gst = mod("central_gst")
    g = gst.officers((DATA / "central_gst_mumbai_thane.html").read_text(), "https://x/y", {"state": "MH", "zone": "z"})
    assert g[0][1]["name"].split()[-1] in _tr_of((DATA / "central_gst_mumbai_thane.html").read_text(), g[0][1]["src_pos"]).get_text(" ")
    bank = mod("central_banking")
    text = (DATA / "central_banking_ifsc.csv").read_text(encoding="utf-8-sig")
    st = bank.state_of(next(__import__("csv").DictReader(__import__("io").StringIO(text))))
    b = bank.records(text, {"state": st}, "u")
    assert b[0][1]["src_pos"]["row"] == 1 and b[0][1]["ifsc"] in text.splitlines()[b[0][1]["src_pos"]["line"] - 1]
    br = mod("health_br_shs")
    page = DATA / "gaps2" / "br_shs_district_28.html"
    get = fake_get({lambda u, mm, dd: "district" in u and dd["page"] == "1": "gaps2/br_shs_district_28.html",
                    lambda u, mm, dd: "block" in u and dd["page"] == "1": "gaps2/br_shs_block_28.html"})
    recs, _, _ = br.fetch({"district_id": "28", "district": "Patna"}, get)
    d = recs[0][1]
    assert d["src_url"].endswith("get_contact_district_data") and d["src_sha256"] == hashlib.sha256(page.read_bytes()).hexdigest()
    assert d["src_pos"]["ajax_page"] == 1 and d["src_pos"]["row"] >= 1
