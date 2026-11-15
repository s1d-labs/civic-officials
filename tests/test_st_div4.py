"""Division heads queued by seeds/dept_div4.json (2026-11-15), on the full pages saved from dev-vps-3 on 2026-11-15
(tests/data/st_div_pages/div4/): Haryana Police Rohtak Range page at its new url, Regional Commissioner Bengaluru officers page,
and the Chhattisgarh GAD IAS civil list as on 02.11.2026 (layout text, pdftotext -layout) read with "post_end_rx" / "name_rx"."""
import gzip
import json
from pathlib import Path

from dforms import _state
from dforms import st_div_pages as P
from dforms import st_div_postlist as L

HERE = Path(__file__).resolve().parent
D = HERE / "data" / "st_div_pages" / "div4"
SEEDS = {i["payload"]["key"]: i["payload"] for i in json.loads((HERE.parent / "seeds" / "dept_div4.json").read_text())}


def text(name):
    return gzip.open(D / name, "rt", encoding="utf-8").read()


def test_seeds():
    assert set(SEEDS) == {"div4-hr-rohtak-range", "div4-ka-bengaluru", "div4-cg-ias-civil-list"}
    for p in SEEDS.values():
        assert p["route"] == "direct" and p["india_only"]


def test_rohtak_range_new_url():
    p = SEEDS["div4-hr-rohtak-range"]
    recs = P.parse_page(p, text("hr_police_rtk.html.gz"), p["urls"][0])
    by = {d["post"]: d for _, d in recs}
    assert len(recs) == 4
    ig = by["IGP/Rohtak Range, Rohtak"]
    assert ig["name"] == "Hamid Akhtar, IPS" and ig["level"] == "division" and ig["email"] == "igroh@hry.nic.in"
    assert {d["district"] for d in recs[1:] for d in [d[1]]} == {"Charkhi Dadri", "Rohtak", "Bhiwani"}
    assert recs[0][0] == "dept:st_div_pages:div4-hr-rohtak-range:static-telephonedirectory-rtk:5:3"


def test_regional_commissioner_bengaluru():
    p = SEEDS["div4-ka-bengaluru"]
    recs = P.parse_page(p, text("ka_rcb_officers.html.gz"), p["urls"][0])
    heads = [d for _, d in recs if d.get("post_kind") == "divisional_commissioner"]
    assert len(recs) == 6 and len(heads) == 1
    assert heads[0]["name"] == "Sri Naveen Raj Singh, I.A.S" and heads[0]["division"] == "Bengaluru"
    assert len(heads[0]["districts"]) == 9


def test_cg_civil_list_bastar_bilaspur():
    p = SEEDS["div4-cg-ias-civil-list"]
    pages = text("cg_ias_civil_list_02112026.layout.txt.gz").split("\f")
    recs = L.parse_pages(p, pages)
    by = {d["division"]: d for _, d in recs}
    assert len(recs) == 2 and set(by) == {"Bastar", "Bilaspur"}
    b = by["Bastar"]
    assert b["name"] == "Doman Singh" and b["post"] == "Commissioner, Bastar Division" and b["email"] == "doman.singh66@gmail.com"
    assert b["post_kind"] == "divisional_commissioner" and b["designation_full"] == "Commissioner, Bastar Division, Jagdalpur. 19-07-2024."
    assert by["Bilaspur"]["name"] == "Sunil Kumar Jain" and len(by["Bilaspur"]["districts"]) == 8
    assert recs[0][0] == "dept:st_div_postlist:div4-cg-ias-civil-list:58:bilaspur"


def test_post_text_without_end_rx_unchanged():
    e = {"post_col": 4, "lines": ["1   Commissioner,   Bastar   Division,", "    Jagdalpur."]}
    assert L.post_text(e) == "Commissioner, Jagdalpur."
    assert L.post_text(e, end_rx=r"$") == "Commissioner, Bastar Division, Jagdalpur."


def test_gujarat_ranges_and_haryana_order():
    _state._DIV.clear()
    gj = _state.divisions("GJ")
    assert len(gj) == 9 and "Rajkot Range" in gj
    assert _state.districts_of("GJ", "Rajkot Range")[0] == "Rajkot Range"
    assert _state.districts_of("HR", "Rohtak")[0] == "Rohtak"                 # revenue division first
