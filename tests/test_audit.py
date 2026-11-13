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


def test_card_lines_are_not_blocks_the_cards_are():
    """Kamareddy hospitals, page 3 (S3WaaS public utility, the full saved page): 12 cards (li.public-utlty-catg), each with
    lines "Email : | x", "Category/Type : | y". The lines are not the blocks; the 12 cards are, and the reader keeps all 12."""
    from dforms import emerg_hosp_s3waas
    body = gzip.decompress((DATA / "emerg_hosp_kamareddy.html.gz").read_bytes())
    url = "https://kamareddy.telangana.gov.in/public-utility-category/hospitals/page/3/"
    recs = emerg_hosp_s3waas.records([(url, body.decode("utf-8"))], {"url": url})
    assert len(recs) == 12
    src = audit.read_source(body, "text/html", "x.html.gz")
    assert len(src.rows) == 12 and all(r["title"] for r in src.rows) and "repeated blocks" in src.note
    a = audit.audit_source(src, [(rid, "", d.get("phone") or "", d.get("email") or "") for rid, d in recs], "dforms.emerg_hosp_s3waas")
    assert a["verdict"] == "ok" and a["records_person"] == 12


def test_pri_kl_member_pages_and_ward_table():
    """Kerala SEC (cforms/pri_kl), full saved pages. A member page holds one member: its blocks are the site menus, the empty
    dialogs (old template) or the sections of the one profile (2026 template), all named by pri_kl.AUDIT_LEAVES_OUT. The ward
    table wyrw/2371 lists 24 members; their records take the member pages as source and name the table in list_url
    (seeds/build_audit.py counts them for the table): 24 of 24 rows, ok."""
    from cforms import pri_kl
    for name, n_out in (("pri_kl_member_old", 5), ("pri_kl_member_2026", 8)):
        src = audit.read_source(gzip.decompress((DATA / f"{name}.html.gz").read_bytes()), "text/html", "x.html.gz")
        a = audit.audit_source(src, [("pri:KL:x:w1", "Member", "", "")], "cforms.pri_kl")
        assert a["rows_left_out"] == n_out and a["rows_visible"] == 0 and a["verdict"] == "not_tabular"
    body = gzip.decompress((DATA / "pri_kl_wyrw_2371.html.gz").read_bytes())
    url = "https://sec.kerala.gov.in/public/wyrw/2371"
    rows = pri_kl.ward_rows(body.decode("utf-8"), url)
    assert len(rows) == 24 and all(r[3] and r[7] for r in rows)
    recs = [(f"pri:KL:gp:x:w{r[1]}", r[3], "", "") for r in rows]
    a = audit.audit_source(audit.read_source(body, "text/html", "x.html.gz"), recs, "cforms.pri_kl")
    assert a["verdict"] == "ok" and a["records_person"] == 24 and a["rows_matched"] == 24
    # only the 2 records whose member page did not answer take the table as source: that alone is low
    assert audit.audit_source(audit.read_source(body, "text/html", "x.html.gz"), recs[:2], "cforms.pri_kl")["verdict"] == "low"


def test_tn_heads_judged_by_the_heads_names():
    """Dharapuram, the WordPress search answer "chair" (the full saved answer, 673 KB): 343 person-like rows (councillor list,
    schemes, disclosures); the reader keeps the 2 head pages (chair, vice-chair). cforms/tn.py holds the councillors; the audit
    judges tn_heads by the heads' names (AUDIT_HEADS)."""
    from cforms import tn_heads
    body = gzip.decompress((DATA / "tn_heads_dharapuram.json.gz").read_bytes())
    url = "https://www.tnurbantree.tn.gov.in/dharapuram/wp-json/wp/v2/pages?search=chair"
    recs = tn_heads.parse([(url, body.decode("utf-8"))], {"site": "dharapuram"})
    assert sorted(rid for rid, _ in recs) == ["councillor:TN:head:dharapuram:chair", "councillor:TN:head:dharapuram:vice-chair"]
    a = audit.audit_source(audit.read_source(body, "application/json", "x.json.gz"), recs_of(recs), "cforms.tn_heads")
    assert a["rows_visible"] == 343 and a["verdict"] == "ok" and a["reason"].startswith("heads only: 2 heads")


def test_photo_alt_text_counts_as_source_text():
    """e-Nigam member list (Mohali, cforms/cr_pb): the members' names are only in the photos' alt / title. With them in the source
    text, the 50 member-list records and the head are found by name (names_found 1.0), and the state switcher is left out."""
    from cforms import cr_pb
    body = gzip.decompress((ROOT / "tests" / "data" / "cr_pb_mohali_vice_detail_full.html.gz").read_bytes())
    t = body.decode("utf-8")
    d = cr_pb.detail(t)
    recs = [("vice", d["name"], d.get("phone") or "", "")] + [(m["ward_no"], m["name"], m["phone"], "") for m in cr_pb.member_list(t)]
    a = audit.audit_source(audit.read_source(body, "text/html", "x.html.gz"), recs, "cforms.cr_pb")
    assert a["names_found"] == 1.0 and a["records_person"] == 51 and a["rows_matched"] == 51 and a["rows_left_out"] >= 30


def test_vacant_posts_and_police_headers_are_not_data_rows():
    """UP SEC winner list rows of a vacant post ("पद रिक्त", no person) and the UP Police header rows ("S.No | Name of IPS
    Officer | Rank | Posted as | CUG / Mobile No. | ...") are not data rows; a real winner row is."""
    vacant = ["6 - जोया", "1 - औरंगाबाद", "2", "अनुसूचित जाति महिला", "-", "-", "-", "पद रिक्त"]
    assert not audit.person_row(vacant)
    assert not audit.person_row(["S.No", "Name of IPS Officer", "Rank", "Posted as", "CUG / Mobile No.", "Office No.", "Email Id"])
    assert audit.person_row(["6", "Barawal", "General (Woman)", "2", "GHEESA KANWAR", "BHERU SINGH", "F", "8990836618"])
