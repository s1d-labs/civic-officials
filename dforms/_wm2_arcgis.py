"""Shared helper for wm2_* readers: page one ArcGIS REST feature layer (MapServer/N or FeatureServer/N with Query on) as GeoJSON.

Paging is by objectid (keyset): each request asks for `where AND <oid> > last`, ordered by the oid, `page` features at a time,
so the result is complete even when the server has no resultOffset support or the layer changes during the run.
The pages are joined into one FeatureCollection; the reader stores it gzipped in the bucket (fetch once, process anywhere)
and civic-india/wm2_*.py converts the saved copy.

    fc, why = page_layer(get, layer_url, where="1=1", oid="objectid", page=1000, out_fields="*")
    path, blob = store(fc, "wardmaps/sbm/09/800001-800500")     -> ("....geojson.gz", gzip bytes)
"""
import gzip
import json

MAX_PAGES = 400        # 400 x 1000 features: far above any one item; stops a loop on a server that ignores the oid filter


def query(get, layer_url, params):
    """One POST to <layer>/query. Returns the parsed JSON, or (None, why)."""
    r = get(layer_url.rstrip("/") + "/query", method="POST", data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r is None:
        return None, "no answer"
    try:
        d = r.json()
    except ValueError:
        return None, "not JSON (" + r.text[:80].replace("\n", " ") + ")"
    if isinstance(d, dict) and "error" in d:
        return None, "server error: " + json.dumps(d["error"])[:150]
    return d, ""


def page_layer(get, layer_url, where="1=1", oid="objectid", page=1000, out_fields="*", geometry=True, extra=None):
    """All features of `where`, as one GeoJSON FeatureCollection (EPSG:4326). Returns (fc, why); why is "" on success."""
    feats, last = [], -1
    for _ in range(MAX_PAGES):
        params = {"where": f"({where}) AND {oid} > {last}", "outFields": out_fields, "orderByFields": f"{oid} ASC",
                  "resultRecordCount": str(page), "returnGeometry": "true" if geometry else "false", "outSR": "4326",
                  "f": "geojson"}
        params.update(extra or {})
        d, why = query(get, layer_url, params)
        if d is None:
            return ({"type": "FeatureCollection", "features": feats}, why) if not feats else \
                ({"type": "FeatureCollection", "features": feats}, f"stopped after {len(feats)} features: {why}")
        got = d.get("features") or []
        if not got:
            break
        ids = [f.get("id", (f.get("properties") or {}).get(oid)) for f in got]
        ids = [i for i in ids if isinstance(i, int)]
        if not ids or max(ids) <= last:
            return {"type": "FeatureCollection", "features": feats + got}, "server ignored the objectid filter"
        feats.extend(got)
        last = max(ids)
        if len(got) < page and not d.get("exceededTransferLimit") and not (d.get("properties") or {}).get("exceededTransferLimit"):
            break
    return {"type": "FeatureCollection", "features": feats}, ""


def store(fc, stem):
    """(bucket path, gzip bytes, content type) for one FeatureCollection."""
    blob = gzip.compress(json.dumps(fc, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 6)
    return f"{stem}.geojson.gz", blob, "application/gzip"
