"""Offline tests of the PRI elected-member readers for West Bengal (dforms/pri_wb.py) and Assam (dforms/pri_as.py), on answers
saved in tests/data/pri/ (WB: portal.wbsec.org JSON answers of 2026-11-13; AS: archive copy of sec.assam.gov.in/results and one
synthetic table page, marked as such in its title)."""
import json

from pri_common import DATA, ROOT, check_pri, fake_get, mod

API = "https://portal.wbsec.org/Index.aspx/SelectCandidateVotesinFavourPortalList"


def _wb_route(level, uid, name):
    return (lambda u, m, d: u == API and m == "POST" and f"'CandidateFor':'{level}'" in d and f"'{uid}'" in d), f"pri/{name}"


def test_pri_wb_seeds_and_tree():
    m = mod("pri_wb")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_wb.json").read_text())
    assert seeds == m.items() and len(seeds) == 22 + 346 and len({s["key"] for s in seeds}) == len(seeds)
    t = m.tree()
    assert len(t) == 22 and sum(len(z["ps"]) for z in t) == 346 and sum(len(p["gp"]) for z in t for p in z["ps"]) == 3321
    assert all(z.get("lgd") for z in t)                                           # every ZP has its LGD code
    assert sum(bool(p.get("lgd")) for z in t for p in z["ps"]) >= 320
    assert sum(bool(g.get("lgd")) for z in t for p in z["ps"] for g in p["gp"]) >= 3000
    assert m.METHOD


def test_pri_wb_zp_district():
    m = mod("pri_wb")
    p = next(i["payload"] for i in m.items() if i["key"] == "pri_wb:zp:110000000")
    r, f = _wb_route("ZP", 110000000, "wb_zp_coochbehar.json")
    get = fake_get({r: f})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 33 and len(get.calls) == 1
    check_pri(recs, "pri_wb", "WB")
    d = dict(recs)["pri:pri_wb:zp:71842"]
    assert d["name"] == "PRATIMA DEB" and d["party"] == "AITC" and d["votes"] == 18839 and d["runner_up"] == "RENUKA BARMAN"
    assert d["margin"] == 18839 - 14001 and d["level"] == "zp" and d["lgd_code"] == "268" and d["ward"] == "MEKHLIGANJ/ZP-1"
    assert d["ward_no"] == "1" and d["status"] == "won (most votes)" and d["src_pos"] == {"index": 0, "id": 71842}
    assert d["src_url"] == API and len(d["src_sha256"]) == 64 and d["cells"]["ElectoralPartSerialNo"] == "38/75"


def test_pri_wb_block_ps_and_gp():
    m = mod("pri_wb")
    p = next(i["payload"] for i in m.items() if i["key"] == "pri_wb:ps:110101000")
    routes = dict([_wb_route("PS", 110101000, "wb_ps_coochbehar1.json"), _wb_route("GP", 110101001, "wb_gp_moamari.json")])
    get = fake_get(routes)
    m.time.sleep = lambda s: None                      # other GPs of the block are not saved: no waiting between tries
    recs, files, why = m.fetch(p, get)
    assert recs == [] and why.startswith("no answer for 14 of 16 units")      # the item fails whole: the hub runs it again
    tree_ps = m.tree()[0]["ps"][0]
    one = dict(tree_ps, gp=tree_ps["gp"][:1])
    r1, rows1 = m.call(get, "ps", 110101000)
    r2, rows2 = m.call(get, "gp", 110101001)
    ps = m.records(rows1, r1, "ps", one, m.tree()[0], one)
    gp = m.records(rows2, r2, "gp", one["gp"][0], m.tree()[0], one)
    check_pri(ps + gp, "pri_wb", "WB")
    assert len(ps) == 42 and len(gp) == 11
    g = dict(gp)["pri:pri_wb:gp:10155"]
    assert g["name"] == "ANJALI BARMAN SARKAR" and g["body_name"] == "MOAMARI" and g["lgd_code"] == "108946"
    assert g["lgd_match"] == "fuzzy" and g["block"] == "COOCH BEHAR - I" and g["post"] == "Gram Panchayat Member"
    assert g["address"].startswith("VILL-MOWAMARI") and g["age"] == 36 and g["father_name"] == "PRASENJIT BARMAN"
    assert all(d["lgd_code"] == "3219" for _, d in ps)


def test_pri_wb_tie_and_single():
    m = mod("pri_wb")
    rows = [{"SeatID": 1, "SeatIndex": 1, "SeatName": "X/I-1", "CandidateName": "A", "VoteInFavour": 10},
            {"SeatID": 1, "SeatIndex": 2, "SeatName": "X/I-1", "CandidateName": "B", "VoteInFavour": 10},
            {"SeatID": 2, "SeatIndex": 1, "SeatName": "X/I-2", "CandidateName": "C", "VoteInFavour": 0}]
    body = {"id": 9, "name": "X"}
    recs = dict(m.records(rows, None, "gp", body, {"name": "D"}, {"name": "B1"}))
    assert set(recs) == {"pri:pri_wb:gp:1:1", "pri:pri_wb:gp:1:2", "pri:pri_wb:gp:2"}
    assert recs["pri:pri_wb:gp:1:1"]["status"] == "tie in the result list" and "margin" not in recs["pri:pri_wb:gp:1:1"]
    assert recs["pri:pri_wb:gp:1:2"]["runner_up"] == "A" and recs["pri:pri_wb:gp:1:1"]["runner_up_votes"] == 10
    assert recs["pri:pri_wb:gp:2"]["status"] == "only candidate in the result list" and recs["pri:pri_wb:gp:2"]["candidates"] == 1


def test_pri_as_save_step():
    m = mod("pri_as")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_as.json").read_text())
    assert seeds == m.items() and seeds[0]["payload"]["route"] == "proxy" and m.METHOD
    get = fake_get({m.URL: "pri/as_results_index.html"})
    recs, files, why = m.fetch(seeds[0]["payload"], get)
    assert why == "" and files and files[0][0].startswith("depts/pri_as/")
    assert recs[0][1]["type"] == "source_file" and recs[0][1]["url"] == m.URL
    asked = [u for _, u, _ in get.calls]
    assert asked[0] == m.URL and "https://sec.assam.gov.in/results/pe-result-2025" in asked
    assert all(u.startswith("https://sec.assam.gov.in/") for u in asked)
    assert not any("facebook" in u or "btc-election" in u for u in asked)


def test_pri_as_plain_table():
    m = mod("pri_as")
    html = (DATA / "pri/as_table_synthetic.html").read_text()
    recs = m.table_records(html, m.URL, None, "t")
    check_pri(recs, "pri_as", "AS")
    d = dict(recs)
    assert len(recs) == 2 and d["pri:pri_as:t:1-2"]["name"] == "TEST PERSON ONE" and d["pri:pri_as:t:1-2"]["votes"] == 12345
    assert d["pri:pri_as:t:1-2"]["level"] == "zp" and d["pri:pri_as:t:1-2"]["constituency"] == "1-Test ZPC"
    assert "votes" not in d["pri:pri_as:t:1-3"]                                  # "n/a" is not a number
