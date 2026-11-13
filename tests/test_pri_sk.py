"""Offline tests of dforms/pri_sk.py (Sikkim Panchayat General Election 2022) on the saved PDFs: SEC notifications 20 and 21 of
13-11-2022 (contested wards, all districts) and the Soreng district lists (every ward)."""
import json

from pri_common import ROOT, check_pri, fake_get, mod

FILES = {"sec-gp": "pri/sk_sec_gp_2022.pdf", "sec-zp": "pri/sk_sec_zp_2022.pdf",
         "soreng-gp": "pri/sk_soreng_gp_2022.pdf", "soreng-zp": "pri/sk_soreng_zp_2022.pdf"}


def run(label):
    m = mod("pri_sk")
    p = next(i["payload"] for i in m.items() if i["key"] == f"pri_sk:{label}")
    recs, files, why = m.fetch(p, fake_get({p["url"]: FILES[label]}))
    assert why == "" and files == []
    check_pri(recs, "pri_sk", "SK")
    return dict(recs)


def test_pri_sk_seeds():
    m = mod("pri_sk")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_sk.json").read_text())
    assert seeds == m.items() and len(seeds) == 4 and m.METHOD
    assert {s["key"] for s in seeds} == {f"pri_sk:{k}" for k in FILES}


def test_pri_sk_sec_gp():
    d = run("sec-gp")
    assert len(d) == 695
    assert {x["district"] for x in d.values()} == {"Gyalshing", "Soreng", "Namchi", "Gangtok", "Pakyong", "Mangan"}
    r = d["pri:pri_sk:2022:sec:gyalshing:1:4"]
    assert r["name"] == "Lakpa Tshering Sherpa" and r["body_name"] == "Karzi Mangnam" and r["ward"] == "Upper Karzi"
    assert r["level"] == "gp" and r["sn"] == "1" and r["src_pos"]["page"] == 1
    t = next(x for x in d.values() if x["name"] == "Gyatso Bhutia")
    assert t["ward"] == "Tashiding (Tashiding Chogyal Lakhang)" and t["body_name"] == "Tashiding"   # ward broken over 2 lines
    assert not any("Secretary" in x["body_name"] for x in d.values())                                # copy-to lines left out


def test_pri_sk_sec_zp():
    d = run("sec-zp")
    assert len(d) == 102 and {x["body_name"] for x in d.values()} == {"Gyalshing", "Soreng", "Namchi", "Gangtok", "Pakyong", "Mangan"}
    r = d["pri:pri_sk:2022:sec:gyalshing:zp:1"]
    assert r["name"] == "Bina Manger" and r["ward"] == "Karzi Mangnam" and r["symbol"] == "Table" and r["level"] == "zp"


def test_pri_sk_soreng_gp_merged_gpu_cells():
    d = run("soreng-gp")
    assert len(d) == 200 and len({x["body_name"] for x in d.values()}) == 36
    r = d["pri:pri_sk:2022:dist:soreng:1:1"]
    assert r["name"] == "Chali Maya Kami" and r["body_name"] == "Samdong Sribadam" and r["ward"] == "Sango Taar Lower Sribadam"
    assert r["category"] == "SC(W)"
    r = d["pri:pri_sk:2022:dist:soreng:24:3"]                       # GPU and ward cells joined by one space in the text
    assert r["name"] == "Tika Ram Pradhan" and r["body_name"] == "Lower Timburbong" and r["ward"] == "Banpala Salghari"
    assert r["category"] == "OBC(S)" and r["sn"] == "130"
    assert d["pri:pri_sk:2022:dist:soreng:2:4"]["body_name"] == "Bara Samdong Boom Reshi"
    assert all(x.get("category") for x in d.values())


def test_pri_sk_soreng_zp():
    d = run("soreng-zp")
    assert len(d) == 17
    r = d["pri:pri_sk:2022:dist:soreng:zp:12"]
    assert r["name"] == "Mikki Hangma Subba (Limboo)" and r["ward"] == "Soreng Mangsari" and r["category"] == "ST(W)"
