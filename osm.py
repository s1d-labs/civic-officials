"""Task `osm`: public-service points and admin boundaries from OpenStreetMap (owner, 2026-11-14: "try OSM then, let OSM help").

One queue item = one Geofabrik extract (India: https://download.geofabrik.de/asia/india-latest.osm.pbf, about 1.6 GB). The task
downloads the file ONCE (checked against Geofabrik's .md5), filters it with pyosmium (pip `osmium`, no apt, no sudo) and uploads
compressed GeoJSON-lines files per kind to the family bucket. No request goes to a government site.

Licence: OpenStreetMap data is under the Open Database Licence 1.0 (ODbL). Credit "(c) OpenStreetMap contributors"
(https://www.openstreetmap.org/copyright). A public database that combines these files with other data must be shared under the
ODbL. Keep the files in their own tables and source field; do not mix them silently into government records.

Layout in the bucket (project civic-officials-osm, so every key starts with "civic-officials-osm/"):
  osm/<date>/<kind>.geojsonl.gz     one GeoJSON Feature per line (kinds: KINDS below, and "boundary")
  osm/<date>/filtered.osm.pbf       the filtered objects with the ways and nodes they need (to process again without a download)
  osm/<date>/manifest.json          source file, md5, sizes, counts, sha256 of each file, licence and credit
  osm/latest.json                   {"date", "manifest"}: written last, so a reader of latest.json finds complete files
<date> = the extract's date (YYYY-MM-DD, from the dated Geofabrik file name india-YYMMDD.osm.pbf, else the PBF header).

Feature properties: osm_type (node / way / relation), osm_id, version, timestamp (UTC), kind, geom ("point" for a node,
"centroid" for a way or a multipolygon: the area-weighted centroid of its outer rings), tags (ALL tags of the object: name,
name:hi, name:<lang>, operator, addr:*, phone, website, ref, wikidata ...). Boundary features carry the (multi)polygon and
admin_level.

Queue item payload: {"url": "<.osm.pbf url>", "region": "india", "force": false}. The item is done without work when
osm/<date>/manifest.json is already in the bucket (force = true builds it again).

Disk: a GitHub runner has about 14 GB free; the task needs the extract + about 1.5 x its size for the filtered file and the
outputs, and checks the free space first. Work folder: OSM_DIR (default: the temp folder); removed at the end.

`python osm.py --local FILE.osm.pbf OUT_DIR` filters a local file without the hub (writes the same files to OUT_DIR).
"""
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import sys
import tempfile
import time

TASK = "osm"
PREFIX = "osm"
AMENITY = ("police", "fire_station", "post_office", "school", "college", "hospital", "clinic", "doctors", "pharmacy", "bank",
           "atm", "courthouse", "townhall", "community_centre", "library", "social_facility")
KINDS = AMENITY + ("office_government", "office_administrative", "healthcare")
ADMIN_LEVELS = {str(n) for n in range(2, 11)}
FILTER_KEYS = ("amenity", "office", "healthcare", "boundary")
LICENSE = {"license": "ODbL-1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
           "attribution": "© OpenStreetMap contributors", "copyright_url": "https://www.openstreetmap.org/copyright",
           "note": "A public database that holds this data with other data must be shared under the ODbL."}
FREE_MARGIN = 2 * 1024 ** 3
CHUNK = 8 << 20
stop = False


def on_signal(*_):
    global stop
    stop = True


class Stopped(Exception):
    pass


def check_stop():
    if stop:
        raise Stopped("stopped by signal")


# ---- pure parts (tested without a PBF)

def point_kind(tags):
    """The point kind of an object's tags (dict), or None. amenity first, then office, then healthcare."""
    a = tags.get("amenity")
    if a in AMENITY:
        return a
    o = tags.get("office")
    if o == "government":
        return "office_government"
    if o == "administrative":
        return "office_administrative"
    h = tags.get("healthcare")
    if h and h != "no":
        return "healthcare"
    return None


def is_boundary(tags):
    return tags.get("boundary") == "administrative" and tags.get("admin_level", "").strip() in ADMIN_LEVELS


def ring_centroid(coords):
    """(signed area, cx, cy) of a closed ring [(lon, lat), ...] (planar; small areas)."""
    a = cx = cy = 0.0
    ox, oy = coords[0]                  # relative to the first point: less rounding error at lon 77, lat 28
    n = len(coords)
    for i in range(n - 1):
        x0, y0 = coords[i][0] - ox, coords[i][1] - oy
        x1, y1 = coords[i + 1][0] - ox, coords[i + 1][1] - oy
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a /= 2.0
    if abs(a) < 1e-14:
        xs, ys = [p[0] for p in coords], [p[1] for p in coords]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a, ox + cx / (6 * a), oy + cy / (6 * a)


def centroid(rings):
    """Area-weighted centroid of outer rings (each a list of (lon, lat)); the mean of the points when all are degenerate."""
    rings = [r for r in rings if r]
    if not rings:
        return None
    tot = sx = sy = 0.0
    for r in rings:
        if len(r) >= 4 and r[0] == r[-1]:
            a, x, y = ring_centroid(r)
            tot += abs(a)
            sx += x * abs(a)
            sy += y * abs(a)
    if tot > 0:
        return round(sx / tot, 7), round(sy / tot, 7)
    pts = [p for r in rings for p in r]
    return round(sum(p[0] for p in pts) / len(pts), 7), round(sum(p[1] for p in pts) / len(pts), 7)


def feature(osm_type, osm_id, version, ts, kind, geom_kind, geometry, tags):
    props = {"osm_type": osm_type, "osm_id": osm_id, "version": version, "timestamp": ts, "kind": kind, "geom": geom_kind,
             "tags": tags}
    if kind == "boundary":
        props["admin_level"] = tags.get("admin_level")
    return {"type": "Feature", "id": f"{osm_type[0]}{osm_id}", "geometry": geometry, "properties": props}


def date_of(url, header_ts=None, last_modified=None):
    """YYYY-MM-DD of a dated Geofabrik file name (india-261113.osm.pbf), else of the PBF header timestamp, else Last-Modified."""
    m = re.search(r"-(\d{2})(\d{2})(\d{2})\.osm\.pbf$", url or "")
    if m:
        return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if header_ts:
        return header_ts[:10]
    if last_modified:
        try:
            return datetime.datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return time.strftime("%Y-%m-%d", time.gmtime())


# ---- filtering (pyosmium)

def _ts(o):
    try:
        return o.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (AttributeError, ValueError):
        return None


def _tags(o):
    return {t.k: t.v for t in o.tags}


def wanted(o):
    t = o.tags
    return point_kind({"amenity": t.get("amenity", ""), "office": t.get("office", ""),
                       "healthcare": t.get("healthcare", "")}) is not None or \
        (t.get("boundary") == "administrative" and t.get("admin_level", "").strip() in ADMIN_LEVELS)


def filter_pbf(src, out):
    """Pass 1: the wanted objects and every way and node they reference -> out (PBF). Returns the count of wanted objects."""
    import osmium
    n = 0
    with osmium.BackReferenceWriter(out, ref_src=src, overwrite=True) as w:
        for o in osmium.FileProcessor(src).with_filter(osmium.filter.KeyFilter(*FILTER_KEYS)):
            if wanted(o):
                w.add(o)
                n += 1
                if n % 100000 == 0:
                    check_stop()
    return n


def extract(filtered, out_dir, metric=None):
    """Pass 2 over the filtered file: one .geojsonl.gz per kind in out_dir. Returns {kind: count} and the 'skipped' counts."""
    import osmium
    gj = osmium.geom.GeoJSONFactory()
    files, counts = {}, {}
    skipped = {"no_geometry": 0, "bad_location": 0}
    levels = {}

    def out(kind, feat):
        f = files.get(kind)
        if f is None:
            f = files[kind] = gzip.open(os.path.join(out_dir, f"{kind}.geojsonl.gz"), "wt", encoding="utf-8", compresslevel=6)
            counts[kind] = 0
        f.write(json.dumps(feat, ensure_ascii=False, separators=(",", ":")) + "\n")
        counts[kind] += 1

    n = 0
    try:
        for o in osmium.FileProcessor(filtered).with_areas():
            n += 1
            if n % 200000 == 0:
                check_stop()
            if not o.tags:
                continue
            if o.is_node():
                tags = _tags(o)
                k = point_kind(tags)
                if k:
                    try:
                        geom = {"type": "Point", "coordinates": [round(o.location.lon, 7), round(o.location.lat, 7)]}
                    except osmium.InvalidLocationError:
                        skipped["bad_location"] += 1
                        continue
                    out(k, feature("node", o.id, o.version, _ts(o), k, "point", geom, tags))
            elif o.is_way():
                tags = _tags(o)
                k = point_kind(tags)
                if k:
                    try:
                        ring = [(n_.lon, n_.lat) for n_ in o.nodes]
                    except osmium.InvalidLocationError:
                        skipped["bad_location"] += 1
                        continue
                    c = centroid([ring])
                    if not c:
                        skipped["no_geometry"] += 1
                        continue
                    out(k, feature("way", o.id, o.version, _ts(o), k, "centroid", {"type": "Point", "coordinates": list(c)}, tags))
            elif o.is_relation():
                tags = _tags(o)
                if point_kind(tags) and tags.get("type") not in ("multipolygon", "boundary"):
                    skipped["no_geometry"] += 1        # a site / other relation: no area, no point
            elif o.is_area():
                tags = _tags(o)
                from_way = o.from_way()
                otype, oid = ("way" if from_way else "relation"), o.orig_id()
                if is_boundary(tags):
                    try:
                        geom = json.loads(gj.create_multipolygon(o))
                    except (RuntimeError, osmium.InvalidLocationError):
                        skipped["no_geometry"] += 1
                        continue
                    out("boundary", feature(otype, oid, o.version, _ts(o), "boundary", "polygon", geom, tags))
                    lv = tags.get("admin_level", "").strip()
                    levels[lv] = levels.get(lv, 0) + 1
                if not from_way:
                    k = point_kind(tags)
                    if k:
                        try:
                            rings = [[(n_.lon, n_.lat) for n_ in r] for r in o.outer_rings()]
                        except osmium.InvalidLocationError:
                            skipped["bad_location"] += 1
                            continue
                        c = centroid(rings)
                        if not c:
                            skipped["no_geometry"] += 1
                            continue
                        out(k, feature("relation", oid, o.version, _ts(o), k, "centroid", {"type": "Point", "coordinates": list(c)}, tags))
    finally:
        for f in files.values():
            f.close()
    if metric:
        metric("osm_features", sum(counts.values()))
    return counts, skipped, levels


def file_sums(path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(CHUNK), b""):
            md5.update(b)
            sha.update(b)
    return md5.hexdigest(), sha.hexdigest()


def header_ts(path):
    import osmium
    try:
        r = osmium.io.Reader(path, osmium.osm.osm_entity_bits.NOTHING)
        try:
            return r.header().get("osmosis_replication_timestamp") or None
        finally:
            r.close()
    except Exception:  # noqa: BLE001 - the header is a fallback only
        return None


def process(src, work, metric=None):
    """Filter src and write the kind files to work/out. Returns (out_dir, filtered path, counts, skipped, levels, wanted)."""
    out_dir = os.path.join(work, "out")
    os.makedirs(out_dir, exist_ok=True)
    filtered = os.path.join(out_dir, "filtered.osm.pbf")
    t = time.time()
    n_wanted = filter_pbf(src, filtered)
    if metric:
        metric("osm_filter_s", time.time() - t)
    check_stop()
    t = time.time()
    counts, skipped, levels = extract(filtered, out_dir, metric)
    if metric:
        metric("osm_extract_s", time.time() - t)
    return out_dir, filtered, counts, skipped, levels, n_wanted


# ---- hub side

def resolve(session, hub, url):
    """(final url, size, last-modified) of the extract: the dated file that "-latest" redirects to."""
    import requests
    t = time.time()
    try:
        r = session.head(url, allow_redirects=True, timeout=60)
    except requests.RequestException:
        hub.metric("http_error")
        hub.error()
        raise
    hub.metric("n_http")
    hub.metric("t_http_s", time.time() - t)
    if r.status_code != 200:
        hub.metric(f"http_{r.status_code}")
        raise RuntimeError(f"HEAD {url}: HTTP {r.status_code}")
    return r.url, int(r.headers.get("Content-Length") or 0), r.headers.get("Last-Modified")


def download(session, hub, url, path, attempts=3):
    """Stream url to path; check the size and Geofabrik's <url>.md5 (when there is one). Returns (md5, bytes)."""
    import requests
    want = None
    t = time.time()
    try:
        r = session.get(url + ".md5", timeout=60)
        hub.metric("n_http")
        hub.metric("t_http_s", time.time() - t)
        if r.status_code == 200 and re.match(r"^[0-9a-f]{32}\b", r.text.strip()):
            want = r.text.split()[0]
        elif r.status_code != 200:
            hub.metric(f"http_{r.status_code}")
    except requests.RequestException:
        hub.metric("http_error")
    last = None
    for i in range(attempts):
        check_stop()
        md5, n = hashlib.md5(), 0
        t = time.time()
        try:
            with session.get(url, stream=True, timeout=(30, 300)) as r:
                hub.metric("n_http")
                if r.status_code != 200:
                    hub.metric(f"http_{r.status_code}")
                    if r.status_code in (403, 429, 503):
                        hub.block()
                    raise RuntimeError(f"GET {url}: HTTP {r.status_code}")
                size = int(r.headers.get("Content-Length") or 0)
                with open(path, "wb") as f:
                    for b in r.iter_content(CHUNK):
                        if stop:
                            raise Stopped("stopped by signal")
                        f.write(b)
                        md5.update(b)
                        n += len(b)
            hub.metric("t_http_s", time.time() - t)
            hub.metric("osm_download_bytes", n)
            if size and n != size:
                raise RuntimeError(f"download: {n} of {size} bytes")
            if want and md5.hexdigest() != want:
                raise RuntimeError(f"download: md5 {md5.hexdigest()} is not Geofabrik's {want}")
            return md5.hexdigest(), n
        except Stopped:
            raise
        except (requests.RequestException, RuntimeError) as e:
            hub.metric("http_error")
            hub.error()
            last = e
            if i < attempts - 1:
                time.sleep(30 * (i + 1))
    raise last


def run_item(item, hub, bucket, project, work, session):
    """Download, filter, upload one extract. Returns (status, fetched, error)."""
    p = item["payload"]
    url, region = p["url"], p.get("region") or "india"
    final, size, lastmod = resolve(session, hub, url)
    date = date_of(final, None, lastmod)
    base = f"{PREFIX}/{date}"
    if not p.get("force") and bucket.get(f"{project}/{base}/manifest.json"):
        hub.metric("osm_skipped")
        return "done", 0, ""
    free = shutil.disk_usage(work).free
    need = int(size * 2.5) + FREE_MARGIN
    if free < need:
        return "failed", 0, f"disk: {free / 1e9:.1f} GB free, {need / 1e9:.1f} GB needed"
    src = os.path.join(work, os.path.basename(final.split("?")[0]) or "extract.osm.pbf")
    md5, nbytes = download(session, hub, final, src)
    hts = header_ts(src)
    if not re.search(r"-\d{6}\.osm\.pbf$", final) and hts:
        date = date_of(final, hts, lastmod)
        base = f"{PREFIX}/{date}"
    out_dir, filtered, counts, skipped, levels, n_wanted = process(src, work, hub.metric)
    os.remove(src)                                 # the extract is not needed any more: free the disk before the uploads
    files = {}
    for kind in sorted(counts):
        check_stop()
        local = os.path.join(out_dir, f"{kind}.geojsonl.gz")
        fmd5, fsha = file_sums(local)
        key = bucket.put_file(f"{base}/{kind}.geojsonl.gz", local, "application/gzip")
        files[kind] = {"key": key, "features": counts[kind], "bytes": os.path.getsize(local), "md5": fmd5, "sha256": fsha}
        os.remove(local)
    fmd5, fsha = file_sums(filtered)
    fkey = bucket.put_file(f"{base}/filtered.osm.pbf", filtered, "application/octet-stream")
    manifest = {"region": region, "date": date, "source_url": url, "file_url": final, "file_md5": md5, "file_bytes": nbytes,
                "replication_timestamp": hts, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "run_id": hub.run_id, "tool": f"pyosmium {_pyosmium_version()}",
                "filter": {"amenity": list(AMENITY), "office": ["government", "administrative"], "healthcare": "*",
                           "boundary": "administrative", "admin_level": sorted(ADMIN_LEVELS, key=int)},
                "objects_wanted": n_wanted, "files": files, "skipped": skipped, "boundary_levels": levels,
                "filtered_pbf": {"key": fkey, "bytes": os.path.getsize(filtered), "md5": fmd5, "sha256": fsha},
                "format": "GeoJSON Feature per line, gzip; properties: osm_type, osm_id, version, timestamp, kind, geom, tags"
                          " (all tags), admin_level (boundary)", **LICENSE}
    os.remove(filtered)
    hub.upload_many([(f"{base}/manifest.json", json.dumps(manifest, indent=1, ensure_ascii=False).encode(), "application/json")])
    hub.upload_many([(f"{PREFIX}/latest.json", json.dumps({"date": date, "region": region,
                                                         "manifest": f"{project}/{base}/manifest.json", **LICENSE},
                                                        ensure_ascii=False).encode(), "application/json")])
    hub.record(f"osm:{region}:{date}", {"type": "osm_extract", "region": region, "date": date, "file_url": final,
                                        "file_bytes": nbytes, "counts": counts, "manifest": f"{project}/{base}/manifest.json",
                                        **LICENSE})
    return "done", sum(counts.values()), ""


def _pyosmium_version():
    try:
        import osmium.version
        return osmium.version.pyosmium_release
    except Exception:  # noqa: BLE001
        return "?"


def main():
    import requests
    from scrape_hub_client import HubClient
    from bundle import Bucket
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 900
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    session = requests.Session()
    session.headers["User-Agent"] = "s1d-labs civic-officials osm task (+https://github.com/s1d-labs/civic-officials)"
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
            work = tempfile.mkdtemp(prefix="osm-", dir=os.environ.get("OSM_DIR") or None)
            try:
                st, n, err = run_item(item, hub, bucket, project, work, session)
            except Stopped as e:
                hub.complete([item["key"]], "failed", error=str(e))
                break
            except Exception as e:  # noqa: BLE001 - report the item as failed; the hub hands it out again
                st, n, err = "failed", 0, f"{type(e).__name__}: {e}"[:200]
            finally:
                shutil.rmtree(work, ignore_errors=True)
            if st == "done":
                hub.complete([item["key"]], "done", fetched=n)
            else:
                hub.complete([item["key"]], "failed", error=err)
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def local(src, out):
    """Filter a local .osm.pbf into out (same files as the task, no hub, no upload)."""
    os.makedirs(out, exist_ok=True)
    out_dir, filtered, counts, skipped, levels, n_wanted = process(src, out)
    print(json.dumps({"wanted": n_wanted, "counts": counts, "skipped": skipped, "boundary_levels": levels,
                      "files": {k: os.path.getsize(os.path.join(out_dir, f"{k}.geojsonl.gz")) for k in counts},
                      "filtered_bytes": os.path.getsize(filtered), "out": out_dir}, indent=1))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--local":
        local(sys.argv[2], sys.argv[3])
    else:
        main()
