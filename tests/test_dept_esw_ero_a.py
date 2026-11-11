from esw_common import *  # noqa: F401,F403


# ---- EROs: Karnataka, Kerala, Delhi, Bihar, Odisha, Goa, Puducherry (dforms/ero_ka, ero_kl, ero_dl, ero_br, ero_od, ero_ga, ero_py)

def _one(module, url, sample, payload=None):
    p = payload or json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())[0]["payload"]
    get = fake_get({url: sample})
    recs, files, why = mod(module).fetch(p, get)
    assert why == "" and files and files[0][0].startswith(f"depts/{module}/")
    check_records(recs, module, "elections")
    return dict(recs)


def test_ero_ka():
    url = "https://ceo.karnataka.gov.in/blo_data/ac/150.json"
    recs = _one("ero_ka", url, "ero_ka_150.json", {"reader": "ero_ka", "url": url, "state": "KA", "ac": 150, "india_only": True})
    ero = recs["dept:ero_ka:KA-AC-150:ero"]
    assert ero["name"] == "Maruthi J B" and ero["phone"] == "7022790346" and ero["office_id"] == "KA-AC-150"
    assert ero["area"] == "150 - Yelahanka" and ero["level"] == "ac" and ero["last_updated"] == "2026-10-19"
    aero = recs["dept:ero_ka:KA-AC-150:aero:syed-kaleemulla"]
    assert aero["phone"].startswith("9844796976") and aero["post"] == "Assistant Electoral Registration Officer"
    assert len(json.loads((ROOT / "seeds" / "dept_ero_ka.json").read_text())) == 224


def test_ero_kl():
    recs = _one("ero_kl", "https://www.ceo.kerala.gov.in/telephone-numbers", "ero_kl_telephone.html")
    ero = recs["dept:ero_kl:KL-AC-1:ero"]
    assert ero["name"] == "MURALI P V" and ero["email"] == "ero01manjeswar@gmail.com" and ero["office_id"] == "KL-AC-1"
    assert ero["designation"] == "Deputy Collector (LR), Collectorate, Kasaragod" and ero["district"] == "Kasaragod"
    assert recs["dept:ero_kl:KL-AC-1:aero:tahsildar-manjeshwaram"]["phone"] == "8547618464, 9447520163"
    deo = recs["dept:ero_kl:KL-DEO-kasaragod"]
    assert deo["level"] == "district" and deo["name"] == "SREEDHANYA SURESH IAS"
    assert "DEPUTY COLLECTOR, ELECTION" not in [d.get("designation") for d in recs.values()]


def test_ero_kl_alias():
    assert mod("ero_kl").ALIAS["vatakara"] == "vadakara"
    from dforms import _esw
    assert _esw.ac_no("KL", mod("ero_kl").ALIAS["vatakara"]) == 20


def test_ero_dl():
    seeds = {i["payload"]["page"]: i["payload"] for i in json.loads((ROOT / "seeds" / "dept_ero_dl.json").read_text())}
    recs = _one("ero_dl", seeds["ero"]["url"], "ero_dl_ero.html", seeds["ero"])
    ero = recs["dept:ero_dl:DL-AC-1:ero"]
    assert ero["name"] == "Aditya Kumar Jha" and ero["phone"] == "27844214, 9911094739"
    assert ero["email"] == "eronerela.dl@eci.gov.in" and ero["office_id"] == "DL-AC-1" and ero["area"] == "1 - Nerela"
    recs = _one("ero_dl", seeds["aero"]["url"], "ero_dl_aero.html", seeds["aero"])
    aero = recs["dept:ero_dl:DL-AC-2:aero:voter-centre"]
    assert aero["name"] == "Sh.Saurabh Narwal" and aero["email"] == "votercentreac2@gmail.com" and aero["phone"] == "27612011, 9625001567"


def test_ero_br():
    recs = _one("ero_br", "http://ceoelection.bihar.gov.in/RO-ERO_Contact_Details2025.html", "ero_br.html")
    ero = recs["dept:ero_br:BR-AC-46:ero"]
    assert ero["name"] == "AMIT KUMAR" and ero["phone"] == "9031672236" and ero["area"] == "46 - Narpatganj"
    assert all(d.get("office_id") for d in recs.values())
    br = mod("ero_br")
    assert br.ac_no("Kalyanpur", "Purvi Champaran") != br.ac_no("Kalyanpur", "Samastipur")
    assert br.ac_no("Surajgarha", "Lakhisarai")


def test_ero_od():
    recs = _one("ero_od", "https://ceoodisha.nic.in/en/contact/eroaero/", "ero_od.html")
    ero = recs["dept:ero_od:OD-AC-1:ero"]
    assert ero["name"] == "Kunal Motiram Chavan, IAS" and ero["phone"] == "8669011852" and ero["office_id"] == "OD-AC-1"
    assert ero["designation"] == "Addl. District Magistrate, Padampur"
    a = recs["dept:ero_od:OD-AC-1:aero:deputy-collector-sub-collectors-office-padampur"]
    assert a["phone"] == "06683-223401, 9938447276"
    # one cell with two officers -> two records
    assert recs["dept:ero_od:OD-AC-1:aero:tahasildar-jharbandh"]["name"] == "Sri Subadar Pradhan"
    assert recs["dept:ero_od:OD-AC-1:aero:tahasildar-padampur"]["email"] == "tahasil.padampur@gmail.com"
    assert recs["dept:ero_od:OD-AC-100:ero"]["area"] == "100 - Mahakalapada"


def test_ero_ga():
    recs = _one("ero_ga", "https://ceogoa.nic.in/appln/UIL/ERO.aspx", "ero_ga.html")
    ero = recs["dept:ero_ga:GA-AC-2:ero"]
    assert ero["name"] == "Smt Varsha S Parab" and ero["email"] == "sdm-pernem.goa@nic.in" and ero["district"] == "North Goa"
    assert ero["phone"].startswith("+91-8308014526") and ero["office_id"] == "GA-AC-2"
    assert {d["district"] for d in recs.values()} == {"North Goa", "South Goa", "Kushavati"}


def test_ero_py():
    recs = _one("ero_py", "https://ceopuducherry.py.gov.in/contact.php", "ero_py.html")
    ero = recs["dept:ero_py:PY-AC-1:ero"]
    assert ero["name"] == "A. KUMARAN" and ero["phone"] == "9443383419, 0413-2667668" and ero["last_updated"] == "2026-11-05"
    assert ero["designation"] == "Deputy-Collector Revenue (South), Villianur"
    aero = recs["dept:ero_py:PY-AC-1:aero:tahsildar-o-o-dcr-south-villianur"]
    assert aero["name"] == "K.K. VIBEESH" and aero["district"] == "Puducherry"
    assert recs["dept:ero_py:PY-DEO-karaikal"]["email"] == "election.kkl@py.gov.in"
    assert not [d for d in recs.values() if "Returning" in d.get("post", "")]
