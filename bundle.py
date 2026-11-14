"""Task `bundle`: zip files of every saved source copy, kept up to date in the family bucket (owner, 2026-11-14: "The actual
source files we should keep an updated zip in the bucket, which we can serve anytime via a signed link").

No request goes to a government site. Each source is read from the family bucket: the copy that provenance.py saved at
<project>/sources/<sha[:2]>/<sha><ext>.gz (hub.read_urls signs a read link; the runner never holds a storage key).

Layout in the bucket (project civic-officials-bundle, so every key starts with "civic-officials-bundle/"):
  bundle/sources-<shard>.zip      one zip per shard: the sources whose sha256 starts with <shard> (SHARD_DIGITS hex digits);
                                  inside: <host>/<sha256><ext> (the original bytes, decompressed), manifest.csv, README.txt
  bundle/manifests/<shard>.csv.gz the shard's manifest.csv, also apart (the index item joins them without reading the zips)
  bundle/shards/<shard>.json      the shard's state: list_hash, files, missing, bytes, zip size and sha256, built_at
  bundle/index.json               every shard (key, size, sha256, files, built_at, list_hash) and the totals
  bundle/sources.csv.gz           all manifest rows of all shards
  bundle/README.txt               what the files are, how records point to them, the public-records note

Queue items (seeds/build_bundle.py makes them from DB civic):
  shard: {"kind": "shard", "shard": "3f", "list_hash", "expected", "bytes", "cols": COLS, "rows": [[...], ...]}
         The item skips its shard when bundle/shards/<shard>.json in the bucket has the same list_hash (nothing changed).
  index: {"kind": "index", "shards": {shard: list_hash}}: waits until every shard json carries the list_hash given (else the
         item fails with "waiting for N shards" and the hub hands it out again >= 3 minutes later), then writes index.json,
         sources.csv.gz and README.txt.

Disk: the zip is written to BUNDLE_DIR (default: the temp folder) one source at a time; the task checks the free space first
(raw bytes of the shard + 512 MB) and removes the zip after the upload. The zip goes up in one PUT from the file (no copy in
memory), checked against the storage's MD5 ETag.

`python bundle.py --local items.json OUT_DIR [KEYS_ENV]` runs the shard items without the hub (read-only bucket key, nothing
uploaded): a try with a few small sources.
"""
import csv
import gzip
import hashlib
import io
import json
import os
import random
import re
import shutil
import signal
import sys
import tempfile
import time
import zipfile
from urllib.parse import urlsplit

TASK = "bundle"
SHARD_DIGITS = 2
PREFIX = "bundle"
COLS = ["sha256", "key", "host", "ext", "url", "content_type", "bytes", "final_url", "fetched_at", "projects", "readers",
        "records", "record_ids", "archive"]
MANIFEST = ["sha256", "path_in_zip", "zip", "url", "final_url", "host", "content_type", "bytes", "fetched_at", "projects",
            "readers", "records_made", "record_ids_sample", "archive_capture", "status"]
STORED = {".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".gz", ".xlsx", ".docx", ".pptx", ".ods", ".odt", ".7z",
          ".rar", ".mp4", ".mp3", ".jp2"}
FREE_MARGIN = 512 * 1024 * 1024
LINKS_PER_CALL = 100            # the hub's read-urls takes at most 100 keys
CHUNK = 1 << 20
stop = False

README = """Saved source copies of civic-officials (cityofficials.s1d.me)
==============================================================

What the files are
- Each sources-<shard>.zip holds the pages and files that the civic-officials readers fetched from public government web
  sites (HTML pages, PDF files, JSON answers of public APIs, CSV and spreadsheet files).
- A file is the exact bytes that the reader got, as fetched. Its name is <host>/<sha256><ext>: the web site host, then the
  SHA-256 hash of the bytes. The same bytes are kept once, also when two pages gave them.
- The shard of a file is the first {digits} hex digit(s) of its SHA-256. Example: a file with hash 3fa9... is in sources-3f.zip.
- manifest.csv in each zip (and sources.csv.gz for all shards) gives one row per file: sha256, path in the zip, url asked,
  final url, host, content type, bytes, fetch time (UTC), the hub projects that saved it, the readers that read it, the
  number of records made from it, up to 3 record ids, an archive.s1d.me capture of the same url (if any), and the status
  ("ok", or why the file is not in the zip).

How records point to the files
- Every record that a reader made carries "src": {{"sha256", "url"}} (and a "trail" record id). On cityofficials.s1d.me each
  row has a source link; its hash is the same SHA-256 (first 16 hex digits on the page).
- To find the file of a record: take src.sha256, open sources-<first {digits} hex digits>.zip, read the row of that sha256
  in manifest.csv, and open path_in_zip.
- How a record gets its src (most exact first): the reader names the exact bytes (src_sha256); else the url that it read
  when that url gave one answer; else the only source of that queue item; else the record's own url field. Details:
  provenance.py in https://github.com/s1d-labs/civic-officials.
- You can check a file: its SHA-256 must be the hash in its name.

Public records
- The files are copies of pages and files that Indian government bodies publish on public web sites. They are kept so that
  each entry on cityofficials.s1d.me can be checked against the page it came from.
- Rights in the content stay with the publishing bodies. The copies are given for checking, research and public-interest
  use. The pages can be out of date: check the live site before you rely on a name or number.

Build: {built} UTC. Shards: {shards}. Files: {files}. Original bytes: {bytes}.
"""


def on_signal(*_):
    global stop
    stop = True


def host_of(url):
    try:
        h = (urlsplit(url or "").hostname or "").lower()
    except ValueError:
        h = ""
    h = re.sub(r"[^a-z0-9.-]", "_", h).strip(".")
    return h or "unknown-host"


def ext_of_key(key, sha):
    """'.html' of '<project>/sources/ab/<sha>.html.gz'."""
    name = key.rsplit("/", 1)[-1]
    if name.endswith(".gz"):
        name = name[:-3]
    rest = name[len(sha):] if name.startswith(sha) else os.path.splitext(name)[1]
    rest = rest.lower() if re.fullmatch(r"\.[A-Za-z0-9]{1,8}", rest or "") else ""
    return rest or ".bin"


def std_key(project, sha, ext):
    return f"{project}/sources/{sha[:2]}/{sha}{ext}.gz"


def copy_key(r):
    """The bucket key of a payload row: the "key" column, or (when empty) the standard key under the first project."""
    return r[1] or std_key(r[9].split(";")[0], r[0], r[3])


def row(sha, key, url, final_url, ctype, nbytes, fetched_at, projects, readers, records, record_ids, archive):
    """One compact payload row (COLS order). key is "" when it is the standard key under the first project (copy_key)."""
    final_url = final_url or ""
    ext = ext_of_key(key, sha)
    if key == std_key((projects or "").split(";")[0], sha, ext):
        key = ""
    return [sha, key, host_of(final_url or url), ext, url or "", ctype or "", int(nbytes or 0),
            "" if final_url == url else final_url, fetched_at or "", projects or "", readers or "", int(records or 0),
            "|".join(record_ids or []), archive or ""]


def list_hash(rows):
    """Hash of the shard's source list (the sha256 values): the zip changes only when this changes."""
    return hashlib.sha256("\n".join(sorted(r[0] for r in rows)).encode()).hexdigest()


def rel(path):
    return f"{PREFIX}/{path}"


def zip_name(shard):
    return f"sources-{shard}.zip"


def manifest_row(r, shard, status):
    d = dict(zip(COLS, r))
    return [d["sha256"], f"{d['host']}/{d['sha256']}{d['ext']}" if status == "ok" else "", zip_name(shard), d["url"],
            d["final_url"] or d["url"], d["host"], d["content_type"], d["bytes"], d["fetched_at"], d["projects"], d["readers"],
            d["records"], d["record_ids"], d["archive"], status]


def date_time(at):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)", at or "")
    t = tuple(int(x) for x in m.groups()) if m else (1980, 1, 1, 0, 0, 0)
    return t if t[0] >= 1980 else (1980, 1, 1, 0, 0, 0)


def gunzip_chunks(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:
        while True:
            b = g.read(CHUNK)
            if not b:
                break
            yield b


def check_copy(raw, sha):
    """'' when the gzip copy decompresses to bytes with this sha256, else why not."""
    if raw is None:
        return "copy not in the bucket"
    h = hashlib.sha256()
    try:
        for b in gunzip_chunks(raw):
            h.update(b)
    except (OSError, EOFError, zipfile.BadZipFile) as e:
        return f"copy did not decompress: {type(e).__name__}"
    return "" if h.hexdigest() == sha else "copy does not match its sha256"


def write_shard(path, shard, rows, fetch, metric=None):
    """Write the zip of one shard at `path`. fetch(rows) yields (row, gzip bytes or None) for a batch of rows, one download
    at a time (one copy in memory). Returns (manifest rows, files written, missing)."""
    manifest, written, missing = [], 0, 0
    rows = sorted(rows, key=lambda r: (r[2], r[0]))
    with zipfile.ZipFile(path, "w", allowZip64=True) as zf:
        for i in range(0, len(rows), LINKS_PER_CALL):
            if stop:
                raise InterruptedError("stopped by signal")
            batch = rows[i:i + LINKS_PER_CALL]
            for r, raw in fetch(batch):
                sha, ext = r[0], r[3]
                why = check_copy(raw, sha)
                if why:
                    missing += 1
                    manifest.append(manifest_row(r, shard, why))
                    if metric:
                        metric("bundle_missing")
                    continue
                zi = zipfile.ZipInfo(f"{r[2]}/{sha}{ext}", date_time(r[8]))
                zi.compress_type = zipfile.ZIP_STORED if ext in STORED else zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                with zf.open(zi, "w", force_zip64=r[6] > 1 << 31) as out:
                    for b in gunzip_chunks(raw):
                        out.write(b)
                written += 1
                manifest.append(manifest_row(r, shard, "ok"))
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(MANIFEST)
        w.writerows(manifest)
        zf.writestr(zipfile.ZipInfo("manifest.csv", time.gmtime()[:6]), buf.getvalue().encode(), zipfile.ZIP_DEFLATED)
        zf.writestr(zipfile.ZipInfo("README.txt", time.gmtime()[:6]),
                    readme(1, written, sum(r[6] for r in rows)).encode(), zipfile.ZIP_DEFLATED)
    return manifest, written, missing


def readme(shards, files, nbytes, built=None):
    return README.format(digits=SHARD_DIGITS, built=built or time.strftime("%Y-%m-%d %H:%M", time.gmtime()), shards=shards,
                         files=f"{files:,}", bytes=f"{nbytes:,}")


def file_sums(path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(CHUNK):
            md5.update(b)
            sha.update(b)
    return md5.hexdigest(), sha.hexdigest()


def csv_gz(manifest, header=True):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if header:
        w.writerow(MANIFEST)
    w.writerows(manifest)
    return gzip.compress(buf.getvalue().encode(), 6)


# ---- hub side: read links, uploads

class Bucket:
    """The family bucket through the hub: read links and upload links only (no storage key)."""

    def __init__(self, hub, session):
        self.hub, self.s = hub, session

    def get(self, key, timeout=(20, 300)):
        """Bytes of one object (full key '<project>/...'), or None."""
        return self.get_many([key], timeout).get(key)

    def get_many(self, keys, timeout=(20, 300)):
        return dict(self.iter(keys, timeout))

    def iter(self, keys, timeout=(20, 300)):
        """(key, bytes or None) for each key, one download at a time; read links asked 100 at a time per project."""
        import requests
        by_proj = {}
        for k in keys:
            by_proj.setdefault(k.split("/", 1)[0], []).append(k)
        for proj, ks in by_proj.items():
            for i in range(0, len(ks), LINKS_PER_CALL):
                links = self.hub.read_urls(proj, ks[i:i + LINKS_PER_CALL])
                for k in ks[i:i + LINKS_PER_CALL]:
                    t = time.time()
                    try:
                        r = self.s.get(links[k], timeout=timeout)
                    except requests.RequestException:
                        self.hub.metric("http_error")
                        self.hub.error()
                        yield k, None
                        continue
                    self.hub.metric("n_http")
                    self.hub.metric("t_http_s", time.time() - t)
                    if r.status_code != 200 and r.status_code != 404:
                        self.hub.metric(f"http_{r.status_code}")
                    yield k, (r.content if r.status_code == 200 else None)

    def put_file(self, path, local, content_type, attempts=8):
        """One PUT straight from the file (no copy in memory), checked against the storage's MD5 ETag. Returns the key."""
        import requests
        md5, _ = file_sums(local)
        size = os.path.getsize(local)
        last = None
        for i in range(attempts):
            link = self.hub.call("POST", f"/api/v1/runs/{self.hub.run_id}/upload-urls",
                                 {"files": [{"path": path, "content_type": content_type}]})["urls"][0]
            try:
                with open(local, "rb") as f:
                    r = requests.put(link["url"], data=f, headers={**link["headers"], "Content-Length": str(size)},
                                     timeout=(30, 1800))
                etag = r.headers.get("ETag", "").strip('"')
                if r.status_code in (200, 201) and (not etag or etag == md5):
                    self.hub.metric("uploaded_files")
                    self.hub.metric("uploaded_bytes", size)
                    return link["key"]
                last = RuntimeError(f"upload of {path}: HTTP {r.status_code}, etag {etag or '-'} vs md5 {md5}")
            except requests.RequestException as e:
                last = e
            if i < attempts - 1:
                time.sleep(min(60.0, 2 ** i) * random.uniform(0.5, 1.5))
        self.hub.metric("upload_failed")
        raise last


def shard_state(bucket, project, shard):
    raw = bucket.get(f"{project}/{rel(f'shards/{shard}.json')}")
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return None


def run_shard(item, hub, bucket, project, workdir):
    """Build, upload and record one shard. Returns (status, fetched, error)."""
    p = item["payload"]
    shard, rows = p["shard"], p["rows"]
    if p.get("cols", COLS) != COLS:
        return "failed", 0, "payload columns differ from this checkout's COLS"
    old = shard_state(bucket, project, shard)
    if old and old.get("list_hash") == p["list_hash"] and old.get("zip_key"):
        hub.metric("bundle_skipped")
        return "done", 0, ""
    need = sum(r[6] for r in rows) + FREE_MARGIN
    free = shutil.disk_usage(workdir).free
    if free < need:
        return "failed", 0, f"disk: {free / 1e9:.1f} GB free, {need / 1e9:.1f} GB needed"
    local = os.path.join(workdir, zip_name(shard))
    try:
        def fetch(batch):
            by_key = {}
            for r in batch:
                by_key.setdefault(copy_key(r), []).append(r)
            for k, raw in bucket.iter(list(by_key)):
                for r in by_key[k]:
                    yield r, raw
        manifest, written, missing = write_shard(local, shard, rows, fetch, hub.metric)
        _, zsha = file_sums(local)
        zsize = os.path.getsize(local)
        zkey = bucket.put_file(rel(zip_name(shard)), local, "application/zip")
    finally:
        if os.path.exists(local):
            os.remove(local)
    state = {"shard": shard, "list_hash": p["list_hash"], "zip_key": zkey, "zip_bytes": zsize, "zip_sha256": zsha,
             "files": written, "missing": missing, "raw_bytes": sum(r[6] for r in rows), "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "run_id": hub.run_id}
    # the manifest first, the state last: a state in the bucket means the zip and its manifest are there
    hub.upload_many([(rel(f"manifests/{shard}.csv.gz"), csv_gz(manifest), "application/gzip")])
    hub.upload_many([(rel(f"shards/{shard}.json"), json.dumps(state, indent=1).encode(), "application/json")])
    hub.metric("bundle_files", written)
    return "done", written, ""


def run_index(item, hub, bucket, project):
    want = item["payload"]["shards"]
    keys = {s: f"{project}/{rel(f'shards/{s}.json')}" for s in want}
    got = bucket.get_many(list(keys.values()))
    states, waiting = {}, []
    for s, h in sorted(want.items()):
        try:
            st = json.loads(got.get(keys[s]) or b"null")
        except ValueError:
            st = None
        if not st or st.get("list_hash") != h:
            waiting.append(s)
        else:
            states[s] = st
    if waiting:
        return "failed", 0, f"waiting for {len(waiting)} shards: {' '.join(waiting[:20])}"[:200]
    mkeys = {s: f"{project}/{rel(f'manifests/{s}.csv.gz')}" for s in want}
    mans = bucket.get_many(list(mkeys.values()))
    out = io.BytesIO()
    n_rows = 0
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=6) as g:
        g.write((",".join(MANIFEST) + "\n").encode())
        for s in sorted(want):
            raw = mans.get(mkeys[s])
            if raw is None:
                return "failed", 0, f"manifest of shard {s} is not in the bucket"
            lines = gzip.decompress(raw).split(b"\n", 1)
            body = lines[1] if len(lines) > 1 else b""
            n_rows += body.count(b"\n")
            g.write(body)
    files = sum(st["files"] for st in states.values())
    raw_bytes = sum(st["raw_bytes"] for st in states.values())
    built = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    index = {"built_at": built, "shard_digits": SHARD_DIGITS, "files": files, "rows": n_rows,
             "missing": sum(st["missing"] for st in states.values()), "raw_bytes": raw_bytes,
             "zip_bytes": sum(st["zip_bytes"] for st in states.values()), "sources_csv": f"{project}/{rel('sources.csv.gz')}",
             "readme": f"{project}/{rel('README.txt')}",
             "shards": [{k: states[s][k] for k in ("shard", "zip_key", "zip_bytes", "zip_sha256", "files", "missing", "raw_bytes",
                                                   "built_at", "list_hash")} for s in sorted(states)]}
    hub.upload_many([(rel("sources.csv.gz"), out.getvalue(), "application/gzip"),
                     (rel("README.txt"), readme(len(states), files, raw_bytes, built[:16].replace("T", " ")).encode(), "text/plain; charset=utf-8")])
    hub.upload_many([(rel("index.json"), json.dumps(index, indent=1).encode(), "application/json")])
    return "done", len(states), ""


def main():
    import requests
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 600
    workdir = os.environ.get("BUNDLE_DIR") or tempfile.gettempdir()
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    bucket = Bucket(hub, requests.Session())
    try:
        while time.time() < deadline and not stop:
            if hub.settings.get("paused"):
                time.sleep(30)
                continue
            try:
                items = hub.claim(1, steal=True, retry_failed=True)
            except requests.RequestException:
                time.sleep(30)
                continue
            if not items:
                break
            item = items[0]
            try:
                if item["payload"].get("kind") == "index":
                    st, n, err = run_index(item, hub, bucket, project)
                else:
                    st, n, err = run_shard(item, hub, bucket, project, workdir)
            except InterruptedError as e:
                hub.complete([item["key"]], "failed", error=str(e)[:200])
                break
            except Exception as e:  # noqa: BLE001 - one bad shard must not stop the worker
                st, n, err = "failed", 0, f"{type(e).__name__}: {e}"[:200]
            if st == "done":
                hub.complete([item["key"]], "done", fetched=n)
            else:
                hub.complete([item["key"]], "failed", error=err)
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(items_file, out_dir, keys="/etc/scrape-hub/member-keys/sarthak.env"):
    """Shard items without the hub: read the copies with a read-only key (audit.read_env / audit.s3_get), write the zips and
    manifests to out_dir, upload nothing. For a try with a few small sources (seeds/build_bundle.py --sample)."""
    import requests
    import audit
    env, sess = audit.read_env(keys), requests.Session()
    os.makedirs(out_dir, exist_ok=True)
    for it in json.load(open(items_file, encoding="utf-8")):
        p = it["payload"]
        if p.get("kind") != "shard":
            continue

        def fetch(batch):
            for r in batch:
                yield r, audit.s3_get(env, copy_key(r), sess)
        path = os.path.join(out_dir, zip_name(p["shard"]))
        manifest, written, missing = write_shard(path, p["shard"], p["rows"], fetch)
        with open(os.path.join(out_dir, f"{p['shard']}.csv.gz"), "wb") as f:
            f.write(csv_gz(manifest))
        print(json.dumps({"shard": p["shard"], "files": written, "missing": missing, "zip_bytes": os.path.getsize(path),
                          "raw_bytes": sum(r[6] for r in p["rows"]), "status": sorted({m[-1] for m in manifest})}))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--local":
        local(sys.argv[2], sys.argv[3], *sys.argv[4:5])
    else:
        sys.exit(main())
