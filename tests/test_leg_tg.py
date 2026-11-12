"""Telangana MLAs and MLCs (dforms/leg_tg.py) from legislature.telangana.gov.in, on the member lists and two profiles fetched
2026-11-12 from dev-vps-3 (scripts, styles and page chrome taken out)."""
import json

from esw_common import DATA, ROOT, Answer, check_records, mod

D = DATA / "leg_tg"


def _get(list_file, profile_file):
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append(url)
        if "MemberDetails" in url:
            return Answer((D / profile_file).read_bytes(), url)
        return Answer((D / list_file).read_bytes(), url)
    get.calls = calls
    return get


def test_leg_tg_seeds():
    m = mod("leg_tg")
    items = json.loads((ROOT / "seeds" / "dept_leg_tg.json").read_text())
    assert items == m.items() and [i["payload"]["kind"] for i in items] == ["AC", "LC"]
    assert all(i["payload"]["india_only"] and i["payload"]["state"] == "TS" for i in items)
    assert m.query("getMLAMemberDetails?q=bWVtaWQ9MzU3NiZjb25zdGlkPTEmdGVybWlkPTE2Jm9yZGVyYnk9MQ==") == {
        "memid": "3576", "constid": "1", "termid": "16", "orderby": "1"}


def test_leg_tg_assembly():
    m = mod("leg_tg")
    p = m.items()[0]["payload"]
    get = _get("tg_list.html", "tg_mem1.html")
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 118 and len(get.calls) == 119   # 60 Khairatabad: "VACANT" on the list
    assert [f[0] for f in files] == ["depts/leg_tg/list-ac.html.gz", "depts/leg_tg/profiles-ac.json.gz"]
    check_records(recs, "leg_tg", "elected")
    r = dict(recs)
    assert {k.split("-")[-1] for k in r} == {str(i) for i in range(1, 120)} - {"60"}
    a = r["dept:leg_tg:TS-AC-1"]
    assert (a["name"], a["party"], a["area"], a["phone"], a["email"]) == (
        "DR. PALVAI HARISH BABU", "BJP", "1 - Sirpur", "9502781218, 6302608518", "harishpalvai@gmail.com")
    assert a["address"].startswith("H.No.3-4-20, Sirsilk Colony") and a["member_id"] == "3576"
    assert a["profile"]["Education Qualifications"] == "M.B.B.S., M.S. (Ortho), D.N.B. (Ortho)"
    assert r["dept:leg_tg:TS-AC-5"]["area"] == "5 - Asifabad (ST)" and r["dept:leg_tg:TS-AC-5"]["name"] == "KOVA LAXMI"


def test_leg_tg_council():
    m = mod("leg_tg")
    p = m.items()[1]["payload"]
    get = _get("tg_clist.html", "tg_cmem1.html")
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 39                        # 40 seats, one vacant
    r = dict(recs)
    v = r["dept:leg_tg:TS-LC-s-vani-devi"]
    assert v["area"] == "Graduates, Mahabubnagar, Ranga Reddy, Hyderabad" and v["level"] == "state"
    assert v["phone"] == "9885195165, 9966991548" and v["email"] == "sesvanirao@gmail.com"
    groups = [d["area"].split(",")[0] for d in r.values()]
    assert groups.count("Nominated") == 6 and groups.count("Local Authorities") == 13
