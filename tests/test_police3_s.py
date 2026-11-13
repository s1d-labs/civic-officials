"""South / north-east police readers (dforms/police3_*.py) on saved samples (tests/data/police3_*): no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_police2n import FakeGet  # noqa: E402

from dforms import police3_tg  # noqa: E402

TG = "police3_tg/"
HYD = police3_tg.HYD
CYB = police3_tg.CYB


def one(recs):
    assert len(recs) == 1
    return recs[0][1]


def test_tg_items():
    get = FakeGet({HYD + "know_your_ps.html": TG + "hyd_know_your_ps.html", CYB + "Preview?page_id=273": TG + "cyb_273.html"})
    items = police3_tg.items(get)
    forms = {}
    for i in items:
        forms[i["payload"]["form"]] = forms.get(i["payload"]["form"], 0) + 1
        assert i["payload"]["reader"] == "police3_tg"
    assert forms == {"hyd_dir": 1, "s3waas": 6, "si_table": 1, "hyd": 106, "cyb": 33}
    assert len({i["key"] for i in items}) == len(items)
    kinds = [i["payload"]["kind"] for i in items if i["payload"]["form"] == "cyb"]
    assert kinds.count("ps") == 23 and kinds.count("acp") == 7 and kinds.count("dcp") == 3


def test_tg_hyd_station():
    url = HYD + "ps/charminar_ps.html"
    recs, files, why = police3_tg.fetch({"form": "hyd", "kind": "ps", "url": url}, FakeGet({url: TG + "hyd_ps_charminar.html"}))
    d = one(recs)
    assert why == "" and files[0][0].startswith("depts/police/police3_tg/")
    assert d["area"] == "Charminar" and d["level"] == "police_station" and d["district"] == "Hyderabad"
    assert d["name"] == "T. Rambabu" and d["rank"] == "Inspector of Police"
    assert d["phone"] == "8712660310, 040-27854787, 040-27854953, 8712661283"
    assert d["email"] == "sho-cmnr-hyd@tspolice.gov.in" and d["patrol_cars"] == "8712664337, 8712664338"
    assert d["officers"][0] == {"post": "Detective Inspector", "name": "K. Narsing Rathod", "phone": "8712660311"}
    assert len(d["officers"]) == 7 and d["strength"]["Constables"] == 55 and d["src_pos"]


def test_tg_hyd_acp_dcp_dir():
    u1, u2, u3 = HYD + "acp/malakpet_acp.html", HYD + "dcp/charminarzone_dcp.html", HYD + "Important_Contacts.html"
    get = FakeGet({u1: TG + "hyd_acp_malakpet.html", u2: TG + "hyd_dcp_charminarzone.html", u3: TG + "hyd_important_contacts.html"})
    a = one(police3_tg.fetch({"form": "hyd", "kind": "acp", "url": u1}, get)[0])
    assert a["level"] == "circle" and a["area"] == "Malakpet" and a["name"] == "L Raja Venkat Reddy"
    assert a["phone"] == "040-27854713, 8712660507" and a["jurisdiction"] == ["Malakpet", "Chaderghat", "Dabeerpura"]
    d = one(police3_tg.fetch({"form": "hyd", "kind": "dcp", "url": u2}, get)[0])
    assert d["level"] == "district" and d["area"] == "Charminar Zone" and d["name"] == "Sri. Khare Kiran Prabhakar, IPS"
    assert d["officers"][0]["name"] == "Sri. Md Majeed" and d["email"] == "dcp-cmnrzn-hyd@tspolice.gov.in"
    recs, _, why = police3_tg.fetch({"form": "hyd_dir", "url": u3}, get)
    assert len(recs) == 29
    cp = recs[0][1]
    assert cp["post"] == "Commissioner of Police, Hyderabad City" and cp["name"] == "Sri. V.C. Sajjanar, IPS"
    assert cp["email"] == "cp-hyderabad@tspolice.gov.in" and cp["src_pos"] == {"table": 0, "row": 1}


def test_tg_cyberabad():
    u = CYB + "Preview?page_id="
    get = FakeGet({u + "106": TG + "cyb_106.html", u + "130": TG + "cyb_130.html", u + "34": TG + "cyb_34.html"})
    s = one(police3_tg.fetch({"form": "cyb", "kind": "ps", "url": u + "106"}, get)[0])
    assert s["area"] == "Jagadgirigutta PS" and s["district"] == "Medchal Malkajgiri" and s["name"] == "N Suresh"
    assert s["phone"] == "8712663230, 8712663229" and s["email"] == "shojagadgirigutta@gmail.com"
    assert s["officers"][0]["name"] == "P. Narendra Reddy" and s["cyber_warrior"] == "8712512867"
    a = one(police3_tg.fetch({"form": "cyb", "kind": "acp", "url": u + "130"}, get)[0])
    assert a["area"] == "RC - Puram" and a["name"] == "CH. Y. Srinivas Kumar" and a["phone"] == "8712663460, 040-27853445"
    d = one(police3_tg.fetch({"form": "cyb", "kind": "dcp", "url": u + "34"}, get)[0])
    assert d["area"] == "SERILINGAMPALLY" and d["name"] == "CH. Srinivas, IPS" and d["phone"] == "8712663004, 040-27853423"


def test_tg_district_pages():
    u1 = "https://mahabubabad.telangana.gov.in/police/"
    u2 = "https://hanumakonda.telangana.gov.in/public-utility-category/police-stations/"
    get = FakeGet({u1: TG + "mahabubabad_police.html", u2: TG + "hanumakonda_ps.html"})
    recs, _, why = police3_tg.fetch({"form": "si_table", "url": u1, "district": "Mahabubabad"}, get)
    assert len(recs) == 45 and all(d.get("phone") and d.get("name") for _, d in recs)
    first = recs[0][1]
    assert first["area"] == "Mahabubabad Town" and first["post"] == "SI-I" and first["phone"] == "9440795238"
    recs, _, why = police3_tg.fetch({"form": "s3waas", "url": u2, "district": "Hanumakonda"}, get)
    assert len(recs) == 10 and all(d["state"] == "TG" for _, d in recs)
