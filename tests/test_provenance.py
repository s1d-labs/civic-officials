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
