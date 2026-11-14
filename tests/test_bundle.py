"""bundle.py: shard zips of the saved source copies, end to end against the client's TestHub (no bucket, no site)."""
import csv
import gzip
import hashlib
import io
import json
import os
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bundle  # noqa: E402

PROJ = "civic-officials-depts"


def source(body, ext, url, ctype, records=1, project=PROJ):
    sha = hashlib.sha256(body).hexdigest()
    key = f"{project}/sources/{sha[:2]}/{sha}{ext}.gz"
    return sha, key, bundle.row(sha, key, url, url, ctype, len(body), "2026-11-12T10:00:00Z", project, "dforms.x", records,
                                [f"r:{sha[:6]}"], "")


def queue(hub, project, items):
    hub.state["projects"][project] = {"settings": {}}
    hub.state["queue"][project] = {
        it["key"]: {"key": it["key"], "payload": it["payload"], "status": "pending", "attempts": 0, "fetched": 0, "error": "",
                    "partition_id": zlib.crc32(it["key"].encode()) % 1_000_000, "order": i} for i, it in enumerate(items)}


def test_row_key_ext_host():
    sha = "ab" * 32
    r = bundle.row(sha, f"p-x/sources/ab/{sha}.html.gz", "https://Www.Example.gov.in:8443/a?b=1", "", "text/html", 10, "", "p-x;p-y",
                   "", 0, [], "")
    assert r[1] == "" and bundle.copy_key(r) == f"p-x/sources/ab/{sha}.html.gz"       # standard key: not repeated in the payload
    assert r[2] == "www.example.gov.in" and r[3] == ".html" and r[7] == ""
    r2 = bundle.row(sha, f"p-y/sources/ab/{sha}.pdf.gz", "u", "u2", "application/pdf", 1, "", "p-x;p-y", "", 0, [], "")
    assert r2[1] == f"p-y/sources/ab/{sha}.pdf.gz" and bundle.copy_key(r2) == r2[1] and r2[7] == "u2"
    assert bundle.ext_of_key(f"p/sources/ab/{sha}.gz", sha) == ".bin" and bundle.host_of("") == "unknown-host"
    assert bundle.list_hash([r, r2]) == bundle.list_hash([r2, r])


def test_pool_loop_end_to_end(tmp_path, monkeypatch):
    """Two shards and the index: zips with the original bytes, manifest rows (ok / missing / bad copy), index.json,
    sources.csv.gz; the index waits for the shards; a second run skips shards whose list did not change."""
    from scrape_hub_client.testhub import TestHub
    import scrape_hub_client
    store = tmp_path / "store"
    pdf = b"%PDF-1.4 fake pdf bytes " * 50
    srcs = [source(b"<html><table><tr><td>Officer A</td></tr></table></html>", ".html", "https://a.gov.in/officers", "text/html"),
            source(pdf, ".pdf", "https://b.nic.in/list.pdf", "application/pdf"),
            source(b'[{"name": "B"}]', ".json", "https://c.gov.in/api", "application/json"),
            source(b"never saved", ".html", "https://d.gov.in/", "text/html"),             # no copy in the bucket
            source(b"tampered", ".html", "https://e.gov.in/", "text/html")]               # copy with other bytes
    bodies = [b"<html><table><tr><td>Officer A</td></tr></table></html>", pdf, b'[{"name": "B"}]', None, b"something else"]
    for (sha, key, _), body in zip(srcs, bodies):
        if body is not None:
            p = store / key
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(gzip.compress(body))
    by_shard = {}
    for sha, _, r in srcs:
        by_shard.setdefault(sha[:bundle.SHARD_DIGITS], []).append(r)
    # two shards: put everything in the first two shard names the hashes give (so the test does not depend on the hashes)
    names = sorted(by_shard)
    shards = {names[0]: by_shard[names[0]], "zz": [r for n in names[1:] for r in by_shard[n]]}
    items = []
    for s, rows in shards.items():
        items.append({"key": f"bundle:{s}:{bundle.list_hash(rows)[:12]}",
                      "payload": {"kind": "shard", "shard": s, "list_hash": bundle.list_hash(rows), "expected": len(rows),
                                  "bytes": sum(r[6] for r in rows), "cols": bundle.COLS, "rows": rows}})
    index = {"key": "bundle-index:x", "payload": {"kind": "index", "shards": {s: bundle.list_hash(r) for s, r in shards.items()}}}
    hub = TestHub(store_dir=store)
    hub.start()
    project = "civic-officials-bundle"
    try:
        queue(hub, project, [index] + items)           # the index first: it must wait for the shards
        monkeypatch.setenv("SCRAPE_HUB_URL", hub.url)
        monkeypatch.setenv("SCRAPE_HUB_TOKEN", "x")
        monkeypatch.setenv("SCRAPE_POOL_PROJECT", project)
        monkeypatch.setenv("SCRAPE_MAX_HOURS", "1")
        monkeypatch.setenv("BUNDLE_DIR", str(tmp_path / "work"))
        os.makedirs(tmp_path / "work")
        monkeypatch.setattr(scrape_hub_client, "HUB_URL", hub.url, raising=False)
        monkeypatch.setattr(bundle.time, "sleep", lambda s: None)
        bundle.main()
        q = hub.state["queue"][project]
        assert q["bundle-index:x"]["status"] == "failed" and q["bundle-index:x"]["error"].startswith("waiting for 2 shards")
        assert all(q[i["key"]]["status"] == "done" for i in items)
        assert q[items[0]["key"]]["fetched"] + q[items[1]["key"]]["fetched"] == 3
        q["bundle-index:x"]["status"] = "pending"
        bundle.main()
        assert q["bundle-index:x"]["status"] == "done", q["bundle-index:x"]["error"]
        # a second run: the shard lists did not change, so nothing is rebuilt
        for i in items:
            q[i["key"]]["status"] = "pending"
        n_up = len(hub.state["uploads"])
        bundle.main()
        assert all(q[i["key"]]["status"] == "done" and q[i["key"]]["fetched"] == 0 for i in items)
        assert len(hub.state["uploads"]) == n_up
    finally:
        hub.stop()
    base = store / project / "bundle"
    assert not os.listdir(tmp_path / "work")                # the zips are removed after the upload
    seen = {}
    for s in shards:
        z = zipfile.ZipFile(base / f"sources-{s}.zip")
        man = list(csv.DictReader(io.StringIO(z.read("manifest.csv").decode())))
        assert "README.txt" in z.namelist()
        for m in man:
            seen[m["sha256"]] = m
            if m["status"] == "ok":
                info = z.getinfo(m["path_in_zip"])
                assert hashlib.sha256(z.read(info)).hexdigest() == m["sha256"]
                assert info.compress_type == (zipfile.ZIP_STORED if m["path_in_zip"].endswith(".pdf") else zipfile.ZIP_DEFLATED)
        st = json.loads((base / "shards" / f"{s}.json").read_text())
        assert st["list_hash"] == bundle.list_hash(shards[s]) and st["zip_bytes"] == os.path.getsize(base / f"sources-{s}.zip")
    status = {sha: seen[sha]["status"] for sha, _, _ in srcs}
    assert list(status.values()) == ["ok", "ok", "ok", "copy not in the bucket", "copy does not match its sha256"]
    assert seen[srcs[0][0]]["path_in_zip"] == f"a.gov.in/{srcs[0][0]}.html" and seen[srcs[0][0]]["records_made"] == "1"
    idx = json.loads((base / "index.json").read_text())
    assert idx["files"] == 3 and idx["missing"] == 2 and idx["rows"] == 5 and [s["shard"] for s in idx["shards"]] == sorted(shards)
    rows = list(csv.DictReader(io.StringIO(gzip.decompress((base / "sources.csv.gz").read_bytes()).decode())))
    assert len(rows) == 5 and {r["sha256"] for r in rows} == {sha for sha, _, _ in srcs}
    assert "src.sha256" in (base / "README.txt").read_text()
