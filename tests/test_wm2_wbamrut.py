"""seeds/wm2_wbamrut.json (West Bengal AMRUT GeoServer WFS, nagargispariseva.wb.gov.in) with dforms/wm2_wfs.py: no network.
The fixture has 3 wards of Midnapore (ULB_Code 250230) with the layer's own attribute names, taken from ramSeraph's copy of
WBAMRUT:wb_ward_boundary (indian_admin_boundaries release `urban`, WB_AMRUT_Wards); outlines thinned to keep the file small.
The live host did not answer from dev-vps-3 or vpsin on 2026-11-13, so no live page could be saved."""
import gzip
import json
from urllib.parse import parse_qs, urlsplit

from test_dept_police import DATA, FakeGet
from test_wm2_portals import seed

from dforms import wm2_wfs

SAMPLE = DATA / "wm2" / "wbamrut_wb_ward_boundary.geojson"
SEEDS = "wm2_wbamrut.json"


def answer_pages(total=3):
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    seen = []

    def answer(url, method, data):
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        seen.append(q)
        assert method == "GET" and q["version"] == "2.0.0" and q["srsName"] == "EPSG:4326"
        s, c = int(q["startIndex"]), int(q["count"])
        part = body["features"][s:s + c]
        return json.dumps(dict(body, features=part, numberMatched=total, numberReturned=len(part))).encode()
    return answer, seen


def test_seeds():
    ps = {k: seed(SEEDS, k) for k in ("wm2_wbamrut-wb-ward-boundary", "wm2_wbamrut-revenue-ward-boundary",
                                       "wm2_wbamrut-wb-municipal-boundary")}
    for p in ps.values():
        assert p["reader"] == "wm2_wfs" and p["state"] == "19" and p["source"] == "wbamrut_wfs"
        assert p["url"] == "https://nagargispariseva.wb.gov.in/geoserver/WBAMRUT/wfs" and p["layer"].startswith("WBAMRUT:")
    assert ps["wm2_wbamrut-wb-municipal-boundary"]["kind"] == "town_boundary"
    assert ps["wm2_wbamrut-revenue-ward-boundary"]["ward_kind"] == "revenue"


def test_ward_layer_paged():
    p = dict(seed(SEEDS, "wm2_wbamrut-wb-ward-boundary"), page=2)
    answer, seen = answer_pages()
    recs, files, why = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))
    assert why == "" and [q["startIndex"] for q in seen] == ["0", "2"]
    assert seen[0]["typeNames"] == "WBAMRUT:wb_ward_boundary" and seen[0]["sortBy"] == "MUN_ID"
    (rid, r), = recs
    assert rid == "wm2_wbamrut_wfs:19-250230-midnapore"
    assert r["body_name"] == "Midnapore" and r["body_code"] == "250230" and r["district"] == "318"
    assert r["wards"] == 3 and r["features"] == 3 and r["src_pos"]["feature_index"] == [0, 1, 2]
    (path, blob, ctype), = files
    assert path == r["file"] == "wardmaps/wbamrut_wfs/19/wb_ward_boundary.geojson.gz"
    assert len(json.loads(gzip.decompress(blob))["features"]) == 3


def test_town_boundary_layer_record():
    p = seed(SEEDS, "wm2_wbamrut-wb-municipal-boundary")
    answer, _ = answer_pages()
    (rid, r), = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))[0]
    assert rid == "gis_wbamrut_wfs:19-wb_municipal_boundary" and r["kind"] == "town_boundary"
    assert r["features"] == 3 and r["by_district"] == {"318": 3} and "ULB_Code" in r["fields"]


def test_host_down():
    p = seed(SEEDS, "wm2_wbamrut-wb-ward-boundary")
    assert wm2_wfs.fetch(p, FakeGet({})) == ([], [], "no answer")
