"""Offline tests of the emergency and disaster service readers (dforms/emerg_<layer>_<xx>.py) and their seeds
(seeds/dept_emerg_*.json). Samples in tests/data/emerg_*; no test touches the network."""
import json
from pathlib import Path

from esw_common import DATA, ROOT, Answer, check_records, fake_get, mod  # noqa: F401


def by_id(recs):
    return dict(recs)


def check_seed(module, prefix):
    items = mod(module).items()
    keys = [i["key"] for i in items]
    assert items and len(keys) == len(set(keys)), "no items or duplicate keys"
    for i in items:
        assert i["key"].startswith(prefix) and i["payload"]["reader"] == module and i["payload"]["url"].startswith("https://"), i
        assert len(i["payload"].get("state", "")) == 2, i
    return items


def test_seeds_have_emerg_keys():
    for f in sorted((ROOT / "seeds").glob("dept_emerg_*.json")):
        for i in json.loads(f.read_text()):
            assert i["key"].startswith("emerg_"), (f.name, i["key"])


# ---- Hospitals on S3WaaS public-utility pages (emerg_hosp) ----
def test_hosp_s3waas():
    m = mod("emerg_hosp_s3waas")
    items = check_seed("emerg_hosp_s3waas", "emerg_hosp_s3waas-")
    assert len(items) == 471
    url = "https://buldhana.nic.in/en/public-utility-category/hospitals/"
    p = next(i["payload"] for i in items if i["payload"]["url"] == url)
    assert (p["state"], p["district"]) == ("MH", "Buldhana")
    recs, files, why = m.fetch(p, fake_get({url: "emerg_hosp_s3waas_buldhana_p1.html"}))
    # the pager points to page 2, which the fake site does not answer: page 1 alone
    assert why == "" and len(recs) == 3 and files[0][0].startswith("depts/emerg_hosp_s3waas/buldhana.nic.in-")
    check_records(recs, "emerg_hosp_s3waas", "health")
    d = by_id(recs)["dept:emerg_hosp_s3waas:buldhana.nic.in:district-hospital-buldhana"]
    assert d["layer"] == "emerg_hosp" and d["level"] == "facility" and d["area"] == "District Hospital Buldhana"
    assert (d["phone"], d["email"], d["facility_type"]) == ("7262242423", "cs_buldhana@rediffmail.com", "Government")
    assert (d["ambulances_govt"], d["ambulances_108"], d["last_updated"]) == (7, 1, "2026-11-06")
    assert "post" not in d and "emergency_phone" not in d
    assert by_id(recs)["dept:emerg_hosp_s3waas:buldhana.nic.in:primary-health-center-adgaon-raja"]["ambulances_108"] == 0


def test_hosp_emergency_label():
    m = mod("emerg_hosp_s3waas")
    html = ('<div class="public-utlty-catg"><h3 class="heading4">Civil Hospital X</h3><ul>'
            '<li>Main Road, X - 152002, Casualty : 01632-244111</li><li><strong>Phone :</strong> 01632-244000</li></ul></div>')
    (rid, d), = m.records([("https://x.nic.in/public-utility-category/hospitals/", html)], {"url": "https://x.nic.in/", "state": "PB"})
    assert d["emergency_phone"] == "01632-244111" and d["phone"] == "01632-244000, 01632-244111"
    assert "pincode" not in d or d["pincode"] != d["phone"]


# ---- District helpline pages on S3WaaS portals (emerg_help) ----
def test_help_s3waas_mokokchung():
    m = mod("emerg_help_s3waas")
    items = check_seed("emerg_help_s3waas", "emerg_help_s3waas-")
    assert len(items) == 111
    url = "https://mokokchung.nic.in/helpline/"
    p = next(i["payload"] for i in items if i["payload"]["url"] == url)
    recs, files, why = m.fetch(p, fake_get({url: "emerg_help_s3waas_mokokchung.html"}))
    assert why == "" and len(recs) == 18 and files[0][0] == "depts/emerg_help_s3waas/mokokchung.nic.in-helpline.html.gz"
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids))
    for rid, d in recs:
        assert rid.startswith("dept:emerg_help_s3waas:mokokchung.nic.in:") and d["layer"] == "emerg_help" and d["phone"], d
        assert d["dept"] in ("police", "health") and d["state"] == "NL" and d["source"] == url, d
    b = by_id(recs)
    d = b["dept:emerg_help_s3waas:mokokchung.nic.in:police-station-i-mokokchung"]
    assert (d["level"], d["phone"], d["last_updated"]) == ("police_station", "0369-2226241, 9485232688", "2019-05-28")
    assert (b["dept:emerg_help_s3waas:mokokchung.nic.in:sdpo-tuli"]["level"],
            b["dept:emerg_help_s3waas:mokokchung.nic.in:sdpo-tuli"]["post"]) == ("subdivision", "SDPO")
    assert b["dept:emerg_help_s3waas:mokokchung.nic.in:oc-police-station-kobulong"]["post"] == "OC"
    assert b["dept:emerg_help_s3waas:mokokchung.nic.in:impur-christian-hospital-ambulance"]["level"] == "facility"


def test_help_s3waas_jammu_heading():
    m = mod("emerg_help_s3waas")
    url = "https://jammu.nic.in/helpline/"
    recs, _, why = m.fetch({"url": url, "state": "JK", "district": "Jammu"}, fake_get({url: "emerg_help_s3waas_jammu.html"}))
    assert why == "" and recs
    d = by_id(recs)["dept:emerg_help_s3waas:jammu.nic.in:police-stations-std-code-0191-bagh-e-bahu"]
    # the row says only "Bagh-e-Bahu"; the heading above the table gives the service and the STD code
    assert (d["dept"], d["level"], d["area"], d["phone"], d["std_code"]) == ("police", "police_station", "Bagh-e-Bahu", "2459777", "0191")


def test_help_classify():
    m = mod("emerg_help_s3waas")
    assert m.dept_of("Women Help line") == "women_child" and m.dept_of("Child Helpline 1098") == "women_child"
    assert m.dept_of("District Control Room And Dist Emergency Operation centre, Katihar") == "disaster"
    assert m.dept_of("Fire Brigade, Nongpoh") == "fire" and m.dept_of("Police Control Room") == "police"
    assert m.dept_of("ENERGY DEPARTMENT, PATNA CONTROL ROOM") is None and m.dept_of("MGNREGA") is None
    assert m.dept_of("Rudraprayag Control Room") == "disaster"


# ---- One Stop Centres, Madhya Pradesh (emerg_osc) ----
def test_osc_mp():
    m = mod("emerg_osc_mp")
    (it,) = check_seed("emerg_osc_mp", "emerg_osc_mp")
    assert it["payload"]["india_only"] is True and it["payload"]["url"] == m.URL
    pages = json.loads((DATA / "emerg_osc_mp_p1_parts.json").read_text())
    recs = m.records(b"", m.URL, pages=pages)
    assert len(recs) == 4
    check_records(recs, "emerg_osc_mp", "women_child")
    d = dict(recs)["dept:emerg_osc_mp:aagar-malwa"]
    # the cell texts sit on several lines around the row's middle; each piece goes to its ruled band and column
    assert (d["name"], d["post"], d["phone"], d["std_code"]) == ("Ms Bhavna Barodia", "Centre Administrator", "7362 260260", "07362")
    assert d["address"] == "Near govt. boys hostel malikhedi road, Village Malikhedi, Agar, Agar-Malwa 465441"
    assert (d["email"], d["layer"], d["level"], d["state"]) == ("oscagarmalwa@gmail.com", "emerg_osc", "facility", "MP")
    assert dict(recs)["dept:emerg_osc_mp:ashoknagar"]["name"] == "Mrs Sushila Minj"


def test_osc_mp_fetch_not_pdf():
    m = mod("emerg_osc_mp")
    recs, files, why = m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_help_s3waas_jammu.html"}))
    assert recs == [] and why == "not a pdf" and files[0][0] == "depts/emerg_osc_mp/osc-list.pdf.gz"


# ======== Fire stations (emerg_fire: DL, GA, KL, KA, ML, TR, Nagpur) ========
def check_fire(recs, module, state):
    """depts.py contract + the emerg layer tag; every row has an area (vacant posts and planned stations may have no contact)."""
    assert recs
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:") and d["type"] == "dept_office" and d["dept"] == "fire", d
        assert d["layer"] == "emerg_fire" and d["state"] == state and d["source"] and d["level"] and d["area"], d




def test_fire_seeds_have_keys():
    import glob
    from pathlib import Path
    for f in glob.glob(str(Path(DATA).parent.parent / "seeds" / "dept_emerg_fire_*.json")):
        items = json.loads(Path(f).read_text())
        assert items and all(i["key"].startswith("emerg_fire_") and i["payload"]["reader"] for i in items), f


# ---- Delhi Fire Service (grid PDF + station phone list) ----
def test_fire_dl():
    m = mod("emerg_fire_dl")
    assert len(m.items()) == 1
    p1 = json.loads((DATA / "emerg_fire_dl_p1.json").read_text())
    pages = [([tuple(t) for t in p1["texts"]], [tuple(h) for h in p1["h"]], [tuple(v) for v in p1["v"]])]
    phones = m.phone_lines((DATA / "emerg_fire_dl_phones.txt").read_text())
    assert phones["connaughtplace"][:2] == ("CONNAUGHT PLACE", "23414444")
    assert phones["connaughtplace"][2] == {"line": 2, "line_text": "            CONNAUGHT PLACE            23414444"}
    recs = m.records(pages, phones, m.URL, m.PHONES_URL)
    check_fire(recs, "emerg_fire_dl", "DL")
    d = by_id(recs)
    st = d["dept:emerg_fire_dl:st-connaught-circus"]          # alias: Connaught Place in the phone list
    assert (st["phone"], st["subdivision"], st["division"], st["zone"]) == ("23414444", "New Delhi", "New Delhi", "Central")
    assert d["dept:emerg_fire_dl:st-shankar-road"]["subdivision"] == "Patel Nagar"     # merged cell spans 4 stations
    assert d["dept:emerg_fire_dl:st-j-r-road"]["subdivision"] == "Karol Bagh"
    ado = d["dept:emerg_fire_dl:sd-patel-nagar-vinay-kumar"]
    assert (ado["post"], ado["level"], ado["email"]) == ("Assistant Divisional Officer", "subdivision", "pnsd.dlfire@delhi.gov.in")
    cfo = d["dept:emerg_fire_dl:zone-central-chief-fire-officer-dr-s-k-tomar"]
    assert cfo["additional_charge"] is True and cfo["email"] == "cfocz.dlfire@delhi.gov.in"
    assert d["dept:emerg_fire_dl:zone-central-deputy-chief-fire-officer-vacant"]["vacant"] is True
    assert sum(1 for _, x in recs if x["level"] == "facility") == 21


def test_fire_dl_fetch_answers():
    m = mod("emerg_fire_dl")
    recs, files, why = m.fetch({"url": m.URL}, fake_get({}))
    assert (recs, files, why) == ([], [], "no answer")


# ---- Goa DFES (cards) ----
def test_fire_ga():
    m = mod("emerg_fire_ga")
    assert len(m.items()) == 1
    recs, files, why = m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_fire_ga.html"}))
    assert why == "" and len(recs) == 5 and files[0][0] == "depts/emerg_fire_ga/contact-us.html.gz"
    check_fire(recs, "emerg_fire_ga", "GA")
    d = by_id(recs)
    dr = d["dept:emerg_fire_ga:director-goa-dr-nitin-v-raiker"]
    assert (dr["level"], dr["mobile"], dr["email"]) == ("state", "9763717052", "dir-fire.goa@nic.in")
    st = d["dept:emerg_fire_ga:fire-station-pernem-shri-n-h-parwar"]
    assert (st["level"], st["post"], st["zone"]) == ("facility", "Station Fire Officer", "North Zone")
    assert (st["mobile"], st["landline"]) == ("7391047133, 8308846751", "2201201/ 2201393/101")
    assert d["dept:emerg_fire_ga:fire-station-pilerne-shri-shrikrishna-r-parrikar"]["additional_charge"] is True
    mg = d["dept:emerg_fire_ga:fire-station-margao-shri-herculano-gill-souza"]      # name in an h3, not h4
    assert mg["zone"] == "South Zone" and mg["email"] == "mrg-fire.goa@gov.in"
    ado = d["dept:emerg_fire_ga:asst-div-officer-central-zone-shri-francisco-mendes"]
    assert ado["area"] == "Central Zone" and ado["additional_charge"] is True


# ---- Kerala Fire and Rescue Services (Malayalam tables, HQ cards, WordPress posts) ----
def test_fire_kl_district_table():
    m = mod("emerg_fire_kl")
    assert len(m.items()) == 7
    url = "https://fire.kerala.gov.in/district-fire-offices/"
    p = {"kind": "table", "table": "district", "url": url}
    recs, files, why = m.fetch(p, fake_get({url: "emerg_fire_kl_district.html"}))
    assert why == "" and files[0][0] == "depts/emerg_fire_kl/table-district.html.gz"
    check_fire(recs, "emerg_fire_kl", "KL")
    d = by_id(recs)
    t = d["dept:emerg_fire_kl:dfo-thiruvananthapuram"]
    assert (t["level"], t["post"], t["phone"], t["email"]) == ("district", "District Fire Officer", "0471-2333101", "adotvm.frs@kerala.gov.in")
    assert t["name"] == t["name_regional"] == "ശ്രീ. സൂരജ് എസ്" and t["district"] == "Thiruvananthapuram"
    assert d["dept:emerg_fire_kl:dfo-kollam"]["area_regional"] == "കൊല്ലം"
    # the academy cell names three officers; it is a state office in Thrissur, not a district office
    ac = [x for r, x in recs if r.startswith("dept:emerg_fire_kl:dfo-adoac-frs")]
    assert len(ac) == 3 and all(x["level"] == "state" and x["district"] == "Thrissur" for x in ac)
    assert len(recs) == 5


def test_fire_kl_hq_and_posts():
    m = mod("emerg_fire_kl")
    recs, _, why = m.fetch({"kind": "team", "url": "U"}, fake_get({"U": "emerg_fire_kl_hq.html"}))
    assert why == "" and len(recs) == 2
    dg = by_id(recs)["dept:emerg_fire_kl:hq-dg-frs"]
    assert (dg["post"], dg["phone"], dg["fax"], dg["email"]) == ("ഡയറക്ടർ ജനറൽ", "0471-2320868, 2320872", "0471-2337422", "dg.frs@kerala.gov.in")
    recs, files, why = m.fetch({"kind": "posts", "page": 1, "url": "P"}, fake_get({"P": "emerg_fire_kl_posts.json"}))
    assert why == "" and len(recs) == 1 and files[0][0] == "depts/emerg_fire_kl/posts-1.json.gz"     # the "Parade" post is skipped
    rid, st = recs[0]
    assert rid == "dept:emerg_fire_kl:st-1132" and st["phone"] == "0471 232 0872" and st["district"] == "Thiruvananthapuram"
    assert st["source"] == "https://fire.kerala.gov.in/en/thiruvananthapuram/" and st["last_updated"] == "2021-03-17"


# ---- Tripura Fire & Emergency Services (contact table: divisions and stations) ----
def test_fire_tr():
    m = mod("emerg_fire_tr")
    assert len(m.items()) == 1
    recs, files, why = m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_fire_tr.html"}))
    assert why == "" and len(recs) == 6 and files[0][0] == "depts/emerg_fire_tr/contact-us.html.gz"
    check_fire(recs, "emerg_fire_tr", "TR")
    d = by_id(recs)
    dr = d["dept:emerg_fire_tr:hq-dr-tamal-majumdar"]
    assert (dr["post"], dr["phone"]) == ("Director of Fire & Emergency Services", "(0381) 232-6451")   # the fax number is left out
    assert dr["email"] == "dg.fire-tr@gov.in, tripurafireservice@gmail.com"
    dv = d["dept:emerg_fire_tr:div-gomati"]
    assert (dv["level"], dv["name"], dv["division"]) == ("division", "Sh. J. B. Jamatia", "Gomati")
    st = d["dept:emerg_fire_tr:st-agartala"]
    assert (st["landline"], st["mobile"], st["has_101"], st["division"]) == ("(0381) 232-5630", "6033231202", True, "West")
    assert d["dept:emerg_fire_tr:st-udaipur"]["division"] == "Gomati"


# ---- Meghalaya F&ES (key contacts + station list for districts) ----
def test_fire_ml():
    m = mod("emerg_fire_ml")
    assert len(m.items()) == 1
    routes = {m.URL: "emerg_fire_ml_contacts.html", m.STATIONS_URL: "emerg_fire_ml_stations.html"}
    recs, files, why = m.fetch({"url": m.URL}, fake_get(routes))
    assert why == "" and len(recs) == 6 and len(files) == 2
    check_fire(recs, "emerg_fire_ml", "ML")
    d = by_id(recs)
    ig = d["dept:emerg_fire_ml:off-fes-meg"]
    assert (ig["name"], ig["landline"], ig["mobile"], ig["email"]) == ("Shri. F. G. Kharshiing (IPS)", "0364-2224668", "9436100424", "fes.meg@meghalaya.gov.in")
    sh = d["dept:emerg_fire_ml:st-shillong-fire-station"]
    assert (sh["name"], sh["post"], sh["mobile"], sh["district"]) == ("Shri. Ganesh Muktan", "Station Officer", "9863324602, 8575415433", "East Khasi Hills")
    assert "landline" not in sh                                                     # "(Office) NA"
    assert d["dept:emerg_fire_ml:st-raj-bhavan-fire-station"]["district"] == "East Khasi Hills"   # Raj Bhavan = Governor House
    assert d["dept:emerg_fire_ml:st-fire-control-room"]["short_codes"] == "101"
    pb = d["dept:emerg_fire_ml:st-polo-bazar-f-es-station"]                          # on the station list only
    assert pb["building"] == "Non Functional. No land." and pb["source"] == m.STATIONS_URL


# ---- Karnataka SFES (216-station list with the CFO / RFO / DFO chain) ----
def test_fire_ka():
    m = mod("emerg_fire_ka")
    assert m.items()[0]["payload"]["india_only"] is True
    recs = m.records((DATA / "emerg_fire_ka_layout.txt").read_text(), m.URL)
    check_fire(recs, "emerg_fire_ka", "KA")
    d = by_id(recs)
    st = d["dept:emerg_fire_ka:st-1"]
    assert (st["area"], st["zone"], st["region"], st["district_office"]) == ("Mayohall", "East", "East", "Mayohall")
    assert d["dept:emerg_fire_ka:st-6"]["area"] == "Kolar" and d["dept:emerg_fire_ka:st-6"]["district_office"] == "Kolar"
    assert d["dept:emerg_fire_ka:unit-vidhan-soudha-units"]["unit"] is True
    hb = d["dept:emerg_fire_ka:st-144"]                       # DFO carried down, then replaced on its own row
    assert (hb["area"], hb["zone"], hb["district_office"]) == ("Hubli City", "Hubli", "Hubli City")
    assert d["dept:emerg_fire_ka:st-140"]["district_office"] == "Hubli Amargol"
    assert d["dept:emerg_fire_ka:unit-academy"]["zone"] == "Commandent"
    assert sum(1 for _, x in recs if x.get("station_no")) == 14


# ---- Nagpur Municipal Corporation fire stations (Excel PDF, wrapped cells) ----
def test_fire_nagpur():
    m = mod("emerg_fire_nagpur")
    assert len(m.items()) == 1
    recs = m.records((DATA / "emerg_fire_nagpur_layout.txt").read_text(), m.URL)
    check_fire(recs, "emerg_fire_nagpur", "MH")
    assert len(recs) == 10 and all(d["name"] and d["mobile"] and d["district"] == "Nagpur" for _, d in recs)
    d = by_id(recs)
    hq = d["dept:emerg_fire_nagpur:nagpur-fire-emergency-service-mahanagarpalika-nagpur-hq"]
    assert (hq["post"], hq["name"], hq["landline"], hq["mobile"]) == ("Divisional Fire Officer", "Shri. Bhimrao.P. Chandankhede", "0712-2567777, 2567029", "9923751402")
    assert hq["address"] == "Chatrapati Shivaji Maharaj Adminstration Building Civil Line NMC Nagpur"
    cv = d["dept:emerg_fire_nagpur:civil-fire-station"]                  # second officer in the HQ row
    assert (cv["post"], cv["email"]) == ("Assistant Divisional Fire Officer", "tushar_1133@yahoo.com")
    lk = d["dept:emerg_fire_nagpur:lakadganj-fire-station"]
    assert (lk["email"], lk["email_as_written"]) == ("dilipchavhan@gmail.com", "dilipchavhan&gmail.com")


# ======== Disaster management and home guards (emerg_ddma: S3WaaS, KL, SK; emerg_hg: UP) ========
def check_emerg(recs, module, dept, layer):
    check_records(recs, module, dept)
    for rid, d in recs:
        assert d["layer"] == layer and d["level"] in ("state", "division", "district", "subdistrict", "subdivision", "facility"), d
        assert d.get("area") and d.get("post"), d


# ---- S3WaaS district disaster management pages ----
def s3(name, url, district, state):
    m = mod("emerg_ddma_s3waas")
    p = {"reader": "emerg_ddma_s3waas", "url": url, "district": district, "state": state}
    return m.fetch(p, fake_get({url: f"emerg_ddma_s3waas_{name}.html"}))


def test_s3waas_table_with_header():
    recs, files, why = s3("chamoli", "https://chamoli.gov.in/disaster-management/", "Chamoli", "UK")
    assert why == "" and len(recs) == 2 and files[0][0] == "depts/emerg_ddma_s3waas/chamoli.gov.in-disaster-management.html.gz"
    check_emerg(recs, "emerg_ddma_s3waas", "disaster", "emerg_ddma")
    d = by_id(recs)["dept:emerg_ddma_s3waas:chamoli.gov.in:page:disaster-management-officer"]
    assert (d["name"], d["post"], d["area"]) == ("Shri Nand Kishore Joshi", "Disaster Management Officer", "Chamoli")
    assert d["phone"] == "01372-251437, 9411352136" and d["fax"] == "01372-252203"
    assert d["email"] == "ddmachamoli1077@gmail.com" and d["last_updated"] == "2025-10-27" and d["state"] == "UK"


def test_s3waas_name_and_post_in_one_cell():
    recs, _, why = s3("serchhip", "https://serchhip.nic.in/disaster-management/", "Serchhip", "MZ")
    assert why == "" and len(recs) == 4
    check_emerg(recs, "emerg_ddma_s3waas", "disaster", "emerg_ddma")
    d = recs[0][1]
    assert (d["name"], d["post"]) == ("Pi Rebecca Laldinmawii Hrahsel, MCS", "SDO (Sadar) Serchhip")
    assert d["covers"].startswith("New Serchhip North") and d["phone"] == "03838-222285, 8974736278"


def test_s3waas_plain_text():
    recs, _, why = s3("lakhisarai", "https://lakhisarai.nic.in/disaster-management/", "Lakhisarai", "BR")
    assert why == "" and len(recs) == 2
    check_emerg(recs, "emerg_ddma_s3waas", "disaster", "emerg_ddma")
    a, b = recs[0][1], recs[1][1]
    assert (a["post"], a["phone"], a["level"]) == ("State Control Room", "0612-2217305", "state")
    assert (b["post"], b["phone"]) == ("District Control Room Numbers", "06346-232124, 232190, 9431071977")   # Landline + Mobile lines


def test_s3waas_name_designation_lines():
    recs, _, _ = s3("namsai", "https://namsai.nic.in/disaster-management/", "Namsai", "AR")
    assert len(recs) == 1
    d = recs[0][1]
    assert (d["name"], d["post"], d["phone"]) == ("Mrs. Thongchin", "District Disaster Management Officer", "8259003656")


def test_s3waas_no_answer_and_seed():
    m = mod("emerg_ddma_s3waas")
    assert m.fetch({"url": "https://x.nic.in/disaster-management/"}, fake_get({})) == ([], [], "no answer")
    items = m.items()
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) and all(k.startswith("emerg_ddma_s3waas-") for k in keys)
    assert all(i["payload"]["reader"] == "emerg_ddma_s3waas" and i["payload"]["state"] for i in items)
    assert sum(1 for i in items if i["payload"].get("saved")) >= 150


# ---- Kerala DM Directory 2025 ----
def test_kl_directory():
    m = mod("emerg_ddma_kl")
    pages = (DATA / "emerg_ddma_kl_layout.txt").read_text().split("\f")
    recs = m.records(pages)
    assert len(recs) == 21
    ids = by_id(recs)
    for rid, d in recs:
        assert rid.startswith("dept:emerg_ddma_kl:") and d["layer"] == "emerg_ddma" and d["state"] == "KL" and d["phone"], d
    d = ids["dept:emerg_ddma_kl:helplines:state:state-emergency-helpline"]
    assert d["helpline"] == "1070" and d["level"] == "state"
    d = ids["dept:emerg_ddma_kl:deoc:kollam:district-emergency-operations-centre"]
    assert (d["district"], d["phone"], d["dept"]) == ("Kollam", "0474-2794002, 9447677800, 2794004", "disaster")
    d = ids["dept:emerg_ddma_kl:teoc:thiruvananthapuram:kattakada"]
    assert (d["area"], d["level"], d["phone"]) == ("Kattakada", "subdistrict", "0471 2291414, 9497711284")
    d = ids["dept:emerg_ddma_kl:district:thiruvananthapuram:district-police-chief"]
    assert (d["dept"], d["section"], d["phone"]) == ("police", "Police", "9497996991, 0471-2320579, 0471-2320486")
    d = ids["dept:emerg_ddma_kl:district:thiruvananthapuram:fire-and-rescue-station-thiruvananthapuram"]
    assert (d["dept"], d["level"]) == ("fire", "facility")   # the station name on the next line is not a district heading
    assert len(m.items()) == 1


def test_kl_not_pdf():
    m = mod("emerg_ddma_kl")
    assert m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_ddma_sk.html"}))[2] == "not a PDF"


# ---- Sikkim SSDMA who is who ----
def test_sk_whoiswho():
    m = mod("emerg_ddma_sk")
    recs, files, why = m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_ddma_sk.html"}))
    assert why == "" and len(recs) == 9 and files[0][0] == "depts/emerg_ddma_sk/whoiswho.html.gz"
    check_emerg(recs, "emerg_ddma_sk", "disaster", "emerg_ddma")
    ids = by_id(recs)
    d = ids["dept:emerg_ddma_sk:ssdma-officials:director"]
    assert (d["level"], d["name"], d["phone"], d["email"]) == ("state", "Shri. Prabhakar Rai", "9434179141, 03592-201145",
                                                                "directorssdma@gmail.com")
    d = ids["dept:emerg_ddma_sk:ddma-gyalshing:adc-gyalshing"]
    assert (d["district"], d["level"], d["name"], d["org"]) == ("Gyalshing", "district", "Mr. Suresh Rai",
                                                               "Land Revenue and Disaster Management Department")


# ---- Uttar Pradesh Home Guards officials ----
def test_hg_up():
    m = mod("emerg_hg_up")
    recs = m.records([(DATA / "emerg_hg_up_layout.txt").read_text()])
    assert len(recs) == 16
    check_emerg(recs, "emerg_hg_up", "police", "emerg_hg")
    ids = by_id(recs)
    d = ids["dept:emerg_hg_up:cghg-up"]
    assert (d["post"], d["level"], d["phone"], d["email"]) == ("Commandant General, Home Guards", "state", "8005194100", "cghg-up@nic.in")
    d = ids["dept:emerg_hg_up:cmdhgrb-up"]
    assert (d["post"], d["district"], d["phone"]) == ("District Commandant, Home Guards", "Rae Bareli", "8005194068")
    d = ids["dept:emerg_hg_up:dtc-hg.lu"]
    assert d["level"] == "division" and d["area"] == "Lucknow" and d["email"] == "dtc-hg.lu@up.gov.in"
    assert m.unit("cmdhgpr-up")[2] == "pr" and m.CODES["pr"] == "Pratapgarh" and m.TRAINING["pr"] == "Prayagraj"
    assert len(m.CODES) == 75 and len(m.items()) == 1


def test_seed_keys():
    for f in ROOT.glob("seeds/dept_emerg_ddma_*.json"):
        for it in json.loads(f.read_text()):
            assert it["key"].startswith("emerg_ddma_") and it["payload"]["reader"] in f.stem, (f, it["key"])
    for f in ROOT.glob("seeds/dept_emerg_hg_*.json"):
        for it in json.loads(f.read_text()):
            assert it["key"].startswith("emerg_hg_") and it["payload"]["reader"] in f.stem, (f, it["key"])
