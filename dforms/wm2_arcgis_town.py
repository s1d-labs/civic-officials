"""One town's ward layer on a public ArcGIS REST server (city / state GIS portals): download the layer ONCE into the bucket.

Same as dforms/wm2_arcgis.py (keyset paging with dforms/_wm2_arcgis.py, layer stored gzipped as served), for layers that hold
the wards of ONE town and have no town name or code field (e.g. HARSAC OneMap: "MCF Ward Boundary" = Faridabad, "Ward Boundary
2023" = Gurugram / Manesar). The seed names the town; the record carries it, so civic-india can match the layer to civic.ulb.

Payload (seeds/wm2_*.json):
  {"reader": "wm2_arcgis_town", "url": "<layer url>", "where": "<default 1=1>", "oid": "<objectid field>", "state": "<LGD state code>",
   "india_only": <bool>, "source": "<short source key>", "chunk": "<file stem, unique per layer>",
   "body_name": "<town name as in LGD>", "body": "<LGD local_body_code>", optional "district",
   "fields": {"ward_no", optional "ward_name"} (attribute names in the layer), optional "page", "ward_kind", "vintage"}
Stored file: wardmaps/<source>/<state>/<chunk>.geojson.gz.
Record "wm2_<source>:<state>-<body>" = {"type": "wm_layer_town", "source", "state", "body_name", "body_code" (= LGD code from the
  seed), "lgd_code", "district", "wards", "features", "file", "url", "where", "ward_kind", "vintage", "src_pos"}.
"""
from dforms import wm2_arcgis

METHOD = "arcgis feature layer of one town (geojson)"     # source trail (provenance.py): how this reader reads its sources


def fetch(p, get):
    fields = {k: v for k, v in (p.get("fields") or {}).items() if k in ("ward_no", "ward_name")}
    recs, files, why = wm2_arcgis.fetch({**p, "fields": fields}, get)
    if why:
        return recs, files, why
    if len(recs) != 1:
        return [], [], f"expected one town in the layer, got {len(recs)}"
    _, d = recs[0]
    d = {**d, "body_name": p["body_name"], "body_code": str(p["body"]), "lgd_code": str(p["body"]),
         "district": p.get("district", "")}
    return [(f"wm2_{p['source']}:{p.get('state', 'XX')}-{p['body']}", d)], files, ""
