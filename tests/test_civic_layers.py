"""Offline tests of the civic layer readers (dforms/civic_<layer>_<xx>.py) and their seeds (seeds/dept_civic_*.json).
Samples in tests/data/civic_*; no test touches the network."""
import json

import pytest

from esw_common import DATA, ROOT, Answer, check_records, fake_get, mod  # noqa: F401



# ---- Polling stations (pollst: PY, LD, HR) ----
def check_pollst(recs, module, state):
    """Every record: id prefix, type, dept elections, level polling_station, a station, AC and part numbers, a source."""
    ids = [r for r, _ in recs]
    assert recs and len(ids) == len(set(ids)), "no rows or duplicate record ids"
    for rid, d in recs:
        assert rid == f"dept:{module}:{state}-{d['ac_no']}-{d['part_no']}", rid
        assert d["type"] == "dept_office" and d["dept"] == "elections" and d["level"] == "polling_station", d
        assert d["layer"] == "pollst" and d["state"] == state and d["source"] and d["area"] == d["station"], d


def test_pollst_py():
    m = mod("civic_pollst_py")
    url = m.url_of(2)
    assert url == "https://ceopuducherry.py.gov.in/blo_ps.php?c=Mg=="
    recs, files, why = m.fetch({"url": url, "ac_no": 2}, fake_get({url: "civic_pollst_py.html"}))
    assert why == "" and len(recs) == 5 and files[0][0] == "depts/civic_pollst_py/ac2.html.gz"
    check_pollst(recs, "civic_pollst_py", "PY")
    rid, d = recs[0]
    assert rid == "dept:civic_pollst_py:PY-2-1"
    assert d["station"] == "Govt. Primary School, MARIAMMANKOIL STREET, SILUKARIPALAYAM, Puducherry-605107"
    assert (d["name"], d["phone"], d["post"]) == ("RAMALINGAM", "9442992663", "BLO")
    assert (d["ac_name"], d["district"], d["last_updated"]) == ("THIRUBHUVANAI", "Puducherry", "2026-04-27")
    assert recs[4][1]["name"] == "KARUNAGARAN R"


def test_pollst_ld():
    m = mod("civic_pollst_ld")
    recs, files, why = m.fetch({"url": m.URL}, fake_get({m.URL: "civic_pollst_ld.html"}))
    assert why == "" and len(recs) == 4
    check_pollst(recs, "civic_pollst_ld", "LD")
    d = recs[1][1]
    assert d["station"] == "P M Shri Dr.APJ Abdul Kalam Memmorial Govt.Senior Secondary School, Chetlat"
    assert (d["part_no"], d["locality"], d["polling_area"]) == ("2", "Chetlat", "Entire Part 2")


def test_pollst_hr():
    m = mod("civic_pollst_hr")
    pages = json.loads((DATA / "civic_pollst_hr_pages.json").read_text())
    recs = m.parse(pages, "https://ceoharyana.gov.in/Website/ReviseListOfPollingBooth/13-Bhiwani.pdf", "Bhiwani")
    check_pollst(recs, "civic_pollst_hr", "HR")
    by = {r: d for r, d in recs}
    d = by["dept:civic_pollst_hr:HR-54-1"]
    assert (d["ac_name"], d["station"], d["locality"]) == ("Loharu", "Govt. High School (East Wing), Naloi", "Naloi")
    assert d["polling_area"].startswith("Part No.-1 Voter Village Naloi (Partly) H. No. 1 to 53") and "For All" not in d["polling_area"]
    d = by["dept:civic_pollst_hr:HR-57-1"]
    assert d["station"] == "Office of Veterinary Poly. Clinic, Bhiwani (West Wing)"
    assert (d["town"], d["ward_no"]) == ("Bhiwani", "1")
    assert {d["ac_no"] for d in by.values()} == {54, 57}
    # the number row under the header ("1 2 3 4 5 6 7") is no polling station
    assert all(d["station"] not in ("2", "3") for d in by.values())


def test_pollst_hr_fetch_keeps_pdf():
    m = mod("civic_pollst_hr")
    url = "https://ceoharyana.gov.in/Website/ELECTIONCOMMISSION/Images/x.pdf"
    recs, files, why = m.fetch({"url": url}, fake_get({url: "civic_pollst_ld.html"}))
    assert recs == [] and why == "not a PDF" and files[0][0] == "depts/civic_pollst_hr/x.pdf.gz"


def test_pollst_hr_items_from_index():
    m = mod("civic_pollst_hr")
    html = b'<a href="/Website/ELECTIONCOMMISSION/Images/07416094.pdf">Panchkula</a><a href="/x.htm">no</a>'
    its = m.items(lambda url, **k: Answer(html, url))
    assert [i["key"] for i in its] == ["civic_pollst_hr-2024-panchkula"]
    assert its[0]["payload"]["url"] == "https://ceoharyana.gov.in/Website/ELECTIONCOMMISSION/Images/07416094.pdf"
    assert len(m.items(None)) == len(m.KNOWN)


def test_pollst_seed_files():
    """seeds/dept_civic_pollst_<xx>.json: unique keys that start with the module, a reader that exists, a url and a state."""
    every = []
    for f in sorted((ROOT / "seeds").glob("dept_civic_pollst_*.json")):
        m = f.stem[len("dept_"):]
        items = json.loads(f.read_text())
        keys = [i["key"] for i in items]
        every += keys
        assert items and len(keys) == len(set(keys)), f
        for i in items:
            p = i["payload"]
            assert i["key"].startswith(m) and p["reader"] == m and p["url"] and p["state"], (f, i)
            assert hasattr(mod(m), "fetch")
    assert len(every) == len(set(every)) and len(every) >= 50


# ---- Fair price shops (fps: SMART-PDS and AePDS states) ----
FPS_SP = ["ap", "ar", "as", "br", "cg", "dl", "ga", "hr", "jh", "jk", "la", "mz", "nl", "sk", "tr", "uk", "dh"]
FPS_JSP = ["kl", "mp", "mh", "ch"]


def test_smartpds_district_with_offices():
    """Assam, Kamrup Metro: the device list gives the dealers; the vendor's test shop (123456789...) is left out; masked dealer
    mobiles give no phone; an unmasked nominee mobile is kept as the page shows it."""
    m = mod("civic_fps_as")
    get = fake_get({("POST", "https://epos.assam.gov.in/Epos_Spring/api/fpsdevicemapping/device"): "civic_fps_as_device.json",
                    lambda u, me, d: "getSearchDetailsBlock" in u: "civic_fps_as_blocks.json",
                    lambda u, me, d: "getSearchDetailsFps" in u: "civic_fps_mz_fps.json"})
    recs, files, why = m.fetch({"reader": "civic_fps_as", "url": "https://epos.assam.gov.in", "state": "AS", "dist_code": "322",
                                "district": "Kamrup Metro"}, get)
    assert why == "" and len(files) == 2
    check_records(recs, "civic_fps_as", "food_supplies")
    d = dict(recs)
    assert "dept:civic_fps_as:123456789055" not in d and "dept:civic_fps_as:123456789057" not in d
    r = d["dept:civic_fps_as:132200100002"]
    assert r["name"] == "KHAGEN DAS" and r["post"] == "FPS dealer" and r["level"] == "facility" and r["layer"] == "fps"
    assert r["district"] == "Kamrup Metro" and r["fps_id"] == "132200100002" and "phone" not in r
    assert r["nominee_1"] == "MUNNA DAS" and "nominee_1_phone" not in r
    assert len(recs) == 4
    # one POST per district, one block list, one search call per block (2 blocks)
    assert [c[0] for c in get.calls].count("POST") == 1 and sum("getSearchDetailsFps" in c[1] for c in get.calls) == 2


def test_smartpds_office_join():
    """Mizoram: the Search list of a supply office ties each shop to the office (area / block)."""
    f = mod("civic_fps_mz")
    import dforms._civic_fps as F
    get = fake_get({lambda u, me, d: "getSearchDetailsBlock" in u: "civic_fps_mz_blocks.json",
                    lambda u, me, d: "getSearchDetailsFps" in u: "civic_fps_mz_fps.json"})
    offices, raw = F.sp_offices(get, f.BASE, "283")
    assert offices["128300000001"][1] == "Aizawl West" or offices["128300000001"][1] == "Aizawl East"
    assert offices["128300000001"][2] == "CAROLYNE LALDAWNGLIANI"
    device = {"dist_name_en": "Aizawl", "list": [{"fps_id": "128300000003", "del_name": "LALRINTLUANGA", "del_mob": "XXXXX-X1234",
                                                  "terminal_id": "XXXX-X0001", "nom_1_name": "-NA-", "nom_1_mob": "-NA-"}]}
    recs = F.sp_parse(device, offices, "civic_fps_mz", "MZ", f.BASE, "283")
    check_records(recs, "civic_fps_mz", "food_supplies")
    r = recs[0][1]
    assert r["area"] in ("Aizawl East", "Aizawl West") and r["block"] == r["area"] and "nominee_1" not in r


def test_smartpds_districts():
    import dforms._civic_fps as F
    get = fake_get({lambda u, me, d: "getSearchDetailsDistrict" in u: "civic_fps_mz_districts.json"})
    assert F.sp_districts(get, "https://epos.mizoram.gov.in") == [("283", "Aizawl"), ("284", "Champhai")]


def test_aepds_kerala():
    """Kerala: ARD (ration depot) number, dealer and nominees; no mobile (the column is commented out in the page)."""
    m = mod("civic_fps_kl")
    get = fake_get({("POST", "https://epos.kerala.gov.in/fps_device.action"): "civic_fps_kl_device.html"})
    recs, files, why = m.fetch({"reader": "civic_fps_kl", "url": "https://epos.kerala.gov.in", "state": "KL", "dist_code": "22",
                                "district": "Wayanad"}, get)
    assert why == "" and len(files) == 1
    check_records(recs, "civic_fps_kl", "food_supplies")
    d = dict(recs)
    r = d["dept:civic_fps_kl:2262001"]
    assert r["name"] == "HAMZA A P" and r["nominee_1"] == "Noufal P" and r["nominee_2"] == "RASHEED K E"
    assert r["district"] == "Wayanad" and r["terminal_id"] == "1802515945" and "phone" not in r
    assert len(recs) == 4


def test_aepds_mp_nominee_only():
    """Madhya Pradesh: a shop without a dealer name keeps its nominee (post 'FPS nominee'); Hindi names stay as written."""
    m = mod("civic_fps_mp")
    get = fake_get({("POST", "https://epos.mp.gov.in/fps_device.action"): "civic_fps_mp_device.html"})
    recs, _, why = m.fetch({"reader": "civic_fps_mp", "url": "https://epos.mp.gov.in", "state": "MP", "dist_code": "856"}, get)
    check_records(recs, "civic_fps_mp", "food_supplies")
    d = dict(recs)
    assert d["dept:civic_fps_mp:1905001"]["post"] == "FPS nominee"
    assert d["dept:civic_fps_mp:1905002"]["name"] == "Rajendr Bijapari" and d["dept:civic_fps_mp:1905002"]["district"] == "Agar"
    assert d["dept:civic_fps_mp:1905003"]["name"].startswith("राम") and d["dept:civic_fps_mp:1905003"]["name"].endswith("यादव")


def test_aepds_district_list():
    import dforms._civic_fps as F
    ds = F.jsp_districts((ROOT / "tests" / "data" / "civic_fps_kl_page.html").read_text())
    assert ("22", "Wayanad") in ds and len(ds) == 14


def test_masks():
    import dforms._civic_fps as F
    assert F.unmasked("XXXXX-X9494") == "" and F.unmasked("-NA-") == "" and F.unmasked("9469522347") == "9469522347"
    assert F.name_of("-NA-") == "" and F.name_of(" Hiramoni  Rajbongshi") == "Hiramoni Rajbongshi"


def test_fps_name_faults():
    """Data-quality review 2026-11-11 (rows from the saved JK, AS, AP and BR device lists): a mobile written in the name moves to
    the phone; labels and codes ("Fps", "PACX", a shop id, "VA0725332B303768") give no name; "FPS IS <id> IS ALSO TAGGE",
    "IC 18", "Ic No.0746026 dealer" and a trailing comma leave the name; 10-digit numbers that cannot be mobiles are no phone."""
    import dforms._civic_fps as F
    device = json.loads((DATA / "civic_fps_names.json").read_text())
    d = {k.rsplit(":", 1)[1]: v for k, v in F.sp_parse(device, {}, "civic_fps_jk", "JK", "https://epos.jk.gov.in")}
    check_records([(f"dept:civic_fps_jk:{k}", v) for k, v in d.items()], "civic_fps_jk", "food_supplies")
    assert "100200100017" not in d                                                  # "Fps", masked mobile: nothing to keep
    assert (d["100200200043"]["name"], d["100200200043"]["phone"]) == ("FPS WATERHAIL-B (MUSHTAQ AHMAD)", "7889612561")
    assert (d["100201100003"]["name"], d["100201100003"]["phone"]) == ("FPS LALPORA(MOHD AMIN QURESHI)", "6005893552")
    assert (d["100201200002"]["name"], d["100201200002"]["phone"]) == ("GRD Zabgulla (Sajad Ahmad Dinda", "9906060301")
    r = d["101200200032"]                                                           # a mistyped 9-digit mobile: out of the name
    assert r["name"] == "SAMBOORA C CB- RAFIYA FAROOQ" and r["name_number"] == "990623760" and "phone" not in r
    assert (d["130700100641"]["name"], d["130700100641"]["post"]) == ("Dharam Das Dhandari", "FPS nominee")   # AS: id as name
    assert d["131300300161"]["name"] == "BUDHESWAR GOGOI" and "name_number" not in d["131300300161"]
    assert d["1052005"]["name"] == "Anuradha"                                       # AP: trailing comma
    assert (d["0746025"]["name"], d["0746025"]["post"], d["0746025"]["phone"]) == ("V.SrinivasaRao", "FPS nominee", "9666706699")
    assert (d["1318017"]["name"], d["1318017"]["phone"]) == ("U. Raghavaiah", "9849488376")
    assert (d["0782002"]["name"], d["0782002"]["post"]) == ("Ramesh", "FPS nominee")
    assert d["120700100033"]["name"] == "USMAN ANSARI TAG SUBHITA DEVI" and "phone" not in d["120700100033"]   # BR 9999999999
    assert "phone" not in d["120700500738"]                                         # BR 2222222222
    r = d["122100100054"]                                                           # BR "PACX": no name, the dealer phone stays
    assert "name" not in r and r["phone"] == "8873983252" and r["post"] == "FPS dealer" and r["nominee_1"] == "maheshwar ray"
    assert F.unmasked("3090090924") == "" and F.unmasked("1901001000") == "" and F.unmasked("8969690685") == "8969690685"
    assert F.unmasked("0612-2233445") == "0612-2233445"
    assert F.split_name("NITIN JAGANNATH KOR 9272888265 ASOLE NR") == ("NITIN JAGANNATH KOR ASOLE NR", "9272888265")
    assert F.split_name("Ichhapur IC") == ("Ichhapur IC", "") and F.split_name("PACs Aurahi Purab")[0] == "PACs Aurahi Purab"


def test_fps_jsp_name_faults():
    """MP: a longitude in the dealer cell ("77.528877") is no name (the nominee stands in, or the shop has no row); MH: a mobile in
    the dealer cell is the dealer's phone; a trailing comma leaves the name."""
    import dforms._civic_fps as F
    mp = dict(F.jsp_parse((DATA / "civic_fps_mp_names.html").read_text(), "civic_fps_mp", "MP", "https://epos.mp.gov.in"))
    check_records(list(mp.items()), "civic_fps_mp", "food_supplies")
    assert "dept:civic_fps_mp:0505046" not in mp and mp["dept:civic_fps_mp:0505045"]["name"] == "Ramsingh parihar"
    assert (mp["dept:civic_fps_mp:0505048"]["name"], mp["dept:civic_fps_mp:0505048"]["post"]) == ("Girraj Singh Dhakad", "FPS nominee")
    mh = dict(F.jsp_parse((DATA / "civic_fps_mh_names.html").read_text(), "civic_fps_mh", "MH", "https://epos.mahafood.gov.in"))
    check_records(list(mh.items()), "civic_fps_mh", "food_supplies")
    r = mh["dept:civic_fps_mh:151521800431"]
    assert (r["name"], r["phone"], r["nominee_1"]) == ("LAXMAN DEVRAO(MURMI)", "9552481105", "Mangalbai Laxman Mhaske")
    assert mh["dept:civic_fps_mh:150307770109"]["name"] == "V.S.Nichit"


def test_seed_files_b():
    """Every seeds/dept_civic_fps_*.json / dept_civic_lpg_*.json: unique keys, an existing reader, url and state."""
    keys = []
    files = sorted((ROOT / "seeds").glob("dept_civic_fps_*.json")) + sorted((ROOT / "seeds").glob("dept_civic_lpg_*.json"))
    assert {f.stem[len("dept_civic_fps_"):] for f in files if "fps" in f.stem} >= set(FPS_SP + FPS_JSP)
    for f in files:
        m = f.stem[len("dept_"):]
        items = json.loads(f.read_text())
        assert items, f
        for i in items:
            p = i["payload"]
            assert i["key"].startswith(m) and len(i["key"]) <= 200
            assert p["reader"] == m and p.get("url") and p.get("state"), (f, i)
            keys.append(i["key"])
        assert hasattr(mod(m), "fetch") and hasattr(mod(m), "items")
    assert len(keys) == len(set(keys))


# ---- Post offices, Common Service Centres, fire stations (post, csc, fire) ----
MODULES_C = ("civic_post_in", "civic_post_dir_in", "civic_post_s3waas", "civic_csc_kl", "civic_csc_s3waas", "civic_fire_ap",
           "civic_fire_tn", "civic_fire_py",
           "civic_fire_s3waas")


def check_c(recs, module, dept, layer, person=False):
    """depts.py record shape; a facility row may have only its office in "area" (the post office directory has no people)."""
    ids = [r for r, _ in recs]
    assert recs and len(ids) == len(set(ids)), "no records or duplicate ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:"), rid
        assert d["type"] == "dept_office" and d["dept"] == dept and d["layer"] == layer, d
        assert d.get("level") and d.get("source") and d.get("state") and d.get("area"), d
        if person:
            assert d.get("name") or d.get("phone") or d.get("email"), d
        for k in ("lat", "lon"):
            assert k not in d or isinstance(d[k], float), d


def by_id(recs):
    return dict(recs)


def test_seed_files_c():
    for m in MODULES_C:
        items = json.loads((ROOT / "seeds" / f"dept_{m}.json").read_text())
        keys = [i["key"] for i in items]
        assert items and len(keys) == len(set(keys)) and all(k.startswith(m) for k in keys), m
        for i in items:
            p = i["payload"]
            assert p["reader"] == m and p["url"].startswith("https://") and p["state"] and "india_only" in p, i
        assert items == mod(m).items(), f"seeds/dept_{m}.json is not what {m}.items() gives"


def test_post_in():
    m = mod("civic_post_in")
    items = m.items()
    assert len(items) == 83 and items[0]["payload"]["lo"] == 1 and items[-1]["payload"]["hi"] >= m.TOTAL
    url = items[6]["payload"]["url"]
    assert "objectid%3E%3D12001+AND+objectid%3C%3D14000" in url and "f=json" in url
    get = fake_get({url: "civic_post_in.json"})
    recs, files, why = m.fetch(items[6]["payload"], get)
    assert why == "" and len(recs) == 6 and files[0][0] == "depts/civic_post_in/objectid-012001.json.gz"
    check_c(recs, "civic_post_in", "postal", "post")
    d = by_id(recs)["dept:civic_post_in:605007-nallavadu-bo"]
    assert d["state"] == "PY" and d["post"] == "Branch Postmaster" and d["office_type"] == "BO" and d["pincode"] == "605007"
    assert d["division"] == "Pondicherry Division" and d["circle"] == "Tamilnadu Circle" and d["lat"] == 11.854554
    assert d["lon"] == 79.811464 and d["notes"] == "Near by SMP 1KM" and d["delivery"] == "Delivery"
    assert "name" not in d                                   # the directory names offices, never postmasters


def test_post_in_state_codes():
    c = mod("_civic")
    assert c.state_code("The Dadra And Nagar Haveli And Daman And Diu") == "DH"
    assert c.state_code("Jammu And Kashmir") == "JK" and c.state_code("Na") == "" and c.state_code("Tamil Nadu Circle") == "TN"
    assert c.lat("NA") is None and c.lat("0") is None and c.lon("79.81") == 79.81


def test_post_dir_in():
    m = mod("civic_post_dir_in")
    get = fake_get({m.URL: "civic_post_dir_in.html"})
    recs, files, why = m.fetch(m.items()[0]["payload"], get)
    assert why == "" and files[0][0] == "depts/civic_post_dir_in/directory.html.gz"
    check_c(recs, "civic_post_dir_in", "postal", "post", person=True)
    posts = {d["post"]: d for _, d in recs}
    assert len(recs) == 6 and not any("Postal Services Board" in d["circle"] for _, d in recs)   # directorate rows left out
    cpmg = by_id(recs)["dept:civic_post_dir_in:maharashtra-circle-chief-postmaster-general"]
    assert cpmg["name"] == "Shri Ramchandra Kisan Jayabhaye" and cpmg["phone"] == "022-22620049"
    assert cpmg["email"] == "cpmg_mah@indiapost.gov.in" and cpmg["state"] == "MH" and cpmg["level"] == "circle"
    goa = posts["Postmaster General, Goa Region, Panaji"]
    assert goa["state"] == "GA" and goa["level"] == "region" and goa.get("vacant") is True and "name" not in goa
    assert posts["Director Postal Services, Mizoram Dn, Aizawal"]["state"] == "MZ"
    assert posts["Post Master General, N.E.-I Region Agartala/ Aizawl"]["state"] == "TR"
    ne = by_id(recs)["dept:civic_post_dir_in:north-east-circle-chief-postmaster-general"]
    assert ne["state"] == "IN" and ne["circle"] == "North East Circle"           # a circle of seven states


def test_csc_kl():
    m = mod("civic_csc_kl")
    items = m.items()
    assert len(items) == m.PAGES and items[1]["payload"]["url"] == "https://akshaya.kerala.gov.in/centers/1"
    centre = "https://akshaya.kerala.gov.in/centers/3008/akshaya-kendram-19-th-mile-19-th-mile-kannur"
    get = fake_get({"https://akshaya.kerala.gov.in/centers/1": "civic_csc_kl_list.html", centre: "civic_csc_kl_centre.html"})
    recs, files, why = m.fetch(items[1]["payload"], get)
    assert why == "" and len(recs) == 2 and len(files) == 2          # the second centre page did not answer: list data only
    check_c(recs, "civic_csc_kl", "digital_services", "csc", person=True)
    a, b = by_id(recs)["dept:civic_csc_kl:KNR267"], by_id(recs)["dept:civic_csc_kl:KNR274"]
    assert a["name"] == "Sam Augusthy" and a["post"].startswith("Staff in Charge") and a["lat"] == 9.7903554
    assert a["phone"] == "9447918141, 9747265983" and a["email"] == "akshayakulamavu062@gmail.com, samaxn3@gmail.com"
    assert a["source"].startswith("https://akshaya.kerala.gov.in/centers/3008/") and a["district"] == "Kannur"
    assert b["area"] == "Ettikkulam" and b["phone"] == "6282044785" and "name" not in b and b["source"].endswith("/centers/1")


def test_csc_kl_joined_values():
    """Data-quality review 2026-11-11 (centre page 2352, saved copy): two mobiles and two emails that the site writes with no
    separator are split; a landline that lost its STD 0 gets it back; a good number stays as written."""
    m = mod("civic_csc_kl")
    d = m.detail((DATA / "civic_csc_kl_joined.html").read_text())
    assert d["phone"] == "9020277399, 9446680882" and d["staff_phone"] == ""                  # the staff phone "0" is no phone
    assert d["email"] == "sajnaboban@gmail.com, sajna_magfil@yahoo.co.in" and d["staff_email"] == "deepankuran1@gmail.com"
    c = {"id": "2352", "slug": "annoor", "url": "https://akshaya.kerala.gov.in/centers/2352/annoor", "code": "KNR217",
         "place": "Annoor", "district": "Kannur", "phone": m.fix_phones("90202773999446680882")}
    rid, r = m.record(c, d, "https://akshaya.kerala.gov.in/centers/1")
    assert r["phone"] == "9020277399, 9446680882" and r["email"].count("@") == 3
    assert m.fix_phones("4872998822") == "04872998822" and m.fix_phones("4962695307, 9645686986") == "04962695307, 9645686986"
    assert m.fix_phones("91427084179995773470") == "9142708417, 9995773470" and m.fix_phones("0478 2572067") == "0478 2572067"
    assert m.split_emails("preemano11koodali@gmail.comkoodalikn1091@gmail.com") == \
        "preemano11koodali@gmail.com koodalikn1091@gmail.com"
    assert m.split_emails("john.common@gmail.com") == "john.common@gmail.com"


def test_csc_kl_past_the_end():
    m = mod("civic_csc_kl")
    p = m.items()[79]["payload"]
    assert m.fetch(p, fake_get({p["url"]: "civic_csc_kl_empty.html"}))[0::2] == ([], "")
    assert m.fetch(p, fake_get({}))[2] == "no answer"


def test_fire_ap():
    m = mod("civic_fire_ap")
    items = m.items()
    assert len(items) == 28 and all(i["payload"]["india_only"] for i in items)
    get = fake_get({items[0]["payload"]["url"]: "civic_fire_ap_1.html"})
    recs, files, why = m.fetch(items[0]["payload"], get)
    assert why == "" and len(recs) == 4
    check_c(recs, "civic_fire_ap", "fire", "fire", person=True)
    d = by_id(recs)
    dfo = d["dept:civic_fire_ap:srikakulam:dfo"]
    assert dfo["name"] == "J Mohan Rao" and dfo["level"] == "district" and dfo["email"] == "dcfo.sklm@gmail.com"
    assert dfo["phone"] == "9949991052, 08942-224436"
    st = d["dept:civic_fire_ap:srikakulam:ichapuram"]
    assert st["name"] == "K. V. K. KASINATH" and st["post"] == "Station Fire Officer" and st["phone"] == "08947 231101, 8317587461"
    assert st["email"] == "sfo.ipm101@gmail.com" and st["lat"] == 19.1397672 and st["lon"] == 84.6978283
    op = d["dept:civic_fire_ap:srikakulam:fire-outpost-mandasa"]
    assert op["station_type"] == "outpost" and op["name"] == "B. Someswara Rao" and op["phone"] == "9963730662"


def test_fire_tn():
    m = mod("civic_fire_tn")
    items = m.items()
    assert len(items) == 8 and "thirdlvl_id=NDEx&" in items[0]["payload"]["url"]
    get = fake_get({items[0]["payload"]["url"]: "civic_fire_tn_north.html"})
    recs, files, why = m.fetch(items[0]["payload"], get)
    assert why == "" and len(recs) == 6 and files[0][0] == "depts/civic_fire_tn/NDEx.html.gz"
    check_c(recs, "civic_fire_tn", "fire", "fire", person=True)
    g = by_id(recs)["dept:civic_fire_tn:chennai-south:guindy"]
    assert g["area"] == "Guindy" and g["landline"] == "044-22502101" and g["cug"] == "9445086050" and g["tab"] == "7305096056"
    assert g["email"] == "guindyfire112@gmail.com" and g["last_updated"] == "2026-10-21" and g["region"] == "Northern Region"
    assert by_id(recs)["dept:civic_fire_tn:chennai-north:esplanade"]["district"] == "Chennai North"


def test_fire_py(monkeypatch):
    m = mod("civic_fire_py")
    text = (DATA / "civic_fire_py_p1.txt").read_text(encoding="utf-8")
    monkeypatch.setattr(m._esw, "pdf_pages", lambda content: [text])
    recs, files, why = m.fetch(m.items()[0]["payload"], lambda url, **k: type("R", (), {"content": b"%PDF-1.4"})())
    assert why == "" and len(recs) == 16 and files[0][0] == "depts/civic_fire_py/officers.pdf.gz"
    check_c(recs, "civic_fire_py", "fire", "fire", person=True)
    d = by_id(recs)
    assert d["dept:civic_fire_py:divisional-fire-officer"]["name"] == "K. Ilango"
    assert d["dept:civic_fire_py:divisional-fire-officer"]["level"] == "state"
    k = d["dept:civic_fire_py:karaikal"]
    assert k["name"] == "S. Manogaran" and k["post"] == "Station Officer (Additional Charge)" and k["district"] == "Karaikal"
    assert k["phone"] == "04368-230101, 04368-230112, 9894052099"
    y = d["dept:civic_fire_py:yanam"]
    assert y["name"] == "J. Meera Sahib" and y["post"] == "Officer in-charge" and y["phone"] == "0884-2321288, 09441462389"
    assert d["dept:civic_fire_py:d-nagar"]["area"] == "D’Nagar"


def test_post_s3waas():
    """Page 1 is a saved answer cut to 3 cards; page 2 is made from it (one card, no next link) to test the pager."""
    m = mod("civic_post_s3waas")
    seed = m.items()
    assert len(seed) > 300 and all(i["payload"]["state"] and i["payload"]["district"] for i in seed)
    url = "https://ashoknagar.nic.in/en/public-utility-category/post/"
    p = {"reader": "civic_post_s3waas", "url": url, "state": "MP", "district": "Ashoknagar", "max_pages": 30}
    get = fake_get({url: "civic_post_s3waas_p1.html", url + "page/2/": "civic_post_s3waas_p2.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 4 and len(files) == 2 and [c[1] for c in get.calls] == [url, url + "page/2/"]
    check_c(recs, "civic_post_s3waas", "postal", "post", person=True)
    ho = by_id(recs)["dept:civic_post_s3waas:ashoknagar.nic.in:473331-ashoknagar-ho"]
    assert ho["post"] == "Postmaster" and ho["office_type"] == "HO" and ho["phone"] == "8770099340"
    assert ho["last_updated"] == "2026-11-10" and ho["district"] == "Ashoknagar"
    so = by_id(recs)["dept:civic_post_s3waas:ashoknagar.nic.in:473335-isagarh-so"]
    assert so["post"] == "Sub Postmaster" and so["source"] == url + "page/2/"
    assert m.post_of("Greamspet Post Office") == (None, "Postmaster") and m.post_of("Nallavadu B.O")[0] == "BO"


def test_csc_s3waas():
    m = mod("civic_csc_s3waas")
    seed = m.items()
    assert len(seed) >= 30 and all(i["payload"]["state"] for i in seed)
    assert sum(i["payload"]["operator_first"] for i in seed) >= 4
    url = "https://kaithal.gov.in/public-utility-category/atal-seva-kendra-rural/"
    p = {"reader": "civic_csc_s3waas", "url": url, "state": "HR", "district": "Kaithal", "operator_first": True,
         "centre_type": "Atal Seva Kendra"}
    recs, files, why = m.fetch(p, fake_get({url: "civic_csc_s3waas_kaithal.html"}))
    assert why == "" and len(recs) == 3 and len(files) == 1
    check_c(recs, "civic_csc_s3waas", "digital_services", "csc", person=True)
    names = [d.get("name") for _, d in recs]
    assert names == ["Hira Lal", "Amit Kumar", "Subhash Sharma"]                 # "S/O Sadhu Ram ..." is cut
    d = by_id(recs)["dept:civic_csc_s3waas:kaithal.gov.in:atal-seva-kendra-rural:atal-seva-kendra-ram-nagar-guhla"]
    assert d["email"] == "lalh1090@gmail.com" and d["post"] == "Operator" and d["centre_type"] == "Atal Seva Kendra"
    assert m.operator("Village Andali, Siwan") == "" and m.operator("Panchayat Office, Bhuna Road") == ""
    p2 = dict(p, operator_first=False)
    assert all("name" not in d for _, d in m.fetch(p2, fake_get({url: "civic_csc_s3waas_kaithal.html"}))[0])


def test_fire_s3waas():
    m = mod("civic_fire_s3waas")
    assert len(m.items()) == 11
    url = "https://jalpaiguri.gov.in/public-utility-category/fire-station/"
    p = {"reader": "civic_fire_s3waas", "url": url, "state": "WB", "district": "Jalpaiguri"}
    recs, files, why = m.fetch(p, fake_get({url: "civic_fire_s3waas_jalpaiguri.html"}))
    assert why == "" and len(recs) == 2
    check_c(recs, "civic_fire_s3waas", "fire", "fire", person=True)
    d = by_id(recs)["dept:civic_fire_s3waas:jalpaiguri.gov.in:dhupguri-f-s"]
    assert d["phone"] == "03563-250001, 8584027273, 8584027274" and d["pincode"] == "735210"   # PIN in the address is not a phone


# ---- Health facilities, urban clinics, anganwadi centres (health, clinic, anganwadi) ----
MODULES_D = ("civic_health_in", "civic_health_dl", "civic_health_py", "civic_clinic_mumbai", "civic_anganwadi_kl")


def check_facilities(recs, module, dept, layer):
    """depts.py record rules for facility rows: id prefix, type, dept, level facility, a layer, a state, a source, a place name;
    facility rows may have no person (the source names nobody), so area stands in for name/phone/email."""
    ids = [r for r, _ in recs]
    assert ids and len(ids) == len(set(ids)), "no rows or duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:"), rid
        assert d["type"] == "dept_office" and d["dept"] == dept and d["level"] == "facility" and d["layer"] == layer, d
        assert d.get("state") and d.get("source") and d.get("post") and (d.get("area") or d.get("name")), d


def seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


@pytest.mark.parametrize("module", MODULES_D)
def test_seed_files_d(module):
    items = seed(module)
    keys = [i["key"] for i in items]
    assert items and len(keys) == len(set(keys))
    for i in items:
        p = i["payload"]
        assert i["key"].startswith(module) and len(i["key"]) <= 200
        assert p["reader"] == module and p.get("url") and p.get("state"), i
        assert hasattr(mod(module), "fetch")


def test_health_in():
    m = mod("civic_health_in")
    recs = m.parse(json.loads((DATA / "civic_health_in.json").read_text()))
    check_facilities(recs, "civic_health_in", "health", "health")
    d = dict(recs)
    a = d["dept:civic_health_in:hd-1"]
    assert a["area"] == "THIRUPATHUR UPHC" and a["facility_type"] == "Primary Health Centre" and a["state"] == "TN"
    assert a["pin"] == "635601" and a["lat"] == 12.492635 and a["lon"] == 78.564177 and a["district"] == "Vellore"
    b = d["dept:civic_health_in:hd-2"]
    assert b["phone"] == "04341-222043" and b["facility_type"] == "Sub-District Hospital"
    # second layer: Health Centers in India (point geometry, location type)
    c = dict(m.parse(json.loads((DATA / "civic_health_in_centres.json").read_text()), layer="centres"))
    k = c["dept:civic_health_in:hc-1"]
    assert k["area"] == "Kavuru CPT" and k["facility_type"] == "PHC" and k["location_type"] == "Rural" and k["state"] == "AP"
    assert k["lat"] == 16.039086 and k["lon"] == 80.657662 and "address" not in k                  # "NA" is left out
    check_facilities(list(c.items()), "civic_health_in", "health", "health")
    # seed: 2,000-row objectid ranges that cover both layers (165,111 and 199,604 rows on 2026-11-11)
    items = seed("civic_health_in")
    hd = [i for i in items if i["payload"]["layer"] == "directory"]
    hc = [i for i in items if i["payload"]["layer"] == "centres"]
    assert hd[0]["payload"]["lo"] == 1 and hd[-1]["payload"]["hi"] > 165111 and hc[-1]["payload"]["hi"] > 199604
    assert "objectid+%3E%3D+1+AND+objectid+%3C+2001" in hd[0]["payload"]["url"] and "outSR=4326" in hc[0]["payload"]["url"]
    got, files, why = m.fetch(hd[0]["payload"], fake_get({hd[0]["payload"]["url"]: "civic_health_in.json"}))
    assert len(got) == 3 and not why and files[0][0] == "depts/civic_health_in/hd-000001.json.gz"
    got, _, why = m.fetch(hc[0]["payload"], fake_get({hc[0]["payload"]["url"]: "civic_health_in_centres.json"}))
    assert len(got) == 3 and not why and got[0][0] == "dept:civic_health_in:hc-1"

    def stats(u, method, data):
        return "outStatistics" in u
    its = m.items(fake_get({stats: "civic_health_in_max.json"}))                        # both layers answer max 165111 here
    assert len(its) == 166 and its[82]["payload"]["lo"] == 164001 and its[83]["payload"]["layer"] == "centres"


def test_health_in_faults():
    """Data-quality review 2026-11-11: the landline column lost the leading STD 0 ("2184254444"); PINs and 0-only numbers are no
    phone; the post is the facility type the source gives (it named every facility "Medical Officer" before)."""
    m = mod("civic_health_in")
    d = dict(m.parse(json.loads((DATA / "civic_health_in_faults.json").read_text())))
    check_facilities(list(d.items()), "civic_health_in", "health", "health")
    ph = {k.rsplit("-", 1)[1]: v.get("phone") for k, v in d.items()}
    assert ph["8093"] == "02184254444" and ph["160313"] == "05315-245188" and ph["37227"] == "04371 291191"
    assert ph["160826"] == "03325000000" and ph["4031"] == "02483-231497"            # "91" + number; a good number stays as is
    assert ph["4134"] is None and ph["8927"] is None and ph["4043"] is None          # 07263-000000, the PIN 735228, "0"
    post = {k.rsplit("-", 1)[1]: v["post"] for k, v in d.items()}
    assert post["8093"] == "Primary health centre" and post["4043"] == "Health sub centre"
    assert post["4031"] == "Community health centre" and post["5167"] == "Health facility"
    assert "Medical Officer" not in post.values()
    assert m.post_of("Sub-District Hospital") == "Sub-District Hospital" and m.post_of("PHC") == "Primary health centre"
    assert m.post_of("Sub Centre") == "Health sub centre" and m.post_of("") == "Health facility"


def test_health_dl(monkeypatch):
    m = mod("civic_health_dl")
    pages = (DATA / "civic_health_dl_layout.txt").read_text().split("\f")
    recs = m.parse(pages)
    check_facilities(recs, "civic_health_dl", "health", "health")
    d = dict(recs)
    a = d["dept:civic_health_dl:DL-shahdara-1"]
    assert a["area"] == "DGD Karkardooma" and a["phone"] == "22371280" and a["ac"] == 59 and a["ac_name"] == "Vishwas Nagar"
    assert a["address"] == "Opp. Saini Enclave LSC, Karkardooma, Delhi- 92. (12 Hours Double Shift)"
    assert a["opened"] == "14.03.2002" and a["building"] == "DHS" and a["facility_type"] == "Dispensary (DGD)"
    c = d["dept:civic_health_dl:DL-shahdara-3"]
    assert c["phone"] == "22301945" and c["building"] == "Non-DHS (Govt.)"            # "22301945 extn." + "3030"
    s = d["dept:civic_health_dl:DL-new-delhi-13"]
    assert s["facility_type"] == "Seed PUHC" and s["ac"] == 36
    r = d["dept:civic_health_dl:DL-central-25"]                                         # no assembly columns on this row
    assert r["area"] == "DGD Rouse Avenue" and "ac" not in r and r["opened"] == "Under Process"
    assert r["address"] == "Rouse Avenue Court, New Delhi-110002"
    monkeypatch.setattr(m._esw, "pdf_pages", lambda content: pages)
    p = seed("civic_health_dl")[0]["payload"]
    got, files, why = m.fetch(p, fake_get({p["url"]: "civic_health_dl_layout.txt"}))
    assert len(got) == len(recs) and not why


def test_clinic_mumbai(monkeypatch):
    m = mod("civic_clinic_mumbai")
    pages = (DATA / "civic_clinic_mumbai_layout.txt").read_text().split("\f")
    recs = m.parse(pages)
    check_facilities(recs, "civic_clinic_mumbai", "health", "clinic")
    d = dict(recs)
    one = d["dept:civic_clinic_mumbai:MCGM-HBT-1"]
    assert one["area"] == "Shanti Nagar HBT Clinic" and one["ward"] == "FN" and one["pin"] == "400037"
    assert one["address"].startswith("Balkrishna Mitra mandal ground") and one["address"].endswith("Hill,Mumbai-400037.")
    assert one["facility_type"] == "HBT clinic (porta cabin)" and "7:00am to 2:00pm" in one["timing"]
    two = d["dept:civic_clinic_mumbai:MCGM-HBT-2"]
    assert two["ward_printed"] is False and "ward" not in two                         # merged ward cell: not on this row
    r = d["dept:civic_clinic_mumbai:MCGM-HBT-104"]
    assert r["area"] == "Sai Sundar Nagar SRA Building" and r["ward"] == "GS" and r["zone"] == "II"
    assert r["facility_type"] == "HBT clinic (ready structure)"
    assert d["dept:civic_clinic_mumbai:MCGM-HBT-103"]["area"] == "Matunga Labour Camp(Jasmin Mill Road)"
    assert d["dept:civic_clinic_mumbai:MCGM-HBT-107"]["address"] == "Opposite Boomerang,Saki Vihar road,Kurla West Mumbai 400072"
    monkeypatch.setattr(m._esw, "pdf_pages", lambda content: pages)
    p = seed("civic_clinic_mumbai")[0]["payload"]
    got, _, why = m.fetch(p, fake_get({p["url"]: "civic_clinic_mumbai_layout.txt"}))
    assert len(got) == len(recs) and not why


def test_anganwadi_kl():
    m = mod("civic_anganwadi_kl")
    url = "https://adimalypanchayat.lsgkerala.gov.in/en/page/anganwady-details"
    recs = m.parse((DATA / "civic_anganwadi_kl.html").read_text(), url)
    check_facilities(recs, "civic_anganwadi_kl", "women_child", "anganwadi")
    assert all(r.get("name") and r.get("phone") for _, r in recs)
    d = dict(recs)
    a = d["dept:civic_anganwadi_kl:adimalypanchayat-w-53"]
    assert a["name"] == "Shyamala V T" and a["phone"] == "9645606554" and a["area"] == "Deviyar"
    assert a["ward_no"] == "22" and a["ward_name"] == "Deviyar" and a["body"] == "Adimaly Grama Panchayat"
    z = d["dept:civic_anganwadi_kl:adimalypanchayat-w-110"]
    assert z["name"] == "Deepa R" and z["ward_name"] == "Thalamali" and z["ward_no"] == "9"
    assert len(recs) == 7
    items = seed("civic_anganwadi_kl")
    p = next(i["payload"] for i in items if i["payload"]["url"] == url)
    got, files, why = m.fetch(p, fake_get({url: "civic_anganwadi_kl.html"}))
    assert len(got) == 7 and not why and files[0][0] == "depts/civic_anganwadi_kl/adimalypanchayat.html.gz"
    # a body without the page (404: get() answers None)
    q = next(i["payload"] for i in items if "kochicorporation" in i["payload"]["url"])
    assert q["local_body_code"] == "252220" and m.fetch(q, fake_get({}))[2] == "no page"
    assert sum(i["payload"].get("body_type") == "urban" for i in items) == 93


def test_health_py(monkeypatch):
    m = mod("civic_health_py")
    pages = (DATA / "civic_health_py_layout.txt").read_text().split("\f")
    recs = m.parse(pages)
    check_facilities(recs, "civic_health_py", "health", "health")
    assert all(d.get("name") and d.get("post") for _, d in recs)
    d = dict(recs)
    two = d["dept:civic_health_py:PY-puducherry-2"]
    assert two["name"] == "Sagayamari K" and two["post"] == "State Accountant" and two["area"] == "PSHS Office"   # gap in the name
    assert two["joined"] == "10/7/2002" and two["facility_type"] == "office"
    mo = d["dept:civic_health_py:PY-puducherry-324"]
    assert mo["name"] == "Vasantharaj A" and mo["post"] == "Medical Officer (HWC)" and mo["area"] == "Lingareddipalayam"
    assert mo["facility_type"] == "HWC"
    wrap = d["dept:civic_health_py:PY-puducherry-468"]                                 # name and place go on the next line
    assert wrap["name"] == "M. Punguzhali" and wrap["area"] == "PHC Nettapakkam/Karayamputhur/Maducarai"
    k = d["dept:civic_health_py:PY-karaikal-1"]
    assert k["district"] == "Karaikal" and k["name"] == "K. Sundravadivelu Deivasigamani" and k["post"] == "Lab. Technician"
    assert d["dept:civic_health_py:PY-mahe-1"]["joined"] == "17-Nov-04" and d["dept:civic_health_py:PY-mahe-1"]["area"] == "G.G.H.MAHE"
    monkeypatch.setattr(m._esw, "pdf_pages", lambda content: pages)
    p = seed("civic_health_py")[0]["payload"]
    got, _, why = m.fetch(p, fake_get({p["url"]: "civic_health_py_layout.txt"}))
    assert len(got) == len(recs) == 12 and not why
