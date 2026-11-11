import re

from esw_common import *  # noqa: F401,F403


# ---- water: Uttarakhand, Delhi Jal Board, Odisha (PHEO + WATCO), West Bengal, Tripura, Manipur
# (dforms/water_uk, water_dl, water_od, water_wb, water_tr, water_mn)

def _w6_fetch(module, routes, payload):
    recs, files, why = mod(module).fetch(payload, fake_get(routes))
    assert why == "" and files and all(f[0].startswith(f"depts/{module}/") for f in files), why
    check_records(recs, module, "water")
    return dict(recs)


def _w6_seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def test_water_uk():
    seed = _w6_seed("water_uk")
    assert [i["payload"]["page"] for i in seed] == [1, 2, 3]
    p = seed[0]["payload"]
    recs = _w6_fetch("water_uk", {p["url"]: "water_uk_p1.html"}, p)
    cgm = recs["dept:water_uk:chief-general-manager:dehradun"]
    assert cgm["level"] == "state" and cgm["name"] == "Shri. D.K.Singh" and cgm["email"] == "cgmujs@gmail.com, cgm-js-ua@nic.in"
    se = recs["dept:water_uk:superintending-engineer:pithoragarh"]
    assert se["level"] == "circle" and se["phone"] == "8449705009" and se["serves"].startswith("Pithoragarh, Bageshwar")
    ee = recs["dept:water_uk:executive-engineer:khatima"]
    assert ee["level"] == "division" and ee["area"] == "Khatima" and ee["email"] == "eeujskht@gmail.com"
    assert ee["office_id"] == "UK-UJS-executive-engineer-khatima" and ee["last_updated"] == "2025-04-22"
    assert recs["dept:water_uk:general-manager:kumaon"]["level"] == "zone"


def test_water_dl():
    seed = _w6_seed("water_dl")
    assert len(seed) == 1 and len(seed[0]["payload"]["urls"]) == 68
    assert {int(re.search(r"ac_(\d+)_", u).group(1)) for u in seed[0]["payload"]["urls"]} == set(range(1, 71)) - {38, 40}
    url = next(u for u in seed[0]["payload"]["urls"] if "/ac_11_" in u)
    p = {"reader": "water_dl", "url": url, "state": "DL", "ac": 11}      # an old one-file queue item still works
    recs = _w6_fetch("water_dl", {url: "water_dl_ac11.pdf"}, p)
    ee = recs["dept:water_dl:DL-AC-11:ee:ee-c-22"]
    assert ee["name"] == "Sh. S.K Dhaiya" and ee["phone"] == "9971168047" and ee["level"] == "division"
    assert ee["ac"] == "DL-AC-11" and ee["office_id"] == "DL-DJB-ee-c-22"
    ae2 = recs["dept:water_dl:DL-AC-11:ae:2"]
    assert ae2["name"] == "Sh. Narender Sharma" and ae2["phone"] == "9650094212" and ae2["area"] == "11 - Nangloi Jat"
    assert recs["dept:water_dl:DL-AC-11:je:1"]["phone"] == "7982479583"
    ppp = recs["dept:water_dl:DL-AC-11:ae:1:ppp-area"]
    assert ppp["name"] == "Smt. Kamlesh Manchanda" and ppp["section"] == "PPP Area"
    assert recs["dept:water_dl:DL-AC-11:ce:ce-maintenance-i-ce-west"]["name"] == "Sh. SK Dahiya"
    assert len(recs) == 11


def test_water_dl_one_record_per_officer():
    # the same officers are listed in the file of every constituency they serve: one record each, all constituencies in "acs"
    seed = _w6_seed("water_dl")[0]["payload"]
    u11 = next(u for u in seed["urls"] if "/ac_11_" in u)
    u12 = next(u for u in seed["urls"] if "/ac_12_" in u)
    p = dict(seed, urls=[u11, u12])
    recs = _w6_fetch("water_dl", {u11: "water_dl_ac11.pdf", u12: "water_dl_ac11.pdf"}, p)
    assert len(recs) == 11 and all(d["acs"] == ["DL-AC-11", "DL-AC-12"] for d in recs.values())
    ee = recs["dept:water_dl:DL-AC-11:ee:ee-c-22"]
    assert ee["ac"] == "DL-AC-11" and ee["name"] == "Sh. S.K Dhaiya"
    assert recs["dept:water_dl:DL-AC-11:ae:2"]["area"].startswith("11 - Nangloi Jat, 12 - ")
    # a file that does not answer fails the item (no short constituency lists)
    recs, files, why = mod("water_dl").fetch(p, fake_get({u11: "water_dl_ac11.pdf"}))
    assert recs == [] and "no answer" in why


def test_water_dl_merge_names():
    m = mod("water_dl")
    a = {"name": "Sh. SK Dahiya", "post": "CE(Maintenance)-I CE(West)", "ac": "DL-AC-10", "phone": "9650291401", "level": "zone"}
    b = {"name": "Sh SK Dahiya", "post": "CE (Maintenance)-I CE (West)", "ac": "DL-AC-11", "phone": "9650291401", "level": "zone",
         "section": "PPP Area"}
    c = {"name": "Sh. N.K. Dargan", "post": "SE (Proj) W-I", "ac": "DL-AC-11", "level": "circle"}
    out = m.merge([("x:10", a), ("x:11", b), ("y:11", c)])
    assert [r for r, _ in out] == ["x:10", "y:11"] and out[0][1]["acs"] == ["DL-AC-10", "DL-AC-11"]
    assert out[0][1]["phone"] == "9650291401" and out[0][1]["sections"] == ["", "PPP Area"]


def test_water_dl_phone_in_name():
    people = mod("water_dl")._people
    assert people(["Sh. Amit Prajapati 8851283671"]) == [{"name": ["Sh. Amit Prajapati"], "posts": [], "phones": ["8851283671"]}]
    two = people(["Sh.Anshu 62077 53525 Sh. Sourav 8853495254"])
    assert [p["name"] for p in two] == [["Sh.Anshu"], ["Sh. Sourav"]] and two[0]["phones"] == ["62077 53525"]
    two = people(["Sh. Manoj Kumar Bairwa(9650888215) Sh.Akshay Kumar", "9455811307"])
    assert [(p["name"], p["phones"]) for p in two] == [(["Sh. Manoj Kumar Bairwa"], ["9650888215"]), (["Sh.Akshay Kumar"], ["9455811307"])]
    assert people(["Sh. Gaurav", "931543474"])[0]["phones"] == ["931543474"]


def test_water_dl_people():
    people = mod("water_dl")._people(["Sh Naveen Kumar", "Khare", "SE (C)-11", "9650291085", "Sh. X", "9650000000"])
    assert [p["name"] for p in people] == [["Sh Naveen Kumar", "Khare"], ["Sh. X"]] and people[0]["posts"] == ["SE (C)-11"]


def test_water_od_pheo():
    seed = _w6_seed("water_od")
    p = next(i["payload"] for i in seed if i["payload"].get("portal") == 16)
    recs = _w6_fetch("water_od", {p["url"]: "water_od_pheo16.html"}, p)
    ae = recs["dept:water_od:pheo-16:sub-division-no-iii-berhampur:assistant-engineer"]
    assert ae["name"] == "Sri J.Rabi Narayan patra" and ae["phone"] == "9437066311" and ae["level"] == "subdivision"
    assert ae["area"] == "Sub-Division No-III, Berhampur"
    je = recs["dept:water_od:pheo-16:section-kaliabali:junior-engineer"]
    assert je["level"] == "section" and je["phone"] == "9437479463"
    office = recs["dept:water_od:pheo-16:office"]
    assert office["phone"] == "0680-2209914" and office["fax"] == "0680-2233833"
    assert not any("account" in d["post"].lower() for d in recs.values())
    assert len([i for i in seed if i["payload"]["page"] == "pheo"]) == 24


def test_water_od_watco():
    seed = {i["payload"]["page"]: i["payload"] for i in _w6_seed("water_od") if i["payload"]["page"] != "pheo"}
    recs = _w6_fetch("water_od", {seed["watco"]["url"]: "water_od_watco.json"}, seed["watco"])
    gm = next(d for d in recs.values() if d["post"] == "General Manager" and "Division - I, Bhubaneswar" in d["area"])
    assert gm["name"] == "Er. Bikram Rout" and gm["email"] == "gmdivonewatco@gmail.com" and gm["level"] == "division"
    sub = next(d for d in recs.values() if d.get("name") == "Er. Rabindra Nath Mohapatra")
    assert sub["level"] == "subdivision" and sub["phone"] == "9437205213" and sub["area"] == "Nayapalli Sub Division"
    main = _w6_fetch("water_od", {seed["watco-main"]["url"]: "water_od_watco_main.json"}, seed["watco-main"])
    md = main["dept:water_od:watco-main:managing-director"]
    assert md["name"] == "Er. Debabrata Mohanty" and md["phone"] == "0674-2571444, 8895000800"
    assert md["email"] == "md@watcoodisha.in, mdwatcoodisha@gmail.com"


def test_water_wb():
    seed = _w6_seed("water_wb")
    assert len(seed) == 9
    p = next(i["payload"] for i in seed if i["payload"]["designation"] == "Executive Engineer")
    m = mod("water_wb")
    get = fake_get({p["url"]: "water_wb_form.html", ("POST", m.SEARCH): "water_wb_ee.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and files
    check_records(recs, "water_wb", "water")
    post = [c for c in get.calls if c[0] == "POST"][0]
    assert post[2]["DesignationId"] == p["designation_id"] and post[2]["__RequestVerificationToken"]
    assert post[2]["AdvancedDepartmentId"] == m.DIRECTORATE
    recs = dict(recs)
    ee = recs["dept:water_wb:executive-engineer-jalpaiguri-division"]
    assert ee["name"] == "Shri Ashis Ganguly" and ee["phone"] == "03561225535" and ee["email"] == "ee_jlp@wbphed.gov.in"
    assert ee["area"] == "Jalpaiguri Division" and ee["level"] == "division" and ee["office_id"] == "WB-PHED-jalpaiguri-division"
    assert recs["dept:water_wb:deputy-superintending-engineer-planning-circle-i"]["level"] == "circle"


def test_water_tr():
    p = _w6_seed("water_tr")[0]["payload"]
    assert p["india_only"] is True
    recs = _w6_fetch("water_tr", {p["url"]: "water_tr_contact.html"}, p)
    ce = recs["dept:water_tr:o-o-the-chief-engineer:chief-engineer:o-o-the-chief-engineer"]
    assert ce["name"] == "Er. Manoranjan Debbarma" and ce["phone"] == "6009171807" and ce["level"] == "state"
    ee = recs["dept:water_tr:agartala-ii-division-office:executive-engineer:agartala-ii-division"]
    assert ee["name"] == "Er. Kamalesh Debbarma" and ee["email"] == "dwsdivisionagartala2@yahoo.com" and ee["level"] == "division"
    ae = recs["dept:water_tr:sub-division-office:assistant-engineer:pwd-se-complex"]
    assert ae["phone"] == "9862774894, 03824-261228" and ae["level"] == "subdivision"


def test_water_tr_place():
    place = mod("water_tr")._place
    assert place("Sub_Division Office", "DWS Sub-Division, Rupaichari , Sabroom,South Tripura") == "Rupaichari"
    assert place("Sub_Division Office", "O/O The Assistant Engineer, PWD(DWS), Sub-Division No-II, Udaipur Division") == "No-II, Udaipur"
    assert place("Agartala II Division Office", "anything") == "Agartala II Division"


def test_water_mn(monkeypatch):
    p = _w6_seed("water_mn")[0]["payload"]
    pages = (DATA / "water_mn_directory.txt").read_text().split("\f")
    m = mod("water_mn")
    monkeypatch.setattr(m._esw, "pdf_pages", lambda content: pages)
    recs = _w6_fetch("water_mn", {p["url"]: "water_mn_directory.txt"}, p)
    assert len(recs) == 40
    ee = recs["dept:water_mn:ee-imphal-east"]
    assert ee["name"] == "Salima Begum" and ee["phone"] == "8974607157" and ee["email"] == "salimabegum1484@gmail.com"
    assert ee["level"] == "division" and ee["area"] == "Imphal East" and ee["last_updated"] == "2026-06-03"
    assert recs["dept:water_mn:addl-chief-engineer"]["name"] == "Kirankumar Laishram"
    assert recs["dept:water_mn:addl-chief-engineer:2"]["name"] == "Dorendra Rajkumar"
    assert recs["dept:water_mn:ee-ipd-i"]["name"] == "Sudesh"
    assert recs["dept:water_mn:ee-mechanical-electrical"]["email"] == "rajkumaridayabati@gmail.com"
    assert recs["dept:water_mn:ee-monitoring-evaluation"]["email"] == "monitoringandevaluationdivision@gmail.com"
    assert recs["dept:water_mn:se-urban-circle"]["level"] == "circle"
