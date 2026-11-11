"""Offline tests of the fair price shop readers dforms/civic_fps2_<xx>.py (states not in dforms/civic_fps_*.py) on small saved
answers in tests/data/fps2/ (saved 2026-11-11; files named *_shape.* are written by hand in the shape the page script reads).
No test touches the network."""
import json

from esw_common import DATA, ROOT, Answer, check_records, fake_get, mod  # noqa: F401


# ---- SMART-PDS: UP, OD, WB, MN, ML ----
EAST = {"up": ("UP", "https://smartpds.up.gov.in", 75), "od": ("OD", "https://smartpds.odisha.gov.in", 30),
        "wb": ("WB", "https://smartpds.wb.gov.in", 29), "mn": ("MN", "https://epos.mn.gov.in", 18),
        "ml": ("ML", "https://epos.megfcsca.gov.in", 1)}


def _routes(xx, fps=None):
    r = {("POST", f"{EAST[xx][1]}/Epos_Spring/api/fpsdevicemapping/device"): f"fps2/fps2_{xx}_device.json",
         lambda u, me, d: "getSearchDetailsBlock" in u: f"fps2/fps2_{xx}_blocks.json"}
    if fps:
        r[lambda u, me, d: "getSearchDetailsFps" in u] = fps
    return r


def _fetch(xx, code, district, routes=None):
    m = mod(f"civic_fps2_{xx}")
    get = fake_get(routes or _routes(xx))
    recs, files, why = m.fetch({"reader": f"civic_fps2_{xx}", "url": m.BASE, "state": m.STATE, "dist_code": code,
                                "district": district}, get)
    check_records(recs, f"civic_fps2_{xx}", "food_supplies")
    return dict(recs), files, why, get


def test_fps2_modules():
    for xx, (state, base, _) in EAST.items():
        m = mod(f"civic_fps2_{xx}")
        assert m.MODULE == f"civic_fps2_{xx}" and m.STATE == state and m.BASE == base and m.INDIA_ONLY is False


def test_fps2_manipur_nominee_phones():
    """Manipur, Imphal West: the dealer mobile is masked (no phone); both nominee mobiles are kept in full."""
    d, files, why, get = _fetch("mn", "1277", "Imphal West")
    assert why == "" and len(files) == 2 and len(d) == 3
    r = d["dept:civic_fps2_mn:127700100163"]
    assert r["name"] == "Nongthombam Kesho Singh" and r["post"] == "FPS dealer" and r["layer"] == "fps" and r["level"] == "facility"
    assert r["state"] == "MN" and r["district"] == "Imphal West" and r["fps_id"] == "127700100163" and "phone" not in r
    assert r["nominee_1"] == "Manbahadur thapa" and r["nominee_1_phone"] == "9612967958"
    assert r["nominee_2"] == "Irom Indira Devi" and r["nominee_2_phone"] == "8974048310"
    assert r["source"] == "https://epos.mn.gov.in/FPS_Device_Mapping"
    # one device POST, one block list, one Search call per supply office (4 subdivisions)
    assert [c[0] for c in get.calls].count("POST") == 1 and sum("getSearchDetailsFps" in c[1] for c in get.calls) == 4


def test_fps2_manipur_office_join():
    """A Search answer of a supply office gives the shop its area (block). fps2_mn_search_shape.json is written by hand in the
    shape of the Search answer ([{fps_id, ownername}], as in civic_fps_mz_fps.json): no Manipur Search answer was saved."""
    routes = _routes("mn")
    routes = {(lambda u, me, d: "getSearchDetailsFps" in u and "office_code=1277002" in u): "fps2/fps2_mn_search_shape.json",
              **routes}
    d, _, _, _ = _fetch("mn", "1277", "Imphal West", routes)
    r = d["dept:civic_fps2_mn:127700100164"]
    assert r["area"] == "Subdivn Lamphel" and r["block"] == "Subdivn Lamphel" and r["afso_code"] == "1277002"
    assert d["dept:civic_fps2_mn:127700100163"]["area"] == "Imphal West" and "block" not in d["dept:civic_fps2_mn:127700100163"]


def test_fps2_odisha_panchayat_shops():
    """Odisha, Boudh: gram panchayat shops (dealer = the panchayat officer); 'XXXXX-XNA' and 'NA' values give nothing."""
    d, _, why, _ = _fetch("od", "349", "BOUDH")
    assert why == "" and len(d) == 4
    r = d["dept:civic_fps2_od:0601G005"]
    assert r["name"] == "PEO SAGADA G.P." and r["district"] == "BOUDH" and "phone" not in r
    assert r["nominee_1"] == "BIDYADHAR MAHAKUL" and r["nominee_1_phone"] == "9778856465"
    assert "nominee_2" not in r and "nominee_2_phone" not in r
    r = d["dept:civic_fps2_od:0602G002"]
    assert r["nominee_2"] == "Srimanta Pradhan" and r["nominee_2_phone"] == "8456024769"
    r = d["dept:civic_fps2_od:0601G092"]
    assert r["name"] == "PEO KHALIAPALI" and not any(k.startswith("nominee") for k in r)


def test_fps2_west_bengal():
    """West Bengal, Kalimpong: a shop without nominees; a shop whose two nominees share one mobile (kept as given)."""
    d, _, why, _ = _fetch("wb", "222", "KALIMPONG")
    assert why == "" and len(d) == 4
    r = d["dept:civic_fps2_wb:132708700001"]
    assert r["name"] == "Rama Sankar Prasad" and r["state"] == "WB" and not any(k.startswith("nominee") for k in r)
    r = d["dept:civic_fps2_wb:132708700013"]
    assert r["nominee_1_phone"] == r["nominee_2_phone"] == "9547270700"


def test_fps2_uttar_pradesh():
    d, _, why, _ = _fetch("up", "181", "Shrawasti")
    assert why == "" and len(d) == 3
    r = d["dept:civic_fps2_up:10510012"]
    assert r["name"] == "Rajendra" and r["district"] == "Shrawasti" and r["state"] == "UP" and "phone" not in r
    assert r["nominee_1"] == "shashank gupta" and r["nominee_1_phone"] == "9170646251" and r["dist_code"] == "181"


def test_fps2_meghalaya_wiring():
    """Meghalaya: no saved answer yet (expired certificate). The same SMART-PDS answer at the Meghalaya host gives ML records;
    without a district list (every request fails) the reader says so."""
    m = mod("civic_fps2_ml")
    get = fake_get({("POST", f"{m.BASE}/Epos_Spring/api/fpsdevicemapping/device"): "fps2/fps2_mn_device.json"})
    recs, _, why = m.fetch({"reader": "civic_fps2_ml", "url": m.BASE, "state": "ML", "dist_code": "1277"}, get)
    check_records(recs, "civic_fps2_ml", "food_supplies")
    assert why == "" and len(recs) == 3 and all(r["state"] == "ML" for _, r in recs)
    assert m.fetch({"reader": "civic_fps2_ml", "url": m.BASE, "state": "ML"}, fake_get({})) == ([], [], "no district list")
    its = m.items(fake_get({}))
    assert len(its) == 1 and "dist_code" not in its[0]["payload"]


def test_fps2_items_from_district_lists():
    for xx in ("up", "od", "wb", "mn"):
        m = mod(f"civic_fps2_{xx}")
        its = m.items(fake_get({lambda u, me, d: "getSearchDetailsDistrict" in u: f"fps2/fps2_{xx}_districts.json"}))
        assert len(its) == EAST[xx][2] and all(i["payload"]["url"] == m.BASE and i["payload"]["dist_code"] for i in its)


def test_fps2_seeds_east():
    every = []
    for xx, (state, base, n) in EAST.items():
        seeds = json.loads((ROOT / "seeds" / f"dept_civic_fps2_{xx}.json").read_text())
        assert len(seeds) == n, xx
        for i in seeds:
            p = i["payload"]
            assert i["key"].startswith(f"civic_fps2_{xx}-") and p["reader"] == f"civic_fps2_{xx}" and p["url"] == base
            assert p["state"] == state and "india_only" not in p
            every.append(i["key"])
    assert len(every) == len(set(every)) == 153


# ---- Gujarat (ipds FPS dealer list) and Rajasthan (food.rajasthan FPS contact list) ----

GJ_PAGE = "https://ipds.gujarat.gov.in/FpsSale/frm_stateFPS.aspx"
RJ_PAGE = "https://food.rajasthan.gov.in/FairPriceShop.aspx"


def test_fps2_gj_all_rows():
    """Gujarat: the GET's own hidden fields go back with ddlTopRows=0 (ALL); dealer names stay in Gujarati; districts get the English
    name from the site's district list; no phone."""
    m = mod("civic_fps2_gj")
    get = fake_get({("GET", GJ_PAGE): "fps2/fps2_gj_page.html", ("POST", GJ_PAGE): "fps2/fps2_gj_all.html"})
    recs, files, why = m.fetch({"reader": "civic_fps2_gj", "url": GJ_PAGE, "state": "GJ", "india_only": True}, get)
    assert why == "" and len(files) == 1 and files[0][0] == "depts/civic_fps2_gj/dealer-list.html.gz"
    check_records(recs, "civic_fps2_gj", "food_supplies")
    posts = [c for c in get.calls if c[0] == "POST"]
    assert len(posts) == 1 and posts[0][2]["ddlTopRows"] == "0" and posts[0][2]["__EVENTTARGET"] == "ddlTopRows"
    assert posts[0][2]["__VIEWSTATE"].endswith("TRIM")          # the page's own (trimmed) ViewState went back
    d = dict(recs)
    assert len(recs) == 4
    r = d["dept:civic_fps2_gj:2"]
    assert r["name"] == "ઠકકર પિયુષકુમાર મહેન્દ્રભાઈ" and r["post"] == "FPS dealer" and r["layer"] == "fps"
    assert r["district"] == "Kachchh" and r["district_regional"] == "કચ્છ" and r["block"] == "લખપત" and r["village"] == "સીયોત"
    assert r["fps_id"] == "2" and r["status"] == "ACTIVE" and "phone" not in r and "lat" not in r
    assert d["dept:civic_fps2_gj:24130"]["district"] == "Devbhumi Dwarka"


def test_fps2_gj_first_page_and_city():
    """The plain GET already shows 5 rows (3 kept in the sample) in the same table; Ahmedabad City maps to district Ahmedabad."""
    m = mod("civic_fps2_gj")
    recs = m.parse((DATA / "fps2" / "fps2_gj_page.html").read_text())
    assert [r for r, _ in recs] == ["dept:civic_fps2_gj:2", "dept:civic_fps2_gj:4", "dept:civic_fps2_gj:6"]
    row = ('<table><tr class="dg_Item"><td>1</td><td>9001</td><td>પટેલ રમેશભાઈ</td><td>અમદાવાદ શહર</td><td>મણિનગર ઝોન</td>'
           '<td>મણિનગર</td><td>ACTIVE</td></tr></table>')
    (rid, r), = m.parse(row)
    assert rid == "dept:civic_fps2_gj:9001" and r["district"] == "Ahmedabad" and r["supply_district"] == "Ahmedabad City"


def test_fps2_gj_no_form():
    m = mod("civic_fps2_gj")
    assert m.fetch({"url": GJ_PAGE}, lambda *a, **k: None) == ([], [], "no page")
    get = lambda url, method="GET", data=None, headers=None: Answer(b"<html><body>Down</body></html>", url)  # noqa: E731
    assert m.fetch({"url": GJ_PAGE}, get)[2] == "no form on the page"


def test_fps2_rj_district():
    """Rajasthan, Kota: GET, then the page's hidden fields with the district and the Search button; dealer name in English with the
    Hindi as name_regional; the full mobile; '0' gives no phone; rural rows keep panchayat and block, urban rows the municipality."""
    m = mod("civic_fps2_rj")
    get = fake_get({("GET", RJ_PAGE): "fps2/fps2_rj_page.html", ("POST", RJ_PAGE): "fps2/fps2_rj_kota.html"})
    recs, files, why = m.fetch({"reader": "civic_fps2_rj", "url": RJ_PAGE, "state": "RJ", "india_only": True, "dist_code": "127",
                                "district": "Kota", "district_regional": "कोटा"}, get)
    assert why == "" and len(files) == 1 and files[0][0] == "depts/civic_fps2_rj/district-127.html.gz"
    check_records(recs, "civic_fps2_rj", "food_supplies")
    (_, _, form), = [c for c in get.calls if c[0] == "POST"]
    assert form["ctl00$ContentPlaceHolder1$ddl_All_District"] == "127" and form["ctl00$ContentPlaceHolder1$txt_Search"] == "Search"
    assert "__EVENTTARGET" not in form or not form["__EVENTTARGET"]
    d = dict(recs)
    assert len(recs) == 6
    r = d["dept:civic_fps2_rj:6762"]
    assert r["name"] == "HEMRAJ BAIRWA" and r["name_regional"] == "हेमराज बैरवा" and r["phone"] == "9784270802"
    assert r["district"] == "Kota" and r["panchayat"] == "ख्यावदा" and r["block"] == "इटावा" and r["subdistrict"] == "पीपल्दा"
    assert r["area"] == "ख्यावदा" and r["area_type"] == "rural" and r["post"] == "FPS dealer" and r["fps_id"] == "6762"
    assert d["dept:civic_fps2_rj:6763"]["shop_name"] == "Vishnu Prasad Kushwaha"     # shop name can differ from the dealer
    u = d["dept:civic_fps2_rj:1470"]
    assert u["area_type"] == "urban" and u["municipality"] == "कोटा" and u["block"] == "कोटा" and u["phone"] == "9413514021"
    assert "phone" not in d["dept:civic_fps2_rj:9702"]                              # contact number "0"


def test_fps2_rj_districts():
    m = mod("civic_fps2_rj")
    ds = m.districts((DATA / "fps2" / "fps2_rj_page.html").read_text())
    assert len(ds) == 41 and ("127", "कोटा") in ds and ("099", "गंगानगर") in ds
    get = fake_get({("GET", RJ_PAGE): "fps2/fps2_rj_page.html"})
    its = m.items(get)
    assert len(its) == 41 and its[0]["key"] == "civic_fps2_rj-119" and its[0]["payload"]["india_only"] is True


def test_fps2_seeds_south():
    """Seed files: keys start with civic_fps2_<xx>-, are unique, and name an existing reader."""
    every = []
    for xx, n in (("gj", 1), ("rj", 41)):
        items = json.loads((ROOT / "seeds" / f"dept_civic_fps2_{xx}.json").read_text())
        assert len(items) == n
        for i in items:
            p = i["payload"]
            assert i["key"].startswith(f"civic_fps2_{xx}-") and p["reader"] == f"civic_fps2_{xx}" and p["url"] and p["state"] == xx.upper()
            assert p["india_only"] is True and hasattr(mod(p["reader"]), "fetch")
            every.append(i["key"])
    assert len(every) == len(set(every))
    rj = json.loads((ROOT / "seeds" / "dept_civic_fps2_rj.json").read_text())
    assert {"dist_code": "127", "district": "Kota"}.items() <= rj[[i["payload"]["dist_code"] for i in rj].index("127")]["payload"].items()


# ---- SMART-PDS hosts found for HP, PY, TG, AN, LD (and TN, not reachable yet) ----
SP = {"hp": ("HP", "https://smartpds.hp.gov.in", 12), "py": ("PY", "https://smartpds.py.gov.in", 4),
      "tg": ("TG", "https://smartpds.telangana.gov.in", 33), "an": ("AN", "https://epos.andamannicobar.gov.in", 3),
      "ld": ("LD", "https://epos.utl.gov.in", 1), "tn": ("TN", "https://smartpds.tn.gov.in", 1)}


def _sp(xx, code, district=""):
    m = mod(f"civic_fps2_{xx}")
    get = fake_get({("POST", f"{m.BASE}/Epos_Spring/api/fpsdevicemapping/device"): f"fps2/fps2_{xx}_device.json"})
    recs, files, why = m.fetch({"reader": m.MODULE, "url": m.BASE, "state": m.STATE, "dist_code": code, "district": district}, get)
    check_records(recs, m.MODULE, "food_supplies")
    assert why == "" and files[0][0] == f"depts/{m.MODULE}/device-{code}.json.gz"
    return dict(recs)


def test_fps2_lakshadweep_dealer_mobiles():
    """Lakshadweep gives the dealer mobile in full and both nominee mobiles; the vendor test shop 123456789121 is left out."""
    d = _sp("ld", "587", "Lakshadweep")
    assert len(d) == 3 and "dept:civic_fps2_ld:123456789121" not in d
    r = d["dept:civic_fps2_ld:158700100001"]
    assert (r["name"], r["phone"], r["post"]) == ("SALEEMA PM", "9497774780", "FPS dealer")
    assert (r["nominee_1"], r["nominee_1_phone"], r["nominee_2"], r["nominee_2_phone"]) == ("RASHEEDA", "8078511145", "SAFIULLA PK", "9495842050")
    assert r["state"] == "LD" and r["district"] == "Lakshadweep" and r["area"] == "Lakshadweep"


def test_fps2_telangana_nominee_shop():
    """Telangana, Hyderabad: masked dealer mobile (no phone), nominee mobiles in full; a shop with dealer 'NA' names nominee 1."""
    d = _sp("tg", "536", "Hyderabad")
    assert len(d) == 3
    r = d["dept:civic_fps2_tg:1671101"]
    assert r["name"] == "Gadepaga Balakrishna" and "phone" not in r and r["nominee_1_phone"] == "9393166934" and r["state"] == "TG"
    r = d["dept:civic_fps2_tg:1671105"]
    assert (r["name"], r["post"], r["nominee_1_phone"]) == ("Mirayala Srinivasulu", "FPS nominee", "9395309770")


def test_fps2_hp_ids_carry_district():
    """HP shop numbers are short; the record id carries the district code. 'NA' nominees give no nominee fields."""
    d = _sp("hp", "034", "KINNAUR")
    assert sorted(d) == ["dept:civic_fps2_hp:034-2411", "dept:civic_fps2_hp:034-2412", "dept:civic_fps2_hp:034-2416"]
    r = d["dept:civic_fps2_hp:034-2411"]
    assert r["name"] == "BHADUR SINGH" and r["district"] == "KINNAUR" and r["fps_id"] == "2411" and "phone" not in r
    assert not any(k.startswith("nominee") for k in r)


def test_fps2_py_an():
    d = _sp("py", "636", "Mahe")
    r = d["dept:civic_fps2_py:100300000001"]
    assert (r["name"], r["nominee_1"], r["nominee_1_phone"], r["state"]) == ("RIGNA K P", "SINIMOL P", "9946495992", "PY")
    d = _sp("an", "638", "Nicobar")
    r = d["dept:civic_fps2_an:638591600128"]
    assert r["name"] == "Miss. Olive" and "phone" not in r and r["state"] == "AN" and r["district"] == "Nicobar"


def test_fps2_sp_items_and_tn():
    for xx in ("hp", "py", "tg", "an", "ld"):
        m = mod(f"civic_fps2_{xx}")
        its = m.items(fake_get({lambda u, me, d: "getSearchDetailsDistrict" in u: f"fps2/fps2_{xx}_districts.json"}))
        assert len(its) == SP[xx][2] and all(i["payload"]["dist_code"] and i["payload"]["url"] == m.BASE for i in its)
    m = mod("civic_fps2_tn")                                   # host not reachable: the same SMART-PDS answer gives TN records
    get = fake_get({("POST", f"{m.BASE}/Epos_Spring/api/fpsdevicemapping/device"): "fps2/fps2_py_device.json"})
    recs, _, why = m.fetch({"reader": m.MODULE, "url": m.BASE, "state": "TN", "dist_code": "1"}, get)
    assert why == "" and recs and all(r["state"] == "TN" for _, r in recs) and m.INDIA_ONLY is True
    assert m.fetch({"url": m.BASE}, fake_get({})) == ([], [], "no district list")


# ---- Punjab (epos.punjab.gov.in FPS Details report) ----
PB = "https://epos.punjab.gov.in"


def test_fps2_pb_district():
    """Kapurthala: the office list gives Dhilwan and Fattu Dhinga; each office's shop list gives the owners (masked mobiles: no phone)."""
    m = mod("civic_fps2_pb")
    get = fake_get({("POST", f"{PB}/afso_fps_details.action"): "fps2/fps2_pb_afso.html",
                    ("POST", f"{PB}/fps_aso_details.action"): "fps2/fps2_pb_fps.html"})
    recs, files, why = m.fetch({"reader": m.MODULE, "url": PB, "state": "PB", "dist_code": "036", "district": "Kapurthala"}, get)
    check_records(recs, m.MODULE, "food_supplies")
    assert why == "" and len(files) == 3 and files[0][0] == "depts/civic_fps2_pb/afso-036.html.gz"
    offices = [c[2]["office_code"] for c in get.calls if c[1].endswith("fps_aso_details.action")]
    assert offices == ["1036001", "1036002"]
    d = dict(recs)                                             # the same saved shop list answers both offices
    assert len(d) == 4
    r = d["dept:civic_fps2_pb:103600100003"]
    assert r["name"] == "Gurwinderjit singh" and r["name_source"] == "Gurwinderjit_singh" and "phone" not in r
    assert r["district"] == "Kapurthala" and r["block"] == "Dhilwan" and r["afso_code"] == "1036001" and r["total_cards"] == 668
    assert "terminal_id" not in r and "terminal_id" not in d["dept:civic_fps2_pb:103600100001"]


def test_fps2_pb_items():
    m = mod("civic_fps2_pb")
    ds = m.districts((DATA / "fps2" / "fps2_pb_dfso.html").read_text())
    assert len(ds) == 2 and all(c in m.DISTRICTS for c, _ in ds)
    its = m.items(fake_get({}))
    by = {i["payload"]["dist_code"]: i for i in its}
    assert len(its) == 23 and by["036"]["key"] == "civic_fps2_pb-036" and by["036"]["payload"]["district"] == "Kapurthala"


# ---- Jharkhand (aahar.jharkhand.gov.in "Locate Your Dealer On Google Map"; *_shape samples are written by hand) ----
JH = "https://aahar.jharkhand.gov.in"


def test_fps2_jh_locate():
    m = mod("civic_fps2_jh")
    get = fake_get({("GET", m.PAGE): "fps2/fps2_jh_page.html",
                    ("POST", f"{JH}/transactions/get-blocks-by-district"): "fps2/fps2_jh_blocks_shape.json",
                    (lambda u, me, d: u.endswith("get-dealers-by-block") and d["rgi_block_code"] == "2700"): "fps2/fps2_jh_dealers_shape.json",
                    ("POST", m.PAGE): "fps2/fps2_jh_map_shape.html"})
    recs, files, why = m.fetch({"reader": m.MODULE, "url": JH, "state": "JH", "dist_code": "365", "district": "Khunti"}, get)
    check_records(recs, m.MODULE, "food_supplies")
    assert why == "" and len(recs) == 2 and [f[0] for f in files] == ["depts/civic_fps2_jh/365-2700.json.gz",
                                                                     "depts/civic_fps2_jh/365-2701.json.gz"]
    form = [c[2] for c in get.calls if c[0] == "POST" and c[1] == m.PAGE][0]
    assert form["_csrfToken"].startswith("e75aea15") and form["dealer_id"] == "10101" and form["rgi_block_code"] == "2700"
    r = dict(recs)["dept:civic_fps2_jh:10101"]
    assert (r["name"], r["licence_no"], r["phone"], r["lat"], r["lon"]) == ("SUNITA DEVI", "365001", "9431000000", 23.1234567, 85.1234567)
    assert r["block"] == "Karra" and r["district"] == "Khunti" and r["address"] == "Village Karra, Block Karra"


def test_fps2_jh_helpers():
    m = mod("civic_fps2_jh")
    assert m.dealer_label("RAM KUMAR (365001)") == ("RAM KUMAR", "365001")
    assert m.dealer_label("365001 - RAM KUMAR") == ("RAM KUMAR", "365001")
    assert m.dealer_label("RAM KUMAR") == ("RAM KUMAR", "")
    assert m.coords("var marker = {lat: 23.36, lng: 85.33};") == (23.36, 85.33)
    assert m.coords("LatLng(0.000, 0.000)") == (None, None)
    recs, _, why = m.fetch({"dist_code": "365", "locate": False}, fake_get({}))
    assert why == "no page or no form token"
    its = m.items()
    assert len(its) == 24 and all(i["payload"]["india_only"] for i in its)


# ---- every fps2 seed file ----
def test_fps2_all_seed_files():
    every = []
    for f in sorted((ROOT / "seeds").glob("dept_civic_fps2_*.json")):
        mname = f.stem[len("dept_"):]
        its = json.loads(f.read_text())
        assert its, f
        for i in its:
            p = i["payload"]
            assert i["key"].startswith(mname + "-") and p["reader"] == mname and p["url"] and p["state"], (f, i)
            assert hasattr(mod(mname), "fetch")
            every.append(i["key"])
    assert len(every) == len(set(every)) and len(every) >= 250
