"""Ward boundary layers on public GeoServer WFS services (first: TNGIS, Tamil Nadu): download each layer ONCE into the bucket.

Fetch once, process anywhere: this reader pages one WFS feature type (GetFeature, WFS 2.0.0, GeoJSON output, EPSG:4326, no
login, no token), stores it gzipped and writes one record per town in the layer, like dforms/wm2_arcgis.py. civic-india
reads the saved copy later, matches each town to civic.ulb and checks ward counts and overlap with the town boundary.

TNGIS: the public viewer https://tngis.tn.gov.in/generic_viewer/ sets geoServerURL = "https://tngis.tn.gov.in/tngismaps/wms"
(assets/js/global.js); the same GeoServer answers WFS at /tngismaps/wfs (GetCapabilities lists 1,482 feature types).

Payload (seeds/wm2_tngis.json):
  {"reader": "wm2_wfs", "url": "<WFS endpoint>", "layer": "<workspace:name>", "state": "<LGD state code>",
   "india_only": <true when only an Indian IP is answered>, "source": "<short source key>", "chunk": "<file stem>",
   optional "cql" (CQL_FILTER), optional "page" (features per request, default 500),
   optional "fields": {"ward_no", "ward_name", "body_name", "body_code", "district"} (attribute names in the layer),
   optional "sort" (sortBy: one attribute or several, "a,b"), optional "ward_kind", optional "vintage"}
GeoServer answers a paged request (startIndex) on a table without a primary key only with a sortBy ("Cannot do natural order
without a primary key"): every TNGIS layer item has "sort".
Paging: startIndex + count with sortBy on "sort" (default: no sortBy = the server's natural order, stable for one table);
the run is complete only when the features received = numberMatched of the first page.
Stored file: wardmaps/<source>/<state>/<chunk>.geojson.gz. Records "wm2_<source>:<state>-<body key>" as in wm2_arcgis.

Other layers (seeds/tngis_services.json, 2026-11-12: police stations and jurisdictions, PDS shops, health facilities, schools,
anganwadi, CSC / e-Sevai, offices, taluk / block / revenue village / village panchayat / town boundaries): payload "kind"
(e.g. "police_station", "taluk_boundary") instead of the ward "fields". The layer goes to gis/<source>/<state>/<chunk>.geojson.gz
and the item writes ONE record "gis_<source>:<state>-<chunk>" = {"type": "gis_layer", "kind", "layer", "file", "features",
"fields" (every attribute name), "geometry_types", "has_z", "by_district" (when payload "district" names the attribute),
"expect" (numberMatched at seeding), "one_shot"}. civic-india reads the saved copy (keeps every attribute, UTF-8 Tamil text).

Layer mode (payload "kind") streams the pages: each page is written to the gzip file at
once, one feature per line ({"type":"FeatureCollection","features":[ / <feature>, / ... / ]}), so a layer of 900,000 features
does not sit in memory as Python objects, and civic-india's tngis_load.py can read it line by line. Payload "page" sets the
features per request; pages up to ceil(numberMatched / page) are asked for (MAX_PAGES is the floor). Record ids: one per layer
("gis_<source>:<state>-<chunk>"). Bug fixed 2026-11-13: a ward layer without body "fields" (wm2_tngis chennai-ward,
ponneri-ward, ...) wrote its one town as "wm2_<source>:<state>-all", so all such layers overwrote one record (the 41 TNGIS
service layers of 2026-11-12, run by a checkout without layer mode, did the same); that town now gets the chunk as its key.

Stable order: a layer without a primary key gives new feature ids on each request, and paging over a non-unique sortBy can
repeat or skip rows. After paging, the reader checks for repeated ids and repeated features (same properties and geometry);
on a repeat it asks for the whole layer in ONE request (count = numberMatched, up to ONE_SHOT_MAX) and keeps that answer
when it has exactly numberMatched features.
"""
import gzip
import hashlib
import io
import json
import math
from collections import Counter
from urllib.parse import urlencode

from dforms._wm2_arcgis import store
from dforms.wm2_arcgis import towns

METHOD = "geojson layer (WFS GetFeature)"     # source trail (provenance.py): how this reader reads its sources

MAX_PAGES = 400
ONE_SHOT_MAX = 250000


def get_page(get, p, start, count):
    """One GetFeature page. Returns (parsed JSON, why)."""
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": p["layer"],
         "outputFormat": "application/json", "srsName": "EPSG:4326", "startIndex": str(start), "count": str(count)}
    if p.get("sort"):
        q["sortBy"] = p["sort"]
    if p.get("cql"):
        q["CQL_FILTER"] = p["cql"]
    r = get(p["url"] + "?" + urlencode(q))
    if r is None:
        return None, "no answer"
    try:
        d = r.json()
    except ValueError:
        return None, "not JSON (" + r.text[:80].replace("\n", " ") + ")"
    if not isinstance(d, dict) or d.get("type") != "FeatureCollection":
        return None, "not a FeatureCollection: " + json.dumps(d)[:120]
    return d, ""


def max_pages(p, page):
    """Pages to ask for at most: MAX_PAGES, or more when the seed's expect needs more."""
    exp = p.get("expect")
    return max(MAX_PAGES, math.ceil(exp / page) + 5) if isinstance(exp, int) and exp > 0 else MAX_PAGES


def _fhash(f):
    return hashlib.sha1(json.dumps([f.get("properties"), f.get("geometry")], sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")).digest()


def _repeats(feats):
    """True when a feature id or a whole feature (properties + geometry) comes twice."""
    ids = [f.get("id") for f in feats if f.get("id") is not None]
    if len(ids) != len(set(ids)):
        return True
    seen = set()
    for f in feats:
        h = hashlib.sha1(json.dumps([f.get("properties"), f.get("geometry")], sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).digest()
        if h in seen:
            return True
        seen.add(h)
    return False


def page_wfs(get, p):
    """All features of the layer (and cql), as one FeatureCollection. Returns (fc, why); why is "" on success.
    fc["one_shot"] is True when the pages repeated features and one whole-layer request replaced them."""
    page = int(p.get("page", 500))
    feats, total = [], None
    for _ in range(max_pages(p, page)):
        d, why = get_page(get, p, len(feats), page)
        if d is None:
            return {"type": "FeatureCollection", "features": feats}, \
                why if not feats else f"stopped after {len(feats)} features: {why}"
        if total is None:
            total = d.get("numberMatched", d.get("totalFeatures"))
            total = total if isinstance(total, int) else None
        got = d.get("features") or []
        feats.extend(got)
        if not got or len(got) < page or (total is not None and len(feats) >= total):
            break
    fc = {"type": "FeatureCollection", "features": feats}
    if total is not None and len(feats) != total:
        return fc, f"got {len(feats)} of {total} features"
    if len(feats) > page and _repeats(feats):
        if total is None or total > ONE_SHOT_MAX:
            return fc, "repeated features across pages (unstable order: set \"sort\")"
        d, why = get_page(get, p, 0, total)
        if d is None:
            return fc, "repeated features across pages; one-request retry failed: " + why
        got = d.get("features") or []
        if len(got) != total:
            return fc, f"repeated features across pages; one-request retry got {len(got)} of {total}"
        return {"type": "FeatureCollection", "features": got, "one_shot": True}, ""
    return fc, ""


def _txt(v):
    return "" if v is None else str(v).strip()


class LayerSink:
    """Writes features to a gzip GeoJSON file, one feature per line, and keeps the layer record's counts (no feature list)."""

    def __init__(self, district=""):
        self.buf = io.BytesIO()
        self.gz = gzip.GzipFile(fileobj=self.buf, mode="wb", compresslevel=6, mtime=0)
        self.gz.write(b'{"type":"FeatureCollection","features":[\n')
        self.n, self.fields, self.gtypes, self.has_z, self.by_d = 0, {}, Counter(), False, Counter()
        self.ids, self.hashes, self.repeat, self.district = set(), {}, False, district

    def add(self, f, page_no=0):
        """page_no: a feature equal to one of an EARLIER page is a repeat (paging order not stable); equal rows inside one
        answer are the layer's own data and are kept."""
        fid = f.get("id")
        if fid is not None:
            if fid in self.ids:
                self.repeat = True
            self.ids.add(fid)
        h = _fhash(f)
        if self.hashes.setdefault(h, page_no) != page_no:
            self.repeat = True
        pr = f.get("properties") or {}
        for k in pr:
            self.fields.setdefault(k, None)
        g = f.get("geometry") or {}
        self.gtypes[g.get("type") or "none"] += 1
        if not self.has_z:
            c = g.get("coordinates")
            while isinstance(c, list) and c and isinstance(c[0], list):
                c = c[0]
            self.has_z = isinstance(c, list) and len(c) > 2
        if self.district:
            self.by_d[_txt(pr.get(self.district)) or "?"] += 1
        self.gz.write((b",\n" if self.n else b"") + json.dumps(f, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        self.n += 1

    def close(self):
        self.gz.write(b"\n]}\n")
        self.gz.close()
        return self.buf.getvalue()


def stream_wfs(get, p):
    """Layer mode: all features of the layer into a LayerSink, page by page. Returns (sink, one_shot, why); why "" on success.
    On the first repeated feature (unstable order) paging stops; a layer up to ONE_SHOT_MAX is then asked for in one request."""
    page = int(p.get("page", 500))
    sink, total = LayerSink(p.get("district", "")), None
    for page_no in range(max_pages(p, page)):
        d, why = get_page(get, p, sink.n, page)
        if d is None:
            return sink, False, why if not sink.n else f"stopped after {sink.n} features: {why}"
        if total is None:
            total = d.get("numberMatched", d.get("totalFeatures"))
            total = total if isinstance(total, int) else None
        got = d.get("features") or []
        for f in got:
            sink.add(f, page_no)
        if sink.repeat:
            break
        if not got or len(got) < page or (total is not None and sink.n >= total):
            break
    if sink.repeat:
        if total is None or total > ONE_SHOT_MAX:
            return sink, False, "repeated features across pages (unstable order: set \"sort\")"
        d, why = get_page(get, p, 0, total)
        if d is None:
            return sink, False, "repeated features across pages; one-request retry failed: " + why
        got = d.get("features") or []
        if len(got) != total:
            return sink, False, f"repeated features across pages; one-request retry got {len(got)} of {total}"
        sink = LayerSink(p.get("district", ""))
        for f in got:
            sink.add(f)
        return sink, True, ""
    if total is not None and sink.n != total:
        return sink, False, f"got {sink.n} of {total} features"
    return sink, False, ""


def layer_record(p, sink, path, one_shot):
    """The one record of a non-ward layer (payload "kind")."""
    rec = {"type": "gis_layer", "kind": p.get("kind") or "layer", "source": p["source"], "state": str(p.get("state", "XX")),
           "layer": p["layer"], "url": p["url"], "where": p.get("cql", ""), "file": path, "features": sink.n,
           "fields": list(sink.fields), "geometry_types": dict(sink.gtypes), "has_z": sink.has_z, "one_shot": one_shot,
           "expect": p.get("expect"), "sort": p.get("sort", ""), "vintage": p.get("vintage", ""),
           "src_pos": {"layer_file": path}}      # the whole layer, every feature (the pages are in the trail)
    for k in ("category", "dup_of"):
        if p.get(k):
            rec[k] = p[k]
    if p.get("district"):
        rec["by_district"] = dict(sorted(sink.by_d.items()))
    return rec


def chunk_of(p):
    return p.get("chunk") or p["layer"].split(":")[-1].replace(" ", "_").lower()


def fetch(p, get):
    source, state, chunk = p["source"], str(p.get("state", "XX")), chunk_of(p)
    if p.get("kind"):
        # one layer = one file + one gis_layer record of its own (never a shared "-all" ward record)
        sink, one_shot, why = stream_wfs(get, p)
        if why:
            return [], [], why
        if not sink.n:
            return [], [], "no features in " + p["layer"]
        path = f"gis/{source}/{state}/{chunk}.geojson.gz"
        return [(f"gis_{source}:{state}-{chunk}", layer_record(p, sink, path, one_shot))], \
            [(path, sink.close(), "application/gzip")], ""
    fc, why = page_wfs(get, p)
    if why:
        return [], [], why
    if not fc["features"]:
        return [], [], "no features in " + p["layer"]
    path, blob, ctype = store({"type": "FeatureCollection", "features": fc["features"]}, f"wardmaps/{source}/{state}/{chunk}")
    fields = p.get("fields") or {}
    recs = []
    for key, t in sorted(towns(fc, fields).items()):
        key = chunk if key == "all" else key          # no body name / code in the layer: the layer's own key
        recs.append((f"wm2_{source}:{state}-{key}", {
            "type": "wm_layer_town", "source": source, "state": state, "body_name": t["body_name"], "body_code": t["body_code"],
            "district": t["district"], "wards": len(t["wards"]) if fields.get("ward_no") else t["features"],
            "features": t["features"], "file": path, "url": p["url"], "layer": p["layer"], "where": p.get("cql", ""),
            "ward_kind": p.get("ward_kind", ""), "vintage": p.get("vintage", ""),
            "src_pos": {"layer_file": path, "feature_index": t["index"], **({"feature_id": t["ids"]} if t["ids"] else {})}}))
    return recs, [(path, blob, ctype)], ""
