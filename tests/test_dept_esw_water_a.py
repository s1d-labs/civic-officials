from esw_common import *  # noqa: F401,F403


# ---- Water: Kerala KWA, Karnataka KUWSDB + BWSSB, Tamil Nadu TWAD, Rajasthan PHED, Maharashtra MJP, Haryana PHED, Himachal JSV
# (dforms/water_kl, water_ka, water_tn, water_rj, water_mh, water_hr, water_hp)

def _water(module, sample, payload=None, url=None):
    p = payload or json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())[0]["payload"]
    get = fake_get({url or p["url"]: sample})
    recs, files, why = mod(module).fetch(p, get)
    assert why == "" and files and files[0][0].startswith(f"depts/{module}/")
    check_records(recs, module, "water")
    return dict(recs), get


def test_water_levels():
    from dforms._water import level_of
    assert level_of("AEE,IPD Sub Dn., Changanassery") == "subdivision"
    assert level_of("EE & TA TO SE") == "division" and level_of("S.E. O/o ACE") == "circle"
    assert level_of("Chief Engineer South Region") == "zone" and level_of("Chief Engineer (HRD & Gl)") == "state"
    assert level_of("AE,WW Section No.I, Kottayam") == "section" and level_of("Superintendent Engineer") == "circle"


def test_water_kl():
    recs, _ = _water("water_kl", "water_kl_contact.html")
    se = recs["dept:water_kl:KL-KWA-ph-circle-kottayam:superintending-engineer-ph-circle-kottayam"]
    assert se["level"] == "circle" and se["area"] == "PH Circle, Kottayam" and se["phone"] == "0481-2562745, 8547638029"
    assert se["email"] == "cru.phckottayam@kerala.gov.in, sephck@gmail.com" and se["last_updated"] == "2026-11-10"
    assert recs["dept:water_kl:KL-KWA-head-office:head-office"]["level"] == "state"
    aee = recs["dept:water_kl:KL-KWA-ph-circle-kottayam:aee-ipd-sub-dn-changanassery"]
    assert aee["level"] == "subdivision" and aee["area"] == "IPD Sub Dn., Changanassery"


def test_water_ka_kuwsdb():
    p = next(i["payload"] for i in json.loads((ROOT / "seeds" / "dept_water_ka.json").read_text()) if i["payload"]["page"] == "kuwsdb")
    recs, _ = _water("water_ka", "water_ka_kuwsdb.html", p)
    ce = recs["dept:water_ka:KA-KUWSDB-bangalore-revenue-zone:chief-engineer"]
    assert ce["level"] == "zone" and ce["name"] == "Sri. Nandeesh J R" and ce["email"] == "cekwbbng@gmail.com"
    chair = recs["dept:water_ka:KA-KUWSDB-central-office:chairman"]
    assert chair["level"] == "state" and chair["phone"] == "080-41106502, 080-26539002"


def test_water_ka_bwssb():
    p = next(i["payload"] for i in json.loads((ROOT / "seeds" / "dept_water_ka.json").read_text()) if i["payload"]["page"] == "bwssb")
    recs, _ = _water("water_ka", "water_ka_bwssb.html", p)
    ee = recs["dept:water_ka:KA-BWSSB-central-1"]
    assert ee["level"] == "division" and ee["name"] == "Nagendra B" and ee["phone"] == "22945187, 9845444078"
    aee = recs["dept:water_ka:KA-BWSSB-c-11"]
    assert aee["email"] == "aeec1@bwssb.gov.in" and aee["parent"] == "KA-BWSSB-central-1"
    stn = recs["dept:water_ka:KA-BWSSB-c-12-magadi-road-1"]
    assert stn["level"] == "section" and stn["name"] == "Vishwanath M R" and stn["parent"] == "KA-BWSSB-c-12"
    assert len([d for d in recs.values() if d["level"] == "division"]) == 1          # one division cell over six rows
    # a station headed by a JE (text as on the page)
    cell = ("<tr><td>West 4 | T Chandrashekar Prasad | Executive Engineer</td><td>W 43 | Nandini K R | Assistant Executive Engineer</td>"
            "<td>Srinivasanagar<br>Name:Kumuda (JE)<br>Address: 3rd Main Road<br>Office Number:22945147<br>Mobile No.: 9035903638</td></tr>")
    je = dict(mod("water_ka").bwssb(f"<table><tr><th>Service Stations</th></tr>{cell}</table>"))["dept:water_ka:KA-BWSSB-w-43-srinivasanagar"]
    assert je["name"] == "Kumuda" and je["post"] == "Junior Engineer" and je["phone"] == "22945147, 9035903638"


def test_water_tn():
    items = json.loads((ROOT / "seeds" / "dept_water_tn.json").read_text())
    assert len(items) == 12 and all(i["payload"]["india_only"] for i in items)
    p = items[0]["payload"]
    recs, _ = _water("water_tn", "water_tn_ee0.html", p)
    ee = recs["dept:water_tn:TN-TWAD-executive-engineer-project-division-karur"]
    assert ee["level"] == "division" and ee["area"] == "Project Division, Karur" and ee["email"] == "eeprojkarur.twad@tn.gov.in"
    assert ee["address"].endswith("- 639008") and ",," not in ee["address"]
    p = next(i["payload"] for i in items if i["payload"]["rank"] == "chief-engineer")
    recs, _ = _water("water_tn", "water_tn_ce.html", p)
    ce = recs["dept:water_tn:TN-TWAD-chief-engineer-twad-board-madurai"]
    assert ce["level"] == "zone" and ce["area"] == "Madurai" and ce["phone"] == "0452-2582054"


def test_water_rj():
    recs, _ = _water("water_rj", "water_rj_directory.html")
    ee = recs["dept:water_rj:RJ-PHED-e-e-city-dn-south-i-gandhi-nagar-jaipur"]
    assert ee["name"] == "SH. KRISHAN KANT GUPTA" and ee["phone"] == "9166619700, 0141-2705173"
    assert ee["level"] == "division" and ee["email"] == "eesouth1.jai.phed@rajasthan.gov.in"
    assert not any("chief-minister" in k for k in recs)
    wsso = recs["dept:water_rj:RJ-PHED-ee-wsso-i-jaipur"]
    assert wsso["phone"] == "8279108611" and wsso["level"] == "division" and wsso["district"] == "Jaipur"
    from dforms.water_rj import person
    assert person("VACANT( Additional Charges SH. HIMANSHU MEEL 9414266006)") == ("HIMANSHU MEEL (additional charge)", "9414266006")


def test_water_mh():
    recs, _ = _water("water_mh", "water_mh_whoswho.html")
    ce = recs["dept:water_mh:MH-MJP-region-kokan:chief-engineer"]
    assert ce["level"] == "zone" and ce["area"] == "Kokan" and ce["email"] == "ce.mjp-thane@mah.gov.in"
    se = recs["dept:water_mh:MH-MJP-region-kokan:superintending-engineer-thane"]
    assert se["level"] == "circle" and se["area"] == "Thane" and se["name"] == "Mr. Tanmay Kamble (Incharge)"
    assert recs["dept:water_mh:MH-MJP-headquarters-finance:director-finance"]["level"] == "state"


def test_water_hr():
    recs, _ = _water("water_hr", "water_hr_teldir.pdf")
    se = recs["dept:water_hr:HR-PHED-ambala-circle"]
    assert se["level"] == "circle" and se["name"] == "Sh.Vikas Balyan" and se["phone"] == "9996671716, 0171-2601273"
    assert se["last_updated"] == "2026-11-02"
    assert recs["dept:water_hr:HR-PHED-hisar-phed-no-2"]["email"] == "ee2hisar@phedharyana.gov.in"
    assert "name" not in recs["dept:water_hr:HR-PHED-sonipat-circle"]           # "Vacant"


def test_water_hp():
    recs, get = _water("water_hp", "water_hp_jsv.html")
    assert get.calls[0][0] == "POST" and get.calls[0][2]["DepartmentId"] == "B22"
    ee = recs["dept:water_hp:HP-JSV-executive-engineer-d-hamirpur"]
    assert ee["name"] == "Er. Anup Kumar" and ee["phone"] == "01972222846, 9418016171" and ee["level"] == "division"
    assert recs["dept:water_hp:HP-JSV-s-e-dharampur"]["level"] == "circle"
    assert recs["dept:water_hp:HP-JSV-engineer-in-chief"]["email"] == "eespiph@gmail.com"
    assert not any(k.endswith(":p-a") or k.endswith("-p-a") for k in recs)
