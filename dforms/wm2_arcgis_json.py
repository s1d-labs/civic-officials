"""Ward boundary layers on OLD public ArcGIS REST servers (10.2 and older: no GeoJSON output, no paging): download each layer
ONCE into the bucket, as GeoJSON, like dforms/wm2_arcgis.py.

Why a second reader: dforms/wm2_arcgis.py asks for f=geojson and pages with resultRecordCount + orderByFields. ArcGIS 10.2
servers answer "Output format not supported" to f=geojson and ignore the order (supportsAdvancedQueries false), so keyset
paging could skip features. This reader:
  1. asks for every object id of `where` (returnIdsOnly=true),
  2. asks for the features by objectIds, `page` ids at a time (f=json, outSR=4326),
  3. turns the Esri JSON polygons (rings) into GeoJSON (Polygon / MultiPolygon: a clockwise ring starts a polygon, a
     counter-clockwise ring is a hole of the outer ring that holds it),
  4. stores the layer only when it got exactly the features of step 1 (else the item fails and the hub retries).
First layer (2026-11-12): TGRAC (Telangana Remote Sensing Applications Centre, www.tgrac.telangana.gov.in, ArcGIS 10.22),
GovtHospitals_Folder/Health_Facilities_Mapping/MapServer/51 "Wards Municipality": 3,461 wards of 141 municipalities and
corporations, all Telangana outside GHMC (fields FID, Name, Ward_No, ULB_Name, Category, Shape_Area; Shape_Area is stale).
The same ward set (40 towns around Hyderabad only) is TCUR_Folder/TCUR_Telangana_Core_Urban_Region_V2/MapServer/48. No token, no login.

Payload (seeds/wm2_tgrac.json): as dforms/wm2_arcgis.py ("url", "where", "oid", "state", "india_only", "source", "chunk",
"page" (ids per request, default 200), "fields", "ward_kind", "vintage").
Stored file: wardmaps/<source>/<state>/<chunk>.geojson.gz (FeatureCollection, EPSG:4326, every attribute as served; feature
"id" = the object id). Records "wm2_<source>:<state>-<body key>" as in dforms/wm2_arcgis.py (src_pos = the feature's place
in the stored file and its object id).
"""
from dforms._wm2_arcgis import query, store
from dforms.wm2_arcgis import towns     # same records as wm2_arcgis

METHOD = "arcgis layer, esri json (object ids, then features by id), converted to geojson"


def _area2(ring):
    """Twice the signed area (shoelace); negative = clockwise (an Esri outer ring)."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:] + ring[:1]))


def _inside(pt, ring):
    x, y = pt[0], pt[1]
    hit = False
    for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def esri_geometry(g):
    """Esri JSON geometry -> GeoJSON geometry (polygons, polylines, points), or None."""
    if not isinstance(g, dict):
        return None
    if "rings" in g:
        polys = []
        holes = []
        for ring in g["rings"] or []:
            ring = [list(p[:2]) for p in ring]
            if len(ring) < 4:
                continue
            (polys if _area2(ring) < 0 else holes).append([ring])
        if not polys:                   # rings drawn the other way round: take them as outer rings
            polys, holes = holes, []
        for (h,) in holes:
            owner = next((p for p in polys if _inside(h[0], p[0])), polys[-1])
            owner.append(h)
        if len(polys) == 1:
            return {"type": "Polygon", "coordinates": polys[0]}
        return {"type": "MultiPolygon", "coordinates": polys}
    if "paths" in g:
        paths = [[list(p[:2]) for p in path] for path in g["paths"] or []]
        return {"type": "MultiLineString", "coordinates": paths} if paths else None
    if "x" in g and "y" in g and g["x"] is not None:
        return {"type": "Point", "coordinates": [g["x"], g["y"]]}
    return None


def page_layer_json(get, layer_url, where="1=1", oid="OBJECTID", page=200):
    """(FeatureCollection, why): every feature of `where` as GeoJSON; why is "" only when all ids came back."""
    d, why = query(get, layer_url, {"where": where, "returnIdsOnly": "true", "f": "json"})
    if d is None:
        return {"type": "FeatureCollection", "features": []}, why
    ids = sorted(i for i in d.get("objectIds") or [] if isinstance(i, int))
    oid = d.get("objectIdFieldName") or oid
    feats = []
    for k in range(0, len(ids), page):
        chunk = ids[k:k + page]
        d, why = query(get, layer_url, {"objectIds": ",".join(map(str, chunk)), "outFields": "*", "returnGeometry": "true",
                                        "outSR": "4326", "f": "json"})
        if d is None:
            return {"type": "FeatureCollection", "features": feats}, f"stopped after {len(feats)} features: {why}"
        for f in d.get("features") or []:
            a = f.get("attributes") or {}
            feats.append({"type": "Feature", "id": a.get(oid), "geometry": esri_geometry(f.get("geometry")), "properties": a})
    fc = {"type": "FeatureCollection", "features": feats}
    got = {f["id"] for f in feats}
    if got != set(ids):
        return fc, f"got {len(got)} of {len(ids)} object ids"
    return fc, ""


def fetch(p, get):
    where = p.get("where") or "1=1"
    fc, why = page_layer_json(get, p["url"], where=where, oid=p.get("oid", "OBJECTID"), page=int(p.get("page", 200)))
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
            "ward_kind": p.get("ward_kind", ""), "vintage": p.get("vintage", ""),
            "src_pos": {"layer_file": path, "feature_index": t["index"], **({"feature_id": t["ids"]} if t["ids"] else {})}}))
    return recs, [(path, blob, ctype)], ""
