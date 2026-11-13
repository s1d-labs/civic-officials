"""Offline tests of dforms/pri_tr.py (Tripura TTAADC Village Committee results 2026) on a cut of the SEC board's JSON answer
(tests/data/pri/tr_vc2026.json: 1 district, 2 blocks, 2 village committees each)."""
import json

from pri_common import ROOT, check_pri, fake_get, mod


def test_pri_tr_seeds():
    m = mod("pri_tr")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_tr.json").read_text())
    assert seeds == m.items() and len(seeds) == 1 and m.METHOD
    assert seeds[0]["payload"]["route"] == "direct"


def test_pri_tr_fetch():
    m = mod("pri_tr")
    p = m.items()[0]["payload"]
    get = fake_get({("POST", m.API): "pri/tr_vc2026.json"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and files == [] and len(recs) == 40
    assert get.calls == [("POST", m.API, '{"key": "GP_Results_Summary"}')]
    check_pri(recs, "pri_tr", "TR")
    d = dict(recs)
    r = d["pri:pri_tr:vc2026:649"]
    assert r["name"] == "Purnamohan Tripura" and r["body_name"] == "Dalapati" and r["ward"] == "Dalapati-I"
    assert r["ward_no"] == "1" and r["category"] == "ST" and r["votes"] == 118 and r["status"] == "won"
    assert r["district"] == "Dhalai" and r["district_lgd_code"] == "269" and r["block"] == "Dumburnagar"
    assert r["level"] == "gp" and r["role"] == "member" and r["body_type"] == "village_committee"
    assert r["src_pos"]["path"] == "data[0].block_results[1].gp_results[1].constituency_result[0]"
    assert len(r["candidates"]) >= 2 and any(c["is_winner"] == 1 for c in r["candidates"])
    u = d["pri:pri_tr:vc2026:306"]
    assert u["status"] == "elected unopposed" and "votes" not in u and u["category"] == "SC"
    assert sum(1 for _, x in recs if x["status"] == "elected unopposed") == 1


def test_pri_tr_seat_parts():
    m = mod("pri_tr")
    assert m.seat_parts("East Manu-I : Seat No-1 [UR]") == ("East Manu-I", "1", "UR")
    assert m.seat_parts("odd text") == ("odd text", "", "")
