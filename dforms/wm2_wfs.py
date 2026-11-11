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
"""
import json
from urllib.parse import urlencode

from dforms._wm2_arcgis import store
from dforms.wm2_arcgis import towns

MAX_PAGES = 400


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


def page_wfs(get, p):
    """All features of the layer (and cql), as one FeatureCollection. Returns (fc, why); why is "" on success."""
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
    ids = [f.get("id") for f in feats if f.get("id") is not None]
    if len(ids) != len(set(ids)):
        return fc, "duplicate feature ids across pages (unstable order: set \"sort\")"
    return fc, ""


def fetch(p, get):
    fc, why = page_wfs(get, p)
    if why:
        return [], [], why
    if not fc["features"]:
        return [], [], "no features in " + p["layer"]
    source, state = p["source"], str(p.get("state", "XX"))
    path, blob, ctype = store(fc, f"wardmaps/{source}/{state}/{p.get('chunk') or p['layer'].split(':')[-1]}")
    fields = p.get("fields") or {}
    recs = []
    for key, t in sorted(towns(fc, fields).items()):
        recs.append((f"wm2_{source}:{state}-{key}", {
            "type": "wm_layer_town", "source": source, "state": state, "body_name": t["body_name"], "body_code": t["body_code"],
            "district": t["district"], "wards": len(t["wards"]) if fields.get("ward_no") else t["features"],
            "features": t["features"], "file": path, "url": p["url"], "layer": p["layer"], "where": p.get("cql", ""),
            "ward_kind": p.get("ward_kind", ""), "vintage": p.get("vintage", "")}))
    return recs, [(path, blob, ctype)], ""
