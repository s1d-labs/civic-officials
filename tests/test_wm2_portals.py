"""dforms/wm2_arcgis.py (ward layers on state/city ArcGIS portals) on saved samples (tests/data/wm2/): no network.
FakeGet answers the first keyset page from the sample and an empty page after it, as the server does."""
import gzip
import json

from test_dept_police import DATA, FakeGet

from dforms import wm2_arcgis

ROOT = DATA.parent.parent


def pages(sample):
    """Route for <layer>/query: the sample for the first page (oid > -1), then an empty FeatureCollection."""
    body = (DATA / "wm2" / sample).read_bytes()
    seen = []

    def answer(url, method, data):
        seen.append(data)
        assert method == "POST" and data["f"] == "geojson" and data["outSR"] == "4326"
        return body if data["where"].endswith("> -1") else b'{"type":"FeatureCollection","features":[]}'
    return answer, seen


def seed(name, key):
    items = json.loads((ROOT / "seeds" / name).read_text(encoding="utf-8"))
    assert items and all(i["key"].startswith("wm2_") for i in items) and len({i["key"] for i in items}) == len(items)
    return next(i["payload"] for i in items if i["key"] == key)


def test_livingatlas_state():
    p = seed("wm2_livingatlas.json", "wm2_livingatlas-12")
    assert p["where"] == "state='Arunachal Pradesh'" and p["state"] == "12" and p["india_only"] is False
    answer, seen = pages("livingatlas_iwb_ar.geojson")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and len(seen) == 2
    assert seen[1]["where"] == "(state='Arunachal Pradesh') AND objectid > 4292"
    (path, blob, ctype), = files
    assert path == "wardmaps/livingatlas_iwb/12/india_ward_boundaries.geojson.gz" and ctype == "application/gzip"
    assert len(json.loads(gzip.decompress(blob))["features"]) == 3
    (rid, d), = recs
    assert rid == "wm2_livingatlas_iwb:12-pasighat-east-siang"
    assert d["type"] == "wm_layer_town" and d["body_name"] == "Pasighat" and d["district"] == "East Siang"
    assert d["wards"] == 3 and d["features"] == 3 and d["file"] == path and d["url"] == p["url"]


def test_apsac_revenue_wards():
    p = seed("wm2_apsac.json", "wm2_apsac-maud-ward-boundary")
    answer, seen = pages("apsac_maud_naidupet.geojson")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert why == "" and seen[0]["orderByFields"] == "objectid_12 ASC" and seen[0]["resultRecordCount"] == "500"
    (rid, d), = recs
    assert rid == "wm2_apsac_maud:28-1153-naidupet"
    assert d["body_code"] == "1153" and d["wards"] == 3 and d["ward_kind"] == "revenue" and d["vintage"] == "2018-06-01"
    assert files[0][0] == "wardmaps/apsac_maud/28/ward_boundary.geojson.gz"


def test_no_answer_and_server_error():
    p = seed("wm2_apsac.json", "wm2_apsac-maud-ward-boundary")
    assert wm2_arcgis.fetch(p, FakeGet({})) == ([], [], "no answer")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": '{"error":{"code":499,"message":"Token Required"}}'}))
    assert not recs and not files and "Token Required" in why


def test_partial_layer_is_not_stored():
    p = seed("wm2_livingatlas.json", "wm2_livingatlas-12")
    body = (DATA / "wm2" / "livingatlas_iwb_ar.geojson").read_bytes()

    def answer(url, method, data):      # first page fine, second page a server error: nothing is stored, the hub retries
        return body if data["where"].endswith("> -1") else b'{"error":{"code":500,"message":"Unable to complete operation."}}'
    # one full page (3 of page 3) makes page_layer ask again
    p = dict(p, page=3)
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": answer}))
    assert not recs and not files and why.startswith("stopped after 3 features")


def test_no_features():
    p = seed("wm2_livingatlas.json", "wm2_livingatlas-12")
    recs, files, why = wm2_arcgis.fetch(p, FakeGet({p["url"] + "/query": b'{"type":"FeatureCollection","features":[]}'}))
    assert (recs, files) == ([], []) and why.startswith("no features")
