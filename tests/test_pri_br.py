"""Offline tests of dforms/pri_br.py (Bihar SEC panchayat election 2021) on answers recorded once from sec2021.bihar.gov.in
(tests/data/pri/br_*.json.gz: the requests of one item in order, with each answer's body). replay() answers in the same order and
checks that the reader asks the same method, url and form fields."""
import gzip
import json

from pri_common import DATA, ROOT, check_pri, mod
from esw_common import Answer


def replay(name):
    log = json.loads(gzip.decompress((DATA / "pri" / f"br_{name}.json.gz").read_bytes()))
    it = iter(log)

    def get(url, method="GET", data=None, headers=None):
        e = next(it)
        form = {k: v for k, v in (data or {}).items() if not k.startswith("__")}
        assert (e["method"], e["url"], e["form"]) == (method, url, form), (e["form"], form)
        return Answer(e["body"].encode("utf-8"), url)
    get.left = lambda: sum(1 for _ in it)
    return get


def test_pri_br_seeds():
    m = mod("pri_br")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_br.json").read_text())
    assert seeds == m.items() and len(seeds) == 356 and len({s["key"] for s in seeds}) == 356
    assert sum(1 for s in seeds if s["payload"]["mode"] == "result") == 352
    assert {s["payload"]["post"] for s in seeds if s["payload"]["mode"] == "indirect"} == {"1", "2", "3", "4"}
    members = json.loads((ROOT / "seeds" / "dept_pri_br_members.json").read_text())
    assert members == m.member_items() and len(members) == 704
    assert m.METHOD


def test_pri_br_lgd_match():
    m = mod("pri_br")
    assert m.lgd_codes("33", "अरवल", "अरवल", "अवगीला") == ("561", "6804", "238501")    # LGD अबगिला
    assert m.lgd_codes("33", "अरवल", "अरवल", "रामपुर वैना")[2] == "238504"                  # LGD रामपुर बैना
    assert m.lgd_codes(None, "पूर्णियां", None, None)[0] == "205"                            # by name (LGD पुर्णिया)
    assert m.norm("खभैनी पंचायत") == m.norm("खभैनी")


def test_pri_br_result_heads_arwal():
    m = mod("pri_br")
    p = {"reader": "pri_br", "mode": "result", "url": "http://sec2021.bihar.gov.in/claim-objection/Result2.aspx?D=0&PO=1",
         "phase": 2, "district_value": "33", "district": "अरवल", "posts": ["3", "4", "5", "6"], "blocks": ["1"],
         "panchayats": ["330010010", "330010011"], "state": "BR"}
    get = replay("p2_arwal")
    recs, files, why = m.fetch(p, get)
    assert why == "" and get.left() == 0 and len(recs) == 9
    check_pri(recs, "pri_br", "BR")
    d = dict(recs)
    r = d["pri:pri_br:2:33:1:330010010:3:-"]
    assert r["post"] == "Mukhiya" and r["level"] == "gp" and r["role"] == "head" and r["name"] == "राजेश सिंह"
    assert r["votes"] == 1441 and r["n_candidates"] == 10 and r["margin"] == 1441 - 1172 and "winner_by" not in r
    assert r["body_name"] == "अमरा" and r["block"] == "अरवल" and r["district"] == "अरवल"
    assert r["lgd_code"] == "238500" and r["lgd_match"] == "name" and r["lgd_block"] == "6804"
    assert r["src_pos"]["row"] == 7 and r["src_sha256"] and r["src_url"] == p["url"]
    assert r["election"] == "Bihar Panchayat General Election 2021, phase 2" and r["cells"]["कुल प्राप्त मत"] == "1441"
    s = d["pri:pri_br:2:33:1:330010011:4:-"]
    assert s["post"] == "Sarpanch (Gram Kachahri)" and s["body_kind"] == "gram_kachahri" and s["name"] == "सुनीता कुमारी"
    ps = [x for _, x in recs if x["level"] == "ps"]
    assert len(ps) == 3 and {x["constituency"] for x in ps} == {"14", "15", "16"} and all(x["lgd_code"] == "6804" for x in ps)
    zp = d["pri:pri_br:2:33:1:-:6:1"]
    assert zp["name"] == "अशरफुल होदा" and zp["votes"] == 4147 and zp["lgd_code"] == "561" and zp["level"] == "zp"


def test_pri_br_indirect_adhyaksh():
    m = mod("pri_br")
    p = next(i["payload"] for i in m.items() if i["key"] == "pri_br:ind:1")
    get = replay("ind1")
    recs, _, why = m.fetch(p, get)
    assert why == "" and len(recs) == 38
    check_pri(recs, "pri_br", "BR")
    assert all(d["role"] == "head" and d["level"] == "zp" and d.get("lgd_code") for _, d in recs)    # 38 of 38 ZPs matched
    r = next(d for _, d in recs if d["district"] == "अरवल")
    assert r["name"] == "संध्या देवी" and r["father_name"] == "सुधीर कुमार" and r["age"] == 42 and r["gender"] == "महिला"
    assert r["lgd_code"] == "561" and r["reservation"] == "अनारक्षित (अन्य)" and r["src_pos"]["row"] == 3


def test_pri_br_indirect_pramukh_district():
    m = mod("pri_br")
    p = {**next(i["payload"] for i in m.items() if i["key"] == "pri_br:ind:3"), "districts": ["33"]}
    recs, _, why = m.fetch(p, replay("ind3_arwal"))
    assert why == "" and len(recs) == 5
    check_pri(recs, "pri_br", "BR")
    assert {d["block"] for _, d in recs} == {"अरवल", "कुर्था", "करपी", "कलेर", "सोनभद्र वंशी सूर्यपुर"}
    assert {d["lgd_code"] for _, d in recs} == {"6804", "6805", "6806", "6807", "6808"}
    assert all(d["post"] == "Pramukh (Panchayat Samiti)" and d["level"] == "ps" for _, d in recs)
