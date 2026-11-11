"""Odisha polling stations with lat/lon (2025-26 data, after rationalisation): the CEO's map
(https://ceoodisha.nic.in/map.html) reads a public GeoServer WFS layer, bbd_ceo:booth_location_m on mapserver.odisha4kgeo.in.
One queue item = one Assembly Constituency (147). 38,067 points on 2026-11-11 (resultType=hits).

This layer has NO BLO name or phone. Rows are polling-station rows (part number, building, lat/lon, PIN, block, panchayat,
police station id, part number before rationalisation), so blo.py makes records "blo:OD:<ac>:<part>" with an empty
blo_name. The Odisha BLO lists themselves are not open: the "BLO Contact Details" Google Drive file is not shared
(404/403), and the BLO-BLA minutes at /en/test/ need a captcha.
The WFS answered from Germany on 2026-11-11. Properties are kept verbatim in "cells", plus "lat" and "lon".
"""
import requests

WFS = "https://mapserver.odisha4kgeo.in/geoserver/bbd_ceo/ows"
LAYER = "bbd_ceo:booth_location_m"
N_AC = 147


def _name(v):
    """'1 (Padampur)' -> 'Padampur'; 'S1801 (Bargarh)' -> 'Bargarh'."""
    v = str(v or "")
    return v[v.find("(") + 1:v.rfind(")")].strip() if "(" in v and v.endswith(")") else v


def items(s=None):
    return [{"key": f"blo2-od-ps-{ac:03d}", "payload": {"kind": "form-blo2_od", "state": "OD", "ac_no": ac,
                                                       "url": f"{WFS}?typeName={LAYER}&ac_no={ac}", "expected": 260}}
            for ac in range(1, N_AC + 1)]


def rows_from_geojson(doc, p):
    rows = []
    for f in doc.get("features") or []:
        pr = dict(f.get("properties") or {})
        g = f.get("geometry") or {}
        lon, lat = (g.get("coordinates") or [None, None])[:2] if g.get("type") == "Point" else (None, None)
        cells = {k: ("" if v is None else v) for k, v in pr.items()}
        cells["lat"], cells["lon"] = lat, lon
        part = pr.get("part_number")
        rows.append({"ac_no": pr.get("ac_no", p.get("ac_no")), "ac_name": _name(pr.get("asmby_no")),
                     "district": _name(pr.get("district_cd")), "part_no": part,
                     "station": pr.get("psbuilding_name_and_address") or pr.get("part_name") or "",
                     "blo_name": "", "blo_phone": "", "cells": cells})
    rows.sort(key=lambda r: (r["part_no"] is None, r["part_no"] or 0))
    return rows


def fetch(s, p):
    params = {"service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": LAYER,
              "outputFormat": "application/json", "CQL_FILTER": f"ac_no={int(p['ac_no'])}"}
    r = s.get(WFS, params=params, timeout=(20, 120))
    r.raise_for_status()
    try:
        doc = r.json()
    except ValueError:
        raise RuntimeError("WFS answer is not JSON")
    return rows_from_geojson(doc, p)


if __name__ == "__main__":
    import json
    import sys
    s = requests.Session()
    print(json.dumps(fetch(s, {"ac_no": int(sys.argv[1]) if len(sys.argv) > 1 else 1})[:2], ensure_ascii=False, indent=1))
