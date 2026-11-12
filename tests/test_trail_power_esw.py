"""Source trail (provenance.py) of the power, ERO, sub-registrar and water readers: METHOD, src_pos (PDF page + line, HTML table +
row), src_url / src_sha256 where an item reads more than one answer. Saved fixtures only, no network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "tests" / "data"
PW = DATA / "power"

from dforms import _esw, _pdftext  # noqa: E402


def pages_of(name, d=DATA):
    return (d / name).read_text(encoding="utf-8").split("\f")


def check_lines(recs, pages, n_min=1):
    """Every record has a src_pos whose line_text is the page's text at that line (the reader's own lines)."""
    got = 0
    for _, d in recs:
        sp = d.get("src_pos")
        assert sp and sp.get("page"), d
        if "line" in sp:
            lines = pages[sp["page"] - 1].splitlines()
            nos = sp.get("lines") or [sp["line"]]
            assert sp["line"] == nos[0]
            assert sp["line_text"] == "\n".join(lines[n - 1].rstrip() for n in nos) or \
                sp["line_text"] == "\n".join(lines[n - 1] for n in nos), (sp, d)
            got += 1
    assert got >= n_min


def test_lines_helper():
    at = _pdftext.Lines(2, "a\n  b  \nc\nb")
    assert at.pos(["  b", "c"]) == {"page": 2, "line": 2, "line_text": "  b\nc", "lines": [2, 3]}
    assert at.pos("b")["line"] == 4                       # exact text (rstripped) only
    assert _pdftext.block_pos(1, ["x", "", "y"], [0, 2]) == {"page": 1, "line": 1, "line_text": "x\ny", "lines": [1, 3]}
    assert list(_pdftext.page_lines(["a\nb", "c"])) == [(1, 1, "a"), (1, 2, "b"), (2, 1, "c")]


def test_power_pdf_lines():
    from dforms import power_dhbvn, power_goa, power_mvvnl, power_uhbvn
    for f, circle in (("dhbvn_faridabad.txt", "faridabad"), ("dhbvn_hisar.txt", "hisar")):
        pg = pages_of(f, PW)
        check_lines(power_dhbvn.parse_text(pg, circle, "u"), pg, 10)
    pg = pages_of("uhbvn_karnal.txt", PW)
    check_lines(power_uhbvn.parse_text(pg, "karnal", "u"), pg, 5)
    pg = pages_of("mvvnl_lesa.txt", PW)
    recs = power_mvvnl.parse_lesa(pg)
    check_lines(recs, pg, 10)
    pg = json.loads((PW / "goa_pages.json").read_text())
    recs = power_goa.parse_pages(pg)
    assert all(d["src_pos"]["line_text"].splitlines()[0].strip().startswith(str(d["entry"])) for _, d in recs[:20])
    assert power_goa.METHOD.startswith("pdf text") and power_dhbvn.METHOD.startswith("pdf text (pdftotext")


def test_power_hescom_mepdcl_lines():
    from dforms import power_hescom, power_mepdcl
    pg = [(PW / "hescom_sections_p1.txt").read_text()]
    recs = power_hescom.parse_sections(pg)
    check_lines(recs, pg, 5)
    assert all(d["src_pos"]["line_text"].lstrip().startswith(d["office_id"]) for _, d in recs)
    pg = [(PW / "hescom_officers_p1.txt").read_text()]
    check_lines(power_hescom.parse_officers(pg), pg, 3)
    pg = json.loads((PW / "mepdcl_western_pages.json").read_text())
    check_lines(power_mepdcl.parse_pages(pg, "Western", "u"), pg, 3)


def test_power_html_rows():
    from dforms import power_msedcl, power_mvvnl
    recs = power_msedcl.parse_ee((PW / "msedcl_ee.html").read_text())
    assert recs and all(set(d["src_pos"]) == {"table", "row"} and d["method"] == "html table" for _, d in recs)
    recs = power_mvvnl.parse_directory((PW / "mvvnl.html").read_text())
    assert recs and all(d["src_pos"]["row"] >= 2 for _, d in recs)


def test_esw_pdf_lines():
    from dforms import ero_an, sro_mh, sro_up
    pg = pages_of("sro_up_officers.txt")
    check_lines(sro_up.parse_pages(pg), pg, 10)
    pg = pages_of("sro_mh_pune_div.txt")
    recs = sro_mh.parse_pages(pg, "u", "pune")
    check_lines(recs, pg, 10)
    assert all(str(d["sr_no"]) in d["src_pos"]["line_text"] for _, d in recs)
    pg = pages_of("ero_an_layout.txt")
    check_lines(ero_an.parse(pg), pg, 3)


def test_grid_pos_and_out_at():
    from bs4 import BeautifulSoup
    from dforms import _power
    import requests
    t = BeautifulSoup("<table><tr><td>x</td></tr></table><table><tr><th>A</th></tr><tr><td></td></tr><tr><td>b</td></tr></table>",
                      "lxml").find_all("table")[1]
    pos = []
    assert _esw.grid(t, pos=pos) == [["A"], ["b"]] and pos == [{"table": 2, "row": 1}, {"table": 2, "row": 3}]
    assert _power.tr_pos(t.find_all("tr")[2]) == {"table": 2, "row": 3}
    r = requests.Response()
    r._content, r.url = b"body", "https://x.in/a"
    out = _power.Out("m", "XX", "s").at(r, "https://x.in/a")
    d = out.add("k", "division", "A", post="EE")
    assert d["src_url"] == "https://x.in/a" and len(d["src_sha256"]) == 64


def _seed(module, key=None):
    items = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    return next(i for i in items if key is None or i["key"] == key)["payload"]


def _esw_get(routes):
    sys.path.insert(0, str(ROOT / "tests"))
    from esw_common import fake_get
    return fake_get(routes)


def test_postback_records_name_the_exact_answer():
    """ero_tn: GET then POST to the same url; records carry the hash of the POST answer and their table row."""
    import hashlib
    from dforms import ero_tn
    p = _seed("ero_tn", "ero_tn-ero-d2")
    recs, _, why = ero_tn.fetch(p, _esw_get({("GET", p["url"]): "ero_tn_ero_get.html", ("POST", p["url"]): "ero_tn_ero_d2.html"}))
    want = hashlib.sha256((DATA / "ero_tn_ero_d2.html").read_bytes()).hexdigest()
    assert recs and all(d["src_sha256"] == want and d["src_url"] == p["url"] and set(d["src_pos"]) == {"table", "row"}
                        for _, d in recs)


def test_water_wb_search_answer_and_sro_tn_pages():
    import hashlib
    from dforms import sro_tn, water_wb
    p = next(i["payload"] for i in json.loads((ROOT / "seeds" / "dept_water_wb.json").read_text())
             if i["payload"]["designation"] == "Executive Engineer")
    recs, _, _ = water_wb.fetch(p, _esw_get({p["url"]: "water_wb_form.html", ("POST", water_wb.SEARCH): "water_wb_ee.html"}))
    sha = hashlib.sha256((DATA / "water_wb_ee.html").read_bytes()).hexdigest()
    assert recs and all(d["src_url"] == water_wb.SEARCH and d["src_sha256"] == sha and d["src_pos"]["card"] >= 1 for _, d in recs)
    p = _seed("sro_tn")
    get = _esw_get({
        "https://tnreginet.gov.in/portal/": "sro_tn_portal.html",
        (lambda u, m, d: m == "POST" and "actionVal=homePage" in u): "sro_tn_portal.html",
        (lambda u, m, d: m == "POST" and "actionVal=sroList" in u and "_csrf=bd81dca9" in u): "sro_tn_list_p1.html",
        (lambda u, m, d: m == "GET" and u.endswith("d-4033352-p=2")): "sro_tn_list_p2.html"})
    recs, _, _ = sro_tn.fetch(p, get)
    shas = {d["src_sha256"] for _, d in recs}
    assert recs and shas <= {hashlib.sha256((DATA / f).read_bytes()).hexdigest() for f in ("sro_tn_list_p1.html", "sro_tn_list_p2.html")}


def test_xlsx_rows_and_json_paths():
    from dforms import ero_ka, power_apdcl, power_tgspdcl, sro_gj
    p = _seed("sro_gj")
    recs, _, _ = sro_gj.fetch(p, _esw_get({p["url"]: "sro_gj_offices.xlsx"}))
    assert all(d["src_pos"]["sheet"] == "sheet1" and d["src_pos"]["row"] >= 2 for _, d in recs)
    recs = power_apdcl.parse(json.loads((PW / "apdcl.json").read_text()))
    assert all(d["src_pos"]["path"].startswith("allContact[") for _, d in recs)
    recs = power_tgspdcl.parse(json.loads((PW / "tgspdcl.json").read_text()))
    assert all(d["src_pos"]["path"].startswith("circles[") for _, d in recs)
    doc = {"no": 5, "name": "X", "district": "Y", "parts": [[1, "s", "b", "1", "", "", "Aero A", "9876543210", "Ero E", "9876543211"],
                                                            [2, "s", "b", "1", "", "", "Aero A", "9876543210", "Ero E", "9876543211"]]}
    recs = ero_ka.parse(doc, "u")
    assert {d["post"]: d["src_pos"] for _, d in recs}["Electoral Registration Officer"] == {"key": "parts", "index": 0,
                                                                                           "indexes": [0, 1], "col": 8}


def test_methods():
    import importlib
    import glob
    for f in sorted(glob.glob(str(ROOT / "dforms" / "*.py"))):
        name = Path(f).stem
        if name.startswith("_") or not name.startswith(("power", "ero_", "sro_", "water")):
            continue
        m = importlib.import_module("dforms." + name)
        assert isinstance(getattr(m, "METHOD", None), str) and m.METHOD, name
    from dforms import power_mepdcl, power_nbpdcl, sro_gj, water_tn
    assert power_mepdcl.METHOD == "pdf text (pypdf layout)" and power_nbpdcl.METHOD.startswith("html table")
    assert sro_gj.METHOD == "spreadsheet (xlsx)" and water_tn.METHOD.startswith("html cards")
