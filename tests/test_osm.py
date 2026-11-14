"""osm.py: kinds, centroids, and the whole task on a small built extract against the client's TestHub (no Geofabrik download)."""
import gzip
import hashlib
import http.server
import json
import os
import sys
import threading
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import osm  # noqa: E402


def test_point_kind_and_boundary():
    assert osm.point_kind({"amenity": "police"}) == "police"
    assert osm.point_kind({"amenity": "restaurant"}) is None
    assert osm.point_kind({"amenity": "townhall", "office": "government"}) == "townhall"        # amenity first
    assert osm.point_kind({"office": "government", "government": "tax"}) == "office_government"
    assert osm.point_kind({"office": "administrative"}) == "office_administrative"
    assert osm.point_kind({"healthcare": "centre"}) == "healthcare"
    assert osm.point_kind({"healthcare": "no"}) is None
    assert osm.is_boundary({"boundary": "administrative", "admin_level": "10"})
    assert not osm.is_boundary({"boundary": "administrative", "admin_level": "11"})
    assert not osm.is_boundary({"boundary": "political", "admin_level": "6"})


def test_centroid_and_date():
    sq = [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]
    assert osm.centroid([sq]) == (1.0, 1.0)
    big = [(10, 10), (14, 10), (14, 14), (10, 14), (10, 10)]
    cx, cy = osm.centroid([sq, big])                  # weighted by area: 4 vs 16
    assert abs(cx - (1 * 4 + 12 * 16) / 20) < 1e-9 and abs(cy - cx) < 1e-9
    assert osm.centroid([[(1, 1), (3, 1)]]) == (2.0, 1.0)      # an open way: the mean of its nodes
    assert osm.date_of("https://download.geofabrik.de/asia/india-261113.osm.pbf") == "2026-11-13"
    assert osm.date_of("https://x/a-latest.osm.pbf", "2026-11-12T20:21:02Z") == "2026-11-12"
    assert osm.date_of("https://x/a.osm.pbf", None, "Fri, 13 Nov 2026 23:55:16 GMT") == "2026-11-13"


def node(i, lon, lat, tags=()):
    t = "".join(f'<tag k="{k}" v="{v}"/>' for k, v in tags)
    return f'<node id="{i}" version="2" timestamp="2026-11-01T10:00:00Z" lat="{lat}" lon="{lon}">{t}</node>'


def way(i, nodes, tags=()):
    t = "".join(f'<tag k="{k}" v="{v}"/>' for k, v in tags)
    nd = "".join(f'<nd ref="{n}"/>' for n in nodes)
    return f'<way id="{i}" version="3" timestamp="2026-11-02T10:00:00Z">{nd}{t}</way>'


def rel(i, members, tags=()):
    t = "".join(f'<tag k="{k}" v="{v}"/>' for k, v in tags)
    m = "".join(f'<member type="way" ref="{w}" role="{r}"/>' for w, r in members)
    return f'<relation id="{i}" version="4" timestamp="2026-11-03T10:00:00Z">{m}{t}</relation>'


def square(first, x, y, d=0.01):
    return [node(first + k, x + dx, y + dy) for k, (dx, dy) in enumerate([(0, 0), (d, 0), (d, d), (0, d)])]


def build_extract(path):
    """A small OSM file: kinds as node, closed way and multipolygon; admin boundaries as closed way and relation; noise."""
    nodes = [node(1, 77.2, 28.6, [("amenity", "police"), ("name", "Connaught Place Police Station"),
                                  ("name:hi", "कनॉट प्लेस थाना"),
                                  ("phone", "+91 11 2374 0000"), ("addr:city", "New Delhi")]),
             node(2, 77.21, 28.61, [("amenity", "restaurant"), ("name", "Not wanted")]),
             node(30, 77.22, 28.62, [("office", "government"), ("government", "tax"), ("name", "Income Tax Office")]),
             node(31, 77.23, 28.63, [("healthcare", "centre"), ("name", "UPHC")]),
             node(33, 77.24, 28.64, [("amenity", "bank"), ("name", "SBI"), ("operator", "State Bank of India")]),
             node(34, 77.25, 28.65, [("boundary", "administrative"), ("admin_level", "6")])]       # a node is not a boundary
    nodes += square(100, 77.0, 28.0) + square(200, 77.5, 28.5, 0.1) + square(300, 76.0, 28.0, 1.0) + square(400, 77.3, 28.3)
    nodes += square(500, 75.0, 27.0, 0.5)
    ways = [way(10, [100, 101, 102, 103, 100], [("amenity", "hospital"), ("name", "District Hospital")]),
            way(11, [200, 201, 202, 203, 200], [("boundary", "administrative"), ("admin_level", "10"), ("name", "Ward 12")]),
            way(20, [300, 301, 302, 303, 300]),
            way(21, [400, 401, 402, 403, 400]),
            way(22, [500, 501, 502, 503, 500])]
    rels = [rel(900, [(20, "outer")], [("type", "boundary"), ("boundary", "administrative"), ("admin_level", "5"),
                                       ("name", "Test District"), ("wikidata", "Q1")]),
            rel(901, [(21, "outer")], [("type", "multipolygon"), ("amenity", "college"), ("name", "Govt College")]),
            rel(902, [(22, "outer")], [("type", "boundary"), ("boundary", "administrative"), ("admin_level", "11")])]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="test">' + "".join(nodes + ways + rels) + "</osm>"
    src = str(path) + ".osm"
    Path(src).write_text(xml, encoding="utf-8")
    import osmium
    with osmium.SimpleWriter(str(path)) as w:
        for o in osmium.FileProcessor(src):
            w.add(o)
    os.remove(src)


def read_kind(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


def test_local_filter(tmp_path):
    pytest.importorskip("osmium")
    src = tmp_path / "t.osm.pbf"
    build_extract(src)
    out_dir, filtered, counts, skipped, levels, n = osm.process(str(src), str(tmp_path / "w"))
    assert counts == {"police": 1, "office_government": 1, "healthcare": 1, "bank": 1, "hospital": 1, "college": 1, "boundary": 2}
    assert levels == {"10": 1, "5": 1} and n == 9      # 6 point objects, 2 boundaries, and the boundary-tagged node (written, not a polygon)
    pol = read_kind(os.path.join(out_dir, "police.geojsonl.gz"))[0]
    assert pol["id"] == "n1" and pol["geometry"] == {"type": "Point", "coordinates": [77.2, 28.6]}
    p = pol["properties"]
    assert p["osm_type"] == "node" and p["osm_id"] == 1 and p["version"] == 2 and p["timestamp"] == "2026-11-01T10:00:00Z"
    assert p["tags"]["name:hi"].startswith("क") and p["tags"]["phone"] == "+91 11 2374 0000" and p["geom"] == "point"
    hosp = read_kind(os.path.join(out_dir, "hospital.geojsonl.gz"))[0]
    assert hosp["id"] == "w10" and hosp["properties"]["geom"] == "centroid"
    assert hosp["geometry"]["coordinates"] == [77.005, 28.005]
    col = read_kind(os.path.join(out_dir, "college.geojsonl.gz"))[0]
    assert col["id"] == "r901" and col["geometry"]["coordinates"] == [77.305, 28.305]
    bnd = {f["id"]: f for f in read_kind(os.path.join(out_dir, "boundary.geojsonl.gz"))}
    assert set(bnd) == {"w11", "r900"}
    assert bnd["r900"]["geometry"]["type"] == "MultiPolygon" and bnd["r900"]["properties"]["admin_level"] == "5"
    assert bnd["r900"]["properties"]["tags"]["wikidata"] == "Q1" and bnd["w11"]["properties"]["tags"]["name"] == "Ward 12"


class _Files(http.server.BaseHTTPRequestHandler):
    root = None
    hits = []

    def log_message(self, *a):
        pass

    def _send(self, body_only):
        self.hits.append((self.command, self.path))
        if self.path.endswith("-latest.osm.pbf"):
            self.send_response(302)
            self.send_header("Location", self.path.replace("-latest", "-261113"))
            self.end_headers()
            return
        p = self.root / self.path.lstrip("/")
        if not p.is_file():
            self.send_response(404)
            self.end_headers()
            return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not body_only:
            self.wfile.write(data)

    def do_GET(self):
        self._send(False)

    def do_HEAD(self):
        self._send(True)


def test_task_end_to_end(tmp_path, monkeypatch):
    """The task against TestHub: download (redirect + md5), filter, upload the kind files, the filtered PBF, the manifest and
    latest.json, store one record; a second run finds the manifest and does nothing."""
    pytest.importorskip("osmium")
    from scrape_hub_client.testhub import TestHub
    import scrape_hub_client
    files = tmp_path / "files"
    files.mkdir()
    build_extract(files / "india-261113.osm.pbf")
    data = (files / "india-261113.osm.pbf").read_bytes()
    (files / "india-261113.osm.pbf.md5").write_text(hashlib.md5(data).hexdigest() + "  india-261113.osm.pbf\n")
    handler = type("H", (_Files,), {"root": files, "hits": []})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/india-latest.osm.pbf"
    store = tmp_path / "store"
    hub = TestHub(store_dir=store)
    hub.start()
    project = "civic-officials-osm"
    try:
        def queue(key):
            hub.state["projects"][project] = {"settings": {}}
            hub.state["queue"][project] = {key: {"key": key, "payload": {"url": url, "region": "india"}, "status": "pending",
                                                 "attempts": 0, "fetched": 0, "error": "",
                                                 "partition_id": zlib.crc32(key.encode()) % 1_000_000, "order": 0}}
        queue("osm:india:2026-11")
        monkeypatch.setenv("SCRAPE_HUB_URL", hub.url)
        monkeypatch.setenv("SCRAPE_HUB_TOKEN", "x")
        monkeypatch.setenv("SCRAPE_POOL_PROJECT", project)
        monkeypatch.setenv("SCRAPE_MAX_HOURS", "1")
        monkeypatch.setenv("OSM_DIR", str(tmp_path / "work"))
        os.makedirs(tmp_path / "work")
        monkeypatch.setattr(scrape_hub_client, "HUB_URL", hub.url, raising=False)
        monkeypatch.setattr(osm, "FREE_MARGIN", 0)
        osm.main()
        q = hub.state["queue"][project]["osm:india:2026-11"]
        assert q["status"] == "done", q["error"]
        assert q["fetched"] == 8
        base = store / project / "osm" / "2026-11-13"
        man = json.loads((base / "manifest.json").read_text())
        assert man["date"] == "2026-11-13" and man["file_md5"] == hashlib.md5(data).hexdigest()
        assert man["attribution"] == "© OpenStreetMap contributors" and man["license"] == "ODbL-1.0"
        assert set(man["files"]) == {"police", "office_government", "healthcare", "bank", "hospital", "college", "boundary"}
        for kind, f in man["files"].items():
            p = base / f"{kind}.geojsonl.gz"
            assert f["key"] == f"{project}/osm/2026-11-13/{kind}.geojsonl.gz"
            assert hashlib.sha256(p.read_bytes()).hexdigest() == f["sha256"] and len(read_kind(p)) == f["features"]
        assert (base / "filtered.osm.pbf").stat().st_size == man["filtered_pbf"]["bytes"]
        latest = json.loads((store / project / "osm" / "latest.json").read_text())
        assert latest["manifest"] == f"{project}/osm/2026-11-13/manifest.json"
        rec = hub.state["records"][project]["osm:india:2026-11-13"]["data"]
        assert rec["counts"]["boundary"] == 2 and rec["attribution"].startswith("©")
        assert not os.listdir(tmp_path / "work")          # the work folder is removed
        met = hub.state["metrics"][project]
        assert met["n_http"] >= 3 and met["t_http_s"] > 0
        # again: the manifest is there, so no download
        n_get = sum(1 for m, p in handler.hits if m == "GET" and p.endswith(".osm.pbf"))
        queue("osm:india:2026-11b")
        osm.main()
        assert hub.state["queue"][project]["osm:india:2026-11b"]["status"] == "done"
        assert sum(1 for m, p in handler.hits if m == "GET" and p.endswith(".osm.pbf")) == n_get
    finally:
        hub.stop()
        srv.shutdown()
