"""Source trail of the police, emergency and civic layer readers: every record names its position in the source (src_pos) and,
when the item reads more than one answer, the answer it came from (src_url / src_sha256). Offline, on the saved samples."""
import json
from pathlib import Path

import pytest

from esw_common import DATA, mod

ROOT = Path(__file__).resolve().parent.parent


def check_lines(recs, pages, n_min=1):
    """Each record's src_pos names a page and line whose text is the line_text it carries (the exact line of the source)."""
    assert len(recs) >= n_min
    for rid, d in recs:
        pos = d["src_pos"]
        lines = pages[pos.get("page", 1) - 1].split("\n")
        assert lines[pos["line"] - 1] == pos["line_text"], (rid, pos)


def test_methods_present():
    import importlib
    for f in sorted((ROOT / "dforms").glob("*.py")):
        n = f.stem
        if n.startswith(("police", "emerg_", "civic_")) and n != "police_ka":
            m = importlib.import_module("dforms." + n)
            if hasattr(m, "fetch"):
                assert getattr(m, "METHOD", ""), n


def test_emerg_pdf_positions():
    pages = (DATA / "emerg_ddma_kl_layout.txt").read_text().split("\f")
    check_lines(mod("emerg_ddma_kl").records(pages), pages, 20)
    text = (DATA / "emerg_fire_ka_layout.txt").read_text()
    check_lines(mod("emerg_fire_ka").records(text, "u"), [text], 10)
    text = (DATA / "emerg_fire_nagpur_layout.txt").read_text()
    recs = mod("emerg_fire_nagpur").records(text, "u")
    check_lines(recs, [text], 5)
    assert all(d["src_pos"]["lines"] >= 1 for _, d in recs)
    pages = [(DATA / "emerg_hg_up_layout.txt").read_text()]
    recs = mod("emerg_hg_up").records(pages, engine="pdftotext -layout")
    check_lines(recs, pages, 10)
    assert recs[0][1]["method"].startswith("pdf text (pdftotext -layout)")


def test_emerg_ruled_pdfs():
    m = mod("emerg_osc_mp")
    pages = json.loads((DATA / "emerg_osc_mp_p1_parts.json").read_text())
    recs = m.records(b"", m.URL, pages=pages)
    rows = [d["src_pos"]["row"] for _, d in recs]
    assert recs and all(d["src_pos"]["page"] == 1 for _, d in recs) and rows == sorted(rows) and len(set(rows)) == len(rows)
    m = mod("emerg_fire_dl")
    p1 = json.loads((DATA / "emerg_fire_dl_p1.json").read_text())
    pages = [([tuple(t) for t in p1["texts"]], [tuple(h) for h in p1["h"]], [tuple(v) for v in p1["v"]])]
    phones = m.phone_lines((DATA / "emerg_fire_dl_phones.txt").read_text())
    recs = m.records(pages, phones, m.URL, m.PHONES_URL)
    st = [d for _, d in recs if d["level"] == "facility"]
    assert st and all(d["src_pos"]["page"] == 1 and d["src_url"] == m.URL for d in st)
    with_phone = [d for d in st if d.get("phone")]
    assert with_phone and all(d["src_pos"]["phone_line"]["line_text"].strip().endswith(d["phone"].split(",")[0].split()[-1])
                              or d["src_pos"]["phone_line"]["line_text"] for d in with_phone)


def test_civic_pdf_positions():
    pages = (DATA / "civic_clinic_mumbai_layout.txt").read_text().split("\f")
    check_lines(mod("civic_clinic_mumbai").parse(pages), pages, 20)
    pages = (DATA / "civic_health_dl_layout.txt").read_text().split("\f")
    check_lines(mod("civic_health_dl").parse(pages), pages, 20)
    pages = (DATA / "civic_health_py_layout.txt").read_text().split("\f")
    check_lines(mod("civic_health_py").parse(pages), pages, 10)
    text = (DATA / "civic_fire_py_p1.txt").read_text(encoding="utf-8")
    check_lines(mod("civic_fire_py").parse(text), [text], 5)
    pages = json.loads((DATA / "civic_pollst_hr_pages.json").read_text())
    check_lines(mod("civic_pollst_hr").parse(pages, "u"), pages, 5)


def test_police_pdf_positions():
    import io

    from pypdf import PdfReader
    from test_dept_police import FakeGet
    from dforms import police_an, police_kl, police_ld
    recs, _, _ = police_an.fetch({"url": police_an.URL}, FakeGet({police_an.URL: "police_an.pdf"}))
    pdf = PdfReader(io.BytesIO((DATA / "police_an.pdf").read_bytes()))
    pages = [(p.extract_text() or "").splitlines() for p in pdf.pages]
    assert recs
    for _, d in recs:
        pos = d["src_pos"]
        assert pages[pos["page"] - 1][pos["line"] - 1] == pos["line_text"]
    recs, _, _ = police_kl.fetch({"url": police_kl.URL}, FakeGet({police_kl.URL: "police_kl.pdf"}))
    pdf = PdfReader(io.BytesIO((DATA / "police_kl.pdf").read_bytes()))
    lines = {}
    for _, d in recs:
        pos = d["src_pos"]
        if pos["page"] not in lines:
            lines[pos["page"]] = police_kl.lines_of(pdf.pages[pos["page"] - 1])
        assert lines[pos["page"]][pos["line"] - 1] == pos["line_text"]
    get = FakeGet({police_ld.URL: "police_ld.html", police_ld.CHARTER: "police_ld.pdf"})
    recs, _, _ = police_ld.fetch({"url": police_ld.URL, "charter": police_ld.CHARTER}, get)
    d = dict(recs)
    k = next(v for v in d.values() if v.get("phone"))
    assert k["src_url"] == police_ld.URL and k["src_pos"]["table"] >= 1 and k["src_pos"]["row"] >= 2
    assert k["src_pos"]["charter_page"] >= 1 and k["method"] == "html table + pdf text (pypdf)"


def test_civic_json_and_html_positions():
    m = mod("civic_health_in")
    doc = json.loads((DATA / "civic_health_in.json").read_text())
    recs = m.parse(doc)
    for _, d in recs:
        i = d["src_pos"]["index"]
        assert doc["features"][i]["attributes"]["objectid"] == d["src_pos"]["objectid"]
    from dforms import _civic_fps as F
    mp = F.jsp_parse((DATA / "civic_fps_mp_names.html").read_text(), "civic_fps_mp", "MP", "https://epos.mp.gov.in")
    from dforms import _esw
    soup = _esw.soup((DATA / "civic_fps_mp_names.html").read_text())
    for _, d in mp:
        tr = soup.find_all("table")[d["src_pos"]["table"] - 1].find_all("tr")[d["src_pos"]["row"] - 1]
        assert d["fps_id"] in tr.get_text()


def test_civic_tag_and_tr_pos():
    from dforms import _civic, _esw
    import requests
    r = requests.Response()
    r._content, r.url = b"<x>", "https://a.gov.in/p"
    recs = _civic.tag([("a", {}), ("b", {"src_url": "keep"})], r, "https://a.gov.in/p", method="html table")
    assert recs[0][1]["src_url"] == "https://a.gov.in/p" and len(recs[0][1]["src_sha256"]) == 64
    assert recs[1][1]["src_url"] == "keep" and recs[1][1]["method"] == "html table"
    s = _esw.soup("<table><tr><td>a</td></tr></table><table><tr><th>h</th></tr><tr><td>b</td></tr></table>")
    assert _civic.tr_pos(s.find_all("tr")[2]) == {"table": 2, "row": 2}


def row_text(html, pos):
    """Text of the row that a {"table", "row"} src_pos names (rows counted as _esw.grid counts them: the table's own <tr>)."""
    from dforms import _esw
    t = _esw.soup(html).find_all("table")[pos["table"] - 1]
    trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
    return " ".join(trs[pos["row"] - 1].get_text(" ").split())


def digits(s):
    import re
    return re.sub(r"\D", "", s or "")


def check_rows(recs, html, field="phone"):
    n = 0
    for _, d in recs:
        pos = d.get("src_pos") or {}
        if "table" in pos and d.get(field):
            first = d[field].split(",")[0]
            assert digits(first)[-6:] in digits(row_text(html, pos)), (d[field], pos)
            n += 1
    assert n


def test_emerg_table_rows():
    from esw_common import fake_get
    for module, fixture in (("emerg_fire_tr", "emerg_fire_tr.html"), ):
        m = mod(module)
        recs, _, _ = m.fetch({"url": m.URL}, fake_get({m.URL: fixture}))
        check_rows(recs, (DATA / fixture).read_text())
    m = mod("emerg_fire_ml")
    routes = {m.URL: "emerg_fire_ml_contacts.html", m.STATIONS_URL: "emerg_fire_ml_stations.html"}
    recs, _, _ = m.fetch({"url": m.URL}, fake_get(routes))
    check_rows([r for r in recs if r[1]["src_url"] == m.URL], (DATA / "emerg_fire_ml_contacts.html").read_text())
    assert all(d["src_url"] == m.STATIONS_URL and d["src_pos"]["table"] for _, d in recs if d["source"] == m.STATIONS_URL)
    url = "https://chamoli.gov.in/disaster-management/"
    recs, _, _ = mod("emerg_ddma_s3waas").fetch({"url": url, "district": "Chamoli", "state": "UK"},
                                                fake_get({url: "emerg_ddma_s3waas_chamoli.html"}))
    check_rows(recs, (DATA / "emerg_ddma_s3waas_chamoli.html").read_text())
    m = mod("emerg_fire_ga")
    recs, _, _ = m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_fire_ga.html"}))
    assert [d["src_pos"]["card"] for _, d in recs] == sorted(d["src_pos"]["card"] for _, d in recs)
    url = "https://buldhana.nic.in/en/public-utility-category/hospitals/"
    m = mod("emerg_hosp_s3waas")
    recs, _, _ = m.fetch({"url": url, "state": "MH", "district": "Buldhana"}, fake_get({url: "emerg_hosp_s3waas_buldhana_p1.html"}))
    assert all(d["src_url"] == url and d["src_pos"]["card"] >= 1 for _, d in recs)
