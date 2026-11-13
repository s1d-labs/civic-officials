"""Police readers South and West, second pass (dforms/police2s_*.py) on saved samples (tests/data/police2s_*): no network."""
from test_dept_police import FakeGet, check_common, check_seed

from dforms import police2s_gj, police2s_kl, police2s_mh, police2s_mh_misc, police2s_mh_old, police2s_mp, police2s_tg, police_gj


# --- Kerala: district unit sites (cards, blocks, tables) ---------------------------------------------------------------------
def test_kl_cards_paged():
    u = "https://kochicity.keralapolice.gov.in/shos"
    get = FakeGet({u + "?page=2": "police2s_kl_kochi_shos_p2.html", u: "police2s_kl_kochi_shos.html"})
    recs, files, why = police2s_kl.fetch({"reader": "police2s_kl", "url": u, "state": "KL", "unit": "kochicity", "district": "Ernakulam"}, get)
    check_common(recs, "police2s_kl", "KL")
    assert [c[1] for c in get.calls] == [u, u + "?page=2"] and not why and len(files) == 2
    d = dict(recs)
    fk = d["dept:police2s_kl:kochicity:fort-kochi-ps:ratheesh-kc"]
    assert fk["level"] == "police_station" and fk["name"] == "Ratheesh KC" and fk["post"] == "Inspector of Police"
    assert d["dept:police2s_kl:kochicity:maradu-ps:abdul-manaf-a"]["area"] == "Maradu PS"


def test_kl_cards_malayalam():
    u = "https://palakkad.keralapolice.gov.in/who-is-who"
    recs, _, _ = police2s_kl.fetch({"reader": "police2s_kl", "url": u, "state": "KL", "unit": "palakkad"}, FakeGet({u: "police2s_kl_palakkad.html"}))
    check_common(recs, "police2s_kl", "KL")
    by = {d["post"]: d for _, d in recs}
    sp = by["ജില്ലാ പോലീസ് മേധാവി"]
    assert sp["level"] == "district" and sp["phone"] == "9497996977" and sp["email"] == "spplkd.pol@kerala.gov.in"
    assert sp["name_regional"] == sp["name"]
    assert by["എ.എസ്.പി. പാലക്കാട്"]["level"] == "subdivision"
    assert by["ഡി.വൈ.എസ്.പി ജില്ലാ എസ്.ബി"]["level"] == "district" and by["ഡി.വൈ.എസ്.പി ജില്ലാ എസ്.ബി"]["office_type"] == "unit"


def test_kl_blocks_and_table():
    u = "https://kollamcity.keralapolice.gov.in/station-kollam-city"
    recs, _, _ = police2s_kl.fetch({"reader": "police2s_kl", "url": u, "kind": "blocks", "state": "KL"}, FakeGet({u: "police2s_kl_kollam_station.html"}))
    check_common(recs, "police2s_kl", "KL")
    d = dict(recs)["dept:police2s_kl:kollamcity:kollam-east-ps:pushpakumar-g"]
    assert d["phone"] == "9497987030, 0474-2742072" and d["email"] == "shoklmeklm.pol@kerala.gov.in" and d["post"] == "ISHO, Kollam East PS"
    u = "https://kasaragod.keralapolice.gov.in/law-and-order"
    recs, _, _ = police2s_kl.fetch({"reader": "police2s_kl", "url": u, "kind": "table", "state": "KL"}, FakeGet({u: "police2s_kl_kasaragod.html"}))
    check_common(recs, "police2s_kl", "KL")
    assert len(recs) == 3 and all(d["level"] == "subdivision" and d["phone"] for _, d in recs)
    assert {d["area"] for _, d in recs} >= {"കാഞ്ഞങ്ങാട്"}
    assert police2s_kl.fetch({"url": u, "state": "KL"}, FakeGet({}))[2] == "no answer"
    check_seed("police2s_kl")


# --- Gujarat: more units of the police_gj CMS -----------------------------------------------------------------------------
def test_gj_wrapper():
    o = police_gj.ORG.format(u="cpahmedabad")
    get = FakeGet({o: "police_gj_ahd_org.html", o + "&designation_id=1852": "police_gj_ahd_1852.html"})
    recs, files, _ = police2s_gj.fetch({"reader": "police2s_gj", "unit": "cpahmedabad", "url": o, "district": "Ahmedabad"}, get)
    check_common(recs, "police2s_gj", "GJ")
    assert all(f[0].startswith("depts/police/police2s_gj/") for f in files)
    base = dict(police_gj.fetch({"unit": "cpahmedabad", "url": o, "district": "Ahmedabad"}, get)[0])
    assert {r.replace("police2s_gj", "police_gj") for r, _ in recs} == set(base)
    check_seed("police2s_gj")


# --- Maharashtra: state Next.js template ------------------------------------------------------------------------------------
def test_mh_stations_en_mr():
    u = "https://dhulepolice.gov.in/en/about/police-station-incharge"
    get = FakeGet({u: "police2s_mh_dhule_en.html", u.replace("/en/", "/mr/"): "police2s_mh_dhule_mr.html"})
    recs, files, why = police2s_mh.fetch({"reader": "police2s_mh", "url": u, "state": "MH", "district": "Dhule"}, get)
    check_common(recs, "police2s_mh", "MH")
    assert len(recs) == 3 and len(files) == 2 and not why
    d = dict(recs)["dept:police2s_mh:dhulepolice:118862ef-2e0d-42d6-8062-9c3c8886fac2"]
    assert d["name"] == "Shri. Sureshkumar Ghusar" and d["name_regional"] == "श्री. सुरेशकुमार घुसर"
    assert d["area"] == "Cyber" and d["area_regional"] == "सायबर" and d["phone"] == "9423821930"
    assert d["email"] == "cyberps-dhule@mahapolice.gov.in" and d["post"] == "Police Inspector"


def test_mh_kolhapur_and_senior():
    u = "https://kolhapurpolice.gov.in/en/about/police-station-incharge"
    recs, _, _ = police2s_mh.fetch({"reader": "police2s_mh", "url": u, "state": "MH", "district": "Kolhapur", "marathi": False},
                                   FakeGet({u: "police2s_mh_kolhapur.html"}))
    check_common(recs, "police2s_mh", "MH")
    d = {x["area"]: x for _, x in recs}["Chandgad"]
    assert d["phone"] == "9545140151, 9684005940" and d["subdivision"] == "Gadhinglaj Division"
    u = "https://solapurpolice.gov.in/en/about/senior-officers"
    recs, _, _ = police2s_mh.fetch({"reader": "police2s_mh", "url": u, "state": "MH", "district": "Solapur"},
                                   FakeGet({u: "police2s_mh_solapur_senior.html"}))
    by = {x["post"]: x for _, x in recs}
    assert by["Superintendent of Police"]["level"] == "district" and by["Superintendent of Police"]["email"] == "sp.solapur.r@mahapolice.gov.in"
    k = by["Sub-Division Police Officer, Karmala"]
    assert k["level"] == "subdivision" and k["area"] == "Karmala" and k["phone"] == "02182221102"
    assert police2s_mh.undot("sdpodotbarshidotdivatmahapolicedotgovdotin") == "sdpo.barshi.div@mahapolice.gov.in"
    assert police2s_mh.fetch({"url": u}, FakeGet({u: b"<html><title>Website Under Maintenance</title></html>"}))[2] == "site under maintenance"
    check_seed("police2s_mh")


# --- Maharashtra: sites on their own CMS -----------------------------------------------------------------------------------
def test_mh_misc():
    def run(url, sample, **p):
        recs, _, why = police2s_mh_misc.fetch({"reader": "police2s_mh_misc", "url": url, "state": "MH", **p}, FakeGet({url: sample}))
        check_common(recs, "police2s_mh_misc", "MH")
        return {d["area"]: d for _, d in recs}
    a = run("https://amravaticitypolice.gov.in/designations_spi.php", "police2s_mh_amravati_spi.html", kind="labels", district="Amravati")
    assert a["Gadage Nagar Police Station"]["name"] == "Gorakhnath Jadhav"
    assert a["Gadage Nagar Police Station"]["phone"] == "9823191901, 0721-2679330"
    assert a["Walgaon Police Station"]["name"] == "Rita Uike"
    y = run("https://yavatmalpolice.gov.in/officers/police-station-incharge", "police2s_mh_yavatmal.html", kind="ranked", district="Yavatmal")
    assert y["Awdhutwadi Police Station"]["name"] == "Ajit Atmaram Kadam" and y["Awdhutwadi Police Station"]["phone"] == "9112985922"
    assert y["Lohara Police Station"]["post"] == "API" and y["Lohara Police Station"]["subdivision"] == "Yavatmal"
    s = run("https://www.sanglipolice.gov.in/ashta-police-station/", "police2s_mh_sangli_ashta.html", kind="labels", district="Sangli",
            station="Ashta Police Station")
    assert s["Ashta Police Station"]["name"] == "Siddheshwar Janabai Dagdu Jangam" and s["Ashta Police Station"]["phone"] == "9823223379, 02342-243233"
    n = run("https://nagpurgraminpolice.gov.in/contact-list/", "police2s_mh_nagpurgramin.html", kind="labels", district="Nagpur")
    assert n["बुटीबोरी पोलीस स्टेशन"]["name"] == "सचिन लुले" and n["बुटीबोरी पोलीस स्टेशन"]["phone"] == "9823108050"
    check_seed("police2s_mh_misc")


# --- Madhya Pradesh: officers-list tables -----------------------------------------------------------------------------------
def test_mp_tables():
    def run(host, sample):
        u = f"https://{host}.mppolice.gov.in/officers-list/"
        recs, files, why = police2s_mp.fetch({"reader": "police2s_mp", "url": u, "state": "MP", "district": host.capitalize()}, FakeGet({u: sample}))
        check_common(recs, "police2s_mp", "MP")
        return recs
    a = dict(run("alirajpur", "police2s_mp_alirajpur.html"))
    sp = a["dept:police2s_mp:alirajpur:पुलिस-अधीक्षक"]
    assert sp["level"] == "district" and sp["phone"] == "07394-233350, 7049100422" and sp["name"].startswith("श्री समर वर्मा")
    k = a["dept:police2s_mp:alirajpur:थाना-प्रभारी-कोतवाली"]
    assert k["level"] == "police_station" and k["area"] == "कोतवाली" and k["name"].startswith("श्रीमती सोनू सितोले")
    t = {d["post"]: d for _, d in run("tikamgarh", "police2s_mp_tikamgarh.html")}
    assert t["अनु 0 अधी 0 ( पुलिस ) जतारा"]["level"] == "subdivision" and t["अनु 0 अधी 0 ( पुलिस ) जतारा"]["area"] == "जतारा"
    assert t["निरीक्षक थाना प्रभारी कोतवाली"]["level"] == "police_station"
    b = {d["post"]: d for _, d in run("bhopal", "police2s_mp_bhopal.html")}
    assert b["COMMISSIONER OF POLICE - BHOPAL"]["name"] == "SHRI SANJAY KUMAR"
    assert any(d["level"] == "police_station" and d.get("name") for d in b.values())
    u = "https://sagar.mppolice.gov.in/officers-list/"
    assert police2s_mp.fetch({"url": u}, FakeGet({u: b"<div>[table \xe2\x80\x9c1\xe2\x80\x9d not found /]</div>"}))[2].startswith("the page shows no table")
    check_seed("police2s_mp")


# --- Telangana: more S3WaaS district pages ---------------------------------------------------------------------------------
def test_tg_s3waas():
    u = "https://kamareddy.telangana.gov.in/public-utility-category/police/"
    recs, _, _ = police2s_tg.fetch({"reader": "police2s_tg", "url": u, "district": "Kamareddy"}, FakeGet({u: "police2s_tg_kamareddy.html"}))
    check_common(recs, "police2s_tg", "TG")
    assert any(d["level"] == "circle" and d["phone"] == "8712686163" for _, d in recs)
    check_seed("police2s_tg")


# --- Maharashtra: sites on their older layout (police2s_mh -> police2s_mh_old) -------------------------------------------------
OLD = {
    "https://nashikruralpolice.gov.in/police-station-incharge": "police2s_mh_old_nashikr_psi.html",
    "https://nashikruralpolice.gov.in/_next/static/chunks/pages/police-station-incharge-f972e540c07c7c56.js": "police2s_mh_old_nashikr_psi.js",
    "https://nrbkapi.neuronexdevelopers.com/api/officers-admin": "police2s_mh_old_nashikr_psi.json",
    "https://nashikruralpolice.gov.in/senior-officers": "police2s_mh_old_nashikr_senior.html",
    "https://nashikruralpolice.gov.in/_next/static/chunks/pages/senior-officers-ef23064bac25a44e.js": "police2s_mh_old_nashikr_senior.js",
    "https://nrbkapi.neuronexdevelopers.com/api/get-senior-officer": "police2s_mh_old_nashikr_senior.json",
    "https://solapurcitypolice.gov.in/senior_officers": "police2s_mh_old_solapur_senior.html",
    "https://solapurcitypolice.gov.in/police-station/jail-road-police-station": "police2s_mh_old_solapur_ps.html",
    "https://jalnapolice.gov.in/seniorofficers.html": "police2s_mh_old_jalna_senior.html",
    "https://jalnapolice.gov.in/psambad.html": "police2s_mh_old_jalna_ambad.html",
    "https://jalnapolice.gov.in/": "police2s_mh_old_jalna_home.html",
    "https://hingolipolice.gov.in/Officers": "police2s_mh_old_hingoli_officers.html",
    "https://hingolipolice.gov.in/PoliceStation?ps=8": "police2s_mh_old_hingoli_ps8.html",
    "https://hingolipolice.gov.in/PoliceStation": "police2s_mh_old_hingoli_ps.html",
    "https://nagpurrailwaypolice.gov.in/en/officerslist": "police2s_mh_old_nagpurrly.html",
    "https://gadchirolipolice.gov.in/en/about/police-station-incharge": "police2s_mh_old_gadchiroli_psi_empty.html",
}


def run_old(key, host, section):
    get = FakeGet(OLD)
    recs, files, why = police2s_mh.fetch({"reader": "police2s_mh", "key": key, "url": f"https://{host}/en/about/{section}", "state": "MH",
                                          "district": "D"}, get)
    return recs, files, why, get


def test_mh_old_nextapi():
    recs, files, why, get = run_old("nashikruralpolice", "nashikruralpolice.gov.in", "police-station-incharge")
    check_common(recs, "police2s_mh", "MH")
    assert not why and len(recs) == 41 and len(files) == 2
    assert [c[1] for c in get.calls][1:] == list(OLD)[:3]          # /en/about/ (404), old page, its script, the API it names
    d = dict(recs)["dept:police2s_mh:nashikruralpolice:67b487056de1c479f0e56ce4"]
    assert d["area"] == "Lasalgaon Police Station" and d["area_regional"] == "लासलगाव" and d["name"] == "Shri. Sagar Kote"
    assert d["phone"] == "9518527855, 02550266055" and d["email"] == "ps.lasalgaon.nr@mahapolice.gov.in" and d["level"] == "police_station"
    assert d["src_url"] == "https://nrbkapi.neuronexdevelopers.com/api/officers-admin" and d["src_pos"]["index"] == 1
    recs, _, why, _ = run_old("nashikruralpolice", "nashikruralpolice.gov.in", "senior-officers")
    check_common(recs, "police2s_mh", "MH")
    sp = dict(recs)["dept:police2s_mh:nashikruralpolice:67b49d266de1c479f0e56f03"]
    assert len(recs) == 13 and sp["post"] == "Superintendent of Police, Nashik Rural" and sp["level"] == "district"
    assert sp["phone"] == "0253-2200495" and sp["post_regional"] == "पोलीस अधीक्षक, नाशिक ग्रामीण"
    assert police2s_mh_old.api_urls('fetch("".concat("https://x.example","/api/get-visitors")),fetch("".concat("https://x.example","/api/a"))') \
        == ["https://x.example/api/a"]


def test_mh_old_own_sites():
    recs, _, why, _ = run_old("solapurcitypolice", "solapurcitypolice.gov.in", "senior-officers")
    check_common(recs, "police2s_mh", "MH")
    d = {x["post"]: x for _, x in recs}
    assert len(recs) == 11 and d["Commissioner Of Police"]["name"] == "M. Raj Kumar" and d["Commissioner Of Police"]["name_regional"] == "एम. राजकुमार"
    assert d["Deputy Commissioner of Police (HQ)"]["email"] == "cp.solapur.dcp.hq@mahapolice.gov.in"
    recs, _, why, get = run_old("solapurcitypolice", "solapurcitypolice.gov.in", "police-station-incharge")
    assert len([c for c in get.calls if "/police-station/" in c[1]]) == 7 and len(recs) == 1      # only one station page saved
    ps = recs[0][1]
    assert ps["area"] == "Jail Road Police Station" and ps["name"] == "Udaysingh Shyamrao Patil" and ps["phone"] == "02172744631, 9923357799"
    assert ps["subdivision"] == "Assistant Commissioner of Police (Div-1) Solapur City" and ps["level"] == "police_station"
    recs, _, _, _ = run_old("jalnapolice", "jalnapolice.gov.in", "senior-officers")
    assert len(recs) == 7 and {x["post"] for _, x in recs} >= {"Superintendent of Police", "DYSP Partur"}
    recs, _, _, get = run_old("jalnapolice", "jalnapolice.gov.in", "police-station-incharge")
    assert len([c for c in get.calls if c[1].startswith("https://jalnapolice.gov.in/ps")]) == 19
    a = recs[0][1]
    assert a["name"] == "Shri. Santosh Ghodke" and a["phone"] == "9657478003, 02483-220029" and a["email"] == "psambad.jalna@mahapolice.gov.in"
    recs, _, _, _ = run_old("hingolipolice", "hingolipolice.gov.in", "senior-officers")
    assert len(recs) == 6 and recs[0][1]["name"] == "डॉ. श्रेणिक लोढा" and recs[0][1]["post"] == "पोलीस अधीक्षक"
    recs, _, _, get = run_old("hingolipolice", "hingolipolice.gov.in", "police-station-incharge")
    assert len([c for c in get.calls if "?ps=" in c[1]]) == 13
    h = recs[0][1]
    assert h["area"] == "हिंगोली शहर पोलीस ठाणे" and h["phone"] == "8208328532, 8669900678" and h["email"] == "ps.hingolicity.hnl@mahapolice.gov.in"
    recs, _, _, _ = run_old("nagpurrailwaypolice", "www.nagpurrailwaypolice.gov.in", "senior-officers")
    check_common(recs, "police2s_mh", "MH")
    assert len(recs) == 4 and dict(recs)["dept:police2s_mh:nagpurrailwaypolice:sdpo-nagpur"]["email"] == "sdporly@gmail.com"
    assert run_old("nagpurrailwaypolice", "www.nagpurrailwaypolice.gov.in", "police-station-incharge")[2].startswith("no station incharge")
    assert run_old("gadchirolipolice", "gadchirolipolice.gov.in", "police-station-incharge")[2] == "the site's page says 'No records yet'"
