from esw_common import *  # noqa: F401,F403


# ---- EROs: Tamil Nadu, Jharkhand, Manipur, Mizoram, Tripura, Lakshadweep, Andaman & Nicobar, DNHDD
#      (dforms/ero_tn, ero_jh, ero_mn, ero_mz, ero_tr, ero_ld, ero_an, ero_dh)

def _seed(module, key=None):
    items = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    return next(i for i in items if key is None or i["key"] == key)["payload"]


def _run(module, payload, routes):
    get = fake_get(routes)
    recs, files, why = mod(module).fetch(payload, get)
    assert why == "" and files and all(f[0].startswith(f"depts/{module}/") for f in files), why
    check_records(recs, module, "elections")
    return dict(recs), get


def test_ero_tn_ero_postback():
    p = _seed("ero_tn", "ero_tn-ero-d2")
    assert p["district_value"] == "2" and p["india_only"]
    recs, get = _run("ero_tn", p, {("GET", p["url"]): "ero_tn_ero_get.html", ("POST", p["url"]): "ero_tn_ero_d2.html"})
    post = get.calls[1]
    assert post[0] == "POST" and post[2]["ctl00$ContentPlaceHolder1$ddl_District"] == "2" and "__VIEWSTATE" in post[2]
    ero = recs["dept:ero_tn:TN-AC-11:ero"]
    assert ero["name"] == "Thiru A. Rajkumar" and ero["phone"] == "9445190004" and ero["office_id"] == "TN-AC-11"
    assert ero["area"] == "11 - Dr.Radhakrishnan Nagar" and ero["designation"] == "ZONAL OFFICER/ ERO" and ero["district"] == "Chennai"
    assert ero["address"].startswith("GCC ZONE-4")
    assert len(recs) == 3


def test_ero_tn_aero_and_deo():
    p = _seed("ero_tn", "ero_tn-aero-d2")
    recs, _ = _run("ero_tn", p, {("GET", p["url"]): "ero_tn_ero_get.html", ("POST", p["url"]): "ero_tn_aero_d2.html"})
    a = recs["dept:ero_tn:TN-AC-12:aero:asst-revenue-officer-aero"]
    assert a["name"] == "Tmt Suriyabanu" and a["phone"] == "6380923312" and a["post"] == "Assistant Electoral Registration Officer"
    p = _seed("ero_tn", "ero_tn-deo")
    recs, _ = _run("ero_tn", p, {p["url"]: "ero_tn_deo.html"})
    deo = recs["dept:ero_tn:TN-DEO-chennai"]
    assert deo["name"] == "Dr. G.S. SAMEERAN I.A.S" and deo["email"] == "commissioner@chennaicorporation.gov.in"
    assert deo["level"] == "district" and deo["last_updated"] == "2025-03-05"
    assert len(json.loads((ROOT / "seeds" / "dept_ero_tn.json").read_text())) == 77


def test_ero_jh_pager():
    p = _seed("ero_jh", "ero_jh-ero")
    recs, get = _run("ero_jh", p, {("GET", p["url"]): "ero_jh_ero_p1.html", ("POST", p["url"]): "ero_jh_ero_p2.html"})
    assert [c[2]["__EVENTARGUMENT"] for c in get.calls if c[0] == "POST"] == ["Page$2"]
    ero = recs["dept:ero_jh:JH-AC-1:ero"]
    assert ero["name"] == "Sadanand Mahto" and ero["phone"] == "9934579302" and ero["district"] == "Sahebganj"
    assert recs["dept:ero_jh:JH-AC-75:ero"]["name"] == "Preety Kiskoo"      # from the page-2 answer
    assert len(recs) == 4 and all(d["office_id"].startswith("JH-AC-") for d in recs.values())


def test_ero_jh_aero():
    p = _seed("ero_jh", "ero_jh-aero")
    recs, _ = _run("ero_jh", p, {p["url"]: "ero_jh_aero_p1.html"})
    a = recs["dept:ero_jh:JH-AC-1:aero:basukinath-tudu"]
    assert a["phone"] == "7004271620" and a["office_id"] == "JH-AC-1" and a["area"] == "1 - Rajmahal"
    assert mod("ero_jh").ac_number("Kharasawan") == 57


def test_ero_mn():
    p = _seed("ero_mn")
    recs, _ = _run("ero_mn", p, {p["url"]: "ero_mn.html"})
    ero = recs["dept:ero_mn:MN-AC-1:ero"]
    assert ero["name"] == "Khwairakpam Lenin Singh" and ero["email"] == "ero-khndkpam@manipur.gov.in" and ero["office_id"] == "MN-AC-1"
    assert recs["dept:ero_mn:MN-AC-1:aero:sdc-sagolmang"]["name"] == "Boinao Singh Oinam"
    deo = recs["dept:ero_mn:MN-DEO-imphal-east"]
    assert deo["name"] == "Dr. Nivedita Lairenlakpam, IAS" and deo["phone"] == "0385-2458387" and deo["email"] == "deoimphaleast.mn@gov.in"
    assert len(recs) == 9


def test_ero_mz():
    p = _seed("ero_mz", "ero_mz-p1")
    assert p["url"].endswith("?ero_page=1&aero_page=1")
    recs, _ = _run("ero_mz", p, {p["url"]: "ero_mz_p1.html"})
    ero = recs["dept:ero_mz:MZ-AC-39:ero"]
    assert ero["name"] == "Abraham Beirazi Khithie" and ero["district"] == "Siaha" and ero["area"] == "39 - Saiha (ST)"
    assert recs["dept:ero_mz:MZ-AC-14:ero"]["designation"] == "Dy.Secretary, GAD(SAW)"       # number from the page's AC dropdown
    assert sum(1 for d in recs.values() if d["level"] == "district") == 2
    assert len(mod("ero_mz").parse((DATA / "ero_mz_p1.html").read_text(), page=2)) == 4   # DEO cards only from page 1


def test_ero_tr_ero():
    p = _seed("ero_tr", "ero_tr-ero")
    recs, _ = _run("ero_tr", p, {p["url"]: "ero_tr_ero.html"})
    ero = recs["dept:ero_tr:TR-AC-2:ero"]
    assert ero["name"] == "Santanu Bikash Das, TCS" and ero["phone"] == "9862572182"
    assert ero["email"] == "sdmmohanpur2012@gmail.com, santanubikashdas24@gmail.com" and ero["area"] == "2 - Mohanpur"
    assert recs["dept:ero_tr:TR-AC-1:ero"]["designation"] == "District Welfare Officer, West Tripura"


def test_ero_tr_aero_pager():
    p = _seed("ero_tr", "ero_tr-aero")
    recs, get = _run("ero_tr", p, {("GET", p["url"]): "ero_tr_aero_p1.html", ("POST", p["url"]): "ero_tr_aero_p2.html"})
    posts = [c[2]["__EVENTTARGET"] for c in get.calls if c[0] == "POST"]
    assert posts[0] == "ctl00$ContentPlaceHolder1$rptPager$ctl01$lnkPage" and len(posts) <= 2   # page 2, then stop
    a = recs["dept:ero_tr:TR-SD-sabroom:aero:souradip-debnath"]
    assert a["designation"] == "BDO" and a["phone"] == "8415048645" and a["email"] == "bdo.satchand@gmail.com"
    assert a["level"] == "subdivision" and a["area"] == "Sabroom" and a["office_id"] == "TR-SD-sabroom"
    assert len(recs) == 5


def test_ero_ld():
    p = _seed("ero_ld")
    recs, _ = _run("ero_ld", p, {p["url"]: "ero_ld.html"})
    ero = recs["dept:ero_ld:LD-PC-1:ero"]
    assert ero["name"] == "Shri. Avinash Singh, DANICS" and ero["phone"] == "04896262384, 9540334204" and ero["level"] == "pc"
    a = recs["dept:ero_ld:LD-AERO-chetlat"]
    assert a["area"] == "Chetlat" and a["phone"] == "04899276232, 9446801792"    # the page drops the STD 0
    assert len(recs) == 4                                   # BLO rows are left out


def test_ero_an(monkeypatch):
    text = (DATA / "ero_an_layout.txt").read_text()
    recs = dict(mod("ero_an").parse([text]))
    assert recs["dept:ero_an:AN-PC-1:ero"]["name"] == "Shri Priyanka Kumari"
    assert recs["dept:ero_an:AN-PC-1:ero"]["phone"] == "231951, 7827185093" and recs["dept:ero_an:AN-PC-1:ero"]["email"] == "adm.and@nic.in"
    may = recs["dept:ero_an:AN-AERO-mayabunder"]
    assert may["email"] == "assistantcommissionerhqnma@gmail.com" and may["phone"] == "273027, 8375065282" and may["level"] == "subdistrict"
    nma = recs["dept:ero_an:AN-DEO-n-m-andaman"]
    assert nma["email"] == "deo.nma.election2018@gmail.com" and nma["phone"] == "262999, 9531946057, 9434286261"
    assert not any("ceo" in k.lower() for k in recs)        # CEO office rows are left out
    # fetch() on the (large) real PDF is not stored here: pdf_pages is replaced by the saved layout text
    monkeypatch.setattr(mod("ero_an")._esw, "pdf_pages", lambda content: [text])
    p = _seed("ero_an")
    got, _ = _run("ero_an", p, {p["url"]: "ero_an_layout.txt"})
    assert len(got) == 7 and got["dept:ero_an:AN-AERO-rangat"]["phone"] == "274222, 9474245212, 8826081124"


def test_ero_dh():
    p = _seed("ero_dh")
    recs, _ = _run("ero_dh", p, {p["url"]: "ero_dh.html"})
    ero = recs["dept:ero_dh:DH-PC-1:ero"]
    assert ero["name"] == "Smt. Aarti Agrawal,DANICS" and ero["designation"] == "Dy. Collector (Gen), Daman" and ero["office_id"] == "DH-PC-1"
    assert "9871187369" in ero["phone"] and ero["level"] == "pc"
    assert recs["dept:ero_dh:DH-PC-2:ero"]["name"] == "Shri Amit Kumar,DANICS"           # DEO and ERO side by side in one row
    assert recs["dept:ero_dh:DH-DEO-dadra-nagar-haveli"]["name"] == "Shri Priyank Kishore,IAS"
    assert recs["dept:ero_dh:DH-PC-1:aero:mamlatdar-diu"]["phone"] == "02875-252111, 9824137111"
    assert not any(d["post"].startswith(("Returning", "Assistant Returning")) for d in recs.values())
    assert len(recs) == 12
