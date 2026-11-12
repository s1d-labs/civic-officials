"""dforms/wm2_wfs.py with payload "kind" (TNGIS service and boundary layers, seeds/tngis_services.json) on a saved sample:
the first 3 features of generic_viewer:police_stations (sortBy object_id; numberMatched 1315 in the live layer, 2026-11-12).
The layer has no primary key: GeoServer gives new feature ids ("police_stations.fid--...") on each request. No network."""
import gzip
import json
from urllib.parse import parse_qs, urlsplit

from test_dept_police import DATA, FakeGet

import family
from dforms import wm2_wfs
from seeds import build_tngis_services

SAMPLE = DATA / "wm2" / "tngis_police_stations.geojson"
SEEDS = DATA.parent.parent / "seeds" / "tngis_services.json"


def seed(key):
    items = json.loads(SEEDS.read_text(encoding="utf-8"))
    return next(i["payload"] for i in items if i["key"] == key)


def answer_pages(total=3, shuffle_ids=True, repeat_from=None):
    """GetFeature pages cut from the sample by startIndex/count. shuffle_ids: new feature ids per request (no primary key).
    repeat_from: pages after the first start again at this index (an unstable order that repeats rows)."""
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    seen = []

    def answer(url, method, data):
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        seen.append(q)
        assert method == "GET" and q["request"] == "GetFeature" and q["srsName"] == "EPSG:4326"
        s, c = int(q["startIndex"]), int(q["count"])
        if repeat_from is not None and s > 0:
            s = repeat_from
        feats = [dict(f, id=f"police_stations.fid-{len(seen)}-{i}" if shuffle_ids else f["id"])
                 for i, f in enumerate(body["features"][s:s + c])]
        return json.dumps(dict(body, features=feats, numberMatched=total, numberReturned=len(feats))).encode()
    return answer, seen


def test_seeds_and_project():
    items = json.loads(SEEDS.read_text(encoding="utf-8"))
    assert items == build_tngis_services.items()          # the file is the builder's output
    assert len(items) == 43 and all(i["key"].startswith("tngis-") for i in items)
    for i in items:
        p = i["payload"]
        assert p["reader"] == "wm2_wfs" and p["kind"] and p["state"] == "33" and p["india_only"] is False
        assert not p["layer"].startswith(("tngis:", "TNGIS_V2:"))       # those workspaces answer HTTP 500 (database missing)
    p = seed("tngis-police_stations")
    assert p["layer"] == "generic_viewer:police_stations" and p["sort"] == "object_id" and p["expect"] == 1315
    assert seed("tngis-traffic_police_jurisdiction")["layer"] == "generic_viewer:traffic police jurisdiction"
    assert "sort" not in seed("tngis-administrative_boundary_taluk")
    proj = next(x for x in family.PROJECTS if x["name"] == "civic-officials-tngis")
    assert proj["task"] == "wardmaps" and len(proj["items"]) == 43 and not proj.get("proxy") and not proj.get("geo")


def test_layer_paged_one_record():
    p = dict(seed("tngis-police_stations"), page=1, district="ps_name")
    answer, seen = answer_pages()
    recs, files, why = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))
    assert why == "" and [q["startIndex"] for q in seen] == ["0", "1", "2"]
    assert seen[0]["typeNames"] == "generic_viewer:police_stations" and seen[0]["sortBy"] == "object_id"
    (rid, r), = recs
    assert rid == "gis_tngis:33-police_stations"
    assert r["type"] == "gis_layer" and r["kind"] == "police_station" and r["features"] == 3 and r["expect"] == 1315
    assert r["file"] == "gis/tngis/33/police_stations.geojson.gz" and r["one_shot"] is False and r["has_z"] is False
    assert r["fields"][:5] == ["layer_id", "tngis_id", "object_id", "ps_code", "ps_name"]
    assert r["geometry_types"] == {"Point": 3} and r["by_district"]["T15 SRMC"] == 1
    (path, blob, ctype), = files
    fc = json.loads(gzip.decompress(blob))
    assert path == r["file"] and ctype == "application/gzip"
    assert [f["properties"]["object_id"] for f in fc["features"]] == [1, 2, 3] and "one_shot" not in fc


def test_unstable_pages_fall_back_to_one_request():
    p = dict(seed("tngis-police_stations"), page=1)
    answer, seen = answer_pages(repeat_from=0)                 # pages 2 and 3 repeat feature 1 (new ids each time)
    recs, files, why = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))
    assert why == "" and seen[-1]["startIndex"] == "0" and seen[-1]["count"] == "3"
    (_, r), = recs
    assert r["one_shot"] is True and r["features"] == 3
    fc = json.loads(gzip.decompress(files[0][1]))
    assert sorted(f["properties"]["object_id"] for f in fc["features"]) == [1, 2, 3]


def test_3d_and_errors():
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    body["features"][0]["geometry"]["coordinates"].append(0.0)
    p = dict(seed("tngis-police_stations"))
    (_, r), = wm2_wfs.fetch(p, FakeGet({p["url"]: json.dumps(dict(body, numberMatched=3)).encode()}))[0]
    assert r["has_z"] is True
    answer, _ = answer_pages(total=5)
    assert wm2_wfs.fetch(dict(p, page=1), FakeGet({p["url"]: answer}))[2] == "got 3 of 5 features"
    exc = (b'<?xml version="1.0"?><ows:ExceptionReport><ows:Exception exceptionCode="NoApplicableCode"><ows:ExceptionText>'
           b'Unable to obtain connection: database &quot;tnega&quot; does not exist</ows:ExceptionText></ows:Exception>'
           b'</ows:ExceptionReport>')
    assert wm2_wfs.fetch(p, FakeGet({p["url"]: exc}))[2].startswith("not JSON")
    assert wm2_wfs.fetch(p, FakeGet({})) == ([], [], "no answer")
