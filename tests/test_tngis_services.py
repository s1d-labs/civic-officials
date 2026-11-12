"""dforms/wm2_wfs.py with payload "kind" (TNGIS service and boundary layers, seeds/tngis_services.json) on a saved sample:
the first 3 features of generic_viewer:police_stations (sortBy object_id; numberMatched 1315 in the live layer, 2026-11-12).
The layer has no primary key: GeoServer gives new feature ids ("police_stations.fid--...") on each request. No network."""
import gzip
import json
from urllib.parse import parse_qs, urlsplit

from test_dept_police import DATA, FakeGet

import family
from dforms import wm2_wfs
from seeds import build_tngis_all, build_tngis_services

SAMPLE = DATA / "wm2" / "tngis_police_stations.geojson"
SEEDS = DATA.parent.parent / "seeds" / "tngis_services.json"
ALL = DATA.parent.parent / "seeds" / "tngis_all.json"


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
    n_all = len(json.loads(ALL.read_text(encoding="utf-8")))
    assert proj["task"] == "wardmaps" and len(proj["items"]) == 43 + n_all and not proj.get("proxy") and not proj.get("geo")


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


def test_each_layer_its_own_record_and_line_file():
    """2026-11-12 bug: every TNGIS layer wrote the one record wm2_tngis:33-all. Two layers give two gis_layer records, and the
    stored file has one feature per line (civic-india tngis_load.py streams it) and is still one GeoJSON FeatureCollection."""
    ids = []
    for key in ("tngis-police_stations", "tngis-fire_stations"):
        p = dict(seed(key), page=2)
        answer, _ = answer_pages()
        recs, files, why = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))
        assert why == "" and len(recs) == 1
        ids.append(recs[0][0])
        text = gzip.decompress(files[0][1]).decode("utf-8")
        lines = text.split("\n")
        assert lines[0] == '{"type":"FeatureCollection","features":[' and lines[-2:] == ["]}", ""]
        assert len(lines) == 3 + 3 and all(ln.endswith(",") for ln in lines[1:3]) and not lines[3].endswith(",")
        assert [json.loads(ln.rstrip(","))["properties"]["object_id"] for ln in lines[1:4]] == [1, 2, 3]
        assert len(json.loads(text)["features"]) == 3
    assert ids == ["gis_tngis:33-police_stations", "gis_tngis:33-fire_stations"]
    assert not any(i.endswith("-all") for i in ids)


def test_ward_layer_without_fields_keyed_by_chunk():
    """A ward payload with no body "fields" (wm2_tngis chennai-ward, ponneri-ward ...) used to write "wm2_tngis:33-all"."""
    out = []
    for chunk in ("chennai_ward", "ponneri_ward"):
        p = {"reader": "wm2_wfs", "url": "https://tngis.tn.gov.in/tngismaps/wfs", "layer": f"generic_viewer:{chunk}",
             "state": "33", "source": "tngis", "chunk": chunk, "page": 5}
        answer, _ = answer_pages()
        (rid, r), = wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))[0]
        assert r["type"] == "wm_layer_town" and r["file"] == f"wardmaps/tngis/33/{chunk}.geojson.gz" and r["features"] == 3
        out.append(rid)
    assert out == ["wm2_tngis:33-chennai_ward", "wm2_tngis:33-ponneri_ward"]


def test_pages_beyond_max_pages_and_early_stop():
    assert wm2_wfs.max_pages({"expect": 924340}, 2000) == 468 > wm2_wfs.MAX_PAGES
    assert wm2_wfs.max_pages({}, 2000) == wm2_wfs.MAX_PAGES
    p = dict(seed("tngis-police_stations"), page=1)
    answer, seen = answer_pages(repeat_from=0)
    wm2_wfs.fetch(dict(p, expect=None), FakeGet({p["url"]: answer}))
    assert [q["startIndex"] for q in seen] == ["0", "1", "0"]        # paging stops at the first repeat, then one request
    answer, seen = answer_pages(total=wm2_wfs.ONE_SHOT_MAX + 1, repeat_from=0)
    assert wm2_wfs.fetch(p, FakeGet({p["url"]: answer}))[2].startswith("repeated features across pages (unstable")


def test_all_layers_seeds():
    """seeds/tngis_all.json: the other non-mirror layers of the owner's download that the WFS answers (built from tngis_all.tsv)."""
    items = json.loads(ALL.read_text(encoding="utf-8"))
    big = json.loads((ALL.parent / "tngis_all_big.json").read_text(encoding="utf-8"))
    assert items == build_tngis_all.items() and big == build_tngis_all.items(big=True)
    proj = next(x for x in family.PROJECTS if x["name"] == "civic-officials-tngis-big")
    assert proj["items"] == big and proj["workers"] == 1 and not proj.get("proxy") and not proj.get("geo")
    assert {i["payload"]["chunk"] for i in big}.isdisjoint(i["payload"]["chunk"] for i in items)
    items = items + big
    old = {i["payload"]["chunk"] for i in json.loads(SEEDS.read_text(encoding="utf-8"))}
    old_layers = {i["payload"]["layer"] for i in json.loads(SEEDS.read_text(encoding="utf-8"))}
    chunks = [i["payload"]["chunk"] for i in items]
    assert len(items) == len(build_tngis_all.rows()) > 400 and len(set(chunks)) == len(chunks) and not set(chunks) & old
    assert not {i["payload"]["layer"] for i in items} & old_layers
    for i in items:
        p = i["payload"]
        assert i["key"] == "tngis-" + p["chunk"] and p["reader"] == "wm2_wfs" and p["kind"] == p["chunk"]
        assert p["state"] == "33" and p["india_only"] is False and p["source"] == "tngis"
        assert isinstance(p["expect"], int) and p["expect"] > 0 and 100 <= p["page"] <= 5000
        assert not p["layer"].startswith(("tngis:", "TNGIS_V2:"))
        assert len("tngis_" + p["chunk"]) <= 63 and p["chunk"] == p["chunk"].lower() and " " not in p["chunk"]
        assert p["category"] in {"admin_boundary", "service_point", "infrastructure", "land_env", "other"}
        assert p["sort"] and " " not in p["sort"]        # GeoServer pages a table without a primary key only with sortBy
        assert 100 <= p["page"] <= 4000


def test_equal_rows_in_one_answer_are_kept():
    """Two equal features in ONE answer are the layer's own data (no retry); equal to an earlier page = unstable paging."""
    body = json.loads(SAMPLE.read_text(encoding="utf-8"))
    feats = [body["features"][0], dict(body["features"][0], id="x.2"), body["features"][1]]
    p = dict(seed("tngis-police_stations"), page=10)
    calls = FakeGet({p["url"]: json.dumps(dict(body, features=feats, numberMatched=3)).encode()})
    (_, r), = wm2_wfs.fetch(p, calls)[0]
    assert r["features"] == 3 and r["one_shot"] is False and len(calls.calls) == 1
