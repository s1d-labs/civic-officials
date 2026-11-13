"""Offline tests of the town office staff readers (dforms/town2_*.py, dforms/_town2.py) on FULL saved pages in tests/data/town2/
(live from India, dev-vps-3 Mumbai, 2026-11-13). Counts are exact for these pages."""
import json

import provenance
from esw_common import ROOT, check_records, fake_get, mod


def load_seed(name):
    return json.loads((ROOT / "seeds" / f"dept_{name}.json").read_text(encoding="utf-8"))


def item(module, site):
    return next(i["payload"] for i in mod(module).items() if i["payload"]["site"] == site)


def run(module, site, page):
    provenance.rows_reset()
    p = item(module, site)
    recs, files, why = mod(module).fetch(p, fake_get({p["url"]: f"town2/{page}"}))
    return recs, files, why, provenance.rows(len(recs))


# ---- town2_kamrc (Karnataka, <site>.mrc.gov.in/en/city-staff) ----
def test_kamrc_items_match_seed():
    s = load_seed("town2_kamrc")
    assert mod("town2_kamrc").items() == s and len(s) == 316
    assert all(i["payload"]["india_only"] and i["payload"]["route"] == "direct" for i in s)
    assert not {"kalaburagicity", "mangalurucity", "raichurcity"} & {i["payload"]["site"] for i in s}
    assert sum(1 for i in s if i["payload"].get("lgd_code")) == 315


def test_kamrc_badami():
    recs, files, why, rows = run("town2_kamrc", "badamitown", "ka_badamitown.html")
    assert why == "" and len(files) == 1 and len(recs) == 18
    check_records(recs, "town2_kamrc", "town_body")
    d = dict(recs)
    h = d["dept:town2_kamrc:badamitown:chief-officer:sri-a-h-mujavar"]
    assert h["role"] == "head" and h["phone"] == "9740829302" and h["lgd_code"] and h["section"] == "Municipal Chief Officer Details"
    assert h["src_pos"] == {"table": 1, "row": 3}
    ro = d["dept:town2_kamrc:badamitown:revenue-officer:smt-manjula-kanadagal"]
    assert ro["role"] == "staff" and ro["phone"] == "9480210443"
    # a post written on two lines in the cell is one post
    je = [v for v in d.values() if v["name"] == "Sri. Santosh Hadimani"][0]
    assert je["post"] == "Junior Engineer (Civil) (Deputation Vijayapura City Corporation)"
    assert rows["rows_used"] == 18 and rows["rows_skipped"] == {"vacant post": 6}
    assert rows["rows_not_data"] == {"header": 8, "empty": 2}


def test_kamrc_jamkhandi_continuation_tables():
    recs, files, why, rows = run("town2_kamrc", "jamkhandicity", "ka_jamkhandicity.html")
    assert why == "" and len(recs) == 35
    d = dict(recs)
    assert d["dept:town2_kamrc:jamkhandicity:municipal-commissioner:jagadeesh-s-iti"]["role"] == "head"
    # the two tables after the staff table have no heading row: read with its columns, no section
    vm = [v for v in d.values() if v["post"] == "Senoir Valveman"]
    assert len(vm) == 2 and not any("section" in v for v in vm)
    assert len([v for v in d.values() if v["post"] == "Attender"]) == 6
    assert rows["rows_skipped"] == {"vacant post": 3}


def test_kamrc_kudachi_no_name():
    recs, files, why, rows = run("town2_kamrc", "kudachitown", "ka_kudachitown.html")
    assert why == "" and len(recs) == 12 and rows["rows_skipped"] == {"no name": 1}
    assert {v["post"] for _, v in recs} >= {"Chief Officer", "Revenue Officer", "Junior Engineer", "Accountant Consultant"}


def test_kamrc_no_answer():
    p = item("town2_kamrc", "aminagadtown")
    assert mod("town2_kamrc").fetch(p, fake_get({})) == ([], [], "no answer")


# ---- town2_tgcdma (Telangana, <site>.telangana.gov.in/pages/staff-directory) ----
def test_tgcdma_items_match_seed():
    s = load_seed("town2_tgcdma")
    assert mod("town2_tgcdma").items() == s and len(s) == 108
    assert all(i["payload"]["lgd_code"] and i["payload"]["india_only"] for i in s)
    assert "jangoanmunicipality" not in {i["payload"]["site"] for i in s}


def test_tgcdma_suryapet():
    recs, files, why, rows = run("town2_tgcdma", "suryapetmunicipality", "tg_suryapet.html")
    assert why == "" and len(recs) == 23
    check_records(recs, "town2_tgcdma", "town_body")
    d = dict(recs)
    h = d["dept:town2_tgcdma:suryapetmunicipality:commissioner:ch-hanmatha-reddy"]
    assert h["role"] == "head" and h["lgd_code"] == "251684" and h["phone"] == "9849905912"
    assert d["dept:town2_tgcdma:suryapetmunicipality:town-planning-officer:j-sukanya"]["phone"] == "9849906793"
    assert sum(1 for v in d.values() if v["post"] == "TPBO") == 2
    assert rows == {"rows_seen": 24, "rows_used": 23, "rows_skipped": {}, "rows_not_data": {"header": 1}, "rows_given": 24}


# ---- sho_ka (Karnataka district police sites, <site>.karnataka.gov.in) ----
def sho_run(site, page):
    provenance.rows_reset()
    p = item("sho_ka", site)
    base = f"https://{site}.karnataka.gov.in"
    recs, files, why = mod("sho_ka").fetch(p, fake_get({base + p["pages"][0]: f"sho/{page}"}))
    return recs, files, why, provenance.rows(len(recs))


def levels(recs):
    out = {}
    for _, d in recs:
        out[d["level"]] = out.get(d["level"], 0) + 1
    return out


def test_sho_ka_items_match_seed():
    s = load_seed("sho_ka")
    assert mod("sho_ka").items() == s and len(s) == 35
    assert all(i["payload"]["india_only"] and i["payload"]["find"] for i in s)


def test_sho_ka_shivamogga_contact_table():
    recs, files, why, rows = sho_run("shivamoggapolice", "ka_shivamogga_contact.html")
    assert why == "" and len(recs) == 72 and len(files) == 1      # the home page did not answer: the known page only
    check_records(recs, "sho_ka", "police")
    assert levels(recs) == {"police_station": 54, "circle": 7, "subdivision": 6, "district": 5}
    d = dict(recs)
    pi = d["dept:sho_ka:shivamoggapolice-pi-doddapete-ps-9480803330"]
    assert pi["area"] == "DODDAPETE" and pi["sho_rank"] == "PI" and pi["telephone"] == "08182-261406"
    assert pi["email"] == "cpidoddapeteshi@ksp.gov.in" and pi["post"] == "Police Inspector"
    assert d["dept:sho_ka:shivamoggapolice-psi-doddapete-ps-9480803372"]["sho_rank"] == "PSI"
    assert rows["rows_used"] == 72 and rows["rows_skipped"] == {}
    assert rows["rows_filtered"] == {"site furniture table (screen readers, file viewers)": 20}


def test_sho_ka_belagavi_subdivision_blocks():
    recs, files, why, rows = sho_run("belagavidistrictpolice", "ka_belagavi_officers.html")
    assert why == "" and len(recs) == 51 and levels(recs)["police_station"] == 34
    d = dict(recs)
    k = d["dept:sho_ka:belagavidistrictpolice-psi-katkol-ps-9480804081"]
    assert k["area"] == "KATKOL" and k["subdivision"] == "RAMADURGA SUB-DIVISION" and k["district"] == "Belagavi"
    assert d["dept:sho_ka:belagavidistrictpolice-dysp-gokak-9480804023"]["level"] == "subdivision"


def test_sho_ka_bidar_station_rows_without_rank():
    recs, files, why, rows = sho_run("bidarpolice", "ka_bidar_officers.html")
    assert why == "" and len(recs) == 54 and levels(recs)["police_station"] == 32
    nt = dict(recs)["dept:sho_ka:bidarpolice-post-new-town-ps-9480803446"]
    assert nt["post"] == "Police Station" and nt["area"] == "NEW TOWN" and "sho_rank" not in nt


def test_sho_ka_haveri_names():
    recs, files, why, rows = sho_run("haveripolice", "ka_haveri_officers.html")
    assert why == "" and len(recs) == 70 and levels(recs)["police_station"] == 50
    d = dict(recs)
    h = d["dept:sho_ka:haveripolice-pi-haveri-town-ps-motilal-pawar"]
    assert h["name"] == "Motilal Pawar" and h["area"] == "Haveri Town" and h["sho_rank"] == "PI" and "phone" not in h
    g = [v for v in d.values() if v.get("name") == "Parusharam Lamani"][0]
    assert g["level"] == "police_station" and g["area"] == "Guttal" and g["duty"] == "Senior PSI (L&O & Traffic)"
    assert d["dept:sho_ka:haveripolice-pi-dsb-s-k-pawar"]["level"] == "district"


def test_sho_ka_links_and_no_answer():
    m = mod("sho_ka")
    html = (ROOT / "tests" / "data" / "sho" / "ka_haveri_officers.html").read_text(encoding="utf-8")
    assert m.links(html, "https://haveripolice.karnataka.gov.in")[:2] == [
        "https://haveripolice.karnataka.gov.in/392/haveri-district-police-officer-name/en",
        "https://haveripolice.karnataka.gov.in/3/police-stations/en"]
    assert m.fetch(item("sho_ka", "kodagupolice"), fake_get({})) == ([], [], "no answer")
