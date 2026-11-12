"""seeds/wm2_kgis.json (Karnataka KGIS ward layer + town layer, read by dforms/wm2_arcgis.py) on saved samples: no network.
Samples (2026-11-12): 3 wards of Ainapur (KGISTownCode 0101) and 3 towns of the town layer (LGD_TownCode = LGD local_body_code)."""
import gzip
import json

from test_dept_police import FakeGet
from test_wm2_portals import pages, seed

from dforms import wm2_arcgis


def test_kgis_ward_layer():
    p = seed("wm2_kgis.json", "wm2_kgis-ward-dynamic")
    assert p["state"] == "29" and p["oid"] == "OBJECTID" and p["source"] == "kgis"
    answer, seen = pages("kgis_ward_ainapur.geojson")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and len(seen) == 2 and seen[0]["orderByFields"] == "OBJECTID ASC"
    (path, blob, _), = files
    assert path == "wardmaps/kgis/29/ward_dynamic.geojson.gz"
    fc = json.loads(gzip.decompress(blob))
    assert len(fc["features"]) == 3
    assert seen[1]["where"] == "(1=1) AND OBJECTID > " + str(max(f["id"] for f in fc["features"]))
    (rid, d), = recs
    assert rid == "wm2_kgis:29-0101" and d["body_code"] == "0101" and d["wards"] == 3 and d["features"] == 3
    assert d["ward_kind"] == "election" and d["src_pos"]["feature_index"] == [0, 1, 2]


def test_kgis_town_layer():
    p = seed("wm2_kgis.json", "wm2_kgis-town")
    answer, _ = pages("kgis_town_3.geojson")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and files[0][0] == "wardmaps/kgis_towns/29/town.geojson.gz"
    by = {d["body_name"]: (rid, d) for rid, d in recs}
    assert by["AINAPUR"][0] == "wm2_kgis_towns:29-276618-ainapur" and by["AINAPUR"][1]["body_code"] == "276618"
    assert by["ATHANI"][1]["body_code"] == "251812" and len(recs) == 3
