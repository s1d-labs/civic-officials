"""Offline tests of the legislator readers (dforms/leg_*.py: Lok Sabha, Rajya Sabha, state assemblies) on small saved answers in
tests/data/leg/. No test touches the network."""
import json

from esw_common import ROOT, check_records, fake_get, mod


def _seed(module):
    items = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    assert items == mod(module).items() and all(i["key"].startswith("leg_") for i in items)
    return items


def _run(module, url, sample, payload=None):
    p = payload or _seed(module)[0]["payload"]
    recs, files, why = mod(module).fetch(p, fake_get({url: f"leg/{sample}"}))
    assert why == "" and files and files[0][0].startswith(f"depts/{module}/")
    check_records(recs, module, "elected")
    return dict(recs)


def test_leg_helpers():
    from dforms import _leg
    assert _leg.state_code("Keralam") == "KL" and _leg.state_code("NCT of Delhi") == "DL" and _leg.state_code("Telangana") == "TS"
    assert _leg.pc_no("TN", "Nilgiris (SC)") == 19 and _leg.pc_no("AP", "Chittoor (SC)") == 42 and _leg.pc_no("LA", "Ladakh") == 1
    assert _leg.ac_seat("AP", 56, "Achanta") == (175, "")          # the site keeps the united-AP numbers
    assert _leg.ac_seat("KA", "150") == (150, "")
    assert _leg._join("9999864553", "09999864553, (011) 24644455") == "9999864553, (011) 24644455"


def test_leg_ls():
    url = mod("leg_ls").URL
    recs = _run("leg_ls", url, "ls_members.json")
    assert len(recs) == 4
    mani = recs["dept:leg_ls:TN-PC-10"]
    assert mani["name"] == "Mani A" and mani["phone"] == "9894087656" and mani["office_id"] == "TN-PC-10"
    assert mani["email"] == "manimbb@gmail.com, amani.mp@mpls.sansad.in" and mani["level"] == "pc"
    assert mani["delhi_address"] == "902, KRISHNA, BKS MARG, NEW DELHI - 110011" and mani["address"].endswith("Tamil Nadu - 635205")
    assert mani["party"] == "Dravida Munnetra Kazhagam" and mani["area"] == "10 - Dharmapuri" and mani["last_updated"] == "2026-10-05"
    raja = recs["dept:leg_ls:TN-PC-19"]
    assert raja["phone"] == "9999864553, (011) 24644455, 24644466" and raja["constituency"] == "Nilgiris (SC)"
    guw = recs["dept:leg_ls:AS-PC-7"]                              # Guwahati (2023 seat) -> the layer's Gauhati
    assert guw["constituency"] == "Guwahati" and guw.get("seat_note")
    assert "dept:leg_ls:DN-PC-1" in recs


def test_leg_rs():
    p = _seed("leg_rs")[0]["payload"]
    assert len(_seed("leg_rs")) == 9
    recs = _run("leg_rs", p["url"], "rs_members.json", p)
    assert "dept:leg_rs:BR-RS-aas-mohammad" not in recs           # retired members are left out
    w = recs["dept:leg_rs:KL-RS-abdul-wahab"]
    assert w["level"] == "state" and w["office_id"] == "KL-RS-abdul-wahab" and w["email"] == "wahab.pv@sansad.nic.in"
    assert w["phone_residence"] == "04931-220542, 222555, 9447766777, 9847020911" and w["fax"] == "04931-221988"
    assert w["address"].startswith("Peevees Mirage, Nilambur") and w["delhi_address"].startswith("402 - Swarna Jayanti Sadan")
    assert w["term"] == "2021-2027" and w["party"] == "Indian Union Muslim League"
    assert recs["dept:leg_rs:UP-RS-radha-mohan-das-agrawal"]["phone"] == "0551-2200950"
    assert any(d["state"] == "NM" and d.get("nominated") == "yes" for d in recs.values())


def test_leg_kl():
    recs = _run("leg_kl", mod("leg_kl").URL, "kl_member_contacts.html")
    m = recs["dept:leg_kl:KL-AC-62"]
    assert m["name"] == "A C Moideen" and m["area"] == "62 - Kunnamkulam" and m["office_id"] == "KL-AC-62"
    assert m["phone"] == "0471-2512226, 9447978800" and m["email"] == "acmoideen@niyamasabha.nic.in"
    assert m["office_address"] == "MLA Hostel, Neyyar Block 6C" and m["address"].startswith("Aakkaparambil House")
    a = recs["dept:leg_kl:KL-AC-1"]
    assert a["office_address"] == "Nila Block 53" and a["phone"] == "0471-2512317, 9995239701"
    assert recs["dept:leg_kl:KL-AC-113"]["phone"] == "9847965420" and "email" not in recs["dept:leg_kl:KL-AC-113"]
