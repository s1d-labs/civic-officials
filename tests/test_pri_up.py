"""Offline tests of dforms/pri_up.py (Uttar Pradesh SEC panchayat election 2021 winner list) on pages saved 2026-11-13
(tests/data/pri/up_sec2021_*.html.gz; view state cut in the large ones)."""
import gzip
import json
import re

from esw_common import Answer
from pri_common import DATA, ROOT, check_pri, mod

P = "ctl00$ContentPlaceHolder1$"


def page(name):
    return gzip.decompress((DATA / "pri" / f"up_sec2021_{name}.html.gz").read_bytes()).decode("utf-8")


def recs(name, post, **kw):
    m = mod("pri_up")
    return m.records(page(name), post, {"src_url": m.URL, "src_sha256": "x"}, **kw)


def test_pri_up_items():
    m = mod("pri_up")
    items = m.items()
    seeds = json.loads((ROOT / "seeds" / "dept_pri_up.json").read_text())
    assert seeds == items and len(items) == 2 + 4 * 75 and len({i["key"] for i in items}) == len(items)
    assert [i["payload"]["post"] for i in items[:3]] == ["1", "3", "5"]
    assert all(i["payload"]["route"] == "direct" and i["payload"]["reader"] == "pri_up" for i in items)
    assert len(m.lgd()["districts"]) == 75 and m.METHOD


def test_pri_up_zp_adhyaksh_statewide():
    r = recs("p1", "1")
    check_pri(r, "pri_up", "UP")
    assert len(r) == 75 and all(d["lgd_code"] and d["level"] == "zp" and d["role"] == "head" for _, d in r)
    d = dict(r)["pri:pri_up:zp:584"]                     # Amethi
    assert d["name"] == "राजेश कुमार अग्रहरी" and d["phone"] == "9919623555" and d["votes"] == 31 and d["age"] == 51
    assert d["post"] == "Zila Panchayat Adhyaksh" and d["district"] == "Amethi" and d["status"] == "won (contested)"
    assert d["src_pos"] == {"table": "ctl00_ContentPlaceHolder1_GridView1", "row": 2} and d["cells"]["उम्मीदवार"] == d["name"]


def test_pri_up_pramukh_statewide_block_match():
    r = recs("p3", "3")
    check_pri(r, "pri_up", "UP")
    assert len(r) == 825
    matched = sum(1 for _, d in r if d.get("lgd_code"))
    assert matched >= 785                                   # 788 of 825 on 2026-11-13 (95.5 %)
    d = next(d for _, d in r if d["district"] == "Amethi" and d["block"] == "गौरी गंज")
    assert d["status"] == "elected unopposed" and "votes" not in d and d["phone"] == "9919022023"


def test_pri_up_zp_members_district():
    r = recs("p2_d47", "2", district_id="47")
    check_pri(r, "pri_up", "UP")
    assert len(r) == 25 and all(d["lgd_code"] == "153" for _, d in r)
    d = dict(r)["pri:pri_up:zp:153:w24"]
    assert d["ward"] == "गोसाईगंज तृतीय" and d["name"] == "विजय बहादुर यादव" and d["votes"] == 14749


def test_pri_up_pradhan_and_members_block():
    r = recs("p5_b450", "5", district_id="47", block_id="450", block_name="गोसाईगंज")
    check_pri(r, "pri_up", "UP")
    assert len(r) == 76 and sum(1 for _, d in r if d.get("lgd_code")) >= 74       # 75 of 76 on 2026-11-13
    d = dict(r)["pri:pri_up:gp:450:2"]
    assert d["body_name"] == "रहमतनगर" and d["phone"] == "9919852888" and d["block_lgd_code"] == "1913" and d["post"] == "Gram Pradhan"
    assert d["seat_reservation"] == "अनुसूचित जाति" and d["gender"] == "male"
    assert dict(r)["pri:pri_up:gp:450:76"]["lgd_code"]                              # देई टीकर -> Daeetikar
    k = recs("p4_b450", "4", district_id="47", block_id="450", block_name="गोसाईगंज")
    check_pri(k, "pri_up", "UP")
    assert len(k) == 94 and dict(k)["pri:pri_up:ps:450:w2"]["ward"] == "गौरियां कलां एवं सुरियामऊ"
    g = recs("p6_b450", "6", district_id="47", block_id="450", block_name="गोसाईगंज")
    check_pri(g, "pri_up", "UP")
    assert len(g) == 952 and dict(g)["pri:pri_up:gp:450:1:w2"]["name"] == "ताहिरा"


def test_pri_up_fetch_flow_district():
    m = mod("pri_up")
    nodata = page("p5_d47_nodata")

    def get(url, method="GET", data=None, headers=None):
        get.calls.append((method, data and {k: v for k, v in data.items() if not k.startswith("__V")}))
        assert url == m.URL
        if method == "GET":
            return Answer(page("form").encode(), url)
        if data.get("__EVENTTARGET") == P + "ddlPostTypes":
            return Answer(page("post5").encode(), url)
        if data.get("__EVENTTARGET") == P + "ddlDistrictName":
            return Answer(page("post5_d47").encode(), url)
        b = data.get(P + "ddlBlockName")
        if b in ("450", "451"):
            return Answer(page(f"p5_b{b}").encode(), url)
        # another block: the empty answer, with that block chosen
        h = re.sub(r'(<option )selected="selected" (value="-1")', r"\1\2", nodata)
        return Answer(h.replace(f'<option value="{b}">', f'<option selected="selected" value="{b}">').encode(), url)
    get.calls = []
    p = next(i["payload"] for i in m.items() if i["key"] == "pri_up:p5:d47")
    r, files, why = m.fetch(p, get)
    assert why == "" and len(r) == 76 + 18
    check_pri(r, "pri_up", "UP")
    assert len(get.calls) == 3 + 8                       # GET, post, district, then one submit per block (8 blocks)
    assert all(d["blocks_listed"] == 8 and len(d["blocks_without_rows"]) == 6 for _, d in r)
    assert {d["sec_block_id"] for _, d in r} == {"450", "451"}
