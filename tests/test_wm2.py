"""wm2_* ward layer readers on saved samples (tests/data/wm2/): no network. FakeGet answers the ArcGIS query from a 3-ward
sample of the SBM-Urban WardBoundary layer (2026-11-11, geometry cut down), honouring the reader's objectid filter and page
size, so the keyset paging runs as on the pool."""
import gzip
import json
import re
from urllib.parse import parse_qs

from test_dept_police import DATA, FakeGet

from dforms import _wm2_arcgis, wm2_sbm

FC = json.loads((DATA / "wm2" / "sbm_3wards.geojson").read_text())
LAYER = wm2_sbm.LAYER


def layer(fc=FC):
    calls = []

    def answer(url, method, data):
        assert method == "POST" and url == LAYER + "/query"
        calls.append(data)
        assert data["f"] == "geojson" and data["outSR"] == "4326"
        last = int(re.search(r"objectid > (-?\d+)", data["where"]).group(1))
        feats = sorted((f for f in fc["features"] if f["id"] > last), key=lambda f: f["id"])
        return json.dumps({"type": "FeatureCollection", "features": feats[:int(data["resultRecordCount"])]})
    return FakeGet({LAYER + "/query": answer}), calls


def test_pages_whole_range_and_stores_once():
    get, calls = layer()
    recs, files, why = wm2_sbm.fetch({"reader": "wm2_sbm", "url": LAYER, "state": "33", "ulb_from": "803000", "page": 2}, get)
    assert why == ""
    assert len(calls) == 2                               # 2 + 1 features: the short second page ends the loop
    assert "statecode = '33' AND ulbcode >= '803000'" in calls[0]["where"]
    path, blob, ctype = files[0]
    assert path == "wardmaps/sbm/33/803000-end.geojson.gz" and ctype == "application/gzip"
    stored = json.loads(gzip.decompress(blob))
    assert [f["id"] for f in stored["features"]] == [309553, 311305, 316869]
    towns = dict(recs)
    assert set(towns) == {"wm2_sbm:803442", "wm2_sbm:800732"}
    t = towns["wm2_sbm:803442"]
    assert t["type"] == "wm_layer_town" and t["body_name"] == "Ulundurpet" and t["wards"] == 2 and t["file"] == path
    assert t["district"] == "KALLAKURICHI" and t["status"] == {"APPROVED": 2}
    assert towns["wm2_sbm:800732"]["state"] == "9"       # the record keeps the ward's own statecode


def test_rest_item_takes_unseeded_states():
    w = wm2_sbm.where({"state": "rest", "not_states": ["1", "9"]})
    assert w.startswith("statecode IS NULL OR TRIM(statecode) = ''") and "NOT IN ('1','9')" in w


def test_server_error_is_reported():
    get = FakeGet({LAYER + "/query": '{"error": {"code": 400, "message": "Invalid query"}}'})
    recs, files, why = wm2_sbm.fetch({"reader": "wm2_sbm", "state": "9"}, get)
    assert recs == [] and files == [] and why.startswith("server error")


def test_no_answer_and_empty_range():
    assert wm2_sbm.fetch({"reader": "wm2_sbm", "state": "9"}, FakeGet({}))[2] == "no answer"
    get, _ = layer({"type": "FeatureCollection", "features": []})
    assert wm2_sbm.fetch({"reader": "wm2_sbm", "state": "9"}, get)[2] == "no wards in this range"


def test_server_that_ignores_the_filter_stops():
    def same(url, method, data):
        return json.dumps(FC)
    fc, why = _wm2_arcgis.page_layer(FakeGet({LAYER + "/query": same}), LAYER, page=3)
    assert why == "server ignored the objectid filter"


def test_seed_file_shape():
    items = json.loads((DATA.parent.parent / "seeds" / "wm2_sbm.json").read_text())
    assert all(i["key"].startswith("wm2_") and i["payload"]["reader"] == "wm2_sbm" and i["payload"]["india_only"] for i in items)
    assert len({i["key"] for i in items}) == len(items)
    up = [i["payload"] for i in items if i["payload"]["state"] == "9"]
    assert "ulb_from" not in up[0] and "ulb_to" not in up[-1]          # open at both ends: new codes fall in an item
    assert all(a["ulb_to"] == b["ulb_from"] for a, b in zip(up, up[1:]))
