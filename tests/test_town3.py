"""Offline tests of the town office staff readers for the towns' own websites (dforms/town3_*.py, dforms/_town3.py) on FULL saved
pages in tests/data/town3/ (live from India, dev-vps-3 Mumbai, 2026-11-13). Counts are exact for these pages."""
import json

import provenance
from esw_common import ROOT, check_records, fake_get, mod

READERS = ("town3_od_aspx", "town3_od_wp", "town3_own")


def seeds(template):
    out = []
    for f in sorted((ROOT / "seeds").glob(f"dept_town3_*_{template}.json")):
        out += json.loads(f.read_text(encoding="utf-8"))
    return out


def item(module, site):
    return next(i["payload"] for i in mod(module).items() if i["payload"]["site"] == site)


def run(module, site, pages):
    provenance.rows_reset()
    p = item(module, site)
    get = fake_get({u: f"town3/{f}" for u, f in zip(p["pages"], pages)})
    recs, files, why = mod(module).fetch(p, get)
    return recs, files, why, provenance.rows(len(recs)), get


def test_items_match_seeds():
    n = {}
    for m, t in zip(READERS, ("aspx", "wp", "own")):
        it = mod(m).items()
        assert sorted(it, key=lambda i: i["key"]) == sorted(seeds(t), key=lambda i: i["key"])
        n[m] = len(it)
        for i in it:
            p = i["payload"]
            assert p["india_only"] and p["route"] == "direct" and p["lgd_code"] and p["district"] and 1 <= len(p["pages"]) <= 2
            assert p["url"].startswith("http") and i["key"] == f"{m}-{p['site']}"
    assert n == {"town3_od_aspx": 10, "town3_od_wp": 9, "town3_own": 22}
    states = {}
    for m in READERS:
        for i in mod(m).items():
            states[i["payload"]["state"]] = states.get(i["payload"]["state"], 0) + 1
    assert states == {"OD": 25, "UP": 7, "HR": 3, "HP": 3, "PB": 1, "MP": 1, "GJ": 1}
    # sites left out on purpose (copied staff of another town, past chief officers, a town of another state)
    sites = {i["payload"]["site"] for m in READERS for i in mod(m).items()}
    assert not sites & {"npislamnagar.in", "npdaranagar.in", "nprenukoot.in", "petladnagarpalika.org", "npaurangabad.in"}


# ---- town3_od_aspx (Odisha ASP.NET vendor) ----
def test_od_aspx_balangir():
    recs, files, why, rows, get = run("town3_od_aspx", "balangirmunicipality.in", ["od_balangir_admin.html"])
    assert why == "" and len(files) == 1 and len(recs) == 130 and len(get.calls) == 1
    check_records(recs, "town3_od_aspx", "town_body")
    d = dict(recs)
    h = d["dept:town3_od_aspx:balangirmunicipality.in:executive-officer:sri-biswambar-mishra"]
    assert h["role"] == "head" and h["phone"] == "9437788409" and h["lgd_code"] == "250555" and h["state"] == "OD"
    assert h["area"] == "Balangir Municipality" and h["district"] == "Balangir" and h["src_pos"] == {"table": 2, "row": 2}
    # "C.O." here is a Community Organiser, not a Chief Officer
    assert [v["post"] for v in d.values() if v["role"] == "head"] == ["EXECUTIVE OFFICER"]
    assert d["dept:town3_od_aspx:balangirmunicipality.in:j-e:rojalisha-rout"]["role"] == "staff"
    assert rows["rows_used"] == 130 and rows["rows_skipped"] == {"before the heading row": 1, "same row twice": 8}


def test_od_aspx_udala_and_discovery():
    recs, files, why, rows, get = run("town3_od_aspx", "udalanac.in", ["od_udala_admin.html"])
    assert why == "" and len(recs) == 20
    assert dict(recs)["dept:town3_od_aspx:udalanac.in:executive-officer:sri-priyaranjan-jena-ors"]["phone"] == "9439396411"
    assert rows["rows_skipped"] == {"before the heading row": 17, "no post": 1}
    # the known page does not answer: the home page, then its staff links (at most 3 requests in all)
    p = item("town3_od_aspx", "udalanac.in")
    get = fake_get({p["url"]: "town3/od_udala_home.html", "http://www.udalanac.in/Administration.aspx": "town3/od_udala_admin.html"})
    recs, files, why = mod("town3_od_aspx").fetch(p, get)
    assert why == "" and len(recs) == 20 and len(files) == 2
    assert [c[1] for c in get.calls] == [p["pages"][0], p["url"], "http://www.udalanac.in/Administration.aspx"]


def test_od_aspx_no_answer():
    p = item("town3_od_aspx", "koraputmunicipality.in")
    get = fake_get({})
    assert mod("town3_od_aspx").fetch(p, get) == ([], [], "no answer") and len(get.calls) == 2


# ---- town3_od_wp (Odisha WordPress theme) ----
def test_od_wp_dhenkanal_two_pages_with_section():
    recs, files, why, rows, get = run("town3_od_wp", "dhenkanalmunicipality.com", ["od_dhenkanal_171.html", "od_dhenkanal_173.html"])
    assert why == "" and len(files) == 2 and len(recs) == 22
    check_records(recs, "town3_od_wp", "town_body")
    d = dict(recs)
    me = d["dept:town3_od_wp:dhenkanalmunicipality.com:municipal-engineer:rasmita-mishra"]
    assert me["section"] == "Works" and me["phone"] == "7008852004" and me["role"] == "staff"
    assert rows["rows_not_data"] == {"empty": 5, "header": 2} and rows["rows_skipped"] == {}


def test_od_wp_bhuban():
    recs, files, why, rows, get = run("town3_od_wp", "bhubannac.in", ["od_bhuban_staff.html"])
    assert why == "" and len(recs) == 22
    d = dict(recs)
    assert d["dept:town3_od_wp:bhubannac.in:executive-officer:pradat-kumar-sahoo"]["role"] == "head"
    assert "phone" not in d["dept:town3_od_wp:bhubannac.in:driver:suresh-kumar-sahoo"]        # the Mobile column is empty


# ---- town3_own (single-vendor own sites) ----
def test_own_kundarki_hindi():
    recs, files, why, rows, get = run("town3_own", "npkundarki.in", ["up_kundarki_staff.html"])
    assert why == "" and len(recs) == 15
    check_records(recs, "town3_own", "town_body")
    d = dict(recs)
    eo = d["dept:town3_own:npkundarki.in:अधिशासी-अधिकारी:श्री-त्रिवेन्द्र-कुमार"]
    assert eo["role"] == "head" and eo["phone"] == "9458823916" and eo["lgd_code"] == "248930" and eo["state"] == "UP"
    # rows with dots for the post ("....") have no post; rows of dots only have no name
    assert rows["rows_skipped"] == {"no post": 5, "no name": 2}


def test_own_keshod_gujarati():
    recs, files, why, rows, get = run("town3_own", "keshodnagarpalika.co.in", ["gj_keshod_staff.html"])
    assert why == "" and len(recs) == 106
    d = dict(recs)
    co = d["dept:town3_own:keshodnagarpalika.co.in:ચીફ-ઓફિસર:શ્રી-ચારૂબેન-મોરી"]
    assert co["role"] == "head" and co["section"] == "વહીવટી" and co["area"] == "Keshod Municipality"
    assert sum(1 for v in d.values() if v["role"] == "head") == 1
    assert rows["rows_used"] == 106 and rows["rows_skipped"] == {}


def test_own_palwal_avatar_letter():
    recs, files, why, rows, get = run("town3_own", "mcpalwal.in", ["hr_palwal_employees.html"])
    assert why == "" and len(recs) == 42
    d = dict(recs)
    assert d["dept:town3_own:mcpalwal.in:municipal-engineer:bijender-rathi"]["name"] == "Bijender Rathi"
    assert d["dept:town3_own:mcpalwal.in:municipal-engineer:bijender-rathi"]["section"] == "Engineering"
    assert rows["rows_skipped"] == {"same row twice": 1}


def test_own_katangi_sections():
    recs, files, why, rows, get = run("town3_own", "nagarparishadkatangi.in", ["mp_katangi_staff.html"])
    assert why == "" and len(recs) == 23
    d = dict(recs)
    sub = d["dept:town3_own:nagarparishadkatangi.in:उपयंत्री:श्री-रोजश-चौकसे"]
    assert sub["role"] == "staff" and sub["section"] == "लोक निर्माण शाखा"              # उपयंत्री = sub-engineer, not a deputy
    assert d["dept:town3_own:nagarparishadkatangi.in:कम्प्युटर-शाखा:श्री-प्रिशेन्द्र-चौहान"]["post"] == "कम्प्युटर शाखा"   # post "-"


def test_own_nizamabad_two_pages():
    recs, files, why, rows, get = run("town3_own", "npnizamabad.in", ["up_nizamabad_officer.html", "up_nizamabad_employee.html"])
    assert why == "" and len(files) == 2 and len(recs) == 9
    d = dict(recs)
    assert d["dept:town3_own:npnizamabad.in:अध्यक्ष:श्री-अलाउद्दीन"]["role"] == "chair"
    assert d["dept:town3_own:npnizamabad.in:अधिशासी-अधिकारी:श्री-विक्रम-कुमार"]["role"] == "head"


def test_links_order():
    m = mod("_town3")
    html = (ROOT / "tests" / "data" / "town3" / "od_udala_home.html").read_text(encoding="utf-8")
    links = m.links(html, "http://www.udalanac.in/")
    assert links[0] == "http://www.udalanac.in/Administration.aspx" and links[-1] == "http://www.udalanac.in/Contact.aspx"
    assert not any("Holding" in u or "EO_list" in u for u in links)
