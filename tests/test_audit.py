"""audit.py on real saved sources (full pages, as the bucket holds them) and the records the readers made from them."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "tests" / "data" / "audit"

import audit  # noqa: E402


def recs_of(parsed):
    return [(rid, d.get("name") or "", d.get("phone") or "", d.get("email") or "") for rid, d in parsed]


def run_saved(name, ext):
    s = json.loads((DATA / f"{name}.payload.json").read_text(encoding="utf-8"))
    body = (DATA / f"{name}.{ext}").read_bytes()
    assert hashlib.sha256(body).hexdigest() == s["sha256"]          # the exact bytes the reader read
    rid, d = audit.audit_item_source(s, body)
    assert rid == f"audit:{s['sha256']}" and d["type"] == "audit_source"
    return d


def test_mvvnl_old_reader_is_low_new_reader_is_ok():
    """The MVVNL directory page (211 KB, the full page): the reader before 329e48b made 127 records (it dropped the 7-cell rows
    and the rows inside HTML comments); the reader now makes 308. The audit must flag the old output and pass the new one."""
    from dforms import power_mvvnl
    body = (DATA / "mvvnl_directory.html").read_bytes()
    src = audit.read_source(body, "text/html; charset=utf-8", "sources/01/x.html.gz")
    old = json.loads((DATA / "mvvnl_directory_old_records.json").read_text(encoding="utf-8"))["records"]
    a_old = audit.audit_source(src, [tuple(r) for r in old], "dforms.power_mvvnl")
    new = recs_of(power_mvvnl.parse_directory(body.decode("utf-8")))
    a_new = audit.audit_source(src, new, "dforms.power_mvvnl")
    assert len(old) == 127 and len(new) == 308
    # the same source counts for both: visible rows, rows in comments, and the reader's left-out tables
    assert (a_old["rows_visible"], a_old["rows_hidden"]) == (a_new["rows_visible"], a_new["rows_hidden"]) == (127, 197)
    assert a_new["rows_left_out"] == 131 and "STORE CIRCLE" in a_new["tables_left_out"]
    assert a_old["verdict"] == "low" and a_old["coverage"] < 0.45
    assert any(r.startswith("[in an HTML comment]") for r in a_old["unmatched_rows"])
    assert a_new["verdict"] == "ok" and a_new["coverage"] >= 0.95 and a_new["names_found"] == 1.0
    assert a_new["rows_matched"] >= 320 and len(a_new["unmatched_rows"]) == 2


def test_mvvnl_without_the_reader_note_is_check():
    """Without the reader's AUDIT_LEAVES_OUT the head quarter, store and workshop tables count: the new output is not ok."""
    from dforms import power_mvvnl
    import re
    body = (DATA / "mvvnl_directory.html").read_bytes()
    src = audit.read_source(body, "text/html", "x.html.gz")
    a = audit.audit_source(src, recs_of(power_mvvnl.parse_directory(body.decode("utf-8"))), "", left_out=re.compile("^$x"))
    assert a["rows_left_out"] == 0 and a["verdict"] == "check"


def test_kamrc_staff_rows_without_records_are_check():
    """Kalaburagi city corporation staff page: 97 staff rows with phones, 73 records; the 24 office staff rows are listed."""
    d = run_saved("ward3_kamrc_staff", "html")
    assert d["kind"] == "html" and d["rows_visible"] == 97 and d["records_person"] == 73
    assert d["verdict"] == "check" and d["names_found"] == 1.0
    assert len(d["unmatched_rows"]) == 10 and sum(any(ch.isdigit() for ch in r) for r in d["unmatched_rows"]) >= 5


def test_cards_without_tables_count_as_blocks():
    """MP panchayat representatives: an HTML fragment of cards (<li><div class='card'>), no table."""
    d = run_saved("pri_mp", "html")
    assert d["rows_visible"] == 42 and d["records_person"] == 42 and d["verdict"] == "ok"
    assert "repeated blocks" in d["note"]


def test_json_list_of_objects():
    d = run_saved("civic_fps2_tg", "json")
    assert d["kind"] == "json" and d["rows_visible"] == 335 and d["records_person"] == 334 and d["verdict"] == "ok"


def test_html_inside_json():
    """MCD zone page: an API answer whose "menuName" string is the HTML of the page."""
    d = run_saved("ward2n_mcd", "json")
    assert d["note"].startswith("HTML inside JSON") and d["names_found"] == 1.0 and d["phones_found"] == 1.0


def test_pdf_lines():
    """Ahilyanagar talathi list (PDF, text layer, wrapped cells): lines with a phone or a name-like column."""
    d = run_saved("vil_mh_talathi", "pdf")
    assert d["kind"] == "pdf" and 85 <= d["rows_visible"] <= 110 and d["records_person"] == 100
    assert d["verdict"] == "ok" and d["names_found"] == 1.0 and d["phones_found"] == 1.0


def test_map_layer_is_not_tabular():
    """A ward boundary layer: the record describes the layer, it has no name or phone of a person."""
    body = (ROOT / "tests" / "data" / "wm2" / "tngis_ward_boundary.geojson").read_bytes()
    src = audit.read_source(body, "application/json", "gis/x.geojson.gz")
    a = audit.audit_source(src, [("wardmap:tn:erode", "", "", "")], "")
    assert a["verdict"] == "not_tabular"


def test_scan_without_text_is_not_tabular():
    src = audit.Source("pdf")
    src.note = "no text layer (a scan: records come from OCR)"
    a = audit.audit_source(src, [("x:1", "Ram Kumar", "9876543210", "")], "")
    assert a["verdict"] == "not_tabular" and "scan" in a["reason"]


def test_run_item_reads_gzip_checks_sha_and_reports_bad_copies():
    body = (DATA / "pri_mp.html").read_bytes()
    s = json.loads((DATA / "pri_mp.payload.json").read_text(encoding="utf-8"))
    bad = {**s, "sha256": "0" * 64, "file": "sources/00/bad.html.gz"}
    missing = {**s, "sha256": "1" * 64, "file": "sources/11/missing.html.gz"}
    store = {s["file"]: gzip.compress(body), bad["file"]: gzip.compress(body)}
    out, fails = [], []
    n, errors = audit.run_item({"key": "k", "payload": {"sources": [s, bad, missing]}}, lambda x: store.get(x["file"]),
                               lambda rid, d: out.append((rid, d)), lambda *a, **kw: fails.append(a))
    assert n == 1 and out[0][0] == f"audit:{s['sha256']}" and out[0][1]["verdict"] == "ok"
    assert len(errors) == 2 and "does not match" in errors[0] and "not in the bucket" in errors[1]
    assert [f[1] for f in fails] == [f"audit:{bad['sha256']}", f"audit:{missing['sha256']}"]


def test_phone_and_name_helpers():
    assert audit.phone8s("0522-2287801, 9415901146") == {"22287801", "15901146"}
    assert "05222287801" in audit.digit_runs("Phone 0522-2287801 on 12.03.2024")
    assert not any("2024" in r for r in audit.digit_runs("on 12.03.2024"))
    assert audit.name_like("Shri Ramesh Kumar Singh") and audit.name_like("श्री विनोद मंडराह")
    assert not audit.name_like("Executive Engineer") and not audit.name_like("Electricity Test Division")
    assert audit.skeleton("रे खा") == audit.skeleton("रेखा")          # PDF text that breaks a word


def test_family_has_the_audit_project():
    import family
    p = next(p for p in family.PROJECTS if p["name"] == "civic-officials-audit")
    assert p["task"] == "audit" and not p.get("proxy") and not p.get("geo")
    assert "audit" in json.loads((ROOT / "scrape.json").read_text())["tasks"]


def test_results_page_judged_by_names():
    import audit
    from types import SimpleNamespace
    src = SimpleNamespace(kind="html", note="")
    assert audit.verdict_of(src, 300, 1, 1 / 300, 0.0, 1.0, None, results=True)[0] == "ok"
    assert audit.verdict_of(src, 300, 1, 1 / 300, 0.0, 0.5, None, results=True)[0] == "check"
    assert audit.verdict_of(src, 300, 1, 1 / 300, 0.0, 1.0, None)[0] == "low"
    assert audit.results_page("pri_br") and not audit.results_page("power_mvvnl")
