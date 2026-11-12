"""Rajasthan urban ward boundaries (RajDharaa, gisprod.rajasthan.gov.in GISSurvey/Ward_Bndy_ULB/MapServer/0): page the layer
as GeoJSON and store it in the bucket once. Answers only an Indian IP (payload "india_only": true).

The layer needs an ArcGIS token. The state's public Urban GIS viewer (rajdharaa.rajasthan.gov.in/citizenUDH/, guest, no login)
gets one in js/registerTokens.js: an empty POST to RajdharaaCommonWebAPI/api/GenerateGISToken (the APIBaseUrl in js/Config.js).
The answer is {"Status": true, "Messages": [{"ServiceName": "dynamicquery", "Token": "..."}, ...]}; the viewer gives the
"dynamicquery" token to every request to gisprod.../dynamicquery/rest/services. This reader does the same (owner OK,
2026-11-11): a new token for each run, sent only in the POST body of the layer queries. It never goes into the repo, a record,
a file or an error text. When the layer says the token is invalid or expired (498/499), the reader gets a new one once.
If the token API ever needs a login or a captcha, the item fails ("token API: ..."): do not work around that.

On 2026-11-11 the layer held 6,447 ward polygons of 177 towns (CITY_NAME), fields OBJECTID, AREA_NAME, GIS_CODE (town + ward
number), WARD_NO, DISTRICT_NAME, CITY_NAME, CREATED_/LAST_EDITED_USER and _DATE (5,048 wards dated 2026-03-19 .. 2026-05-06,
the rest blank). Jaipur 150, Jodhpur 100, Kota 100 wards: the 2025 delimitation after the city corporations were joined again.

Payload (seeds/wm2_rj_gis.json): {"reader": "wm2_rj_gis", "url": "<layer url>", "token_api": "<GenerateGISToken url>",
  "viewer": "<viewer page, sent as Referer>", "service": "dynamicquery", "where": "1=1", "oid": "OBJECTID", "page": 1000,
  "state": "8", "source": "rj_gis", "chunk": "ward_bndy_ulb", "india_only": true, "ward_kind": "election"}
Stored file: wardmaps/rj_gis/8/ward_bndy_ulb.geojson.gz (one FeatureCollection, EPSG:4326, all attributes as served).
Records "wm2_rj_gis:8-<town slug>" = {"type": "wm_layer_town", "source": "rj_gis", "state": "8", "body_name" (CITY_NAME),
  "body_code": "" (the layer has no town code), "district" (most wards), "districts" {name: wards} (only when > 1),
  "area_names" {AREA_NAME: wards} (parts of a town, e.g. PIPAR CITY NORTH / SOUTH; DEGANA in GOREDI CHANCHA), "wards" (distinct
  ward numbers, leading zeros removed), "features", "created_first", "created_last", "last_edit" (ms, None when blank),
  "file", "url", "where", "ward_kind", "vintage"}.
The reader asks for the feature count first; a run that gets fewer features than that count is not stored (the hub retries).
"""
import collections
import json
import re

from dforms._wm2_arcgis import page_layer, query, store

METHOD = "arcgis feature layer (geojson)"     # source trail (provenance.py): how this reader reads its sources

LAYER = "https://gisprod.rajasthan.gov.in/dynamicquery/rest/services/GISSurvey/Ward_Bndy_ULB/MapServer/0"
TOKEN_API = "https://rajdharaa.rajasthan.gov.in/RajdharaaCommonWebAPI/api/GenerateGISToken"
VIEWER = "https://rajdharaa.rajasthan.gov.in/citizenUDH/"
TOKEN_ERRORS = (498, 499)       # ArcGIS: invalid / expired token, token required


def new_token(get, api, viewer, service="dynamicquery"):
    """(token, why) from the public token API, as the viewer calls it: an empty POST, no credentials."""
    r = get(api, method="POST", data=b"", headers={"Referer": viewer, "X-Requested-With": "XMLHttpRequest",
                                                "Content-Type": "application/x-www-form-urlencoded"})
    if r is None:
        return None, "token API: no answer"
    try:
        d = r.json()
    except ValueError:
        return None, "token API: not JSON (" + r.text[:60].replace("\n", " ") + ")"
    if not isinstance(d, dict) or not d.get("Status"):
        return None, "token API: Status not true"
    tok = next((m.get("Token") for m in d.get("Messages") or [] if isinstance(m, dict) and m.get("ServiceName") == service), None)
    if not tok or not isinstance(tok, str):
        return None, f"token API: no {service} token"
    return tok, ""


def _token_error(r):
    """True when the layer answer is an ArcGIS token error (498/499)."""
    if r is None:
        return False
    head = r.text[:300]
    if '"error"' not in head:
        return False
    try:
        code = (r.json().get("error") or {}).get("code")
    except (ValueError, AttributeError):
        return False
    return code in TOKEN_ERRORS


def with_token(get, api, viewer, service="dynamicquery"):
    """A get() for page_layer/query that adds the token to each POST body. Returns (get, why); why is "" on success."""
    state = {}
    tok, why = new_token(get, api, viewer, service)
    if not tok:
        return None, why
    state["token"] = tok

    def tget(url, method="GET", data=None, headers=None):
        h = dict(headers or {}, Referer=viewer)
        r = get(url, method=method, data=dict(data or {}, token=state["token"]), headers=h)
        if _token_error(r):
            tok, _ = new_token(get, api, viewer, service)
            if tok:
                state["token"] = tok
                r = get(url, method=method, data=dict(data or {}, token=tok), headers=h)
        return r
    return tget, ""


def _txt(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _ward(v):
    w = _txt(v)
    return w.lstrip("0") or w


def towns(fc, path, p):
    by = collections.defaultdict(list)
    at = collections.defaultdict(list)            # source trail: feature places in the stored FeatureCollection
    for i, f in enumerate(fc.get("features") or []):
        pr = f.get("properties") or {}
        by[_txt(pr.get("CITY_NAME"))].append(pr)
        at[_txt(pr.get("CITY_NAME"))].append((i, f.get("id", pr.get("OBJECTID", pr.get("objectid")))))
    recs = []
    for name, rows in sorted(by.items()):
        dist = collections.Counter(_txt(r.get("DISTRICT_NAME")) for r in rows if _txt(r.get("DISTRICT_NAME")))
        area = collections.Counter(_txt(r.get("AREA_NAME")) for r in rows if _txt(r.get("AREA_NAME")))
        wards = {_ward(r.get("WARD_NO")) for r in rows if _txt(r.get("WARD_NO"))}
        made = [r["CREATED_DATE"] for r in rows if isinstance(r.get("CREATED_DATE"), (int, float))]
        edit = [r[k] for r in rows for k in ("LAST_EDITED_DATE", "CREATED_DATE") if isinstance(r.get(k), (int, float))]
        recs.append((f"wm2_{p['source']}:{p['state']}-{_slug(name) or 'none'}", {
            "type": "wm_layer_town", "source": p["source"], "state": p["state"], "body_name": name, "body_code": "",
            "district": dist.most_common(1)[0][0] if dist else "", "districts": dict(dist) if len(dist) > 1 else {},
            "area_names": dict(area) if set(area) != {name} else {}, "wards": len(wards), "features": len(rows),
            "created_first": int(min(made)) if made else None, "created_last": int(max(made)) if made else None,
            "last_edit": int(max(edit)) if edit else None, "file": path, "url": p["url"], "where": p.get("where") or "1=1",
            "ward_kind": p.get("ward_kind", ""), "vintage": p.get("vintage", ""),
            "src_pos": {"layer_file": path, "feature_index": [i for i, _ in at[name]],
                        "feature_id": [x for _, x in at[name] if x is not None]}}))
    return recs


def fetch(p, get):
    p = dict({"url": LAYER, "token_api": TOKEN_API, "viewer": VIEWER, "service": "dynamicquery", "where": "1=1",
              "oid": "OBJECTID", "page": 1000, "state": "8", "source": "rj_gis", "chunk": "ward_bndy_ulb"}, **p)
    tget, why = with_token(get, p["token_api"], p["viewer"], p["service"])
    if tget is None:
        return [], [], why
    where = p["where"]
    d, why = query(tget, p["url"], {"where": where, "returnCountOnly": "true", "f": "json"})
    if d is None:
        return [], [], "count: " + why
    count = d.get("count")
    fc, why = page_layer(tget, p["url"], where=where, oid=p["oid"], page=int(p["page"]))
    if why:
        return [], [], why
    if not fc["features"]:
        return [], [], "no features for " + where
    if isinstance(count, int) and len(fc["features"]) < count:
        return [], [], f"got {len(fc['features'])} of {count} features"
    path, blob, ctype = store(fc, f"wardmaps/{p['source']}/{p['state']}/{p['chunk']}")
    return towns(fc, path, p), [(path, blob, ctype)], ""


if __name__ == "__main__":          # python -m dforms.wm2_rj_gis: the record shape of a saved FeatureCollection (no network)
    import sys
    fc = json.load(open(sys.argv[1], encoding="utf-8"))
    for rid, rec in towns(fc, "local", {"source": "rj_gis", "state": "8", "url": LAYER}):
        print(rid, json.dumps(rec, ensure_ascii=False))
