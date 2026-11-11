"""dforms/wm2_rj_gis.py (Rajasthan RajDharaa ward layer, token from the public GenerateGISToken API) on a saved 4-ward sample
(tests/data/wm2/rj_gis_4wards.geojson, 2026-11-11: Deshnok wards 1, 2, 13 and Pipar City ward 1, as served): no network.
FakeGet answers the token API with a made-up token and the layer as the server does (count, keyset pages, 499 without token)."""
import gzip
import json
import re

from test_dept_police import DATA, FakeGet

from dforms import wm2_rj_gis

FC = json.loads((DATA / "wm2" / "rj_gis_4wards.geojson").read_text())
SEED = json.loads((DATA.parent.parent / "seeds" / "wm2_rj_gis.json").read_text())
P = SEED[0]["payload"]
LAYER = P["url"]
TOKEN_ERR = json.dumps({"error": {"code": 499, "message": "Token Required", "details": []}})


def site(fc=FC, tokens=("tok-one-1234",), valid=None, token_answer=None):
    """FakeGet for the token API and the layer. tokens: what successive token calls give; valid: tokens the layer accepts."""
    given, calls = list(tokens), {"token": 0, "query": []}
    valid = set(tokens) if valid is None else set(valid)

    def token_api(url, method, data):
        assert method == "POST" and not data      # an empty POST, like the viewer: no credentials
        calls["token"] += 1
        if token_answer is not None:
            return token_answer
        tok = given[min(calls["token"], len(given)) - 1]
        return json.dumps({"Status": True, "Messages": [{"ServiceName": "basemap", "Token": "other"},
                                                        {"ServiceName": "dynamicquery", "Token": tok}]})

    def layer(url, method, data):
        assert method == "POST" and url == LAYER + "/query"
        calls["query"].append(data)
        if data.get("token") not in valid:
            return TOKEN_ERR
        if data.get("returnCountOnly") == "true":
            return json.dumps({"count": len(fc["features"])})
        assert data["f"] == "geojson" and data["outSR"] == "4326" and data["orderByFields"] == "OBJECTID ASC"
        last = int(re.search(r"OBJECTID > (-?\d+)", data["where"]).group(1))
        feats = sorted((f for f in fc["features"] if f["id"] > last), key=lambda f: f["id"])
        return json.dumps({"type": "FeatureCollection", "features": feats[:int(data["resultRecordCount"])]})
    return FakeGet({P["token_api"]: token_api, LAYER + "/query": layer}), calls


def test_seed():
    assert len(SEED) == 1 and SEED[0]["key"].startswith("wm2_rj_gis")
    assert P["reader"] == "wm2_rj_gis" and P["india_only"] is True and P["state"] == "8"
    assert P["url"] == wm2_rj_gis.LAYER and P["token_api"] == wm2_rj_gis.TOKEN_API
    assert "token" not in json.dumps(P).lower().replace("token_api", "").replace("generategistoken", "")


def test_pages_with_token_and_stores_once():
    get, calls = site()
    recs, files, why = wm2_rj_gis.fetch(dict(P, page=3), get)
    assert why == "" and calls["token"] == 1
    assert all(q["token"] == "tok-one-1234" for q in calls["query"])
    assert calls["query"][0]["returnCountOnly"] == "true"
    assert [q["where"] for q in calls["query"][1:]] == ["(1=1) AND OBJECTID > -1", "(1=1) AND OBJECTID > 10873"]
    (path, blob, ctype), = files
    assert path == "wardmaps/rj_gis/8/ward_bndy_ulb.geojson.gz" and ctype == "application/gzip"
    assert len(json.loads(gzip.decompress(blob))["features"]) == 4
    towns = dict(recs)
    assert set(towns) == {"wm2_rj_gis:8-deshnok", "wm2_rj_gis:8-pipar-city"}
    d = towns["wm2_rj_gis:8-deshnok"]
    assert d["type"] == "wm_layer_town" and d["body_name"] == "DESHNOK" and d["body_code"] == ""
    assert d["district"] == "BIKANER" and d["districts"] == {"BIKANER": 2, "BHILWARA": 1}   # one ward has a stray district
    assert d["wards"] == 3 and d["features"] == 3 and d["area_names"] == {}
    assert d["created_first"] == d["created_last"] == d["last_edit"] == 1775041283000
    assert d["file"] == path and d["url"] == LAYER and d["ward_kind"] == "election"
    pc = towns["wm2_rj_gis:8-pipar-city"]
    assert pc["wards"] == 1 and pc["area_names"] == {"PIPAR CITY NORTH": 1} and pc["districts"] == {}
    assert pc["created_first"] is None and pc["last_edit"] is None
    assert "tok-one" not in json.dumps(recs) and b"tok-one" not in gzip.decompress(blob)   # the token is never stored


def test_new_token_once_when_the_layer_refuses_it():
    get, calls = site(tokens=("old-token-1", "new-token-2"), valid={"new-token-2"})
    recs, files, why = wm2_rj_gis.fetch(P, get)
    assert why == "" and calls["token"] == 2 and len(recs) == 2 and len(files) == 1
    assert calls["query"][-1]["token"] == "new-token-2"


def test_token_api_fails():
    assert wm2_rj_gis.fetch(P, FakeGet({}))[2] == "token API: no answer"
    get, _ = site(token_answer=json.dumps({"Status": False, "Messages": []}))
    assert wm2_rj_gis.fetch(P, get) == ([], [], "token API: Status not true")
    get, _ = site(token_answer="<html>Please sign in</html>")
    assert wm2_rj_gis.fetch(P, get)[2].startswith("token API: not JSON")
    get, _ = site(token_answer=json.dumps({"Status": True, "Messages": [{"ServiceName": "basemap", "Token": "x"}]}))
    assert wm2_rj_gis.fetch(P, get)[2] == "token API: no dynamicquery token"


def test_layer_keeps_refusing_the_token():
    get, calls = site(tokens=("bad-1", "bad-2"), valid=set())
    recs, files, why = wm2_rj_gis.fetch(P, get)
    assert (recs, files) == ([], []) and "Token Required" in why and calls["token"] == 2
    assert "bad-" not in why


def test_short_run_is_not_stored():
    get, calls = site()
    fewer = dict(FC, features=FC["features"][:2])

    def layer(url, method, data):           # count says 4, the pages give 2
        if data.get("returnCountOnly") == "true":
            return json.dumps({"count": 4})
        return json.dumps(fewer) if data["where"].endswith("> -1") else '{"type":"FeatureCollection","features":[]}'
    get.routes[LAYER + "/query"] = layer
    assert wm2_rj_gis.fetch(P, get) == ([], [], "got 2 of 4 features")
