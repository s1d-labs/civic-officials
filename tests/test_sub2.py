"""Offline tests of the state-wide sub-district officer readers (dforms/sub2_*.py) on small saved answers in tests/data/sub2/.
South: AP / TG / KA district portal "Administrative Setup" pages. West: Gujarat civil lists, Maharashtra ZP directories,
Rajasthan BDO list. Central: Chhattisgarh revenue officer search, MP CEO ERO list. East: Uttarakhand RD directory,
UP Panchayati Raj officer directory."""
import json
import re  # noqa: F401

from esw_common import *  # noqa: F401,F403


# ---- south ----
MENU_AP = {"https://prakasam.ap.gov.in/": "sub2/ap_prakasam_menu.html",
           "https://prakasam.ap.gov.in/tehsil/": "sub2/ap_prakasam_tehsil.html",
           "https://prakasam.ap.gov.in/mpdos": "sub2/ap_prakasam_mpdos.html"}


def _seeds_south(module, n, state, path=""):
    seeds = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    assert len(seeds) == n and len({s["key"] for s in seeds}) == n
    for s in seeds:
        p = s["payload"]
        assert s["key"].startswith("sub2_") and p["reader"] == module and p["state"] == state and p["india_only"] is True
        assert p["url"] == f"https://{p['host']}/{path}" and p["district"]
    assert seeds == mod(module).items()                      # the seed file is what items() makes
    return {s["key"]: s["payload"] for s in seeds}


def _check_south(recs, module, state):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:") and d["type"] == "dept_office" and d["state"] == state, d
        assert d["level"] in ("subdistrict", "block", "subdivision") and d["dept"] in ("revenue", "rural_development", "administration")
        assert d.get("area") and d.get("district") and d.get("source") and d.get("post") and (d.get("phone") or d.get("name")), d


def test_sub2_ap_menu_and_tables():
    m = mod("sub2_ap")
    p = _seeds_south("sub2_ap", 28, "AP")["sub2_ap-prakasam"]
    assert p["district"] == "Prakasam"
    get = fake_get(MENU_AP)
    recs, files, why = m.fetch(p, get)
    asked = [u for _, u, _ in get.calls]
    # the menu gives Revenue Divisions, MANDALS LIST and MPDO LIST; Contact Directory (whoswho.py) is not asked
    assert asked == ["https://prakasam.ap.gov.in/", "https://prakasam.ap.gov.in/subdivision-blocks/",
                     "https://prakasam.ap.gov.in/tehsil/", "https://prakasam.ap.gov.in/mpdos"]
    assert why == "" and len(files) == 3 and files[0][0] == "depts/sub2_ap/prakasam.ap.gov.in-home.html.gz"
    _check_south(recs, "sub2_ap", "AP")
    d = dict(recs)
    t = d["dept:sub2_ap:prakasam.ap.gov.in:subdistrict:chimakurthi"]
    assert (t["area"], t["post"], t["phone"], t["dept"], t["division"]) == ("Chimakurthi", "Tahsildar", "9281034445", "revenue", "Ongole")
    assert t["last_updated"] == "2026-01-31" and t["district"] == "Prakasam" and t["source"] == "https://prakasam.ap.gov.in/tehsil/"
    assert d["dept:sub2_ap:prakasam.ap.gov.in:subdistrict:ongole-urban"]["division"] == "Ongole"      # blank cell = as above
    b = d["dept:sub2_ap:prakasam.ap.gov.in:block:n-g-padu"]
    assert (b["area"], b["phone"], b["email"], b["level"]) == ("N.G Padu", "7093009664", "mpdo.ngpadu@gmail.com", "block")
    assert b["post"] == "Mandal Parishad Development Officer" and b["dept"] == "rural_development"
    assert len(recs) == 9


def test_sub2_ap_mpdo_names_and_rdos():
    m = mod("sub2_ap")
    rows = m.rows((DATA / "sub2" / "ap_anakapalli_mpdos.html").read_text(), "block")
    assert [r["area"] for r in rows] == ["Anakapalli", "Atchutapuram", "Butychayyapeta", "Chodavaram"]
    assert (rows[1]["name"], rows[1]["phone"], rows[1]["email"]) == ("K.Prabhakara Rao", "9000013923", "mpdoatchutapuram@gmail.com")
    rdo = m.rows((DATA / "sub2" / "ap_ananthapuramu_rdo.html").read_text(), "subdivision")
    assert [(r["area"], r["name"], r["phone"]) for r in rdo] == [("Ananthapuramu", "Premanth Kumar", "08554241168"),
                                                                 ("Kalyandurgam", "Vasanth Babu", "8333082895"),
                                                                 ("Guntakal", "Srinivas", "")]
    assert rdo[1]["email"] == "rdokld@gmail.com" and all(r["level"] == "subdivision" for r in rdo)


def test_sub2_ap_no_answer_and_link_rules():
    m = mod("sub2_ap")
    p = m.items()[0]["payload"]
    assert m.fetch(p, fake_get({})) == ([], [], "no answer")
    assert m.kind_of("MPDO LIST") == "block" and m.kind_of("Revenue Divisions") == "subdivision" and m.kind_of("MANDALS LIST") == "subdistrict"
    assert m.kind_of("Taluk Panchayat") == "block" and m.kind_of("Tahsildars Contact Details") == "subdistrict"
    assert m.clean_area("MRO LRPalle") == "LRPalle" and m.clean_area("1.PALASAMUDRAM") == "Palasamudram"
    assert m.clean_area("O/o Tahsildar, Niddadavole") == "Niddadavole" and m.clean_area("RDO Gadwal Division") == "Gadwal"
    html = ("<table><tr><th>Sl No</th><th>Name of the Mandal/ Municipality</th><th>Name of the MPDO</th><th>Phone Number</th></tr>"
            "<tr><td>1</td><td>Yelamanchili Municipality</td><td>A. B</td><td>9000000001</td></tr>"
            "<tr><td>2</td><td>Rambilli</td><td>MPDO RAMBILLI</td><td>9000000002</td></tr></table>")
    assert m.rows(html, "block") == [{"area": "Rambilli", "division": "", "name": "", "post": "", "phone": "9000000002", "email": "",
                                      "level": "block", "address": ""}]       # municipality left out; "MPDO RAMBILLI" is no name


def test_sub2_tg_two_tables_one_page():
    m = mod("sub2_tg")
    p = _seeds_south("sub2_tg", 33, "TG")["sub2_tg-mulugu"]
    get = fake_get({"https://mulugu.telangana.gov.in/": "sub2/tg_mulugu_menu.html",
                    "https://mulugu.telangana.gov.in/tahsildars-mpdos/": "sub2/tg_mulugu_tahsildars_mpdos.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 6
    _check_south(recs, "sub2_tg", "TG")
    d = dict(recs)
    t = d["dept:sub2_tg:mulugu.telangana.gov.in:subdistrict:venkatapur"]
    assert (t["name"], t["phone"], t["email"], t["post"]) == ("Giri Babu", "6281821897", "tahsildarvenkatapur@gmail.com", "Tahsildar")
    g = d["dept:sub2_tg:mulugu.telangana.gov.in:block:govindaraopet"]               # the MPDO table under the "MPDOs" title row
    assert (g["name"], g["phone"], g["post"], g["district"]) == ("Varun Kumar", "9281484751", "Mandal Parishad Development Officer",
                                                                 "Mulugu")
    assert d["dept:sub2_tg:mulugu.telangana.gov.in:subdistrict:govindaraopet"]["name"] == "N. Srujan Kumar"


def test_sub2_tg_level_from_row():
    m = mod("sub2_ap")
    rows = m.rows((DATA / "sub2" / "tg_gadwal_mandals.html").read_text(), "subdistrict")
    assert [(r["area"], r["level"], r["name"]) for r in rows] == [("Gadwal", "subdivision", "Smt. L. Alivelu"),
                                                                  ("Maldakal", "subdistrict", "Smt. Jhansi Rani (I/c)"),
                                                                  ("Ghattu", "subdistrict", "Sri Madan Mohan Goud")]
    assert rows[1]["division"] == ""                       # "79-Gadwal A/C" is a constituency, not a division
    # no place column: the place comes from the designation; Additional Collector, DRO, Law Officer ... are left out
    rows = m.rows((DATA / "sub2" / "tg_medchal_officers.html").read_text(), "subdistrict")
    assert len(rows) == 17 and {r["level"] for r in rows} == {"subdivision", "subdistrict"}
    k = next(r for r in rows if r["area"] == "Ghatkesar")
    assert (k["name"], k["phone"], k["email"]) == ("B. Chandra Shekar", "7995073751", "tahght05@gmail.com, tahght12@gmail.com")
    assert [r["area"] for r in rows if r["level"] == "subdivision"] == ["Keesara", "Malkajgiri"]


def test_sub2_ka_english_menu():
    m = mod("sub2_ka")
    p = _seeds_south("sub2_ka", 33, "KA", "en/")["sub2_ka-dharwad"]
    get = fake_get({"https://dharwad.nic.in/en/": "sub2/ka_dharwad_menu.html",
                    "https://dharwad.nic.in/en/tehsil/": "sub2/ka_dharwad_tehsil.html",
                    "https://dharwad.nic.in/en/subdivision-blocks/": "sub2/ka_dharwad_subdivision.html",
                    "https://dharwad.nic.in/en/taluk-panchayat/": "sub2/ka_dharwad_tp.html"})
    recs, files, why = m.fetch(p, get)
    assert all(u.startswith("https://dharwad.nic.in/en/") for _, u, _ in get.calls)     # not the Kannada twins
    assert why == "" and len(recs) == 8
    _check_south(recs, "sub2_ka", "KA")
    d = dict(recs)
    t = d["dept:sub2_ka:dharwad.nic.in:subdistrict:hubballi"]
    assert (t["phone"], t["email"], t["post"], t["last_updated"]) == ("0836-2233844", "tahsilhbl@gmail.com", "Tahsildar", "2020-12-29")
    e = d["dept:sub2_ka:dharwad.nic.in:block:kundgol"]
    assert (e["phone"], e["post"], e["dept"], e["district"]) == ("08304-290237", "Executive Officer, Taluk Panchayat",
                                                                 "rural_development", "Dharwad")


# ---- west ----
def _seeds_west(module, n):
    seeds = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    assert len(seeds) == n and all(s["key"].startswith("sub2_") and s["payload"]["reader"] == module for s in seeds)
    assert len({s["key"] for s in seeds}) == n
    return seeds


def _check_west(recs, module, state, dept, level):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:") and d["type"] == "dept_office" and d["state"] == state, d
        assert d["dept"] == dept and d["level"] == level and d.get("source") and d.get("area") and d.get("district"), d
        assert d.get("name") or d.get("phone") or d.get("email"), d


# ---------- Gujarat: civil lists (TDO, Mamlatdar, Deputy Collector / Prant Officer) ----------

def _gj(kind, sample):
    m = mod("sub2_gj")
    p = {s["payload"]["kind"]: s["payload"] for s in _seeds_west("sub2_gj", 3)}[kind]
    assert p["india_only"] is True and p["state"] == "GJ"
    get = fake_get({p["url"]: f"sub2/{sample}"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(get.calls) == 1 and files[0][0] == f"depts/sub2_gj/{kind}.pdf"
    return m, dict(recs), recs


def test_sub2_gj_tdo():
    m, d, recs = _gj("tdo", "gj_tdo_civil_list.pdf")
    _check_west(recs, "sub2_gj", "GJ", "rural_development", "block")
    assert len(recs) == 6                       # 7 rows on the page; the officer "Under Suspension" is left out
    t = d["dept:sub2_gj:tdo:bhavnagar:shihor"]
    assert t["name"] == "Mosamsinh Bhagvatsinh Rav" and t["phone"] == "9925232344" and t["email"] == "raomousamsingh@gmail.com"
    assert t["area"] == "Shihor" and t["district"] == "Bhavnagar" and t["district_code"] == "443" and t["last_updated"] == "2025-01-01"
    t = d["dept:sub2_gj:tdo:banas-kantha:dantiwada"]     # "Taluka Development Of-" + "ficer, Dantiwada, Dist." + "Banaskantha"
    assert t["name"] == "Piyush Tarunkumar Payghode" and t["email"] == "tdo-dantiwada@gujarat.gov.in" and t["district"] == "Banas Kantha"
    assert d["dept:sub2_gj:tdo:patan:shankheshwar"]["email"] == "tdo.shankheshwar@gmail.com"   # "tdo.shankhesh-" + "war@gmail.com"
    assert d["dept:sub2_gj:tdo:gandhinagar:dahegam"]["name"] == "Dr.Pankajkumar Joravarsih Mahida"   # the name wraps a line


def test_sub2_gj_mamlatdar():
    m, d, recs = _gj("mamlatdar", "gj_mamlatdar_civil_list.pdf")
    _check_west(recs, "sub2_gj", "GJ", "revenue", "subdistrict")
    assert len(recs) == 5                       # "Chitnish To Collector, Jamnagar" is not a taluka post
    t = d["dept:sub2_gj:mamlatdar:mahesana:unjha"]
    assert t["name"] == "Rekhaben Satishkumar Raval" and t["phone"] == "9712288122, 02767-250970"
    assert t["email"] == "mam-unjha@gujarat.gov.in" and t["area"] == "Unjha" and t["post"] == "Mamlatdar"
    t = d["dept:sub2_gj:mamlatdar:sabar-kantha:posheena"]
    assert t["email"] == "dymam-posina-sab@gujarat.gov.in, hhnai77@gmail.com" and t["district_code"] == "458"
    assert d["dept:sub2_gj:mamlatdar:rajkot:kotda-sanghani"]["phone"] == "9427224746, 7567005495, 02827-276221"


def test_sub2_gj_prant():
    m, d, recs = _gj("dycollector", "gj_dycollector_civil_list.pdf")
    _check_west(recs, "sub2_gj", "GJ", "administration", "subdivision")
    t = d["dept:sub2_gj:dycollector:bhavnagar:talaja"]
    assert t["name"] == "Jaydipsinh Ramanlal Solanki" and t["phone"] == "7567010274, 02842-222260" and t["area"] == "Talaja"
    assert t["email"] == "po-talaja-bav@gujarat.gov.in" and t["post"].startswith("Prant Officer")


def test_sub2_gj_posts_and_names():
    m = mod("sub2_gj")
    assert m.post_place("tdo", "Taluka Development Oficer, Kadi, Dist. Mahesana 24-10-2023")[1:3] == ("Kadi", "Mahesana")
    assert m.post_place("tdo", "Taluka Development Officer, Lakhtar, Surendranagar")[1:3] == ("Lakhtar", "Surendranagar")
    assert m.post_place("mamlatdar", "Mamlatadar, Porbandar (Rural) 09-01-2025")[1:] == ("Porbandar", "", "Porbandar (Rural)")
    for post in ("Mamlatdar, Disaster 22-05-2025", "Mamlatdar, Election, Kachchh 26-05-2025", "Mamlatdar, Collector Office, Morbi",
                 "Chitnish To Collector, Jamnagar", "Mamlatdar, RIC-2"):
        assert m.post_place("mamlatdar", post) is None, post
    assert m.post_place("dycollector", "Prant Ofiicer, Ahwa 29-10-2024")[1] == "Ahwa"
    assert m.post_place("dycollector", "Deputy District Development Officer") is None
    assert m.name_of(["Bhudarbhai Tobhanbhai", "Savsani", "New S.S.C.", "(Jamnagar)"]) == "Bhudarbhai Tobhanbhai Savsani"
    assert m.name_of(["Ranjendrakumar K. Panchal", "New S.S.C.E.", "(Patan )"]) == "Ranjendrakumar K. Panchal"
    assert m.name_of(["Jaydipsinh Ramanlal Solanki", "Bachelor of Rural Studies"]) == "Jaydipsinh Ramanlal Solanki"
    assert m.name_of(["Chintan Virambhai Chaudhari M. Pharm"]) == "Chintan Virambhai Chaudhari"


def test_sub2_gj_no_answer():
    m = mod("sub2_gj")
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")


# ---------- Maharashtra: Zilla Parishad directories (BDOs) ----------

def _zp(host):
    return {s["payload"]["url"]: s["payload"] for s in _seeds_west("sub2_mh_zp", 34)}[f"https://{host}/en/directory/"]


def test_sub2_mh_zp_seeds():
    m = mod("sub2_mh_zp")
    seeds = _seeds_west("sub2_mh_zp", 34)
    assert len({s["payload"]["district_code"] for s in seeds}) == 34 and all(s["payload"]["state"] == "MH" for s in seeds)
    assert m.area_of("Block Development Officer, Akole", "", "", "") == "Akole"
    assert m.area_of("BDO", "PS Office Georai", "BDO", "") == "Georai"
    assert m.area_of("Group Development Officer", "Panchayat Committee, Umarkhed", "", "") == "Umarkhed"


def test_sub2_mh_zp_tables_per_samiti():
    m = mod("sub2_mh_zp")
    p = _zp("zpyavatmal.gov.in")
    recs, files, why = m.fetch(p, fake_get({p["url"]: "sub2/mh_zp_yavatmal_dir.html"}))
    _check_west(recs, "sub2_mh_zp", "MH", "rural_development", "block")
    d = dict(recs)
    assert why == "" and sorted(x["area"] for x in d.values()) == ["Babhulgaon", "Digras", "Kalamb", "Mahagaon", "Pusad"]
    b = d["dept:sub2_mh_zp:zpyavatmal.gov.in:babhulgaon"]
    assert b["phone"] == "9850452994" and b["email"] == "bdo.babhulgaon@maharashtra.gov.in" and "name" not in b   # the site gives no name
    assert b["district"] == "Yavatmal" and b["district_code"] == "500" and b["last_updated"] == "2026-11-05"
    # the Digras table also lists the Pusad GDO and the Pusad table the Mahagaon GDO: the area comes from the address, one record each
    assert d["dept:sub2_mh_zp:zpyavatmal.gov.in:pusad"]["phone"] == "9822227811"


def test_sub2_mh_zp_named_rows():
    m = mod("sub2_mh_zp")
    p = _zp("nagarzp.gov.in")
    recs, files, why = m.fetch(p, fake_get({p["url"]: "sub2/mh_zp_nagar_dir.html"}))
    _check_west(recs, "sub2_mh_zp", "MH", "rural_development", "block")
    d = dict(recs)
    assert len(d) == 4
    a = d["dept:sub2_mh_zp:nagarzp.gov.in:akole"]
    assert a["name"] == "Shri. Amar Tanaji Mane" and a["phone"] == "221230" and a["email"] == "bdo.akole-zpnagar@mah.gov.in"
    assert d["dept:sub2_mh_zp:nagarzp.gov.in:kopargaon"]["name"] == "Shri. Sandip Damodhar Dalvi"       # "(Incharge)" dropped


def test_sub2_mh_zp_linked_page():
    m = mod("sub2_mh_zp")
    p = _zp("www.zpsatara.gov.in")
    get = fake_get({p["url"]: "sub2/mh_zp_satara_dir.html",
                    "https://www.zpsatara.gov.in/en/block-development-officers-contact-list/": "sub2/mh_zp_satara_bdo.html"})
    recs, files, why = m.fetch(p, get)
    _check_west(recs, "sub2_mh_zp", "MH", "rural_development", "block")
    d = dict(recs)
    assert len(d) == 4 and len(get.calls) == 2
    s = d["dept:sub2_mh_zp:www.zpsatara.gov.in:wai"]
    assert s["name"] == "Mr. Narayan Gholap" and s["phone"] == "02168-260249" and s["email"] == "bdowai@in.com, pswaibdo@gmail.com"
    assert s["source"] == "https://www.zpsatara.gov.in/en/block-development-officers-contact-list/"


def test_sub2_mh_zp_redirect_and_tabular():
    m = mod("sub2_mh_zp")
    p = _zp("zpbeed.gov.in")

    def get(url, method="GET", data=None, headers=None):
        get.calls.append(url)
        if url == p["url"]:                                   # zpbeed.gov.in -> https://www.zpbeed.gov.in (path dropped)
            return Answer(b"<html><body>home</body></html>", "https://www.zpbeed.gov.in/")
        if url == "https://www.zpbeed.gov.in/en/directory/":
            return Answer((DATA / "sub2" / "mh_zp_beed_dir.html").read_bytes(), url)
        return None
    get.calls = []
    recs, files, why = m.fetch(p, get)
    _check_west(recs, "sub2_mh_zp", "MH", "rural_development", "block")
    d = dict(recs)
    assert len(d) == 4 and get.calls[:2] == [p["url"], "https://www.zpbeed.gov.in/en/directory/"]
    g = d["dept:sub2_mh_zp:www.zpbeed.gov.in:georai"]
    assert g["name"] == "Shri. Aniruddh Sanap" and g["phone"] == "9850789950" and g["email"] == "bdogevrai47@gmail.com"
    assert not [x for x in d.values() if "Assistant" in x.get("designation", "")]


def test_sub2_mh_zp_no_answer():
    m = mod("sub2_mh_zp")
    assert m.fetch(_zp("zpyavatmal.gov.in"), fake_get({})) == ([], [], "no answer")


# ---------- Rajasthan: Panchayati Raj Department list of Vikas Adhikaris ----------

def test_sub2_rj_bdo_list():
    m = mod("sub2_rj_bdo")
    p = _seeds_west("sub2_rj_bdo", 1)[0]["payload"]
    assert p["india_only"] is True and p["discover"] is True
    get = fake_get({m.CONTACTS: "sub2/rj_contacts_pr_block.json", m.URL: "sub2/rj_bdo_list_p1.pdf"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and [c[1] for c in get.calls] == [m.CONTACTS, m.URL]   # the 2026/Sep upload wins over the 2023 one
    _check_west(recs, "sub2_rj_bdo", "RJ", "rural_development", "block")
    d = dict(recs)
    assert len(d) == 23
    b = d["dept:sub2_rj_bdo:ajmer:bhinay"]
    assert b["name"] == "सुनील वर्मा" and b["phone"] == "8233443132, 01466-273423" and b["email"] == "bdo.ajm.bhin@rajasthan.gov.in"
    assert b["area"] == "Bhinay" and b["area_regional"] == "भिनाय" and b["district_code"] == "86" and b["last_updated"] == "2026-08-17"
    a = d["dept:sub2_rj_bdo:ajmer:ajmer-gramin"]
    assert a["area"] == "Ajmer Rural" and a["office"] == "Ajmer gramin" and a["name"] == "शिवदान सिंह"
    v = d["dept:sub2_rj_bdo:ajmer:arain"]                       # "रिक्त पद": post vacant, office phone kept
    assert v["vacant"] is True and "name" not in v and v["phone"] == "01463-281123"
    assert d["dept:sub2_rj_bdo:balotra:balotara"]["district"] == "Balotra"


def test_sub2_rj_bdo_fallback_url():
    m = mod("sub2_rj_bdo")
    p = m.items()[0]["payload"]
    get = fake_get({m.URL: "sub2/rj_bdo_list_p1.pdf"})            # the contact call fails: the payload url is read
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 23 and files[0][0] == "depts/sub2_rj_bdo/vikas-adhikari-list.pdf"
    assert m.fetch(p, fake_get({})) == ([], [], "no answer")


# ---- central ----
def _check_central(recs, module, state):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:") and d["type"] == "dept_office" and d["state"] == state, d
        assert d.get("level") and d.get("source") and d.get("dept") and d.get("district") and d.get("name") and d.get("area"), d


def _seeds_central(name):
    seeds = json.loads((ROOT / "seeds" / name).read_text())
    assert seeds and all(s["key"].startswith("sub2_") and s["payload"]["india_only"] is True for s in seeds)
    return seeds


def _cg_get(with_004=True):
    routes = {lambda u, m, d: m == "GET": "sub2/cg_rev_home.html",
              lambda u, m, d: m == "POST" and d.get("__EVENTTARGET") == "ddlDistrict" and d.get("ddlDistrict") == "44": "sub2/cg_rev_raipur.html",
              lambda u, m, d: m == "POST" and d.get("ddlDesignation") == "008": "sub2/cg_rev_raipur_008.html"}
    if with_004:
        routes[lambda u, m, d: m == "POST" and d.get("ddlDesignation") == "004"] = "sub2/cg_rev_raipur_004.html"
    return fake_get(routes)


def test_sub2_cg_seeds():
    m = mod("sub2_cg")
    seeds = _seeds_central("dept_sub2_cg.json")
    assert len(seeds) == 33 == len(m.DISTRICTS) and seeds == m.items()
    p = {s["payload"]["district_id"]: s["payload"] for s in seeds}["44"]
    assert (p["district"], p["district_code"], p["url"]) == ("Raipur", "387", "https://revenue.cg.nic.in/RevenueOfficerSearchPage.aspx")
    assert sum(len(v) for v in m.TAHSILS.values()) == 252


def test_sub2_cg_raipur():
    m = mod("sub2_cg")
    p = {s["payload"]["district_id"]: s["payload"] for s in m.items()}["44"]
    get = _cg_get()
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 10 and files[1][0] == "depts/sub2_cg/district-44.html.gz"
    # 1 GET + district postback + 5 post postbacks; each postback carries the page's hidden fields
    assert len(get.calls) == 7 and all("__VIEWSTATE" in c[2] for c in get.calls[1:])
    _check_central(recs, "sub2_cg", "CG")
    d = dict(recs)
    t = d["dept:sub2_cg:CG-44-008-arang"]
    assert t["name"] == "BABULAL KURRE" and t["phone"] == "9399112968" and t["post"] == "Tahsildar" and t["area_regional"] == "आरंग"
    assert t["dept"] == "revenue" and t["level"] == "subdistrict" and t["district"] == "Raipur" and t["lgd_match"] is True
    a = d["dept:sub2_cg:CG-44-008-arang:2"]
    assert a["name"] == "श्रीमती ज्योति मसियारे" and a["post"] == "Additional Tahsildar" and a["phone"] == "9669071457"
    assert d["dept:sub2_cg:CG-44-008-gobra-nawapara"]["name"] == "Mr. Chandra Shekhar Mandai"
    assert d["dept:sub2_cg:CG-44-008-mandir-hasoud"]["area"] == "Mandir Hasoud"      # no Hindi name in LGD: matched by spelling
    sdo = d["dept:sub2_cg:CG-44-004-tilda"]
    assert sdo["level"] == "subdivision" and sdo["dept"] == "administration" and sdo["area_regional"] == "तिलदा-नेवरा"
    assert sdo["name"] == "मुकेश कुमार कोठारी" and sdo["phone"] == "7999597069"
    # all 8 LGD sub-districts of Raipur are named
    assert {v["area"] for v in d.values() if v["level"] == "subdistrict"} == set(m.TAHSILS["387"])


def test_sub2_cg_places():
    m = mod("sub2_cg")
    assert m.place_of("न्यायालय तह्सीलदार धरसीवा") == "धरसीवा" and m.place_of("तहसीलदार ,मंदिर हसौद") == "मंदिर हसौद"
    assert m.place_of("अनुविभागीय अधिकारी (रा.) तिलदा-नेवरा") == "तिलदा-नेवरा"
    assert m.translit("आरंग") == "Arang" and m.translit("अभनपुर") == "Abhanpur" and m.translit("मंदिर हसौद") == "Mandir Hasaud"
    assert m.lgd_name("तिल्दा", "387") == "Tilda" and m.lgd_name("कोयलीबेड़ा", "381") == "Koylibeda"
    assert m.lgd_name("कहीं नहीं", "387") is None


def test_sub2_cg_no_answer():
    m = mod("sub2_cg")
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")


def test_sub2_mp_ero():
    m = mod("sub2_mp_ero")
    seeds = _seeds_central("dept_sub2_mp_ero.json")
    assert seeds == m.items() and len(seeds) == 1
    get = fake_get({lambda u, me, d: me == "GET": "sub2/mp_ceo_home.html",
                    lambda u, me, d: me == "POST" and d.get("__EVENTTARGET") == m.TARGET and "__VIEWSTATE" in d: "sub2/mp_ceo_ero.html"})
    recs, files, why = m.fetch(seeds[0]["payload"], get)
    assert why == "" and len(recs) == 8 and len(get.calls) == 2
    _check_central(recs, "sub2_mp_ero", "MP")
    d = dict(recs)
    one = d["dept:sub2_mp_ero:MP-AC-1"]
    assert one["name"] == "Shri Gagan Singh Meena" and one["phone"] == "8738009405" and one["area"] == "Sheopur"
    assert one["level"] == "subdivision" and one["dept"] == "administration" and one["district_code"] == "431"
    assert d["dept:sub2_mp_ero:MP-AC-3"]["area"] == "Sabalagadh" and d["dept:sub2_mp_ero:MP-AC-3"]["phone"] == "9340800197"
    md = d["dept:sub2_mp_ero:MP-AC-224"]
    assert md["district"] == "Mandsaur" and md["district_code"] == "416" and md["name"] == "Shri Shubham Patidar"
    assert d["dept:sub2_mp_ero:MP-AC-16"]["area"] == "Gwalior East"
    assert m.district_of("KHANDWA") == ("Khandwa (East Nimar)", "405") and m.district_of("NARSINGPUR") == ("Narsimhapur", "418")


def test_sub2_mp_ero_no_answer():
    m = mod("sub2_mp_ero")
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")


# ---- east ----
def _seeds_east(name):
    seeds = json.loads((ROOT / "seeds" / name).read_text())
    assert seeds and all(s["key"].startswith("sub2_") for s in seeds)
    assert len({s["key"] for s in seeds}) == len(seeds)
    return seeds


def _check_east(recs, module, state):
    check_records(recs, module, "rural_development")
    for rid, d in recs:
        assert d["state"] == state and d["level"] == "block" and d.get("area") and d.get("district"), d


# Uttarakhand: Rural Development Department directory (S3WaaS tabular content)

def test_sub2_uk_seed():
    m = mod("sub2_uk")
    seeds = _seeds_east("dept_sub2_uk.json")
    assert seeds == m.items() and seeds[0]["payload"]["url"] == m.URL


def test_sub2_uk_sections():
    m = mod("sub2_uk")
    params, secs = m.tabular_sections((DATA / "sub2" / "uk_rd_directory.html").read_text())
    assert m.ajax_url((DATA / "sub2" / "uk_rd_directory.html").read_text()) == "https://ukrd.uk.gov.in/wp-admin/admin-ajax.php"
    assert m._b64json(params)["nonce"] == "747a57fd42"
    assert [(s["caption"], s["term_id"], s["pages"]) for s in secs] == [("District Almora", 1602, 2), ("District Dehradun", 1566, 1),
                                                                         ("District Pithoragarh", 1594, 2)]
    assert secs[0]["rows"][0][:2] == ["Shri Ramji Sharan Sharma", "Chief Development Officer"]     # the header row is left out


def test_sub2_uk_directory_stale_nonce():
    m = mod("sub2_uk")
    p = m.items()[0]["payload"]
    get = fake_get({m.URL: "sub2/uk_rd_directory.html", ("POST", "https://ukrd.uk.gov.in/wp-admin/admin-ajax.php"): "sub2/uk_rd_paginate_nonce.json"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and files[0][0] == "depts/sub2_uk/directory.html.gz"
    # page 2 of Almora: stale nonce -> the page once more without the cache (no answer here) -> page 2 of Pithoragarh is tried
    # with the old nonce too
    methods = [(c[0], c[1].split("?")[0]) for c in get.calls]
    assert methods[:3] == [("GET", m.URL), ("POST", "https://ukrd.uk.gov.in/wp-admin/admin-ajax.php"), ("GET", m.URL)]
    assert get.calls[1][2]["action"] == "directory_paginate" and get.calls[1][2]["pageno"] == 2
    _check_east(recs, "sub2_uk", "UK")
    d = dict(recs)
    assert len(d) == 7 + 6 + 7
    h = d["dept:sub2_uk:UK-almora:hawalbagh"]
    assert h["name"] == "Shri Santosh Jaithi" and h["phone"] == "7060529201" and h["email"] == "bdohawalbag@gmail.com"
    assert h["post"] == "Block Development Officer" and h["district"] == "Almora" and h["address"] == "Block Development Office, Hawalbagh"
    r = d["dept:sub2_uk:UK-dehradun:raipur"]
    assert r["name"] == "Smt. Aparna Bahuguna" and r["phone"] == "9634083819, 0135-2781673" and r["area"] == "Raipur"
    v = d["dept:sub2_uk:UK-pithoragarh:pithoragarh"]          # "Vin(Pithoragarh)": the LGD block is in brackets
    assert v["area_local"] == "Vin" and v["name"] == "Mr. Rajendra Awasthi" and v["post"] == "Incharge Block Development Officer"
    dd = d["dept:sub2_uk:UK-pithoragarh:didihat"]             # a row with the email written twice (7 cells)
    assert dd["phone"] == "9410135928, 05964-232136" and dd["email"] == "bdoddt@gmail.com"
    assert not [k for k in d if "chief" in k or "acharya" in k]


def test_sub2_uk_paginate_answer():
    m = mod("sub2_uk")
    rows = m.answer_rows((DATA / "sub2" / "uk_rd_paginate_shape.json").read_text())
    assert len(rows) == 12 and rows[0][:2] == ["Shri Abhishek Tripathi", "Chief Development Officer"]     # no header row in a tbody
    assert sum("Block Development" in r[1] for r in rows) == 7
    assert m.answer_rows((DATA / "sub2" / "uk_rd_paginate_nonce.json").read_text()) == []
    assert m.stale((DATA / "sub2" / "uk_rd_paginate_nonce.json").read_text())


def test_sub2_uk_area():
    m = mod("sub2_uk")
    assert m.area_of("Block Development officer Karnaprayag") == ("Karnaprayag", "")
    assert m.area_of("Block Development officeTharali") == ("Tharali", "")
    assert m.area_of("Block Development office Nandanagar (Ghat)") == ("Ghat", "Nandanagar")
    assert m.area_of("Purola Block,") == ("Purola", "")
    assert m.area_of("Development Block Office, Didihat") == ("Didihat", "")
    assert m.district("District bageshwar") == "Bageshwar"


# Uttar Pradesh: Panchayati Raj Department officer directory (ADO and BDO per block)

def test_sub2_up_prd_seeds():
    m = mod("sub2_up_prd")
    seeds = _seeds_east("dept_sub2_up_prd.json")
    assert len(seeds) == 78 and {s["payload"]["district"] for s in seeds} == set(m.LGD)
    k = {s["key"]: s["payload"] for s in seeds}
    assert k["sub2_up_prd-agra"]["target"] == "gridEntry1$ctl02$ben_name"
    assert k["sub2_up_prd-shravasti-2"]["district"] == "Shrawasti" and k["sub2_up_prd-shravasti-2"]["nth"] == 2
    assert k["sub2_up_prd-sant-ravidas-nagar-bhadohi"]["district"] == "Bhadohi"


def test_sub2_up_prd_items_from_summary():
    m = mod("sub2_up_prd")
    its = m.items(fake_get({m.URL: "sub2/up_prd_summary.html"}))
    assert [(i["key"], i["payload"]["target"]) for i in its] == [
        ("sub2_up_prd-agra", "gridEntry1$ctl02$ben_name"), ("sub2_up_prd-firozabad", "gridEntry1$ctl03$ben_name"),
        ("sub2_up_prd-shravasti", "gridEntry1$ctl39$ben_name"), ("sub2_up_prd-shravasti-2", "gridEntry1$ctl40$ben_name")]


def test_sub2_up_prd_district():
    m = mod("sub2_up_prd")
    p = next(s["payload"] for s in _seeds_east("dept_sub2_up_prd.json") if s["key"] == "sub2_up_prd-agra")
    get = fake_get({("GET", m.URL): "sub2/up_prd_summary.html", ("POST", m.URL): "sub2/up_prd_agra.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and files[0][0] == "depts/sub2_up_prd/district-agra.html.gz"
    post = get.calls[1]
    assert post[0] == "POST" and post[2]["__EVENTTARGET"] == "gridEntry1$ctl02$ben_name" and post[2]["__VIEWSTATEGENERATOR"] == "73C56A53"
    _check_east(recs, "sub2_up_prd", "UP")
    d = dict(recs)
    assert len(d) == 9
    a = d["dept:sub2_up_prd:UP-agra:achhnera:ado"]
    assert a["name"] == "MAHENDRA SINGH" and a["phone"] == "9012181122" and a["post"] == "Assistant Development Officer (Panchayat)"
    b = d["dept:sub2_up_prd:UP-agra:akola:bdo"]
    assert b["name"] == "SUSMITA YADAV" and b["phone"] == "9412583005" and b["post"] == "Block Development Officer" and b["district"] == "Agra"
    k = d["dept:sub2_up_prd:UP-agra:khandauli:bdo"]           # mobile and a different WhatsApp number
    assert k["phone"] == "9454698302, 9140034850" and k["whatsapp"] == "9140034850" and k["area"] == "Khandauli"
    e = d["dept:sub2_up_prd:UP-agra:etmadpur:ado"]            # "ADO-ETMADPUR" in the name column: no name, phone kept
    assert "name" not in e and e["phone"] == "9412330932"
    assert d["dept:sub2_up_prd:UP-agra:jagner:bdo"]["name"] == d["dept:sub2_up_prd:UP-agra:fatehabad:bdo"]["name"] == "SUMANT YADAV"


def test_sub2_up_prd_no_answer():
    m = mod("sub2_up_prd")
    p = {"reader": "sub2_up_prd", "url": m.URL, "district_as_written": "AGRA", "nth": 1, "district": "Agra", "state": "UP"}
    assert m.fetch(p, fake_get({})) == ([], [], "no answer")
    assert m.fetch(p, fake_get({("GET", m.URL): "sub2/up_prd_summary.html"}))[2] == "no answer to the district link"
    assert m.district("SANT RAVIDAS NAGAR (BHADOHI)") == "Bhadohi" and m.district("KUSHI NAGAR") == "Kushinagar"
