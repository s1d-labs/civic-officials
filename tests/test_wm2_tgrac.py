"""dforms/wm2_arcgis_json.py (old ArcGIS 10.2 servers: object ids first, then features by id, Esri JSON -> GeoJSON) on a saved
sample: 3 wards of Karimnagar from TGRAC GovtHospitals_Folder/Health_Facilities_Mapping layer 51 "Wards Municipality"
(tests/data/wm2/tgrac_his_karimnagar.json, 2026-11-12)."""
import gzip
import json

from test_dept_police import DATA, FakeGet
from test_wm2_portals import seed

from dforms import wm2_arcgis_json as w

SAMPLE = (DATA / "wm2" / "tgrac_his_karimnagar.json").read_bytes()


def route(ids):
    seen = []

    def answer(url, method, data):
        seen.append(data)
        assert method == "POST" and data["f"] == "json"
        if data.get("returnIdsOnly") == "true":
            return json.dumps({"objectIdFieldName": "FID", "objectIds": ids}).encode()
        assert data["outSR"] == "4326"
        return SAMPLE
    return answer, seen


def test_tgrac_layer():
    p = seed("wm2_tgrac.json", "wm2_tgrac-his-wards-municipality")
    assert p["reader"] == "wm2_arcgis_json" and p["state"] == "36" and p["oid"] == "FID"
    answer, seen = route([1029, 1027, 1028])
    recs, files, why = w.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and len(seen) == 2 and seen[1]["objectIds"] == "1027,1028,1029"
    (path, blob, _), = files
    assert path == "wardmaps/tgrac_his/36/wards_municipality.geojson.gz"
    fc = json.loads(gzip.decompress(blob))
    f0 = fc["features"][0]
    assert f0["id"] == 1027 and f0["properties"]["ULB_Name"] == "Karimnagar" and f0["geometry"]["type"] == "Polygon"
    ring = f0["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] and 77.0 < ring[0][0] < 82.0 and 15.5 < ring[0][1] < 20.0
    (rid, d), = recs
    assert rid == "wm2_tgrac_his:36-karimnagar" and d["wards"] == 3 and d["body_name"] == "Karimnagar"
    assert d["src_pos"]["feature_id"] == [1027, 1028, 1029]


def test_missing_ids_fail():
    p = seed("wm2_tgrac.json", "wm2_tgrac-his-wards-municipality")
    answer, _ = route([1027, 1028, 1029, 999])
    recs, files, why = w.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert (recs, files) == ([], []) and why == "got 3 of 4 object ids"


def test_rings_to_geojson():
    outer = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]          # clockwise: outer ring
    hole = [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]               # counter-clockwise: hole
    second = [[20, 0], [20, 5], [25, 5], [25, 0], [20, 0]]
    g = w.esri_geometry({"rings": [outer, hole, second]})
    assert g["type"] == "MultiPolygon" and len(g["coordinates"]) == 2 and len(g["coordinates"][0]) == 2
    assert w.esri_geometry({"rings": [outer]})["type"] == "Polygon"
    assert w.esri_geometry(None) is None
