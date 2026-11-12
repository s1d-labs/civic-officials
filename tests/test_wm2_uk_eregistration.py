"""seeds/wm2_uk_eregistration.json (Uttarakhand Stamps and Registration GIS, layer 16 Ward_Boundaries) through dforms/wm2_arcgis.py
on a saved sample (tests/data/wm2/uk_eregistration_lohaghat.geojson: 3 Lohaghat wards, rings cut to 8 points): no network."""
import gzip
import json

from test_dept_police import FakeGet
from test_wm2_portals import pages, seed

from dforms import wm2_arcgis


def test_uk_eregistration_layer():
    p = seed("wm2_uk_eregistration.json", "wm2_uk_eregistration-ward-boundaries")
    assert p["reader"] == "wm2_arcgis" and p["state"] == "5" and p["oid"] == "OBJECTID_1" and p["india_only"] is False
    answer, seen = pages("uk_eregistration_lohaghat.geojson")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and len(seen) == 1          # 3 features < page and no exceededTransferLimit: the last page
    assert seen[0]["where"] == "(1=1) AND OBJECTID_1 > -1"
    assert seen[0]["orderByFields"] == "OBJECTID_1 ASC" and seen[0]["resultRecordCount"] == "1000"
    (path, blob, ctype), = files
    assert path == "wardmaps/uk_eregistration/5/ward_boundaries.geojson.gz" and ctype == "application/gzip"
    assert len(json.loads(gzip.decompress(blob))["features"]) == 3
    (rid, d), = recs
    assert rid == "wm2_uk_eregistration:5-800329-lohaghat"
    assert d["body_name"] == "Lohaghat" and d["body_code"] == "800329" and d["district"] == "CHAMPAWAT"
    assert d["wards"] == 3 and d["features"] == 3 and d["ward_kind"] == "election" and d["vintage"] == "2022-01"
    assert d["src_pos"]["feature_index"] == [0, 1, 2] and d["src_pos"]["feature_id"] == [366, 380, 407]
