"""dforms/wm2_wfs.py (ward layers on public GeoServer WFS, first TNGIS) on a saved 2-ward sample (tests/data/wm2/): no network.
The sample is the first GetFeature page of generic_viewer:ward_boundary (count=2; numberMatched 1248 in the live layer)."""
import json
from urllib.parse import parse_qs, urlsplit

from test_dept_police import DATA, FakeGet
from test_wm2_portals import seed

from dforms import wm2_wfs

SAMPLE = DATA / "wm2" / "tngis_ward_boundary.geojson"


def answer_pages(total=2, page_size=1):
    """Answers GetFeature pages cut from the sample by startIndex/count, with numberMatched = total."""
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    seen = []

    def answer(url, method, data):
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        seen.append(q)
        assert method == "GET" and q["request"] == "GetFeature" and q["srsName"] == "EPSG:4326"
        s, c = int(q["startIndex"]), int(q["count"])
        d = dict(body, features=body["features"][s:s + c], numberMatched=total, numberReturned=len(body["features"][s:s + c]))
        return json.dumps(d).encode()
    return answer, seen


def test_seeds():
    p = seed("wm2_tngis.json", "wm2_tngis-ward-boundary")
    assert p["reader"] == "wm2_wfs" and p["layer"] == "generic_viewer:ward_boundary" and p["state"] == "33"
    assert p["fields"]["body_name"] == "town_name"


def test_tngis_ward_boundary_paged():
    p = dict(seed("wm2_tngis.json", "wm2_tngis-ward-boundary"), page=1)
    answer, seen = answer_pages()
    recs, files, why = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))
    assert why == "" and [q["startIndex"] for q in seen] == ["0", "1"]
    assert seen[0]["typeNames"] == "generic_viewer:ward_boundary"
    (rid, r), = recs
    assert rid == "wm2_tngis:33-periyasemur-erode"
    assert r["body_name"] == "Periyasemur" and r["district"] == "Erode" and r["wards"] == 2 and r["features"] == 2
    assert r["file"] == "wardmaps/tngis/33/ward_boundary.geojson.gz" and r["layer"] == "generic_viewer:ward_boundary"
    (path, blob, ctype), = files
    import gzip
    fc = json.loads(gzip.decompress(blob))
    assert path == r["file"] and len(fc["features"]) == 2 and fc["features"][0]["geometry"]["type"] == "MultiPolygon"


def test_incomplete_and_errors():
    p = dict(seed("wm2_tngis.json", "wm2_tngis-ward-boundary"), page=1)
    answer, _ = answer_pages(total=5)
    assert wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))[2] == "got 2 of 5 features"
    assert wm2_wfs.fetch(p, FakeGet({})) == ([], [], "no answer")
    exc = b'<?xml version="1.0"?><ows:ExceptionReport><ows:Exception exceptionCode="InvalidParameterValue"/></ows:ExceptionReport>'
    assert wm2_wfs.fetch(p, FakeGet({p["url"]: exc}))[2].startswith("not JSON")
