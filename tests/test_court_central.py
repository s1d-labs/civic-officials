"""Offline tests of the court and central-government readers (dforms/court_dcourts.py, dforms/central_*.py) and their seeds.
Samples in tests/data/court_dcourts_* and central_* are cut from archive.s1d.me copies (2026-11-05/06) or, for EPFO and the
IFSC list, from one live answer (2026-11-11). No test touches the network."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod

SEEDS = ROOT / "seeds"


# ---- district courts (dcourts.gov.in) ----
def test_court_fetch_judges_and_contacts():
    m = mod("court_dcourts")
    base = "https://patna.dcourts.gov.in/"
    get = fake_get({base + "list-of-judges/": "court_dcourts_patna_judges.html",
                    base + "contact-us/": "court_dcourts_kabirdham_contact.html"})
    recs, files, why = m.fetch({"url": base, "state": "BR", "district": "Patna"}, get)
    assert why == ""
    assert [f[0] for f in files] == ["depts/court_dcourts/patna.dcourts.gov.in-list-of-judges.html.gz",
                                     "depts/court_dcourts/patna.dcourts.gov.in-contact-us.html.gz"]
    check_records(recs, "court_dcourts", "courts")
    judges = [d for _, d in recs if d["kind"] == "judge"]
    assert len(judges) == 6
    d = judges[0]
    assert (d["name"], d["room"], d["location"], d["area"]) == ("ANAMIKA T.", "1", "Patna Sadar", "PATNA SADAR, CIVIL COURT")
    assert d["post"].startswith("Principal District & Sessions Judge") and d["level"] == "district"
    assert d["profile"] == "https://patna.dcourts.gov.in/Judges/ms-anamika-t/" and d["last_updated"] == "2026-11-04"
    barh = [d for d in judges if d["area"] == "SUB DIVISIONAL COURT BARH"]
    assert len(barh) == 3 and all(d["level"] == "subdivision" and d["town"] == "Barh" for d in barh)
    offices = [d for _, d in recs if d["kind"] == "office"]
    assert [(d.get("name"), d["email"]) for d in offices] == [
        ("Rajju Soni", "kabirdham.court@nic.in"), ("Dinesh Somawar", "fmlycrt-kwd@cg.gov.in"), (None, "pandariya.court-cg@gov.in")]
    assert offices[0]["post"] == "Administrative Officer" and offices[0]["phone"].startswith("07741-233480")
    assert offices[2]["area"] == "Civil Court Pandariya" and offices[2]["phone"] == "07754-254447"


def test_court_judges_two_columns():
    m = mod("court_dcourts")
    recs = m.judges((DATA / "court_dcourts_pune_judges.html").read_text(), "https://pune.dcourts.gov.in/list-of-judges/",
                    {"state": "MH", "district": "Pune"})
    assert len(recs) == 6
    d = recs[0][1]
    assert (d["name"], d["post"], d["area"]) == ("A. S. Shende", "Principal District Judge and Sessions Judge, Pune",
                                                   "District and Sessions Court, Pune")
    assert recs[3][1]["area"] == "Small Causes Court, Pune"


def test_court_contact_table():
    m = mod("court_dcourts")
    recs = m.contacts((DATA / "court_dcourts_ranipet_contact.html").read_text(), "https://ranipet.dcourts.gov.in/contact-us/",
                      {"state": "TN", "district": "Ranipet"})
    assert [d["email"] for _, d in recs] == ["rpt.pdc-tn@indiancourts.nic.in", "vlrrpt.adc2-tn@indiancourts.nic.in"]
    assert recs[0][1]["address"] == "Combined Court Building,Opposite to EID Parrys, Ranipet – 632401"
    assert recs[0][1]["area"] == "Principal District Court, Ranipet"


def test_court_helpers():
    m = mod("court_dcourts")
    assert m.person("MS. ANAMIKA T.") == "ANAMIKA T." and m.person("MD. RUSTAM") == "MD. RUSTAM"
    assert m.person("SHAILENDRA KUMAR- II") == "SHAILENDRA KUMAR- II" and m.person("Mr. Mr. Jawad Ahmed") == "Jawad Ahmed"
    assert m.town_of("Prakasam", "Civil Judge [Junior Division], Darsi") == "Darsi"
    assert m.town_of("Solapur", "Civil and Criminal Court, Akkalkot,Solapur") == "Akkalkot"
    assert m.town_of("Patna", "District & Additional Sessions Judge-V, Patna") is None
    assert m.town_of("Patna", "PATNA SADAR, CIVIL COURT") is None


def test_court_seed():
    its = json.loads((SEEDS / "dept_court_dcourts.json").read_text())
    assert len(its) == 731 and len({i["key"] for i in its}) == 731
    for i in its:
        p = i["payload"]
        assert p["reader"] == "court_dcourts" and p["url"].startswith("https://") and ".dcourts.gov.in/" in p["url"]
        assert len(p["state"]) == 2 and p["district"]


# ---- bank branches (IFSC list) ----
def test_banking():
    m = mod("central_banking")
    url = "https://github.com/razorpay/ifsc/releases/download/v2.0.62/IFSC.csv"
    recs, files, why = m.fetch({"url": url, "state": "GJ"}, fake_get({url: "central_banking_ifsc.csv"}))
    assert why == "" and len(recs) == 8 and files[0][0] == "depts/central_banking/IFSC-GJ.csv.gz"
    check_records(recs, "central_banking", "banking")
    rid, d = recs[1]
    assert rid == "dept:central_banking:AANB0000002"
    assert (d["area"], d["district"], d["phone"], d["micr"], d["bank_code"]) == (
        "KATARGAM BRANCH", "SURAT", "+912612536772", "395437002", "AANB")
    assert d["address"] == "BESIDES ANATH BALASHRAM,KATARGAM MAIN ROAD,KATARGAM,SURAT-395004"
    recs, _, why = m.fetch({"url": url, "state": "MH"}, fake_get({url: "central_banking_ifsc.csv"}))
    assert recs == [] and why == "no rows for the state"
    its = json.loads((SEEDS / "dept_central_banking.json").read_text())
    assert len(its) == 36 and {i["payload"]["url"] for i in its} == {url}


# ---- GST / CBIC ----
def test_gst_mumbai():
    m = mod("central_gst")
    url = "https://cgstmumbai.gov.in/en/commissionerate/executive/thane"
    p = {"url": url, "state": "MH", "zone": "mumbai", "area": "CGST Thane (Executive Commissionerate)", "std": "022"}
    recs, files, why = m.fetch(p, fake_get({url: "central_gst_mumbai_thane.html"}))
    assert why == "" and len(recs) == 3
    check_records(recs, "central_gst", "gst")
    d = recs[0][1]
    assert (d["name"], d["post"], d["phone"], d["email"]) == ("Akhilesh Pandey", "Commissioner", "022-20818595", "akhilesh.p78@gov.in")
    assert d["address"].startswith("Office of the Commissioner of CGST & C.Ex., Mumbai Thane, ACCEL House")
    assert recs[1][1]["name"] == "Sarika Shah" and "phone" not in recs[2][1]
    assert len(json.loads((SEEDS / "dept_central_gst.json").read_text())) == 21


# ---- EPFO ----
def test_epfo_directory():
    m = mod("central_social_security")
    url = "https://www.epfo.gov.in/directory/"
    recs, files, why = m.fetch({"url": url, "india_only": True}, fake_get({url: "central_social_security_epfo.html"}))
    assert why == "" and len(recs) == 10
    by = dict(recs)
    o = by["dept:central_social_security:epfo:district-1-1-3"]
    assert (o["area"], o["level"], o["email"], o["std_code"]) == ("Tirupati", "district", "dpfo.tirupati@epfindia.gov.in", "0877")
    d = by["dept:central_social_security:epfo:district-1-1-3:satish-kumar-b-t"]
    assert (d["post"], d["phone"], d["charge"]) == ("Regional P. F. Commissioner (Gr.II)", "0877-2225591", "Additional Charge")
    assert by["dept:central_social_security:epfo:sub_zone-1-1"]["level"] == "division"
    assert by["dept:central_social_security:epfo:zone1:inakoti-sridevi"]["phone"] == "0866-2576700"
    assert all(d["dept"] == "social_security" and d["source"] == url for d in by.values())


# ---- RTO ----
def test_transport_uk():
    m = mod("central_transport")
    url = "https://transport.uk.gov.in/organization/office-dehradun/"
    recs, files, why = m.fetch({"url": url, "state": "UK", "site": "uk", "district": "Dehradun"},
                               fake_get({url: "central_transport_uk_dehradun.html"}))
    assert why == "" and len(recs) == 5
    check_records(recs, "central_transport", "transport")
    o = recs[0][1]
    assert (o["phone"], o["email"], o["registration_code"], o["last_updated"]) == (
        "0135-2743432", "rtodeh-trans-uk@nic.in", "UK07", "2026-07-06")
    d = recs[1][1]
    assert (d["name"], d["post"], d["email"]) == (
        "Sandeep Saini", "Regional Transport Officer (Administration)", "rtodeh-trans-uk@nic.in, dehradunrto@gmail.com")


def test_transport_mh():
    m = mod("central_transport")
    url = "https://transport.maharashtra.gov.in/1184/Regional-Offices"
    recs, files, why = m.fetch({"url": url, "state": "MH", "site": "mh"}, fake_get({url: "central_transport_mh.html"}))
    assert why == "" and len(recs) == 4
    d = recs[0][1]
    assert (d["area"], d["area_regional"], d["phone"]) == ("MH-01", "मुंबई (मध्य)", "022-23551515, 23551511")
    assert d["email"] == "rto.01-mh@gov.in, mh01@mahatranscom.in"
    assert m.split("mh01@mahatranscom.inrto.01-mh@gov.in") == "mh01@mahatranscom.in rto.01-mh@gov.in"
    its = json.loads((SEEDS / "dept_central_transport.json").read_text())
    assert len(its) == 17 and {i["payload"]["site"] for i in its} == {"uk", "mh"}
