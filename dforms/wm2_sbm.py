"""SBM-Urban live ward layer (prodgis.sbmurban.org, SBMGISProduction/GISProductionData/MapServer/3 "WardBoundary"): page it
as GeoJSON and store it in the bucket once. Answers only an Indian IP (payload "india_only": true).

Our copy (DB civic geo.sbm_wards, 70,417 wards) ends 2025-01-30. On 2026-11-11 the live layer held 73,603 wards of 3,827
(state, ulbcode, status) groups, last edit the same day.

One item = one state, or one ulbcode range of a big state (seeds/wm2_sbm.json, made by civic-india/wm2_sbm.py seeds).
The last range of each state is open (no "ulb_to"), so new towns with higher codes fall in it; the item "rest" takes every
ward whose statecode is not one of the seeded states (empty or blank statecode included).

Payload: {"reader": "wm2_sbm", "url": "<layer url>", "state": "<SBM statecode = LGD state code>", "ulb_from": "800001",
          "ulb_to": "800500" (exclusive; absent = open), "not_states": [...] (item "rest" only), "india_only": true,
          "page": 1000}
Stored file: wardmaps/sbm/<state>/<ulb_from>-<ulb_to|end>.geojson.gz (all fields, EPSG:4326, full geometry).
Records "wm2_sbm:<ulbcode>" = {"type": "wm_layer_town", "source": "sbm", "body_code" (SBM ulbcode), "body_name", "state",
  "district", "wards" (not REJECTED), "rejected", "status" {APPROVED: n, OPEN: n, ...}, "last_edit" (ms), "file", "url"}.
civic-india/wm2_sbm.py reads the stored files, compares them with geo.sbm_wards and matches the towns to LGD bodies.
"""
import collections
import re

from dforms._wm2_arcgis import page_layer, store

LAYER = "https://prodgis.sbmurban.org/server/rest/services/SBMGISProduction/GISProductionData/MapServer/3"


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def where(p):
    if p.get("not_states") is not None:
        return "statecode IS NULL OR TRIM(statecode) = '' OR statecode NOT IN (" + ",".join(q(s) for s in p["not_states"]) + ")"
    w = [f"statecode = {q(p['state'])}"]
    if p.get("ulb_from"):
        w.append(f"ulbcode >= {q(p['ulb_from'])}")
    if p.get("ulb_to"):
        w.append(f"ulbcode < {q(p['ulb_to'])}")
    return " AND ".join(w)


def towns(fc, path, url, state):
    by = collections.defaultdict(list)
    for f in fc["features"]:
        pr = f.get("properties") or {}
        by[(pr.get("ulbcode") or "").strip()].append(pr)
    recs = []
    for code, rows in sorted(by.items()):
        st = collections.Counter((r.get("status") or "").strip() or "none" for r in rows)
        name = collections.Counter((r.get("ulbname") or "").strip() for r in rows if (r.get("ulbname") or "").strip())
        dist = collections.Counter((r.get("districtname") or "").strip() for r in rows if (r.get("districtname") or "").strip())
        sc = collections.Counter((r.get("statecode") or "").strip() for r in rows if (r.get("statecode") or "").strip())
        edits = [r.get(k) for r in rows for k in ("updateddate", "createdate") if isinstance(r.get(k), (int, float))]
        recs.append((f"wm2_sbm:{code or 'none'}", {
            "type": "wm_layer_town", "source": "sbm", "body_code": code, "body_name": name.most_common(1)[0][0] if name else "",
            "state": sc.most_common(1)[0][0] if sc else state, "district": dist.most_common(1)[0][0] if dist else "",
            "wards": len(rows) - st.get("REJECTED", 0), "rejected": st.get("REJECTED", 0), "status": dict(st),
            "last_edit": int(max(edits)) if edits else None, "file": path, "url": url}))
    return recs


def fetch(p, get):
    url = p.get("url") or LAYER
    fc, why = page_layer(get, url, where=where(p), oid="objectid", page=int(p.get("page", 1000)))
    if why:
        return [], [], why
    if not fc["features"]:
        return [], [], "no wards in this range"
    tag = "rest" if p.get("not_states") is not None else p["state"]
    stem = f"wardmaps/sbm/{tag}/" + re.sub(r"[^0-9A-Za-z]+", "", str(p.get("ulb_from") or "start")) + "-" + \
        re.sub(r"[^0-9A-Za-z]+", "", str(p.get("ulb_to") or "end"))
    path, blob, ctype = store(fc, stem)
    return towns(fc, path, url, tag), [(path, blob, ctype)], ""
