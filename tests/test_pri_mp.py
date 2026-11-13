"""Offline tests of the Madhya Pradesh PRI reader (dforms/pri_mp.py, Panchayat Darpan) on pages saved 2026-11-13."""
import json

from pri_common import DATA, ROOT, check_pri, fake_get, mod

B = "https://mppanchayatdarpan.gov.in"
REPS = B + "/Panchayat/Handlers/Get_Representatives_Details_By_OfficeID.ashx"


def test_pri_mp_seeds():
    m = mod("pri_mp")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_mp.json").read_text())
    assert seeds == m.items()
    kinds = [s["payload"]["kind"] for s in seeds]
    assert kinds.count("district") == 52 and kinds.count("janpad") == 313 and len({s["key"] for s in seeds}) == 365
    assert m.METHOD
    lgd = m.LGD
    assert sum(1 for d in lgd.values() for j in d["janpads"].values() if j.get("lgd")) >= 300
    assert lgd["33"]["zp_lgd"] == "386" and lgd["33"]["janpads"]["24234"]["lgd"] == "4348"      # Sehore; Nasrullaganj = "नस.गंज"
    assert lgd["29"]["zp_lgd_name"] == "East Nimar"                                              # Khandwa


def test_pri_mp_janpad_flow_sehore():
    m = mod("pri_mp")
    p = next(i["payload"] for i in m.items() if i["key"] == "pri_mp:janpad:24235")
    gp_search = B + "/panchayat/Search.aspx?TypeID=%2bzEfuxGGQVK2FrsclPfLMg%3d%3d"
    get = fake_get({B + "/Handlers/GpZones_En.ashx?LbId=24235": "pri/mp_gpzones_24235.json",
                    ("GET", gp_search): "pri/mp_search_gp.html",
                    (lambda u, meth, d: meth == "POST" and d["ctl00$ContentPlaceHolder1$hdnGp"] == "14985"): "pri/mp_gp_home.html",
                    REPS + "?OID=15567&QS=GP&ID=14985": "pri/mp_gp_reps.html"})
    recs, files, why = m.fetch(p, get)
    check_pri(recs, "pri_mp", "MP")
    assert len(recs) == 21 and why == ""          # the fixture holds one gram panchayat of the 154; the others give no cards
    posts = get.calls
    assert sum(1 for c in posts if c[0] == "POST") == 154                # one View Details post per gram panchayat of the janpad
    d = dict(recs)
    s = d["pri:pri_mp:gp:14985:1"]
    assert s["name"] == "आशीष कुमार" and s["post"] == "Sarpanch" and s["role"] == "head" and s["level"] == "gp"
    assert s["body_name"] == "अहमदपुर" and s["block"] == "सीहोर" and s["district"] == "SEHORE" and s["block_lgd"] == "4349"
    assert s["src_pos"] == {"card": 1} and s["source"].endswith("OID=15567&QS=GP&ID=14985")
    assert d["pri:pri_mp:gp:14985:21"]["post"] == "Up-Sarpanch"
    assert sum(1 for _, r in recs if r["post"].startswith("Panch")) == 19


def test_pri_mp_district_flow_zp_and_janpad():
    m = mod("pri_mp")
    p = next(i["payload"] for i in m.items() if i["key"] == "pri_mp:district:33")
    zp_search = B + "/panchayat/Search.aspx"
    jp_search = B + "/panchayat/Search.aspx?TypeID=Qri3376EFpjxJdBBauGZLg%3d%3d"

    def post_to(page, lb):
        return lambda u, meth, d: meth == "POST" and u == page and d.get("ctl00$ContentPlaceHolder1$hdnLBID", "0") == lb
    get = fake_get({("GET", zp_search): "pri/mp_search_zp.html", ("GET", jp_search): "pri/mp_search_jp.html",
                    post_to(zp_search, "0"): "pri/mp_zp_home.html", post_to(jp_search, "24235"): "pri/mp_jp_home.html",
                    REPS + "?OID=37881&QS=ZP&ID=33": "pri/mp_zp_reps.html", REPS + "?OID=570&QS=JP&ID=24235": "pri/mp_jp_reps.html"})
    recs, files, why = m.fetch(p, get)
    check_pri(recs, "pri_mp", "MP")
    d = dict(recs)
    zp = [r for _, r in recs if r["level"] == "zp"]
    jp = [r for _, r in recs if r["level"] == "ps"]
    assert zp and jp
    a = d["pri:pri_mp:zp:33:1"]
    assert a["name"] == "श्रीमती रचना सिंह मेवाड़ा" and a["role"] == "head" and a["lgd_code"] == "386"
    assert d["pri:pri_mp:zp:33:2"]["role"] == "deputy"
    j = d["pri:pri_mp:jp:24235:1"]
    assert j["name"] == "श्रीमति नावडी बाई" and j["post"].startswith("Adhyaksh") and j["level"] == "ps" and j["lgd_code"] == "4349"
    assert why == ""                         # the other janpads of Sehore are not in the fixture (no cards, no failure)


def test_pri_mp_cards_parse():
    m = mod("pri_mp")
    c = m.cards((DATA / "pri/mp_jp_reps.html").read_text())
    assert c[0][1] == "श्रीमति नावडी बाई" and c[0][2] == "अध्यक्ष, जनपद पंचायत"
    assert c[0][3].startswith(B + "/Panchayat/Pages/Representatives_Profile.aspx?RID=")
    assert all(m.post_of(p) for _, _, p, _ in c)
