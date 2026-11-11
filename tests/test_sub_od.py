"""Offline tests of the Odisha district and sub-district readers (dforms/sub_od_dist.py, dforms/sub_od_rti.py) on small saved answers in
tests/data/sub/ (cut from the live pages of 2026-11-11 and the archive.s1d.me copies of 2026-11-05/06)."""
import re

from esw_common import *  # noqa: F401,F403


def _check(recs, module):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:") and d["type"] == "dept_office" and d["state"] == "OD", d
        assert d.get("level") and d.get("source") and d.get("dept") and d.get("district") and d.get("name"), d


def test_sub_od_dist_pages():
    m = mod("sub_od_dist")
    seeds = json.loads((ROOT / "seeds" / "dept_sub_od_dist.json").read_text())
    assert [s["key"] for s in seeds] == ["sub_od_dist"] and seeds[0]["payload"]["india_only"] is True
    get = fake_get({m.URL: "sub/od_dist_p0.html", m.URL + "?page=1": "sub/od_dist_p1.html", m.URL + "?page=2": "sub/od_dist_p2.html"})
    recs, files, why = m.fetch(seeds[0]["payload"], get)
    assert why == "" and len(files) == 3 and len(get.calls) == 3      # stops after the page without a next link
    _check(recs, "sub_od_dist")
    d = dict(recs)
    dm = d["dept:sub_od_dist:OD-D-344:collector-district-magistrate"]
    assert dm["name"] == "Shri Abdaal M. Akhtar, IAS" and dm["phone"] == "06764-230567" and dm["email"] == "dm-angul@nic.in"
    assert dm["dept"] == "administration" and dm["level"] == "district" and dm["district"] == "Anugola" and dm["district_code"] == "344"
    sp = d["dept:sub_od_dist:OD-D-347:superintendent-of-police-bargarh"]
    assert sp["dept"] == "police" and sp["phone"] == "06646-234480, 9438916490, 9348464352"     # mobiles from the address cell
    # the Sambalpur SP row carries an ADM designation on the page: post as written, dept from the IPS mark
    odd = d["dept:sub_od_dist:OD-D-371:additional-district-magistrate-revenue"]
    assert odd["dept"] == "police" and odd["name"] == "Sri Mukesh Kumar Bhamoo, IPS"
    assert d["dept:sub_od_dist:OD-D-373:superintendent-of-police-rourkela"]["email"] == "sprkl.orpol@nic.in"
    assert m.district_name("JAGATSINGHPUR") == "Jagatsinghapur" and len(m.LGD) == 30


def test_sub_od_dist_no_answer():
    m = mod("sub_od_dist")
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")


def _rti():
    r = mod("sub_od_rti")
    seeds = json.loads((ROOT / "seeds" / "dept_sub_od_rti.json").read_text())
    assert len(seeds) == 30 and all(s["key"].startswith("sub_") and s["payload"]["india_only"] for s in seeds)
    return r, {s["payload"]["district_id"]: s["payload"] for s in seeds}[2]


def _sec(office, s):
    return lambda u, method, data: method == "POST" and f"office_id:{office}/" in u and f"section_id:{s}/" in u


def test_sub_od_rti_offices():
    r, p = _rti()
    assert p["district"] == "Baleshwar" and p["district_code"] == "346" and p["url"] == "https://rtiodisha.gov.in/Districts/2"
    offs = r.wanted(r.offices((DATA / "sub" / "od_rti_district2.html").read_text()))
    got = {(o["level"], r.area_of(o["name"], o["strip"], p["district"]) if o["level"] != "district" else o["name"]) for o in offs}
    assert got == {("district", "Collectorate, Baleswar"), ("district", "Zilla Parishad, Balasore"), ("subdivision", "Nilgiri"),
                   ("subdistrict", "Baliapal"), ("block", "Baliapal"), ("block", "Balasore Sadar")}   # SP and the college are left out
    t = next(o for o in offs if o["level"] == "subdistrict")
    assert (t["dept"], t["dept_id"], t["office_id"], t["dist_id"], t["code"]) == ("revenue", "3", "2089", "2", "03020201")
    assert r.area_of("Tahasil Office, Khaira, Soro, Balasore", r.KINDS[3][4]) == "Khaira"


def test_sub_od_rti_directory():
    r, p = _rti()
    get = fake_get({p["url"]: "sub/od_rti_district2.html", _sec(2089, 10): "sub/od_rti_baliapal_s10.html"})
    recs, files, why = r.fetch(p, get)
    assert why == "" and files[0][0] == "depts/sub_od_rti/district-2.html.gz"
    _check(recs, "sub_od_rti")
    d = dict(recs)
    t = d["dept:sub_od_rti:OD-03020201:tahasildar"]
    assert t["name"] == "Jyotshnarani Nayak" and t["phone"] == "8895800985" and t["area"] == "Baliapal" and t["level"] == "subdistrict"
    assert t["dept"] == "revenue" and t["district"] == "Baleshwar" and t["last_updated"] == "2025-11-19"
    assert t["office_id"] == "OD-RTI-03020201" and t["source"] == "https://rtiodisha.gov.in/pa/T1RILzMvMjA4OS8y"
    assert d["dept:sub_od_rti:OD-03020201:additional-tahasildar"]["name"] == "Satyabrata Panda"
    assert sum(1 for k in d if ":revenue-inspector" in k) == 4
    assert not [v for v in d.values() if re.search(r"assistant|peon", v["post"], re.I)]     # clerks are left out


def test_sub_od_rti_pio_fallback():
    r, p = _rti()
    get = fake_get({p["url"]: "sub/od_rti_district2.html", _sec(2089, 7): "sub/od_rti_baliapal_s7.html"})
    recs, files, why = r.fetch(p, get)
    d = dict(recs)
    assert why == "" and len(d) == 3
    faa = d["dept:sub_od_rti:OD-03020201:tahasildar"]
    assert faa["rti_role"].startswith("1st Appellate Authority") and faa["phone"] == "8895800985"
    assert d["dept:sub_od_rti:OD-03020201:establishment-officer"]["rti_role"].startswith("Assistant Public Information Officer")


def test_sub_od_rti_officer_filter():
    r = mod("sub_od_rti")
    for post in ("Tahasildar", "Additional Tahasildar", "Block Development Officer", "B.D.O.", "Revenue Inspector", "R.I", "Sub-Collector",
                 "Assistant Block Development Officer", "Social Education Organiser (S.E.O)", "Junior Engineer"):
        assert r.is_officer(post), post
    for post in ("Senior Revenue Assistant", "Junior Assistant", "PEON(CONTRACTUAL)", "Driver", "Amin", "Data Entry Operator"):
        assert not r.is_officer(post), post
