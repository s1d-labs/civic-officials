import gzip
import hashlib
import json
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

import provenance


def resp(body, url="https://a.gov.in/p", ctype="text/html; charset=utf-8", status=200, archive=""):
    r = requests.Response()
    r.status_code, r._content, r.url = status, body, url
    r.headers["Content-Type"] = ctype
    if archive:
        r.from_archive = archive
    return r


def test_one_source_copied_once_and_records_annotated():
    t = provenance.Trail("depts", "civic-officials-depts", "7")
    t.begin({"key": "x-1", "payload": {"reader": "x"}}, "dforms.x")
    t.note(resp(b"<html>a</html>"), "https://a.gov.in/p")
    recs, files = t.finish([("dept:x:1", {"type": "dept_office", "name": "A"})], [], "html table")
    sha = hashlib.sha256(b"<html>a</html>").hexdigest()
    data = recs[0][1]
    assert data["src"] == {"sha256": sha, "url": "https://a.gov.in/p"} and data["method"] == "html table"
    assert data["trail"].startswith("trail:x-1:")
    path, blob, ctype = files[0]
    assert path == f"sources/{sha[:2]}/{sha}.html.gz" and gzip.decompress(blob) == b"<html>a</html>"
    by_id = dict(recs)
    assert by_id[f"src:{sha}"]["file"] == path
    tr = by_id[data["trail"]]
    assert tr["type"] == "trail" and tr["reader"] == "dforms.x" and tr["records"] == 1 and tr["run_id"] == "7"
    assert tr["sources"][0]["sha256"] == sha and tr["sources"][0]["copy"] == {"bucket": path}
    # the same bytes in the next item: no second copy, same index
    t.begin({"key": "x-2", "payload": {}}, "dforms.x")
    t.note(resp(b"<html>a</html>"), "https://a.gov.in/p")
    recs2, files2 = t.finish([("dept:x:2", {})], [])
    assert files2 == [] and not any(rid.startswith("src:") for rid, _ in recs2)
    assert recs2[0][1]["src"]["sha256"] == sha


def test_several_sources_reader_names_its_source_and_position():
    t = provenance.Trail("councillors", "p")
    t.begin({"key": "k", "payload": {}}, "cforms.tn_text")
    t.note(resp(b"%PDF-1 one", "https://s.gov.in/1.pdf", "application/pdf"), "https://s.gov.in/1.pdf")
    t.note(resp(b"%PDF-1 two", "https://s.gov.in/2.pdf", "application/pdf"), "https://s.gov.in/2.pdf")
    recs, files = t.finish([("c:1", {"src_url": "https://s.gov.in/2.pdf", "src_pos": {"page": 3, "line": 17}}),
                            ("c:2", {})], [])
    two = hashlib.sha256(b"%PDF-1 two").hexdigest()
    assert recs[0][1]["src"]["sha256"] == two and recs[0][1]["src_pos"] == {"page": 3, "line": 17}
    assert "src" not in recs[1][1]            # two sources and the reader did not say which: only the trail
    assert recs[0][1]["method"] == "pdf"
    assert sorted(p for p, _, _ in files) == sorted(f"sources/{h[:2]}/{h}.pdf.gz" for h in
                                                    (two, hashlib.sha256(b"%PDF-1 one").hexdigest()))


def test_archive_copy_is_not_uploaded_and_size_cap():
    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "r")
    t.note(resp(b"saved", archive="2026-11-12T21:55:14+05:30"), "https://a.gov.in/p")
    recs, files = t.finish([("r:1", {})], [])
    assert files == []
    tr = [d for rid, d in recs if rid.startswith("trail:")][0]
    assert tr["sources"][0]["copy"] == {"archive": "https://a.gov.in/p", "captured": "2026-11-12T21:55:14+05:30"}
    old = provenance.MAX_COPY
    provenance.MAX_COPY = 3
    try:
        t.begin({"key": "k2", "payload": {}}, "r")
        t.note(resp(b"too big"), "https://a.gov.in/q")
        recs, files = t.finish([], [])
    finally:
        provenance.MAX_COPY = old
    assert files == [] and recs[-1][1]["sources"][0]["not_copied"] == "size cap"


def test_reader_of():
    import councillors
    assert councillors.reader_of({"reader": "food_up_fcs"}) == "dforms.food_up_fcs"
    assert councillors.reader_of({"kind": "form-tn_text"}) == "cforms.tn_text"
    assert councillors.reader_of({"kind": "pdf"}) == "councillors.pdf"


class Page(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = b"<html><table><tr><td>Officer A</td></tr></table></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_pool_loop_end_to_end(tmp_path, monkeypatch):
    """councillors.main with a reader that reads one page: records, trail, source copy upload, item done; a failed item stays failed."""
    from scrape_hub_client.testhub import TestHub
    import councillors
    site = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=site.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{site.server_address[1]}/officers"
    hub = TestHub(store_dir=tmp_path / "up")
    hub.start()
    try:
        hub.state["projects"]["civic-officials-test"] = {"settings": {}}
        hub.state["queue"]["civic-officials-test"] = {
            k: {"key": k, "payload": {"reader": "t", "url": url}, "status": "pending", "attempts": 0, "fetched": 0, "error": "",
                "partition_id": zlib.crc32(k.encode()) % 1_000_000, "order": i} for i, k in enumerate(("ok-1", "bad-1"))}
        monkeypatch.setenv("SCRAPE_HUB_URL", hub.url)
        monkeypatch.setenv("SCRAPE_HUB_TOKEN", "x")
        monkeypatch.setenv("SCRAPE_POOL_PROJECT", "civic-officials-test")
        monkeypatch.setenv("SCRAPE_MAX_HOURS", "1")
        monkeypatch.delenv("ARCHIVE_FIRST", raising=False)
        import scrape_hub_client
        monkeypatch.setattr(scrape_hub_client, "HUB_URL", hub.url, raising=False)

        def run(item, get):
            r = get(item["payload"]["url"])
            if item["key"].startswith("bad"):
                return [], [], "no rows"
            return [(f"t:{item['key']}", {"type": "dept_office", "name": "Officer A"})], [], ""
        monkeypatch.setattr(councillors.time, "sleep", lambda s: None)
        councillors.main(run, "depts")
    finally:
        hub.stop()
        site.shutdown()
    q = hub.state["queue"]["civic-officials-test"]
    assert q["ok-1"]["status"] == "done" and q["bad-1"]["status"] == "failed"
    recs = hub.state["records"]["civic-officials-test"]
    recs = {rid: (v.get("data", v) if isinstance(v, dict) else v) for rid, v in recs.items()}
    rec = recs["t:ok-1"]
    sha = rec["src"]["sha256"]
    assert rec["trail"] in recs and recs[f"src:{sha}"]["file"] == f"sources/{sha[:2]}/{sha}.html.gz"
    trails = [d for rid, d in recs.items() if rid.startswith("trail:bad-1")]
    assert trails and trails[0]["records"] == 0      # the failed item keeps its trail (what we read), and stays failed
    ups = json.dumps(hub.state["uploads"], default=str)
    assert sha in ups


def test_form_data_kept_small_hashed_large():
    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "r")
    t.note(resp(b"{}", ctype="application/json"), "https://a.gov.in/api", "POST", {"DepartmentCode": 37, "CategoryCode": 0})
    t.note(resp(b"{1}", ctype="application/json"), "https://a.gov.in/api", "POST", {"__VIEWSTATE": "x" * 9000})
    recs, _ = t.finish([], [])
    s1, s2 = recs[-1][1]["sources"]
    assert json.loads(s1["form_data"]) == {"CategoryCode": 0, "DepartmentCode": 37}
    assert "form_data" not in s2 and s2["form_bytes"] > 9000 and len(s2["form_sha256"]) == 64


def test_src_sha256_wins_and_ambiguous_url_gives_no_src():
    """One url, two answers (POST paging): src_url alone is not enough; at(r) names the exact bytes."""
    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "r")
    r1, r2 = resp(b"[1]", "https://a.gov.in/api", "application/json"), resp(b"[2]", "https://a.gov.in/api", "application/json")
    t.note(r1, "https://a.gov.in/api", "POST", {"page": 1})
    t.note(r2, "https://a.gov.in/api", "POST", {"page": 2})
    recs, _ = t.finish([("a", {**provenance.at(r2, "https://a.gov.in/api"), "src_pos": {"index": 0}}),
                        ("b", {"src_url": "https://a.gov.in/api"}), ("c", {"url": "https://a.gov.in/api"})], [])
    a, b, c = (recs[i][1] for i in range(3))
    assert a["src"]["sha256"] == hashlib.sha256(b"[2]").hexdigest() and "src_sha256" not in a and a["src_url"] == "https://a.gov.in/api"
    assert "src" not in b and "src" not in c


def test_record_url_fallback_is_marked():
    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "r")
    t.note(resp(b"list", "https://a.gov.in/list"), "https://a.gov.in/list")
    t.note(resp(b"one", "https://a.gov.in/one"), "https://a.gov.in/one")
    recs, _ = t.finish([("a", {"url": "https://a.gov.in/one"}), ("b", {"source": "https://elsewhere.in/"})], [])
    assert recs[0][1]["src"] == {"sha256": hashlib.sha256(b"one").hexdigest(), "url": "https://a.gov.in/one", "via": "record url"}
    assert "src" not in recs[1][1]


def test_bytes_read_outside_get_keep_the_readers_hash():
    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "r")
    recs, _ = t.finish([("a", {"src_url": "https://a.gov.in/x.pdf", "src_sha256": "ab" * 32}),
                        ("b", {"src": provenance.file_src(b"%PDF", "https://a.gov.in/y.pdf", "councillors/TN/y.pdf")})], [])
    assert recs[0][1]["src"] == {"sha256": "ab" * 32, "url": "https://a.gov.in/x.pdf"}
    assert recs[1][1]["src"] == {"sha256": hashlib.sha256(b"%PDF").hexdigest(), "url": "https://a.gov.in/y.pdf",
                                 "file": "councillors/TN/y.pdf"}


def test_session_hook_notes_own_session_answers():
    site = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=site.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{site.server_address[1]}/officers"
        t = provenance.Trail("blo2", "p")
        t.begin({"key": "k", "payload": {}}, "forms.x")
        s = requests.Session()
        s.hooks["response"].append(provenance.hook(t))
        s.get(url)
        recs, files = t.finish([("a", {})], [])
    finally:
        site.shutdown()
    assert recs[0][1]["src"]["url"] == url and len(files) == 1


def test_tables_positions_and_directory_blo_records():
    import blo
    import directory
    import officials
    html = ("<table><tr><td>x</td></tr></table><table><tr><th>Name</th><th>Phone</th></tr><tr><td>A</td><td>1</td></tr>"
            "<tr><td></td><td></td></tr><tr><td>B</td><td>2</td></tr></table>")
    t = officials.tables(html)
    assert len(t) == 1 and t[0]["pos"] == [{"table": 2, "row": 2}, {"table": 2, "row": 4}]

    def get(*a):
        return resp(html.encode(), "https://a.gov.in/d")
    recs, _, _ = directory.run({"payload": {"url": "https://a.gov.in/d", "fmt": "html"}}, get)
    rows = [d for _, d in recs if d["type"] == "row"]
    assert rows[1]["src_pos"] == {"table": 2, "row": 4} and rows[1]["method"] == "html table"
    recs, _, _ = blo.run({"payload": {"url": "https://a.gov.in/d", "state": "PY"}}, get)
    assert recs[0][1]["src_pos"] == {"table": 2, "row": 2} and recs[0][1]["method"] == "html table"
    from forms import blo2_pdf
    assert blo.reader_method({"kind": "form-blo2_pdf"}) == blo2_pdf.METHOD


def test_row_counts_on_the_trail_record():
    import officials
    from dforms import _esw
    t = provenance.Trail("depts", "civic-officials-depts", "7")
    t.begin({"key": "r-1", "payload": {}}, "dforms.x")
    html = ("<table><tr><th>Name</th><th>Post</th></tr><tr><td>A</td><td>DM</td></tr><tr><td></td><td></td></tr>"
            "<tr><td>B</td><td>SP</td></tr><tr><td>C</td></tr></table>")
    rows = officials.tables(html)[0]["rows"]
    assert len(rows) == 3
    for r in rows:
        if len(r) < 2:
            provenance.skipped("short row")
            continue
        provenance.used()
    recs, _ = t.finish([("dept:x:a", {}), ("dept:x:b", {})], [])
    tr = dict(recs)[next(rid for rid, _ in recs if rid.startswith("trail:"))]
    assert tr["rows_used"] == 2 and tr["rows_skipped"] == {"short row": 1}
    assert tr["rows_not_data"] == {"header": 1, "empty": 1} and tr["rows_seen"] == 5 and tr["rows_given"] == 3
    # next item: counts start again; a reader that counts nothing adds no row keys
    t.begin({"key": "r-2", "payload": {}}, "dforms.x")
    recs, _ = t.finish([("dept:x:c", {})], [])
    assert not any("rows_seen" in d for _, d in recs)
    # a reader that only says what it skipped: rows_used is the number of data records
    t.begin({"key": "r-3", "payload": {}}, "dforms.x")
    soup = _esw.soup("<table><tr><td>a</td><td>1</td></tr><tr><td></td></tr></table>")
    assert _esw.grid(soup.find("table")) == [["a", "1"]]
    provenance.skipped("no number", 2)
    recs, _ = t.finish([("dept:x:d", {})], [])
    tr = dict(recs)[next(rid for rid, _ in recs if rid.startswith("trail:"))]
    assert tr["rows_used"] == 1 and tr["rows_used_from"] == "records" and tr["rows_seen"] == 4
    assert tr["rows_skipped"] == {"no number": 2} and tr["rows_not_data"] == {"empty": 1}
