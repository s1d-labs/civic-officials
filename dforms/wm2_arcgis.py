"""Ward boundary layers on public ArcGIS REST servers (state and city GIS portals): download each layer ONCE into the bucket.

Fetch once, process anywhere: this reader pages one feature layer (MapServer/N or FeatureServer/N, Query on, no token) with
dforms/_wm2_arcgis.py, stores it gzipped and writes one record per town in the layer. civic-india/wm2_portals.py reads the saved
copy later, matches each town to civic.ulb and checks ward counts and overlap with the town boundary.

Payload (seeds/wm2_*.json):
  {"reader": "wm2_arcgis", "url": "<layer url>", "where": "<SQL where, default 1=1>", "oid": "<objectid field>",
   "state": "<LGD state code>", "india_only": <true when only an Indian IP is answered>, "source": "<short source key>",
   "chunk": "<file stem, e.g. the layer name or a state code>", optional "page" (features per request, default 1000),
   optional "fields": {"ward_no", "ward_name", "body_name", "body_code", "district"} (field names in the layer),
   optional "ward_kind" ("election" | "revenue" | ""), optional "vintage" (date or year the source shows)}
Stored file: wardmaps/<source>/<state>/<chunk>.geojson.gz (one FeatureCollection, EPSG:4326, all attributes as served).
Records "wm2_<source>:<state>-<body key>" = {"type": "wm_layer_town", "source", "state", "body_name", "body_code" (the
  source's own code), "district", "wards" (distinct ward numbers, or features when the layer has no ward number), "features",
  "file", "url", "where", "ward_kind", "vintage"}.
A layer that stops part way (server error after some pages) is not stored: the item fails and the hub retries it.
"""
import re

from dforms._wm2_arcgis import page_layer, store


def _txt(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def towns(fc, fields):
    """{body key: {"body_name", "body_code", "district", "wards": set, "features": n}} from a FeatureCollection."""
    fb, fc_, fd, fw = (fields.get(k) for k in ("body_name", "body_code", "district", "ward_no"))
    out = {}
    for f in fc.get("features") or []:
        pr = f.get("properties") or {}
        name, code, dist = _txt(pr.get(fb)) if fb else "", _txt(pr.get(fc_)) if fc_ else "", _txt(pr.get(fd)) if fd else ""
        key = "-".join(x for x in (code, _slug(name), _slug(dist) if not code else "") if x) or "all"
        t = out.setdefault(key, {"body_name": name, "body_code": code, "district": dist, "wards": set(), "features": 0})
        t["features"] += 1
        if fw:
            w = _txt(pr.get(fw))
            if w:
                t["wards"].add(w)
    return out


def fetch(p, get):
    where = p.get("where") or "1=1"
    fc, why = page_layer(get, p["url"], where=where, oid=p.get("oid", "objectid"), page=int(p.get("page", 1000)))
    if why:
        return [], [], why
    if not fc["features"]:
        return [], [], "no features for " + where
    source, state = p["source"], str(p.get("state", "XX"))
    path, blob, ctype = store(fc, f"wardmaps/{source}/{state}/{p.get('chunk') or 'layer'}")
    fields = p.get("fields") or {}
    recs = []
    for key, t in sorted(towns(fc, fields).items()):
        recs.append((f"wm2_{source}:{state}-{key}", {
            "type": "wm_layer_town", "source": source, "state": state, "body_name": t["body_name"], "body_code": t["body_code"],
            "district": t["district"], "wards": len(t["wards"]) if fields.get("ward_no") else t["features"],
            "features": t["features"], "file": path, "url": p["url"], "where": where,
            "ward_kind": p.get("ward_kind", ""), "vintage": p.get("vintage", "")}))
    return recs, [(path, blob, ctype)], ""
