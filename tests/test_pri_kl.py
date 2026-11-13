"""cforms/pri_kl.py: Kerala panchayat members (SEC ward tables + member pages; body site head cards). Fixtures saved 2026-11-13
from sec.kerala.gov.in (Thiruvananthapuram = URL district 14), alappadpanchayat.lsgkerala.gov.in and lsgkerala.gov.in (archive)."""
import json
from pathlib import Path

import pytest

from cforms import pri_kl

DATA = Path(__file__).parent / "data" / "pri_kl"
SEEDS = Path(__file__).parents[1] / "seeds"


class R:
    def __init__(self, text, url):
        self.text, self.url, self.content, self.status_code = text, url, text.encode(), 200


def page(name):
    return (DATA / name).read_text(encoding="utf-8")


def test_district_numbers():
    assert pri_kl.sec_district(14) == "01" and pri_kl.sec_district("1") == "14" and pri_kl.sec_district("x") == ""


def test_body_list_and_items():
    rows = pri_kl.body_list(page("wyrlb_14_G.html"))
    assert len(rows) == 73
    assert rows[0][:3] == ("G01001", "പാറശാല", "2338") and rows[0][4] == "24"
    items = pri_kl.sec_items({(14, "G"): page("wyrlb_14_G.html")})
    zp = [i for i in items if i["payload"]["level"] == "zp"]
    gp = [i for i in items if i["payload"]["level"] == "gp"]
    assert len(zp) == 14 and len(gp) == 73
    tvm = next(i for i in zp if i["key"] == "pri-kl-d01")["payload"]
    assert tvm["url"].endswith("/public/wyrlb/14/D") and tvm["district"] == "Thiruvananthapuram" and tvm["lgd_code"]
    p = gp[0]["payload"]
    assert p["url"].endswith("/public/wyrw/2338") and p["expected"] == 24 and p["route"] == "direct"
    matched = sum(1 for i in gp if i["payload"].get("lgd_code"))
    assert matched >= 60, matched            # Malayalam name + district against LGD local names


@pytest.mark.parametrize("ml,en,rank", [("പ്രസിഡന്റ്", "", 1), ("വൈസ് പ്രസിഡന്റ്‌", "", 2), ("", "Vice President", 2),
                                         ("", "President", 1), ("ക്ഷേമകാര്യ സ്റ്റാന്റിംഗ് കമ്മിറ്റി മെമ്പർ", "", 0), ("", "", 0)])
def test_head_of(ml, en, rank):
    assert pri_kl.head_of(ml, en) == rank


def test_fetch_sec_district_panchayat():
    url = "https://sec.kerala.gov.in/public/wyrlb/14/D"
    view = "https://sec.kerala.gov.in/public/wyr/view/98590"

    def get(u, **_):
        if u == url:
            return R(page("wyrlb_14_D.html"), u)
        if u == view:
            return R(page("view_98590.html"), u)
        return None
    p = {"kind": "form-pri_kl", "part": "sec", "url": url, "level": "zp", "district": "Thiruvananthapuram", "body": "Thiruvananthapuram",
         "lgd_code": "520", "lb_id": "D01", "sec_code": "D01"}
    recs, files, why = pri_kl.fetch(p, get)
    assert why == "" and len(recs) == 28
    d = dict(recs)
    vp = d["pri:KL:zp:520:w002"]
    assert vp["type"] == "pri_member" and vp["name"] == "B P MURALI" and vp["post"] == "Vice President" and vp["head_rank"] == 2
    assert vp["phone"] == "9446614044" and vp["ward_code"] == "D01001002" and vp["src_pos"]["list_row"] >= 1
    assert vp["src_url"] == view
    heads = [x for x in d.values() if x.get("head_rank") == 1]
    assert len(heads) == 1 and heads[0]["post"] == "President" and heads[0]["member_page"] == "no answer"
    assert heads[0]["src_pos"]["table"] == 0 and heads[0]["src_url"] == url and heads[0]["name_regional"]


def test_fetch_sec_grama_no_posts():
    url = "https://sec.kerala.gov.in/public/wyrw/2338"
    recs, _, why = pri_kl.fetch({"part": "sec", "url": url, "level": "gp", "district": "Thiruvananthapuram", "lb_id": "2338"},
                                lambda u, **_: R(page("wyrw_2338.html"), u) if u == url else None)
    assert why == "" and len(recs) == 24
    rid, d = recs[0]
    assert d["ward_no"] == "001" and d["party"] == "BJP" and d["post"] == "Member" and "head" not in d
    assert rid == "pri:KL:gp:thiruvananthapuram~~:w001"


def test_site_heads():
    cards = pri_kl.profile_cards(page("site_alappad_home.html"))
    assert (cards[0][1], cards[0][2]) == ("Jayasree S", "President")
    url = "https://alappadpanchayat.lsgkerala.gov.in/en"
    recs, _, why = pri_kl.fetch({"part": "site", "url": url, "level": "gp", "district": "Kollam", "body": "Alappad", "lgd_code": "1"},
                                lambda u, **_: R(page("site_alappad_home.html"), u))
    d = dict(recs)
    assert why == "" and set(d) == {"pri:KL:gp:1:head-site", "pri:KL:gp:1:vice-site"}
    assert d["pri:KL:gp:1:head-site"]["name"] == "Jayasree S" and d["pri:KL:gp:1:vice-site"]["name"] == "Saji Sugathan"


def test_index_rows():
    rows, more = pri_kl.index_rows(page("lsg_index_p0.html"))
    assert more and rows and all(r[1][0] in "GBD" for r in rows)
    it = pri_kl.item_site(*rows[0][:3], pri_kl._pri.Lgd("KL"))
    assert it["payload"]["part"] == "site" and it["payload"]["url"].endswith("/en") and it["payload"]["district"]


def test_seed_file():
    items = json.loads((SEEDS / "pri_kl.json").read_text())
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) and "pri-kl-seed-sites" in keys
    sec = [i for i in items if i["payload"].get("part") == "sec"]
    assert len([i for i in sec if i["payload"]["level"] == "zp"]) == 14
    assert len([i for i in sec if i["payload"]["level"] == "ps"]) >= 150
    assert len([i for i in sec if i["payload"]["level"] == "gp"]) >= 900
