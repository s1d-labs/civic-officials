"""Electricity and water readers, second round (dforms/power2_*.py, dforms/water2_*.py) on small saved answers in
tests/data/util2: no network. One fake get() for all readers."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "tests" / "data" / "util2"
LEVELS = ("state", "zone", "circle", "district", "division", "subdivision", "section", "block", "subdistrict", "ward", "body")


class Resp:
    def __init__(self, content, url=""):
        self.content, self.status_code, self.url, self.encoding = content, 200, url, "utf-8"
        self.text = content.decode("utf-8", "replace")
        self.headers = {}

    def json(self):
        return json.loads(self.text)


def fake_get(routes, calls=None):
    """routes: [(method or None, url substring, file name in DATA or bytes)]; None when no route matches."""
    def get(url, method="GET", data=None, headers=None):
        if calls is not None:
            calls.append((method, url, data))
        for m, sub, f in routes:
            if sub in url and (m is None or m == method):
                return Resp(f if isinstance(f, bytes) else (DATA / f).read_bytes(), url)
        return None
    return get


def check(recs, module, dept):
    ids = [i for i, _ in recs]
    assert ids, "no records"
    assert len(ids) == len(set(ids)), "record ids must be unique"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:"), rid
        assert d["type"] == "dept_office" and d["dept"] == dept, d
        assert d["level"] in LEVELS, d["level"]
        assert d.get("area"), d
    return Counter(d["level"] for _, d in recs)


# ======== group a_mp


# ---- Madhya Pradesh

def test_power2_mpcz_harda():
    from dforms import power2_mpcz
    url = power2_mpcz.BASE + "oNmHarda.pdf"
    recs, files, why = power2_mpcz.fetch({"reader": "power2_mpcz", "file": "oNmHarda", "url": url},
                                         fake_get([(None, "oNmHarda.pdf", "power2_mpcz_oNmHarda.pdf")]))
    assert why == "" and files[0][0] == "depts/power/power2_mpcz/oNmHarda.pdf"
    lv = check(recs, "power2_mpcz", "electricity")
    assert lv["section"] >= 12 and lv["division"] >= 3 and lv["subdivision"] >= 2
    by = {d["name"]: d for _, d in recs if d.get("name")}
    d = by["Pawan Baraskar"]          # JE of Harda North D/c, under Harda Rural S/D and (O&M) Dn. Harda North (merged cells)
    assert (d["level"], d["area"], d["phone"]) == ("section", "Harda North", "6232914072")
    assert d["parents"] == {"circle": "O&M Circle Harda", "division": "Harda North", "subdivision": "Harda Rural"}
    assert by["Ankit Patel"]["level"] == "subdivision" and by["Ankit Patel"]["area"] == "Harda Rural"
    assert by["Suresh Kumar"]["post"] == "General Manager" and by["Suresh Kumar"]["email"] == "mpczgmharda@gmail.com"
    assert d["last_updated"] == "2026-10-15" and d["district"] == "Harda"
    assert len(power2_mpcz.items()) == 23


# ---- coordinator modules: Sikkim, PSPCL heads of offices, WBSEDCL telephone list, Gujarat key officials

def test_power2_sikkim_officers_and_cells():
    from dforms import power2_sikkim
    recs, files, why = power2_sikkim.fetch({"reader": "power2_sikkim", "page": "officers", "url": power2_sikkim.BASE + "listofofficers"},
                                           fake_get([(None, "listofofficers", "power2_sikkim_officers.html")]))
    assert why == "" and check(recs, "power2_sikkim", "electricity") == {"state": 7}
    d = recs[0][1]
    assert (d["name"], d["post"], d["phone"]) == ("Bikash Deokota", "PCE cum Secretary", "8145172149, 7501191889")
    recs, _, why = power2_sikkim.fetch({"reader": "power2_sikkim", "page": "cell", "url": power2_sikkim.BASE + "divisioncell/10"},
                                       fake_get([(None, "divisioncell/10", "power2_sikkim_cell10.html")]))
    lv = check(recs, "power2_sikkim", "electricity")
    assert lv["circle"] == 3 and lv["division"] >= 5
    by = {d["name"]: d for _, d in recs}
    # paragraphs line up by position: the second officer of REVENUE-II has the first number (an empty paragraph leads the phones)
    assert by["Jigme Bhutia"]["phone"] == "9002968800" and by["Jigme Bhutia"]["area"] == "REVENUE-II"
    assert by["Purnima Kharel"]["level"] == "circle" and "phone" not in by["Purnima Kharel"]
    assert len(power2_sikkim.items()) == 13


def test_power2_pspcl_hods():
    from dforms import power2_pspcl
    recs, files, why = power2_pspcl.fetch({"reader": "power2_pspcl", "url": power2_pspcl.URL},
                                          fake_get([(None, "Contact-Hods", "power2_pspcl_hods.html")]))
    lv = check(recs, "power2_pspcl", "electricity")
    assert why == "" and lv["zone"] >= 4 and lv["circle"] >= 5
    circ = [d for _, d in recs if d["area"] == "DISTRIBUTION CITY CIRCLE, PSPCL, AMRITSAR" and d["post"] == "Dy.CE"][0]
    assert circ["email"] == "se-ds-asr@pspcl.in" and circ["phone"].startswith("96461-13004")
    assert circ["parents"] == {"zone": "ENGINEER-IN-CHIEF/DS(BORDER), AMRITSAR"} and circ["district"] == "Amritsar"
    assert not any(d.get("name") for _, d in recs)          # the page gives posts, not names


def test_power2_wbsedcl_phones():
    from dforms import power2_wbsedcl
    recs, files, why = power2_wbsedcl.fetch({"reader": "power2_wbsedcl", "url": power2_wbsedcl.URL},
                                            fake_get([(None, "Imp_Phone_Number", "power2_wbsedcl_phones.html")]))
    lv = check(recs, "power2_wbsedcl", "electricity")
    assert why == "" and lv["zone"] == 5 and lv["circle"] >= 10
    by = {(d["level"], d["area"]): d for _, d in recs}
    assert by[("zone", "Kolkata")]["phone"] == "(033)2262-2641/40"
    assert by[("circle", "Howrah")]["phone"] == "(033)2637-0458"


def test_power2_gujarat_cards():
    from dforms import power2_gujarat
    recs, _, why = power2_gujarat.fetch({"reader": "power2_gujarat", "page": "mgvcl", "url": power2_gujarat.PAGES["mgvcl"][1]},
                                        fake_get([(None, "mgvcl.com", "power2_gujarat_mgvcl.html")]))
    lv = check(recs, "power2_gujarat", "electricity")
    assert why == "" and lv["state"] == 3 and lv["circle"] >= 1
    by = {d["name"]: d for _, d in recs}
    assert (by["Shivani Goyal"]["post"], by["Shivani Goyal"]["phone"], by["Shivani Goyal"]["email"]) == \
        ("Managing Director", "0265-2356824", "md.mgvcl@gebmail.com")
    se = by["P. N. Thanawala"]
    assert (se["level"], se["area"], se["phone"]) == ("circle", "Baroda City Circle", "0265-2416270")
    recs, _, why = power2_gujarat.fetch({"reader": "power2_gujarat", "page": "ugvcl", "url": power2_gujarat.PAGES["ugvcl"][1]},
                                        fake_get([(None, "ugvcl.com", "power2_gujarat_ugvcl.html")]))
    assert why == "" and check(recs, "power2_gujarat", "electricity") == {"state": 3}
    assert all(d.get("email", "").endswith("@ugvcl.com") for _, d in recs)


def test_power2_sikkim_staff():
    from dforms import power2_sikkim
    recs, files, why = power2_sikkim.fetch({"reader": "power2_sikkim", "page": "staff", "url": power2_sikkim.BASE + "stafflists"},
                                           fake_get([(None, "stafflists", "power2_sikkim_staff.html")]))
    assert why == "" and files[0][0] == "depts/power/power2_sikkim/staff.html.gz"
    lv = check(recs, "power2_sikkim", "electricity")
    assert lv["circle"] >= 2 and lv["division"] >= 3
    by = {d["name"]: d for _, d in recs}
    assert (by["PRANAY KARKI"]["level"], by["PRANAY KARKI"]["area"], by["PRANAY KARKI"]["phone"]) == ("circle", "GANGTOK-HQ-I", "9647874671")
    ad = by["MALA PRADHAN"]                      # office staff with a sub-division: the sub-division office
    assert (ad["level"], ad["area"], ad["parents"]) == ("subdivision", "Gangtok", {"circle": "GANGTOK-HQ-I"})
    ace = by["Bishnu Kumar Rai"]                 # the Gyalshing table has an e-mail column
    assert ace["email"] == "sagbrishab@yahoo.com" and ace["level"] == "circle" and ace["phone"] == "7865890586"
    assert any(k["payload"]["page"] == "staff" for k in power2_sikkim.items())


# ======== group ka_gj


# ---- group ka_gj: BESCOM, GESCOM (Karnataka), UGVCL sub-divisions (Gujarat) ----

def test_power2_bescom_field_officers():
    from dforms import power2_bescom
    calls = []
    recs, files, why = power2_bescom.fetch({"reader": "power2_bescom"}, fake_get([(None, "media_to_upload1757575623", "power2_bescom.xlsx")], calls))
    assert why == "" and files[0][0].endswith(".xlsx")
    lv = check(recs, "power2_bescom", "electricity")
    assert lv["zone"] == 3 and lv["subdivision"] == 5 and lv["section"] == 12
    d = dict(recs)
    z = d["dept:power2_bescom:zone-bmaz-north"]
    assert z["name"] == "Sri. Basavaraj Patil" and z["phone"] == "8277892599" and z["email"] == "ceenz@bescom.co.in"
    c = d["dept:power2_bescom:circle-bmaz-north-north"]
    assert c["phone"] == "9449844988, 080-22350436"          # a mobile broken over two lines in the cell
    s = [x for k, x in recs if x["level"] == "section" and x["area"] == "ABBIGERE"]
    assert [(x["post"], x["name"], x["phone"]) for x in s] == [
        ("Assistant Engineer", "Sri. Manjunath", "9449864538"), ("Junior Engineer", "Sri.Somashekar reddy", "9448432824"),
        ("Junior Engineer", "Sri. Vasudeva", "9449864539")]
    assert s[0]["parents"] == {"zone": "BMAZ NORTH", "circle": "North", "division": "Jalahalli", "subdivision": "C3"}
    assert s[0]["email"] == "aeabbigerec3@gmail.com" and s[0]["areas"].startswith("Abbigere")
    dv = d["dept:power2_bescom:division-bmaz-south-south-koramangala"]
    assert dv["email"] == "eeadnlsouth.work@gmail.com, eekormangala@bescom.co.in"  # "besc\nom.co.in" mended
    t = [x for x in recs if x[1]["area"] == "TALAK"][0][1]   # Table 7 has no header: the previous sheet's columns
    assert t["name"] == "Surlingappa" and t["post"] == "Junior Engineer" and t["district"] == "Bengaluru urban"


def test_power2_bescom_people_cells():
    from dforms.power2_bescom import people
    assert people("(EE)/Ramachandra 9448279015/08193 229533/(eehiriyuru@bescom.co.in) eehyrdvn.work@gmail.com") == [
        ("EE", "Ramachandra", ["9448279015", "08193-229533"], ["eehiriyuru@bescom.co.in", "eehyrdvn.work@gmail.com"])]
    p = people("AE MANGE GOWDARU 9449840452JE Sri.\naeadugodi_s4@bescom.co.in Girish (inch JE ) 9986775194")
    assert [(a, b, c) for a, b, c, _ in p] == [("AE", "MANGE GOWDARU", ["9449840452"]), ("JE", "Sri. Girish", ["9986775194"])]
    assert people("") == []


def test_power2_gescom_divisions():
    from dforms import power2_gescom
    recs, files, why = power2_gescom.fetch({"reader": "power2_gescom", "page": "divisions"},
                                           fake_get([(None, "o&m-division", "power2_gescom_divisions.html")]))
    assert why == ""
    lv = check(recs, "power2_gescom", "electricity")
    assert lv == {"division": 17}
    d = {x["area"]: x for _, x in recs}
    assert d["KALABURAGI CITY"]["phone"] == "9449597321" and d["KALABURAGI CITY"]["post"] == "Executive Engineer (Elec.)"
    assert d["SHORAPUR"]["post"] == "Assistant Executive Engineer (Elec.)"


def test_power2_gescom_emails_pdf():
    from dforms import power2_gescom
    recs, files, why = power2_gescom.fetch({"reader": "power2_gescom", "page": "emails"},
                                           fake_get([(None, "Mail%20ids", "power2_gescom_emails.pdf")]))
    assert why == "" and files[0][0].endswith(".pdf")
    lv = check(recs, "power2_gescom", "electricity")
    assert lv["zone"] == 2 and lv["circle"] == 5 and lv["subdivision"] >= 20
    d = {(x["level"], x["area"]): x for _, x in recs}
    assert d[("zone", "Kalaburagi")]["email"] == "ceezoneklb@gescom.in, cegulbarga@gmail.com"
    assert d[("circle", "Ballari")]["office_name"] == "SEEO&MCircleOfficeBallari"
    assert d[("subdivision", "CSD-1Klb")]["email"] == "aeecsd1klb@gescom.in, aeecsd1glb@gmail.com"


def test_power2_gj_subdiv_ugvcl():
    from dforms import power2_gj_subdiv
    recs, files, why = power2_gj_subdiv.fetch({"reader": "power2_gj_subdiv", "discom": "ugvcl"},
                                              fake_get([(None, "ugvcl.com/contact", "power2_gj_subdiv_ugvcl.html")]))
    assert why == ""
    lv = check(recs, "power2_gj_subdiv", "electricity")
    assert lv["subdivision"] == 12 and lv["circle"] == 5
    d = dict(recs)
    k = d["dept:power2_gj_subdiv:ugvcl-mehsana-kadi-kadi-1-deputy-engineer-mr-g-m-patel"]
    assert k["area"] == "KADI-1" and k["name"] == "MR.G.M.PATEL" and k["parents"] == {"circle": "MEHSANA", "division": "KADI"}
    se = [x for _, x in recs if x["post"] == "Superintending Engineer"]
    assert [x["name"] for x in se] == ["Mr.A.P.PATEL", "Shri C.J. Rajpal"]   # a repeated row is read once


# ======== group mp_cg
# ---- Madhya Pradesh and Chhattisgarh (group mp_cg)
# No new readers from this group. MPCZ (power2_mpcz) is the coordinator's reader; its test is in a_mp.py.
# MPWZ, MPEZ, CSPDCL, MP PHED, MP Jal Nigam, CG PHED and the Bhopal / Indore / Jabalpur / Gwalior water departments have no
# public, readable officer list on 2026-11-11 (evidence in the mp_cg report). This fragment holds no tests.


# ======== group up_dl


# ---- group up_dl: KESCO, NPCL, Tata Power-DDL, BSES, UP Jal Nigam (Rural) ----

def test_power2_kesco_directory():
    from dforms import power2_kesco
    calls = []
    get = fake_get([(None, "kesco.org.in/about/employee-directory", "power2_kesco_dir.html")], calls)
    recs, files, why = power2_kesco.fetch({"url": power2_kesco.URL}, get)
    assert why == "" and files and len(calls) == 1
    lv = check(recs, "power2_kesco", "electricity")
    assert lv["division"] >= 1 and lv["subdivision"] >= 2 and lv["section"] >= 4 and lv["circle"] == 1 and lv["zone"] >= 1
    d = {r["name"]: r for _, r in recs if r.get("name")}
    ee = d["Sri. Nand Kishore"]
    assert ee["level"] == "division" and ee["phone"] == "9151890159" and ee["email"] == "xen1.11kv@kesco.org.in"
    assert ee["area"] == "kalyanpur" and ee["parents"]["circle"] == "Technical" and ee["last_updated"] == "2026-07-27"
    ae = d["SUSHEEL KUMAR PRAJAPATI"]
    assert ae["level"] == "subdivision" and ae["parents"]["division"] == "kalyanpur" and ae["phone"] == "9151895717"
    je = d["Abhinay Kumar Mishra"]
    assert je["level"] == "section" and je["parents"]["subdivision"] == "Substation GIC"
    assert d["Neha Jain"]["level"] == "zone" and d["Neha Jain"]["post"] == "MD KESCo"
    assert d["Sri P.K. Singh"]["level"] == "circle"
    sso = [r for _, r in recs if r["post"].startswith("Sub-station Operator")]
    assert sso and "name" not in sso[0] and sso[0]["area"] == "MALL ROAD" and sso[0]["phone"] == "9919373444"
    assert not any(r["post"].startswith("Asisstant Accountant") for _, r in recs)     # staff posts are left out
    assert all(r["district"] == "Kanpur Nagar" and r["discom"] == "KESCO" for _, r in recs)


def test_power2_npcl_contact_tables():
    import gzip
    from dforms import power2_npcl
    js = gzip.decompress((DATA / "power2_npcl_main.js.gz").read_bytes())
    calls = []
    get = fake_get([(None, "/static/js/main.061941a7.js", js), (None, "noidapower.com/contact-us", "power2_npcl_contact.html")],
                   calls)
    recs, files, why = power2_npcl.fetch({"url": power2_npcl.URL}, get)
    assert why == "" and len(files) == 2 and len(calls) == 2
    lv = check(recs, "power2_npcl", "electricity")
    assert lv["subdivision"] == 6 and len(recs) == 22
    d = {(r.get("desk"), r["name"]): r for _, r in recs}
    z1 = d[("Zone-1 Head", "Mr. Sushil Kumar Sonar")]
    assert z1["level"] == "zone" and z1["area"] == "Zone-1" and z1["phone"] == "7834807046"
    fbu = [r for _, r in recs if r["area"].startswith("FBU Kasna")][0]
    assert fbu["name"] == "Mr. Ishfaq Ahmad Beigh" and fbu["phone"] == "8287840217" and fbu["parents"] == {"zone": "Zone-2"}
    u2 = [r for _, r in recs if r["area"].startswith("Urban-2")][0]          # rowspan: the Urban-1 officer covers Urban-2 too
    assert u2["name"] == "Mr. Tarun Chauhan" and u2["phone"] == "9911998208"
    cr = [r for _, r in recs if r.get("function") == "Customer Relation"]
    assert len(cr) == 4 and {r["name"] for r in cr} >= {"Mr. Tarun Goel", "Ms. Meghna Dosi"}


def test_power2_tpddl_charter_and_ccc():
    from dforms import power2_tpddl
    text = (DATA / "power2_tpddl_charter_p6.txt").read_text()
    recs = power2_tpddl.parse_charter(text)
    lv = check(recs, "power2_tpddl", "electricity")
    assert lv["district"] == 13
    d = {r["area"]: r for _, r in recs}
    assert d["Keshavpuram District"]["name"] == "Mr. Kishan Lal Chauhan"
    assert d["Rohini District"]["address"].startswith("District Office Rohini, 3/9")
    assert "name" not in d["Shalimar Bagh District"] and d["Dheerpur District"]["name"] == "Mr. Rajender Nirwan"
    assert d["Narela District"]["name"] == "Mr. Rajbeer Singh Serwa"
    ccc = power2_tpddl.parse_ccc((DATA / "power2_tpddl_ccc_p1.txt").read_text())
    check(ccc, "power2_tpddl", "electricity")
    p = {r["area"]: r["phone"] for _, r in ccc}
    assert p["Moti Nagar District"] == "011-66233443" and p["Shalimar Bagh District"] == "9643512592" and len(p) == 12
    # fetch() with a PDF answer: the page text comes from pdf_pages
    orig = power2_tpddl.pdf_pages
    try:
        power2_tpddl.pdf_pages = lambda content, layout=True: ["cover", text]
        recs2, files, why = power2_tpddl.fetch({"part": "charter"}, fake_get([(None, "Customer_Charter_2025", b"%PDF-1.5 x")]))
    finally:
        power2_tpddl.pdf_pages = orig
    assert why == "" and len(recs2) == 13 and files[0][0].endswith(".pdf")


def test_power2_bses_divisions_and_items():
    from dforms import power2_bses
    get = fake_get([(None, "/web/brpl/contact-customer-care", "power2_bses_brpl_contact.html"),
                    (None, "/web/brpl/divisional-offices", "power2_bses_brpl_div.html")])
    its = power2_bses.items(get)
    keys = {i["key"] for i in its}
    assert keys == {"power2_bses:brpl:divisional", "power2_bses:brpl:subdivision", "power2_bses:brpl:om"}
    p = next(i["payload"] for i in its if i["key"].endswith(":divisional"))
    recs, files, why = power2_bses.fetch(p, get)
    assert why == "" and files
    lv = check(recs, "power2_bses", "electricity")
    assert lv["division"] == 5
    d = {r["area"]: r for _, r in recs}
    assert d["Khanpur"]["address"].startswith("BSES Sub-Station Southend Apartment")
    assert d["Alaknanda"]["discom"] == "BSES Rajdhani Power Limited" and d["Alaknanda"]["post"] == "Division Office"


def test_water2_upjn_staff_directory():
    from dforms import water2_upjn
    recs, files, why = water2_upjn.fetch({"url": water2_upjn.URL},
                                         fake_get([(None, "upjn.co.in/Contact/StaffDirectory", "water2_upjn_staff.html")]))
    assert why == "" and files
    lv = check(recs, "water2_upjn", "water")
    assert lv["zone"] >= 2 and lv["circle"] >= 4 and lv["division"] >= 20
    d = {(r["cadre"], r["level"], r["area"]): r for _, r in recs}
    ce = d[("civil", "zone", "लखनऊ क्षेत्र")]
    assert ce["name"] == "अरुण कुमार सिंह" and ce["phone"] == "9151919605" and ce["post"] == "Chief Engineer (Zone)"
    se = d[("civil", "circle", "लखनऊ मण्डल")]
    assert se["phone"] == "9473942583" and se["parents"] == {"zone": "लखनऊ क्षेत्र"}
    ee = d[("civil", "division", "उन्नाव")]
    assert ee["name"] == "अजीत कुमार सिंह" and ee["phone"] == "9473942560" and ee["district"] == "उन्नाव"
    assert ee["parents"] == {"zone": "लखनऊ क्षेत्र", "circle": "लखनऊ मण्डल"} and ee["name_regional"] == ee["name"]
    em = d[("electrical-mechanical", "division", "खण्ड कार्यालय (वि०/यां०) लखनऊ")]
    assert em["name"] == "श्री सै० मो० शावाज" and em["phone"] == "9151919633" and "उन्नाव" in em["districts"]
    assert all(r["org"] == "UP Jal Nigam (Rural)" and r["state"] == "UP" for _, r in recs)


# ======== group east


# ---- group east: TP Odisha discoms, CESC, MSPDCL, WBSEDCL officers by name ----

def _east_text_pages(name):
    import gzip
    return gzip.decompress((DATA / name).read_bytes()).decode("utf-8").split("\f")


def test_power2_tpodisha_tpnodl_xlsx():
    from dforms import power2_tpodisha
    p = {"reader": "power2_tpodisha", "discom": "TPNODL", "kind": "xlsx",
         "url": "https://www.tpnodl.com/xl/contact/Worksheet-in-TPNODL-Contact-Us.xlsx", "state": "OD"}
    recs, files, why = power2_tpodisha.fetch(p, fake_get([(None, "Worksheet-in-TPNODL", "power2_tpodisha_tpnodl.xlsx")]))
    assert why == "" and files[0][0].endswith(".xlsx")
    assert check(recs, "power2_tpodisha", "electricity") == {"circle": 5, "division": 16}
    d = dict(recs)
    c = d["dept:power2_tpodisha:tpnodl-circle-balasore-sidhartha-shankar-ray"]
    assert c["phone"] == "9438906090" and c["email"] == "sidhartha.ray@tpnodl.com, se.balasore@tpnodl.com"
    v = d["dept:power2_tpodisha:tpnodl-division-aed-anandapur-minaketan-samal"]
    assert v["phone"] == "9438906110" and v["parents"] == {"circle": "Keonjhar"} and v["post"] == "Executive Engineer"
    assert power2_tpodisha.fetch(p, fake_get([(None, "Worksheet", b"<html>Request Rejected</html>")]))[2] == "not a spreadsheet"


def test_power2_tpodisha_tpsodl_rti_manual(monkeypatch):
    from dforms import power2_tpodisha
    monkeypatch.setattr(power2_tpodisha, "layout_pages",
                        lambda content: (_east_text_pages("power2_tpodisha_tpsodl_layout.txt.gz"), "pdftotext"))
    p = {"reader": "power2_tpodisha", "discom": "TPSODL", "kind": "rti_manual",
         "url": "https://tpsouthernodisha.com/Editor_UploadedDocuments/Content/RTI_Eng_Manual16.09.2025.pdf", "state": "OD"}
    recs, files, why = power2_tpodisha.fetch(p, fake_get([(None, "RTI_Eng_Manual", b"%PDF-1.4 saved text is used")]))
    assert why == "" and files[0][2] == "application/pdf"
    lv = check(recs, "power2_tpodisha", "electricity")
    assert lv["state"] == 33 and lv["circle"] == 10 and lv["division"] == 20
    by = {d["name"]: d for _, d in recs}
    a = by["Archana Dhar"]
    assert a["area"] == "BED-II, BERHAMPUR" and a["phone"] == "9437959802" and a["email"] == "archana.dhar@tpsouthernodisha.com"
    assert a["parents"] == {"circle": "City"} and a["last_updated"] == "2025-09-15"
    assert by["Dnyaneshwar Dharmadhikari"]["email"] == "dnyaneshwar.dharmadhikari@tpsouthernodisha.com"   # cut over two lines
    assert by["Bijay Kumar Mohanty"]["post"] == "Chief Finance Officer & Regulatory"
    assert by["Hrudaya Ballabha Pradhan"]["area"] == "BED-III, BERHAMPUR" and by["Hrudaya Ballabha Pradhan"]["post"] == "Executive Engineer"
    assert by["Manmatha Nath Mishra"]["level"] == "circle" and by["Manmatha Nath Mishra"]["area"] == "Jeypore"
    assert by["Varun Choudhury"]["area"] == "JED, JEYPORE" and by["Bhagaban Pradhan"]["phone"] == "9437570037"
    assert by["T. Tapanrasmi Subudhi"]["email"] == "t.tapanrasmi.subudhi@tpsouthernodisha.com"


def test_power2_tpodisha_tpcodl_pio(monkeypatch):
    from dforms import power2_tpodisha
    monkeypatch.setattr(power2_tpodisha, "pdf_pages",
                        lambda content, layout=True: _east_text_pages("power2_tpodisha_tpcodl_pio.txt.gz"))
    p = {"reader": "power2_tpodisha", "discom": "TPCODL", "kind": "pio_pdf",
         "url": "https://www.tpcentralodisha.com/Editor_UploadedDocuments/RTI/PIO_Appellate_Authority.pdf", "state": "OD"}
    recs, files, why = power2_tpodisha.fetch(p, fake_get([(None, "PIO_Appellate", b"%PDF-1.7 saved text is used")]))
    assert why == ""
    assert check(recs, "power2_tpodisha", "electricity") == {"division": 20, "circle": 10, "state": 4}
    d = dict(recs)
    s = d["dept:power2_tpodisha:tpcodl-division-bcdd-1-bhubaneswar-simit-das"]
    assert s["email"] == "simit.das@tpcentralodisha.com" and s["parents"] == {"circle": "Bhubaneswar Circle-1"} and s["office_id"] == "108596"
    f = d["dept:power2_tpodisha:tpcodl-circle-cuttack-circle-amarjit-pattanaik"]
    assert f["email"] == "amarjit.pattanaik@tpcentralodisha.com" and "First Appellate" in f["post"]
    assert "dept:power2_tpodisha:tpcodl-division-ked-1-kendrapara-pratap-swain" in d


def test_power2_tpodisha_docx_and_items():
    import io
    import zipfile
    from dforms import _util2_east, power2_tpodisha
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

    def tr(*cells):
        return "<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in cells) + "</w:tr>"
    doc = (f"<w:document {w}><w:body><w:tbl>" + tr("Division", "Name", "Designation", "Mobile No", "Email") +
           tr("Test Division", "Mr Test Person", "Divisional Manager", "9000000001", "t.person@example.com") + "</w:tbl></w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", doc)
    assert _util2_east.docx_tables(buf.getvalue())[0][1][1] == "Mr Test Person"
    recs = power2_tpodisha.parse_docx(buf.getvalue(), "TPCODL", "u", "division")
    assert recs[0][1]["name"] == "Test Person" and recs[0][1]["phone"] == "9000000001"      # synthetic file: the reader's table logic only
    keys = [i["key"] for i in power2_tpodisha.items()]
    assert len(keys) == len(set(keys)) == 5 and all(i["payload"]["india_only"] for i in power2_tpodisha.items())


def test_power2_cesc_gro():
    from dforms import power2_cesc
    p = power2_cesc.items()[0]["payload"]
    recs, files, why = power2_cesc.fetch(p, fake_get([(None, "groCgro", "power2_cesc_gro.html")]))
    assert why == "" and check(recs, "power2_cesc", "electricity") == {"state": 4}
    d = dict(recs)
    r = d["dept:power2_cesc:ht-grievance-redressal-officers-ranadip-das"]
    assert r["email"] == "gro.commht@rpsg.in" and "Billing Related Issues" in r["post"] and r["address"].startswith("CESC House")
    assert d["dept:power2_cesc:central-grievance-redressal-officers-gopal-patra"]["email"] == "cgro1@rpsg.in"


def test_power2_mspdcl_who_is_who():
    from dforms import power2_mspdcl
    p = power2_mspdcl.items()[0]["payload"]
    assert "mspdcl.in/" in p["url"] and "mspdcl.com" not in p["url"]
    recs, files, why = power2_mspdcl.fetch(p, fake_get([(None, "who-is-who", "power2_mspdcl_who.html")]))
    assert why == ""
    lv = check(recs, "power2_mspdcl", "electricity")
    assert lv["state"] == 13 and lv["division"] >= 4
    d = dict(recs)
    b = d["dept:power2_mspdcl:electrical-division-ii-deputy-general-manager-bishnupur"]
    assert b["name"] == "Mairembam Birjit Singh" and b["email"] == "birjitm@gmail.com" and b["parents"] == {"circle": "Electrical Circle-II"}
    assert d["dept:power2_mspdcl:electrical-division-i-deputy-general-manager-ied-ii"]["area"] == "Imphal Electrical Division-II"


def test_power2_wbsedcl_rgro_pages():
    from dforms import power2_wbsedcl_rgro as w
    p = {"reader": "power2_wbsedcl_rgro", "page": "rgro", "url": w.BASE + w.PAGES["rgro"], "state": "WB"}
    recs, files, why = w.fetch(p, fake_get([(None, "Grievance_Redressal_for_consumers", "power2_wbsedcl_rgro.html")]))
    assert why == "" and check(recs, "power2_wbsedcl_rgro", "electricity") == {"circle": 3}
    d = dict(recs)["dept:power2_wbsedcl_rgro:rgro-bidhannagar"]
    assert d["name"] == "Priyangbada Sarkar" and d["phone"] == "(033) 23248415, 9230961519" and d["email"] == "rgro.bidhannagar@wbsedcl.in"
    p = {"reader": "power2_wbsedcl_rgro", "page": "ccc", "url": w.BASE + w.PAGES["ccc"], "state": "WB"}
    recs, files, why = w.fetch(p, fake_get([(None, "Contact_Customer_Care", "power2_wbsedcl_rgro_ccc.html")]))
    assert why == "" and check(recs, "power2_wbsedcl_rgro", "electricity") == {"section": 11}
    c = dict(recs)["dept:power2_wbsedcl_rgro:ccc-bidhan-nagar-ii-sarberia"]
    assert c["phone"] == "8697724422" and c["parents"] == {"division": "Bidhan Nagar-II"} and c["area"] == "Sarberia"
    assert dict(recs)["dept:power2_wbsedcl_rgro:ccc-bidhan-nagar-i-bidhannagar-i"]["phone"] == "2359-9215/2337-0887"


# ======== group pb_rj

# ---- group pb_rj: Punjab PSPCL offices (PIO list, hierarchy, complaint centres), PWSSB, DWSS


def test_power2_pspcl_offices_pio():
    from dforms import power2_pspcl_offices as m
    pages = (DATA / "power2_pspcl_offices_pio_layout.txt").read_text().split("\f")
    recs = m.parse_pio(pages, last_updated="2025-09-11")
    lv = check(recs, "power2_pspcl_offices", "electricity")
    assert lv["subdivision"] >= 15 and lv["division"] >= 4 and lv["circle"] >= 2 and lv["zone"] >= 2
    d = dict(recs)
    s = d["dept:power2_pspcl_offices:pio-aee-sanaur"]
    assert s["level"] == "subdivision" and s["phone"] == "96461-10046" and s["email"] == "aee-sanaur@pspcl.in"
    assert s["parents"] == {"zone": "South Zone", "circle": "DS,Circle, Patiala", "division": "DSEast Divn.PTA"}
    assert s["address"] == "Sanour" and s["last_updated"] == "2025-09-11"
    z = d["dept:power2_pspcl_offices:pio-ce-ds-south"]
    assert z["level"] == "zone" and z["area"] == "South Zone" and z["phone"] == "0175-2215160, 96461-01200"
    assert d["dept:power2_pspcl_offices:pio-se-ds-pta"]["level"] == "circle"
    assert d["dept:power2_pspcl_offices:pio-xen-sub-pta"]["level"] == "division"
    # a row whose post is split over two chunks, and an e-mail broken over two lines
    assert d["dept:power2_pspcl_offices:pio-xen-city-center-asr"]["level"] == "division"
    assert "dept:power2_pspcl_offices:pio-aee-cantt-2ferozepur" in d
    # rows after the distribution zones (thermal plants) are left out
    assert not any("ggsstp" in k for k in d)


def test_power2_pspcl_offices_hierarchy():
    from dforms import power2_pspcl_offices as m
    recs = m.parse_hierarchy((DATA / "power2_pspcl_offices_hier_layout.txt").read_text().split("\f"), last_updated="2026-02-13")
    lv = check(recs, "power2_pspcl_offices", "electricity")
    assert lv["zone"] == 2 and lv["subdivision"] == 10 and lv["section"] == 1
    d = dict(recs)
    s = d["dept:power2_pspcl_offices:h-1112"]
    assert s["area"] == "SUB DIVISION TECHNICAL MALL MANDI AMRITSAR" and s["pincode"] == "143001" and s["office_id"] == "1112"
    assert s["parents"] == {"zone": "Border Zone", "circle": "AMRITSAR", "division": "DS DIVISION CITY CENTER AMRITSAR"}
    assert d["dept:power2_pspcl_offices:h-61"]["level"] == "circle" and d["dept:power2_pspcl_offices:h-6"]["area"] == "East Zone"


def test_power2_pspcl_offices_ncc_fetch():
    from dforms import power2_pspcl_offices as m
    get = fake_get([(None, "nodal-complaint-centres", "power2_pspcl_offices_ncc.html")])
    recs, files, why = m.fetch({"reader": "power2_pspcl_offices", "page": "ncc", "url": m.URLS["ncc"]}, get)
    assert not why and files[0][0] == "depts/power/power2_pspcl_offices/ncc.html.gz"
    lv = check(recs, "power2_pspcl_offices", "electricity")
    assert lv == {"division": len(recs)}
    r = dict(recs)["dept:power2_pspcl_offices:ncc-tarantaran-circle-rayya"]
    assert r["phone"] == "96461-13025" and r["complaint_phone"] == "01853-214200, 96461-13686"
    assert r["parents"] == {"zone": "Border Zone", "circle": "Tarantaran Circle"} and r["last_updated"] == "2026-11-06"
    # a PDF page that is not a PDF is reported, not parsed
    recs, files, why = m.fetch({"reader": "power2_pspcl_offices", "page": "pio"}, fake_get([(None, "PIO_List", b"<html></html>")]))
    assert recs == [] and why == "not a pdf"


def test_power2_pspcl_offices_items():
    from dforms import power2_pspcl_offices as m
    seeds = json.loads((ROOT / "seeds" / "dept_power2_pspcl_offices.json").read_text())
    assert [s["key"] for s in seeds] == [i["key"] for i in m.items()]
    assert all(s["key"].startswith("power2_pspcl_offices:") and s["payload"]["india_only"] is False for s in seeds)


def test_water2_pwssb_fetch():
    from dforms import water2_pwssb as m
    calls = []
    get = fake_get([(None, "admin-ajax.php", "water2_pwssb_t466.json"), (None, "amritsar-circle", "water2_pwssb_page.html")], calls)
    recs, files, why = m.fetch({"reader": "water2_pwssb", "page": "amritsar", "url": "https://pwssb.punjab.gov.in/amritsar-circle/",
                                "table_id": "466", "circle": "Amritsar"}, get)
    assert not why and "table_id=466" in calls[1][1] and len(files) == 2
    lv = check(recs, "water2_pwssb", "water")
    assert lv == {"zone": 1, "circle": 1, "division": 2}
    d = dict(recs)
    ee = d["dept:water2_pwssb:amritsar:executive-engineer-divn-no-1-amritsar"]
    assert ee["name"] == "Gurjinder Singh" and ee["phone"] == "0183-2500746, 9915355229" and ee["email"] == "eea1.pwssb@punjab.gov.in"
    assert ee["parents"] == {"circle": "Amritsar Circle"}
    assert d["dept:water2_pwssb:amritsar:chief-engineer-amritsar"]["name"] == "Satnam Singh"
    # no page answer: the payload's table id is used
    recs, _, why = m.fetch({"reader": "water2_pwssb", "page": "amritsar", "table_id": "466", "circle": "Amritsar"},
                           fake_get([(None, "table_id=466", "water2_pwssb_t466.json")]))
    assert not why and len(recs) == 4
    assert len(m.items()) == 6 and all(i["payload"]["india_only"] for i in m.items())


def test_water2_dwss_fetch():
    from dforms import water2_dwss as m
    recs, files, why = m.fetch({"reader": "water2_dwss", "url": m.URL}, fake_get([(None, "contact-us", "water2_dwss_contact.html")]))
    assert not why and files[0][0] == "depts/water2_dwss/contact-us.html.gz"
    lv = check(recs, "water2_dwss", "water")
    assert lv["zone"] == 3 and lv["circle"] == 5 and lv["state"] == 1
    d = dict(recs)
    se = d["dept:water2_dwss:superintending-engineer-patiala-circle"]
    assert se["name"] == "Naval Kishore" and se["phone"] == "0175-2213033" and se["email"] == "sedwss.patiala@punjab.gov.in"
    ce = d["dept:water2_dwss:chief-engineer-north-north-zone"]
    assert ce["name"] == "Karanbir Singh" and ce["area"] == "North Zone" and ce["email"] == "cedwss.north@gmail.com"
    assert d["dept:water2_dwss:superintending-engineer-shri-muktsar-sahib-circle"]["additional_charge"] is True


# ======== group south_water


# ---- south_water: CMWSSB (Chennai), ... ------------------------------------------------------------------------------------

def test_water2_cmwssb_whoswho():
    from dforms import water2_cmwssb
    calls = []
    get = fake_get([(None, "/ta/whos-who", "water2_cmwssb_whoswho_ta.html"), (None, "/whos-who", "water2_cmwssb_whoswho.html")], calls)
    recs, files, why = water2_cmwssb.fetch({"reader": "water2_cmwssb", "page": "whoswho", "url": "https://cmwssb.tn.gov.in/whos-who",
                                            "url_ta": "https://cmwssb.tn.gov.in/ta/whos-who"}, get)
    assert why == "" and len(files) == 2 and len(calls) == 2
    lv = check(recs, "water2_cmwssb", "water")
    assert lv["state"] >= 3 and lv["division"] >= 3 and lv["circle"] >= 2 and lv["zone"] == 2
    d = dict(recs)
    md = d["dept:water2_cmwssb:ww:managing-director"]
    assert md["name"] == "Thiru. T.Anand, I.A.S." and md["phone"] == "044 28459000" and md["email"] == "md@cmwssb.in"
    assert md["name_regional"].startswith("திரு. த.ஆனந்த்") and md["last_updated"] == "2026-11-05"
    a15 = d["dept:water2_cmwssb:ww:area-engineer-zone-xv"]
    assert a15["level"] == "division" and a15["area"] == "Area XV" and a15["name"] == "Tmt. V.Rekha"
    assert a15["phone"] == "044 24500262, 8144930915" and a15["email"] == "cmwssba15@gmail.com"
    se = d["dept:water2_cmwssb:ww:superintending-engineer-south-zone-xiii-xiv-xv"]
    assert se["level"] == "circle" and se["name"] == "Tmt. H.S.Kalyani"
    assert d["dept:water2_cmwssb:ww:region-i"]["level"] == "zone"


def test_water2_cmwssb_depots():
    import gzip
    from dforms import water2_cmwssb
    pages = json.loads(gzip.decompress((DATA / "water2_cmwssb_depots_pages.json.gz").read_bytes()))
    recs = water2_cmwssb.parse_pages(pages, "https://cmwssb.tn.gov.in/sites/default/files/quick_links/Areaandepotofficeaddress.pdf")
    lv = check(recs, "water2_cmwssb", "water")
    assert lv["section"] == 31 and lv["subdivision"] == 9
    d = dict(recs)
    assert not any("area-engineer" in k and ":dae:" not in k for k in d)       # Area Engineers come from the who's who page
    dae = d["dept:water2_cmwssb:area-1:dae:deputy-area-engineer-i"]
    assert dae["name"] == "B.Raj" and dae["phone"] == "8144930201" and dae["parents"] == {"zone": "Area I Thiruvottiyur"}
    assert dae["address"] == "Kathivakkam Headworks, Kathivakkam High Road, Chennai – 600 057"
    d1 = d["dept:water2_cmwssb:depot-1"]
    assert d1["level"] == "section" and d1["name"] == "C.Muthunayagam" and d1["phone"] == "8144930001" and d1["in_charge"] is True
    assert d1["address"] == "Thalangkuppam, Ennore Express Road, Chennai – 600 057"
    d109 = d["dept:water2_cmwssb:depot-109"]                                  # a table whose heading wraps over three lines
    assert d109["name"] == "R.Sathish Kumar" and d109["phone"] == "8144930109, 24726795"
    assert d109["address"] == "No.136/111, Choolaimedu High Road, Chennai-94."


def test_water2_tg_mb_kothagudem():
    from dforms import water2_tg_mb
    url = "https://kothagudem.telangana.gov.in/missionbhagiratha-intradivision/"
    recs, files, why = water2_tg_mb.fetch({"reader": "water2_tg_mb", "url": url, "state": "TG", "district": "Bhadradri Kothagudem"},
                                          fake_get([(None, "kothagudem.telangana.gov.in", "water2_tg_mb_kothagudem.html")]))
    assert why == "" and len(files) == 1
    lv = check(recs, "water2_tg_mb", "water")
    assert lv["division"] == 2 and lv["subdivision"] == 2 and lv["section"] == 5
    d = {r["post"] + "|" + r["area"]: r for _, r in recs}
    ee = d["Executive Engineer, Grid Division|Kothagudem"]
    assert ee["name"] == "Smt. Ch.Nalini" and ee["phone"] == "9100122238" and ee["email"] == "ee_tdwsp_ktdm@telangana.gov.in"
    assert ee["last_updated"] == "2025-02-25" and ee["district"] == "Bhadradri Kothagudem" and ee["state"] == "TG"
    dee = d["Dy.E.E|Sub Division Kothagudem"]
    assert dee["level"] == "subdivision" and dee["name"] == "M. Shivaiah" and dee["phone"] == "7995660551"
    ae = d["AEE|Laxmidevipalli"]
    assert ae["level"] == "section" and ae["name"] == "K. Venkata Swamy" and ae["phone"] == "6309954518"


def test_water2_tg_mb_no_table_and_items():
    from dforms import water2_tg_mb
    recs, files, why = water2_tg_mb.fetch({"reader": "water2_tg_mb", "url": "https://jangaon.telangana.gov.in/?p=29322", "district": "Jangaon"},
                                          fake_get([(None, "jangaon", "water2_tg_mb_jangaon.html")]))
    assert recs == [] and len(files) == 1 and "no officer table" in why
    calls = []
    items = water2_tg_mb.items(fake_get([(None, "kothagudem.telangana.gov.in/?s=bhagiratha", "water2_tg_mb_search.html")], calls))
    assert len(calls) == 66                                         # 33 district sites x 2 words
    urls = [i["payload"]["url"] for i in items]
    assert urls == ["https://kothagudem.telangana.gov.in/mission-bhagiratha-grid/",
                    "https://kothagudem.telangana.gov.in/missionbhagiratha-intradivision/"]
    assert items[1]["key"] == "water2_tg_mb:kothagudem:missionbhagiratha-intradivision"
    assert items[1]["payload"]["district"] == "Bhadradri Kothagudem" and items[1]["payload"]["reader"] == "water2_tg_mb"


def test_water2_ap_rws_tables_and_text():
    from dforms import water2_ap_rws
    get = fake_get([(None, "krishna.ap.gov.in", "water2_ap_rws_krishna.html"), (None, "spsnellore.ap.gov.in", "water2_ap_rws_spsnellore.html"),
                    (None, "kakinada.ap.gov.in", "water2_ap_rws_kakinada.html")])
    kr, _, why = water2_ap_rws.fetch({"reader": "water2_ap_rws", "url": "https://krishna.ap.gov.in/rural-water-supply-and-sanitation/",
                                      "district": "Krishna"}, get)
    assert why == ""
    lv = check(kr, "water2_ap_rws", "water")
    assert lv == {"circle": 1, "division": 2, "subdivision": 1}
    d = {r["post"]: r for _, r in kr}
    assert d["Executive Engineer(P),Vijayawada"]["area"] == "Vijayawada"                      # post read from the "attached" cell
    assert d["Executive Engineer(P),Vijayawada"]["name"] == "Sri. D.Sainath" and d["Executive Engineer(P),Vijayawada"]["phone"] == "9100121346"
    assert d["Superintending Engineer"]["org"] == "RWS&S" and d["Superintending Engineer"]["last_updated"] == "2025-07-03"
    ne, _, _ = water2_ap_rws.fetch({"reader": "water2_ap_rws", "url": "https://spsnellore.ap.gov.in/?p=31534", "district": "SPSR Nellore"}, get)
    check(ne, "water2_ap_rws", "water")
    dee = [r for _, r in ne if r["area"] == "Kovur Sub-Division"][0]
    assert dee["level"] == "subdivision" and dee["name"] == "Sri. M.LeelaPrakash" and dee["phone"] == "9100121759"
    kk, _, _ = water2_ap_rws.fetch({"reader": "water2_ap_rws", "url": "https://kakinada.ap.gov.in/departments/rural-water-supply/",
                                    "district": "Kakinada"}, get)
    check(kk, "water2_ap_rws", "water")
    assert len(kk) == 1 and kk[0][1]["level"] == "division" and kk[0][1]["phone"] == "9100121101"
    assert kk[0][1]["email"] == "eerwskkd@ap.gov.in" and kk[0][1]["area"] == "Kakinada"
