"""Offline tests of the state health officer readers for GJ, OD, JH (dforms/health_gj_nhm, health_od_cdmo, health_jh_jrhms)
on pages saved 2026-11-12 in tests/data/west/."""
import hashlib
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod


def _seed(name):
    return json.loads((ROOT / "seeds" / f"dept_{name}.json").read_text())


def test_jh_jrhms_district_team():
    m = mod("health_jh_jrhms")
    p = _seed("health_jh_jrhms")[0]["payload"]
    page = DATA / "west" / "jh_jrhms_districtteam.html"
    recs, files, why = m.fetch(p, fake_get({m.URL: "west/jh_jrhms_districtteam.html"}))
    assert why == "" and len(recs) == 48 and len(files) == 1
    check_records(recs, "health_jh_jrhms", "health")
    cs = [d for _, d in recs if d["post"] == "Civil Surgeon"]
    assert len(cs) == 24 and len({d["district"] for d in cs}) == 24
    d = dict(recs)["dept:health_jh_jrhms:BOK:civil-surgeon"]
    assert d["name"] == "Dr. Abhay Bhusan Prasad" and d["phone"] == "9934587787" and d["email"] == "cs.bokaro@gmail.com"
    assert d["district"] == "Bokaro" and d["src_url"] == m.URL
    html = page.read_text(encoding="utf-8")
    from dforms import _esw
    t = _esw.soup(html).find_all("table")[d["src_pos"]["table"] - 1]
    tr = [x for x in t.find_all("tr") if x.find_parent("table") is t][d["src_pos"]["row"] - 1]
    assert "Abhay Bhusan Prasad" in tr.get_text()


def test_od_cdmo_pages():
    m = mod("health_od_cdmo")
    p = _seed("health_od_cdmo")[0]["payload"]
    get = fake_get({m.URL: "west/od_cdmo_p0.html", m.URL + "?page=1": "west/od_cdmo_p1.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 33 and len(files) == 2 and len(get.calls) == 2
    check_records(recs, "health_od_cdmo", "health")
    by = dict(recs)
    d = by["dept:health_od_cdmo:7"]
    assert d["district"] == "Kataka" and d["name"] == "Dr. Manorama Dei" and d["phone"].startswith("9439990009, 9937020964")
    assert by["dept:health_od_cdmo:19"]["level"] == "state" and "district" not in by["dept:health_od_cdmo:19"]
    d = by["dept:health_od_cdmo:22"]
    assert d["district"] == "Mayurbhanj" and d["src_pos"]["view_page"] == 1
    assert d["src_sha256"] == hashlib.sha256((DATA / "west" / "od_cdmo_p1.html").read_bytes()).hexdigest()
    assert sum(1 for _, d in recs if d.get("district")) == 30


def test_od_cdmo_odia_digits():
    m = mod("health_od_cdmo")
    html = ('<table><tr><th>Sr. No.</th><th>District</th><th>Name of the CDMO/ CMO</th><th>Mobile</th><th>Office</th>'
            '<th>Fax</th></tr><tr><td>9</td><td>Dhenkanal</td><td>Dr. X</td><td>9437000000</td><td>୦୬୭୬୨-୨୨୬୪୨୩</td><td></td></tr></table>')
    (_, d), = m.parse(html)
    assert d["phone"] == "9437000000, 06762-226423"


def test_gj_nhm_dpmu():
    m = mod("health_gj_nhm")
    p = _seed("health_gj_nhm")[0]["payload"]
    recs, files, why = m.fetch(p, fake_get({m.URL: "west/gj_nhm_dpmu.html"}))
    assert why == "" and len(recs) == 192
    check_records(recs, "health_gj_nhm", "health")
    assert len({d["district"] for _, d in recs}) == 32
    d = dict(recs)["dept:health_gj_nhm:ahmedabad:1"]
    assert d["post"] == "DPC" and d["name"] == "Dr.Pinal Soni" and d["phone"] == "9099064835"
    assert d["email"] == "dpc.health.ahmedabad7@gmail.com" and d["src_pos"] == {"table": 1, "row": 2}
    assert dict(recs)["dept:health_gj_nhm:kutch:1"]["district"] == "Kachchh"
