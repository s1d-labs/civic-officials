"""dforms/wm2_arcgis_town.py (one town's ward layer, HARSAC OneMap Haryana) on saved samples (tests/data/wm2/harsac_*): no network."""
import gzip
import json

from test_dept_police import FakeGet
from test_wm2_portals import pages, seed

from dforms import wm2_arcgis_town


def test_faridabad_mcf():
    p = seed("wm2_harsac.json", "wm2_harsac-mcf-ward-boundary")
    assert p["state"] == "6" and p["oid"] == "objectid_1" and p["india_only"] is False
    answer, seen = pages("harsac_mcf.geojson")
    recs, files, why = wm2_arcgis_town.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and len(seen) == 2 and seen[1]["where"] == "(1=1) AND objectid_1 > 3"
    (path, blob, ctype), = files
    assert path == "wardmaps/harsac/6/mcf_ward_boundary.geojson.gz" and ctype == "application/gzip"
    assert len(json.loads(gzip.decompress(blob))["features"]) == 3
    (rid, d), = recs
    assert rid == "wm2_harsac:6-248585"
    assert d["body_name"] == "Faridabad" and d["body_code"] == "248585" and d["lgd_code"] == "248585"
    assert d["wards"] == 3 and d["features"] == 3 and d["ward_kind"] == "election"
    assert d["src_pos"]["feature_index"] == [0, 1, 2] and d["src_pos"]["layer_file"] == path


def test_gurugram_2023():
    p = seed("wm2_harsac.json", "wm2_harsac-mcg-ward-boundary-2023")
    answer, seen = pages("harsac_mcg.geojson")
    recs, files, why = wm2_arcgis_town.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and seen[0]["orderByFields"] == "OBJECTID ASC"
    (rid, d), = recs
    assert rid == "wm2_harsac:6-248576" and d["vintage"] == "2023" and d["wards"] == 3 and d["district"] == "Gurugram"


def test_seed_keys_unique():
    items = json.loads((__import__("pathlib").Path(__file__).parent.parent / "seeds" / "wm2_harsac.json").read_text())
    assert len({i["payload"]["chunk"] for i in items}) == len(items) == 3
    assert all(i["payload"]["body"].isdigit() for i in items)


def test_no_answer():
    p = seed("wm2_harsac.json", "wm2_harsac-mcf-ward-boundary")
    assert wm2_arcgis_town.fetch(p, FakeGet({})) == ([], [], "no answer")
