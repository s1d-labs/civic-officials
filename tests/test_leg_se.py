"""Offline tests of the south / east / north-east MLA readers (dforms/leg_tn, leg_ap, leg_py, leg_od, leg_as, leg_ml, leg_mz,
leg_mn, leg_tr, leg_nl, leg_sk) on small saved pages in tests/data/leg/ (2-4 members each)."""
from esw_common import *  # noqa: F401,F403

LEG = "leg/"


def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def _run(module, routes, payload=None):
    p = payload or _seed(module)[0]["payload"]
    get = fake_get({k: LEG + v for k, v in routes.items()})
    recs, files, why = mod(module).fetch(p, get)
    assert why == "" and files and all(f[0].startswith(f"depts/{module}/") for f in files)
    check_records(recs, module, "elected")
    for _, d in recs:
        assert d["level"] == "ac" and d["post"] == "Member of Legislative Assembly"
    return dict(recs), get


def test_seeds_match_items():
    for st in ("tn", "ap", "py", "od", "as", "ml", "mz", "mn", "tr", "nl", "sk"):
        m = mod("leg_" + st)
        assert json.loads((ROOT / "seeds" / f"dept_leg_{st}.json").read_text()) == m.items()
        assert all(i["key"].startswith("leg_") and i["payload"]["reader"] == "leg_" + st for i in m.items())


def test_leg_tn():
    recs, _ = _run("leg_tn", {mod("leg_tn").URL: "tn_list.html"})
    a = recs["dept:leg_tn:TN-AC-14"]
    assert a["name"] == "Aadhav Arjuna" and a["party"] == "TVK" and a["role"] == "Minister" and a["area"] == "14 - Villivakkam"
    assert a["phone"] == "97909 23364" and a["email"] == "mlavillivakkam@tn.gov.in" and a["address"].startswith("No.19-6-3")
    k = recs["dept:leg_tn:TN-AC-65"]
    assert k["phone"] == "94434 44685, 63696 94024, 94432 33685" and k["party"] == "AIADMK" and k["office_id"] == "TN-AC-65"
    v = recs["dept:leg_tn:TN-AC-124"]
    assert v["name"] == "Kutty @ Sudhakar A." and v["party"] == "DMK" and v["constituency"] == "Valparai (SC)"
    assert recs["dept:leg_tn:TN-AC-185"]["constituency"] == "Tiruppattur"       # Sivaganga's Tiruppattur, not Vellore's (50)
    assert not any("vacant" in d["name"].lower() for d in recs.values()) and len(recs) == 4


def test_leg_ap():
    p = _seed("leg_ap")[0]["payload"]
    recs, get = _run("leg_ap", {p["url"]: "ap_district.html", p["address_url"]: "ap_address.html"})
    assert len(get.calls) == 2 and "order_by=6" in get.calls[1][1]
    a = recs["dept:leg_ap:AP-AC-120"]                    # ECI 1 Ichchapuram = site 120
    assert a["name"] == "ASHOK BENDALAM" and a["party"] == "TDP" and a["seat_no"] == 1 and a["district"] == "Srikakulam"
    assert a["email"] == "ichapuram120mla@ap.gov.in" and a["address"].startswith("Ramayyaputtuga(v), Kavati post & Mandal")
    assert a["permanent_address"] == "Ramayyaputhuga(V) Kaviti(M) Itchapuram Srikakulam Dist" and "phone" not in a
    s = recs["dept:leg_ap:AP-AC-121"]
    assert s["name"] == "GOUTHU SIREESHA" and s["email"] == "sireeshavc@gmail.com" and "permanent_address" not in s


def test_leg_py():
    recs, _ = _run("leg_py", {mod("leg_py").URL: "py_mlas.html"})
    a = recs["dept:leg_py:PY-AC-19"]
    assert a["name"] == "C. AIYAPPAN @ MOUTTAYAPPAN" and a["phone"] == "+91-9443282558" and a["area"] == "19 - Ariankuppam"
    assert a["email"] == "mlaariankuppam@py.gov.in" and a["address"] == "No.32, Madhakovil Street, Ariyankuppam, Puducherry-605 007."
    assert recs["dept:leg_py:PY-AC-4"]["name"] == "N. RANGASAMY"


def test_leg_od_pages():
    url = mod("leg_od").URL
    recs, get = _run("leg_od", {("GET", url): "od_p1.html", ("POST", url): "od_p2.html"})
    assert [c[0] for c in get.calls] == ["GET", "POST"]
    post = get.calls[1][2]
    assert post["__VIEWSTATE"] == "vs1" and post["ctl00$ContentPlaceHolder1$btnNext"] == "Next"
    assert len(recs) == 3
    a = recs["dept:leg_od:OD-AC-22"]
    assert a["name"] == "Abhimanyu Sethi" and a["party"] == "Biju Janata Dal" and a["phone"] == "9937123960"
    assert a["email"] == "s.abhimanyu@gov.in" and a["district"] == "Keonjhar" and a["address"].startswith("At/Po - Inchol")


def test_leg_od_aliases():
    od = mod("leg_od")
    assert od._seat("Bhubaneswar Central (Madhya)", "Khordha")[0] == od._seat("Bhubaneswar Madhya", "Khordha")[0] is not None
    assert od._seat("Nabarangapur", "Nabarangpur")[0] and od._seat("Talasara", "Sundargarh")[0]


def test_leg_as():
    p = _seed("leg_as")[0]["payload"]
    recs, get = _run("leg_as", {p["url"]: "as_list.html", "https://assambidhansabha.org/members?id=148": "as_member_148.html"}, p)
    assert len(get.calls) == 3                     # the list page + one detail page per member (the second answers None here)
    a = next(d for d in recs.values() if d["name"] == "Abdur Rahim Ahmed")
    assert a["party"] == "Indian National Congress" and a["phone"] == "9854464244" and a["email"] == "mdarahimahmed@gmail.com"
    assert a["seat_no"] == 23 and a["constituency"] == "Chenga" and a["office_id"] == "AS-AC-47"      # site layer: old Chenga 47
    assert a["permanent_address"].startswith("Village- Gandharipara") and a["address"] == a["permanent_address"]
    b = next(d for d in recs.values() if d["name"] == "Abdus Sobahan Ali Sarkar")
    assert b["phone"] == "8876359697" and "address" not in b


def test_leg_ml():
    p = _seed("leg_ml")[1]["payload"]
    recs, _ = _run("leg_ml", {p["url"]: "ml_p1.html"}, p)
    a = recs["dept:leg_ml:ML-AC-31"]
    assert a["name"] == "SHAKLIAR WARJRI" and a["party"] == "Hill State People's Democratic Party" and a["phone"] == "+91-9366258122"
    assert a["area"] == "31 - Mawthadraishan (ST)"
    e = [d for d in recs.values() if d.get("email")]
    assert len(recs) == 2 and len(e) == 1 and "@" in e[0]["email"] and e[0]["phone"]


def test_leg_mz():
    mz = mod("leg_mz")
    assert mz.list_ids((DATA / LEG / "mz_list.html").read_text()) == [51, 15]
    assert len(mz.items()) == 40 and mz.items()[2]["payload"]["url"] == "https://mizoramassembly.in/members/details/16"
    p = mz.items()[2]["payload"]
    recs, _ = _run("leg_mz", {p["url"]: "mz_member_16.html"}, p)
    a = recs["dept:leg_mz:MZ-AC-3"]
    assert a["name"] == "H. Lalzirliana" and a["party"] == "Mizo National Front (MNF)" and a["address"] == "Mamit"
    assert a["elected_on"] == "2023-12-03" and "phone" not in a and "email" not in a


def test_leg_mn():
    mn = mod("leg_mn")
    assert mn.list_slugs((DATA / LEG / "mn_list.html").read_text()) == ["thokchom-lokeshwar-singh", "kongkham-robindro-singh"]
    p = next(i["payload"] for i in mn.items() if i["payload"]["slug"] == "kongkham-robindro-singh")
    recs, _ = _run("leg_mn", {p["url"]: "mn_kongkham-robindro-singh.html"}, p)
    a = recs["dept:leg_mn:MN-AC-23"]
    assert a["name"] == "Kongkham Robindro Singh" and a["party"] == "Bharatiya Janata Party" and a["phone"] == "9856306151"
    assert a["email"] == "kongkhamrobz@yahoo.com" and a["address"] == "Babupara, Imphal West, P.O. & P.S- Imphal, Manipur"
    assert a["permanent_address"].startswith("Mayang Imphal Thana Awang Leikai")


def test_leg_tr_nl_sk():
    recs, _ = _run("leg_tr", {mod("leg_tr").URL: "tr_list.html"})
    a = recs["dept:leg_tr:TR-AC-1"]
    assert a["name"] == "Brishaketu Debbarma" and a["party"] == "Tipra Motha Party" and a["constituency"] == "Simna(ST)"
    assert recs["dept:leg_tr:TR-AC-2"]["name"] == "Ratan Lal Nath" and len(recs) == 2
    recs, _ = _run("leg_nl", {mod("leg_nl").URL: "nl_list.html"})
    assert recs["dept:leg_nl:NL-AC-1"]["name"] == "H Tovihoto Ayemi" and recs["dept:leg_nl:NL-AC-1"]["website"] == "https://twitter.com/tovihoto"
    assert recs["dept:leg_nl:NL-AC-6"]["constituency"] == "Tenning"
    recs, _ = _run("leg_sk", {mod("leg_sk").URL: "sk_list.html"})
    assert recs["dept:leg_sk:SK-AC-32"]["name"] == "SONAM LAMA" and recs["dept:leg_sk:SK-AC-32"]["constituency"] == "Sangha"
    assert recs["dept:leg_sk:SK-AC-6"]["name"] == "MINGMA NORBU SHERPA"


def test_leg_od_split_constituency():
    od = mod("leg_od")
    assert od.split_cons("Nuapada- (Nuapada , Odisha)") == ("Nuapada", "Nuapada") and od._seat("Nuapada", "Nuapada")[0] == 71
    assert od.split_cons("Bargarh - ( Bargarh , Odisha )") == ("Bargarh", "Bargarh")
