"""cforms/pri_ka.py: eGramSwaraj elected representatives (fixtures saved 2026-11-13: state report, a Goa gram panchayat and
district panchayat, an empty Karnataka gram panchayat)."""
import json
from pathlib import Path

from cforms import pri_ka

DATA = Path(__file__).parent / "data" / "pri_ka"
SEEDS = Path(__file__).parents[1] / "seeds" / "pri_ka.json"


class R:
    def __init__(self, text):
        self.text = text


def fake_get(pages):
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append(url)
        for key, name in pages.items():
            if key in url:
                return R((DATA / name).read_text(encoding="utf-8")) if name else R("[]")
        return R("[]")
    get.calls = calls
    return get


def test_state_gate_karnataka_empty():
    get = fake_get({"ElectedStateReport.do": "egs_state_report.json"})
    recs, files, why = pri_ka.fetch({"state": "KA", "state_code": "29", "lgd_code": "548", "district": "Tumakuru"}, get)
    assert recs == [] and "no elected representatives for KA" in why and len(get.calls) == 1
    rows = json.loads((DATA / "egs_state_report.json").read_text())
    assert pri_ka.state_count(rows, "29") == 0 and pri_ka.state_count(rows, "30") == 1760
    assert json.loads((DATA / "egs_ka_gp_220102.json").read_text()) == []


def test_records_goa_gp_and_zp():
    p = {"state": "GA", "state_code": "30"}
    rows = json.loads((DATA / "egs_ga_gp_254346.json").read_text())
    url = pri_ka.member_url("254346", "30", "gp")
    recs = pri_ka.records(rows, url, p, "gp", "254346", "Advalpal", "North Goa", "Bicholim")
    ids = [r for r, _ in recs]
    assert len(recs) == 6 and ids[0] == "pri:GA:gp:254346:head:egs" and "pri:GA:gp:254346:w03:egs" in ids
    head = recs[0][1]
    assert head["name"] == "VINESHRI VINESH GAONKAR" and head["post"] == "Sarpanch" and head["head"] is True
    assert head["phone"] == "93****4721" and head["phone_masked"] is True and head["src_pos"] == {"index": 0}
    m = dict(recs)["pri:GA:gp:254346:w03:egs"]
    assert m["ward_no"] == "03" and m["post"] == "Panch Member" and m["type"] == "pri_member" and m["level"] == "gp"
    assert m["lgd_code"] == "254346" and m["block"] == "Bicholim" and m["src_url"] == url
    zp = pri_ka.records(json.loads((DATA / "egs_ga_zp_506.json").read_text()), "u", p, "zp", "506", "North Goa")
    assert [r for r, _ in zp] == ["pri:GA:zp:506:head:egs", "pri:GA:zp:506:w1:egs"]


def test_fetch_walks_lgd_tree_when_state_has_members():
    get = fake_get({"ElectedStateReport.do": "egs_state_report.json", "code=506&": "egs_ga_zp_506.json",
                    "code=254346&": "egs_ga_gp_254346.json"})
    recs, files, why = pri_ka.fetch({"state": "GA", "state_code": "30", "lgd_code": "506", "district": "North Goa"}, get)
    assert why == "" and len(recs) == 8 and len(get.calls) > 50
    assert any("level=V" in u for u in get.calls) and all(d["district"] == "North Goa" for _, d in recs)


def test_seeds():
    items = json.loads(SEEDS.read_text())
    assert len(items) == 31 and len({i["key"] for i in items}) == 31
    for i in items:
        p = i["payload"]
        assert p["kind"] == "form-pri_ka" and p["state"] == "KA" and p["state_code"] == "29" and p["route"] == "direct"
        assert p["url"].startswith("https://egramswaraj.gov.in/ElectedMemberRepresent.do?code=" + p["lgd_code"] + "&")
