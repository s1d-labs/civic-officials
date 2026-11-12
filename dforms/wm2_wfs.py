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
   optional "sort" (sortBy attribute), optional "ward_kind", optional "vintage"}
Paging: startIndex + count with sortBy on "sort" (default: no sortBy = the server's natural order, stable for one table);
the run is complete only when the features received = numberMatched of the first page.
Stored file: wardmaps/<source>/<state>/<chunk>.geojson.gz. Records "wm2_<source>:<state>-<body key>" as in wm2_arcgis.

Other layers (seeds/tngis_services.json, 2026-11-12: police stations and jurisdictions, PDS shops, health facilities, schools,
anganwadi, CSC / e-Sevai, offices, taluk / block / revenue village / village panchayat / town boundaries): payload "kind"
(e.g. "police_station", "taluk_boundary") instead of the ward "fields". The layer goes to gis/<source>/<state>/<chunk>.geojson.gz
and the item writes ONE record "gis_<source>:<state>-<chunk>" = {"type": "gis_layer", "kind", "layer", "file", "features",
"fields" (every attribute name), "geometry_types", "has_z", "by_district" (when payload "district" names the attribute),
"expect" (numberMatched at seeding), "one_shot"}. civic-india reads the saved copy (keeps every attribute, UTF-8 Tamil text).

Stable order: a layer without a primary key gives new feature ids on each request, and paging over a non-unique sortBy can
repeat or skip rows. After paging, the reader checks for repeated ids and repeated features (same properties and geometry);
on a repeat it asks for the whole layer in ONE request (count = numberMatched, up to ONE_SHOT_MAX) and keeps that answer
when it has exactly numberMatched features.
"""
import hashlib
import json
from collections import Counter
from urllib.parse import urlencode

from dforms._wm2_arcgis import store
from dforms.wm2_arcgis import towns

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
    for _ in range(MAX_PAGES):
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


def layer_record(p, fc, path):
    """The one record of a non-ward layer (payload "kind")."""
    feats = fc["features"]
    fields, gtypes, has_z, by_d = {}, Counter(), False, Counter()
    for f in feats:
        for k in (f.get("properties") or {}):
            fields.setdefault(k, None)
        g = f.get("geometry") or {}
        gtypes[g.get("type") or "none"] += 1
        if not has_z:
            c = g.get("coordinates")
            while isinstance(c, list) and c and isinstance(c[0], list):
                c = c[0]
            has_z = isinstance(c, list) and len(c) > 2
        if p.get("district"):
            by_d[_txt((f.get("properties") or {}).get(p["district"])) or "?"] += 1
    rec = {"type": "gis_layer", "kind": p["kind"], "source": p["source"], "state": str(p.get("state", "XX")),
           "layer": p["layer"], "url": p["url"], "where": p.get("cql", ""), "file": path, "features": len(feats),
           "fields": list(fields), "geometry_types": dict(gtypes), "has_z": has_z, "one_shot": bool(fc.get("one_shot")),
           "expect": p.get("expect"), "sort": p.get("sort", ""), "vintage": p.get("vintage", "")}
    if p.get("district"):
        rec["by_district"] = dict(sorted(by_d.items()))
    return rec


def fetch(p, get):
    fc, why = page_wfs(get, p)
    if why:
        return [], [], why
    if not fc["features"]:
        return [], [], "no features in " + p["layer"]
    source, state = p["source"], str(p.get("state", "XX"))
    chunk = p.get("chunk") or p["layer"].split(":")[-1]
    if p.get("kind"):
        path, blob, ctype = store({"type": "FeatureCollection", "features": fc["features"]}, f"gis/{source}/{state}/{chunk}")
        return [(f"gis_{source}:{state}-{chunk}", layer_record(p, fc, path))], [(path, blob, ctype)], ""
    path, blob, ctype = store({"type": "FeatureCollection", "features": fc["features"]}, f"wardmaps/{source}/{state}/{chunk}")
    fields = p.get("fields") or {}
    recs = []
    for key, t in sorted(towns(fc, fields).items()):
        recs.append((f"wm2_{source}:{state}-{key}", {
            "type": "wm_layer_town", "source": source, "state": state, "body_name": t["body_name"], "body_code": t["body_code"],
            "district": t["district"], "wards": len(t["wards"]) if fields.get("ward_no") else t["features"],
            "features": t["features"], "file": path, "url": p["url"], "layer": p["layer"], "where": p.get("cql", ""),
            "ward_kind": p.get("ward_kind", ""), "vintage": p.get("vintage", "")}))
    return recs, [(path, blob, ctype)], ""
