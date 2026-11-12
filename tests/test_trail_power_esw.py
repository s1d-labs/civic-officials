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
