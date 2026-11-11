"""Electricity-office readers (dforms/power_<discom>.py) on small saved answers in tests/data/power: no network.
Four blocks (north; west and north-east; south; Andhra Pradesh and east), each with its own fake get()."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "tests" / "data" / "power"


# ---- UP, Haryana, Himachal, Kashmir

class Resp_g1:
    def __init__(self, content):
        self.content, self.status_code = content, 200
        self.text = content.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.text)


def fake_get_g1(routes, calls=None):
    """routes: [(method or None, url substring, file name or bytes)]."""
    def get(url, method="GET", data=None, headers=None):
        if calls is not None:
            calls.append((method, url, data))
        for m, sub, f in routes:
            if sub in url and (m is None or m == method):
                return Resp_g1(f if isinstance(f, bytes) else (DATA / f).read_bytes())
        return None
    return get


def text_pages_g1(name):
    return (DATA / name).read_text(encoding="utf-8").split("\f")


def check_g1(recs, module):
    ids = [i for i, _ in recs]
    assert len(ids) == len(set(ids)), "record ids must be unique"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:")
        assert d["type"] == "dept_office" and d["dept"] == "electricity"
        assert d["level"] in ("state", "zone", "circle", "division", "subdivision", "section")
        assert d.get("area")
    return {d["level"] for _, d in recs}


def by_area_g1(recs, area):
    return [d for _, d in recs if d.get("area") == area]


def test_pvvnl():
    from dforms import power_pvvnl
    calls = []
    recs, files, why = power_pvvnl.fetch({"reader": "power_pvvnl", "district": "Ghaziabad",
                                          "url": "https://pvvnl.org/office_hierarchy/Ghaziabad"},
                                         fake_get_g1([(None, "office_hierarchy/Ghaziabad", "pvvnl.html")], calls))
    assert why == "" and len(recs) == 45 and files[0][0] == "depts/power/power_pvvnl/Ghaziabad.html.gz"
    assert check_g1(recs, "power_pvvnl") == {"zone", "circle", "division", "subdivision"}
    sdo = by_area_g1(recs, "SDO 1 Modinagar")[0]
    assert sdo["level"] == "subdivision" and sdo["name"] == "Sanjay Kumar Singh" and sdo["phone"] == "9193320453"
    assert sdo["email"] == "sdo1.modinagar@pvvnl.org" and sdo["parents"]["division"] == "EDD Modinagar"
    assert sdo["district"] == "Ghaziabad" and sdo["parents"]["zone"] == "Chief Engineer Ghaziabad Zone-II"
    vac = [d for _, d in recs if d["post"].startswith("Superintending Engineer (Attached)")][0]
    assert "name" not in vac                                  # "Vacant"


def test_mvvnl_directory():
    from dforms import power_mvvnl
    recs, files, why = power_mvvnl.fetch({"reader": "power_mvvnl", "part": "directory"},
                                         fake_get_g1([(None, "directory?cd=", "mvvnl.html")]))
    assert why == "" and files[0][0].endswith("directory.html.gz")
    lv = Counter(d["level"] for _, d in recs)
    assert lv == {"division": 8, "circle": 2, "zone": 1}       # no head-quarter, store or commented rows
    se = by_area_g1(recs, "EDC-SITAPUR")[0]
    assert se["level"] == "circle" and se["name"] == "Shri Lalit Krishna" and se["phone"] == "9415901149"
    ee = by_area_g1(recs, "EDD-Sidhauli SITAPUR")[0]
    assert ee["district"] == "Sitapur" and ee["parents"] == {"zone": "SITAPUR ZONE", "circle": "EDC SITAPUR"}
    assert not any("Madhvan" in d["area"] for _, d in recs)


def test_mvvnl_lesa(monkeypatch):
    from dforms import power_mvvnl
    monkeypatch.setattr(power_mvvnl, "layout_pages", lambda content: (text_pages_g1("mvvnl_lesa.txt"), "pdftotext"))
    recs, files, why = power_mvvnl.fetch({"reader": "power_mvvnl", "part": "lesa"},
                                         fake_get_g1([(None, "Lesa-Direcotary", b"%PDF-1.7 saved text is used")]))
    assert why == "" and files[0][2] == "application/pdf"
    assert check_g1(recs, "power_mvvnl") == {"zone", "circle", "division", "subdivision", "section"}
    ce = by_area_g1(recs, "Amausi Zone")[0]
    assert ce["post"] == "Chief Engineer" and ce["phone"] == "9415901415"
    ae = by_area_g1(recs, "AE (33KV) Indralok")[0]
    assert ae["level"] == "subdivision" and ae["phone"] == "9415901425" and ae["parents"]["division"] == "EE (33 KV) Vrindavan"
    je = by_area_g1(recs, "JE (33KV) Indralok")[0]
    assert je["phone"] == "9415901398" and {"name": "Bangla Bazar", "phone": "8005488385"} in je["substations"]


def test_dvvnl():
    from dforms import power_dvvnl
    calls = []
    get = fake_get_g1([("GET", "ContactListNew1", "dvvnl.html"), ("POST", "ContactListNew1", "dvvnl.csv")], calls)
    recs, files, why = power_dvvnl.fetch({"reader": "power_dvvnl"}, get)
    assert why == "" and len(recs) == 24
    assert calls[1][0] == "POST" and calls[1][2]["__EVENTTARGET"] == "ctl00$ContentPlaceHolder1$lnkDownload"
    assert "__VIEWSTATE" in calls[1][2]
    assert check_g1(recs, "power_dvvnl") == {"state", "zone", "circle", "division", "subdivision", "section"}
    je = [d for _, d in recs if d["level"] == "section"]
    assert len(je) == 8 and all(d["post"] == "JE" for d in je)
    md = [d for _, d in recs if d["post"] == "MD"][0]
    assert md["email"] == "md@dvvnl.org" and md["phone"] == "9412719664"


def test_uhbvn(monkeypatch):
    from dforms import power_uhbvn
    monkeypatch.setattr(power_uhbvn, "layout_pages", lambda content: (text_pages_g1("uhbvn_karnal.txt"), "pdftotext"))
    recs, files, why = power_uhbvn.fetch({"reader": "power_uhbvn", "circle": "Karnal"},
                                         fake_get_g1([(None, "contact_us/Karnal.pdf", b"%PDF-1.4 saved text is used")]))
    assert why == "" and len(recs) == 28 and files[0][0] == "depts/power/power_uhbvn/Karnal.pdf"
    assert check_g1(recs, "power_uhbvn") == {"circle", "division", "subdivision"}
    t = by_area_g1(recs, "Taraori")[0]
    assert t["name"] == "Sh. Virender Kumar" and t["post"] == "AEE" and t["phone"] == "01745-242047, 9354726319"
    assert t["email"] == "sdooptaraori@uhbvn.org.in" and t["parents"]["division"] == "XEN Nilonkheri"
    se = by_area_g1(recs, "Operation Circle Karnal")[0]
    assert se["level"] == "circle" and se["name"] == "Sh. Naseeb Singh"


def test_dhbvn(monkeypatch):
    from dforms import power_dhbvn
    monkeypatch.setattr(power_dhbvn, "layout_pages", lambda content: (text_pages_g1("dhbvn_faridabad.txt"), "pdftotext"))
    recs, files, why = power_dhbvn.fetch({"reader": "power_dhbvn", "circle": "faridabad"},
                                         fake_get_g1([(None, "contactus/faridabad.pdf", b"%PDF-1.4 saved text is used")]))
    assert why == "" and len(recs) == 33
    assert check_g1(recs, "power_dhbvn") == {"circle", "division", "subdivision"}
    e = by_area_g1(recs, "East FARIDABAD")[0]
    assert e["name"] == "Er. K. C. Dhiman" and e["phone"] == "0129-2288001, 09540954968"
    assert e["email"] == "sdoopeastfaridabad@dhbvn.org.in" and e["parents"]["division"] == "Old Faridabad"
    g = by_area_g1(recs, "Greater Faridabad")[0]
    assert g["email"] == "xenopgreaterfaridabad@dhbvn.org.in"     # the address is cut over two lines in the pdf
    assert "email" not in by_area_g1(recs, "Dhoj")[0]
    assert by_area_g1(recs, "Hardware Chowk Faridabad")[0]["name"] == "Er. Mohit Yadav"


def test_hpsebl():
    from dforms import power_hpsebl
    recs, files, why = power_hpsebl.fetch({"reader": "power_hpsebl"}, fake_get_g1([(None, "contactlist.html", "hpsebl.html")]))
    assert why == "" and len(recs) == 67
    assert check_g1(recs, "power_hpsebl") == {"zone", "circle", "division", "subdivision"}
    r = by_area_g1(recs, "RIDGE")[0]
    assert r["name"] == "Er.Lal Singh" and r["phone"] == "0177-2653306, 9418160792"
    assert r["parents"] == {"zone": "Shimla Zone", "circle": "Operation Circle Shimla", "division": "City Electrical Division"}
    assert not any("(ES)" in d["area"] for _, d in recs)          # transmission offices are left out


def test_kpdcl():
    from dforms import power_kpdcl
    recs, files, why = power_kpdcl.fetch({"reader": "power_kpdcl"}, fake_get_g1([(None, "kpdcl.jk.gov.in", "kpdcl.html")]))
    assert why == "" and len(recs) == 14
    assert check_g1(recs, "power_kpdcl") == {"circle", "division", "subdivision"}
    k = by_area_g1(recs, "Kangan-SDO")[0]
    assert k["name"] == "Er. Farooq Ahmad Raina" and k["phone"] == "7006285325" and k["district"] == "Ganderbal"
    assert k["parents"] == {"circle": "O&M Circle-Ganderbal", "division": "ED-Ganderbal"}


def test_seeds_g1():
    for m in ("pvvnl", "mvvnl", "dvvnl", "uhbvn", "dhbvn", "hpsebl", "kpdcl"):
        items = json.loads((ROOT / "seeds" / f"dept_power_{m}.json").read_text())
        keys = [i["key"] for i in items]
        assert len(keys) == len(set(keys)) and all(k.startswith(f"power_{m}:") for k in keys)
        assert all(i["payload"]["reader"] == f"power_{m}" and i["payload"]["url"].startswith("https://") for i in items)
        assert all(i["payload"].get("india_only", False) == (m in ("uhbvn", "dhbvn", "hpsebl")) for i in items)


# ---- Rajasthan, Maharashtra, Goa, Telangana, Assam, Arunachal, Meghalaya

from dforms import power_apdcl, power_arunachal, power_goa, power_jvvnl, power_mepdcl, power_msedcl, power_tgspdcl  # noqa: E402


class Resp_g2:
    def __init__(self, b):
        self.content, self.text, self.status_code = b, b.decode("utf-8", "replace"), 200

    def json(self):
        return json.loads(self.content)


def fake_g2(mapping):
    """get() that answers from saved files: {url substring: file name}; None for anything else."""
    def get(url, method="GET", data=None, headers=None):
        for k, f in mapping.items():
            if k in url:
                return Resp_g2((DATA / f).read_bytes())
        return None
    return get


def check_g2(recs, module):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids))
    assert all(r.startswith(f"dept:{module}:") for r in ids)
    for _, d in recs:
        if d["type"] == "dept_office":
            assert d["dept"] == "electricity" and d["level"] in ("state", "zone", "circle", "division", "subdivision", "section")
            assert d.get("area") and d.get("source")
    return {r: d for r, d in recs}


def test_jvvnl():
    recs, files, why = power_jvvnl.fetch({"reader": "power_jvvnl"}, fake_g2({"GetTelephoneDirectory": "jvvnl.json"}))
    assert not why and files[0][0] == "depts/power/power_jvvnl/telephone-directory.json.gz"
    d = check_g2(recs, "power_jvvnl")
    aen = d["dept:power_jvvnl:aen-a-i-dholpur"]
    assert aen["level"] == "subdivision" and aen["name"] == "N.K. Katara" and aen["phone"] == "9413390702"
    assert aen["email"] == "aena1dlp@jvvnl.org" and aen["parents"]["circle"] == "SE (O&M) Dholpur"
    assert d["dept:power_jvvnl:jen-mania"]["level"] == "section"
    assert d["dept:power_jvvnl:zce-jz-jaipur"]["level"] == "zone"
    gss = d["dept:power_jvvnl:aen-o-m-bassi-gss-tunga"]
    assert gss["post"] == "33/11 kV GSS" and gss["phone"] == "9414034820"
    assert d["dept:power_jvvnl:se-o-m-nagaur"]["discom"] == "AVVNL"
    assert d["dept:power_jvvnl:zce-jz-jodhpur"]["discom"] == "JdVVNL"
    assert not any("Chief Minister" in (x.get("post") or "") for x in d.values())      # government rows left out
    assert not any(x.get("post") in ("ARO (A-I) Dholpur", "AO") for x in d.values())   # staff posts left out
    assert "dept:power_jvvnl:zce-t-c-jaipur" not in d                                   # RVPN block left out


def test_tgspdcl():
    recs, files, why = power_tgspdcl.fetch({"reader": "power_tgspdcl"}, fake_g2({"official-contacts": "tgspdcl.json"}))
    assert not why
    d = check_g2(recs, "power_tgspdcl")
    levels = {x["level"] for x in d.values()}
    assert levels == {"zone", "circle", "division", "subdivision", "section"}
    ae = next(x for x in d.values() if x["post"] == "AE/OP/AMEERPET 10")
    assert ae["name"] == "SAMBASIVA RAO BATTULA" and ae["phone"] == "8712468959" and ae["last_updated"] == "2026-11-04"
    assert ae["parents"]["subdivision"] == "ADE/OP/AMEERPET" and ae["parents"]["division"] == "DE/OP/ERRAGADDA"
    hidden = next(x for x in d.values() if x["post"] == "AE/OP/S. K. NAGAR 12")
    assert hidden.get("phone") and hidden.get("shown_on_page") is False                   # isShow 0: kept, flagged (no masking)
    assert not any(x["post"].startswith("PO/") for x in d.values())


def test_apdcl():
    recs, _, why = power_apdcl.fetch({"reader": "power_apdcl"}, fake_g2({"allContact": "apdcl.json"}))
    assert not why
    d = check_g2(recs, "power_apdcl")
    assert sorted(x["level"] for x in d.values()) == ["circle"] * 2 + ["division"] * 2 + ["subdivision"] * 2 + ["zone"] * 2
    sd = d["dept:power_apdcl:88"]
    assert sd["area"] == "Ulubari" and sd["name"] == "Shri Biplab Das" and sd["phone"] == "9954192006"
    assert sd["parents"] == {"circle": "GEC-I", "division": "Guwahati (Central)"} and sd["last_updated"] == "2023-03-02"


def test_arunachal():
    recs, _, why = power_arunachal.fetch({"reader": "power_arunachal"}, fake_g2({"contact.php": "arunachal.html"}))
    assert not why
    d = check_g2(recs, "power_arunachal")
    lumla = d["dept:power_arunachal:subdivision-lumla"]
    assert lumla["name"] == "Shri G Doni" and lumla["phone"] == "9436227779"
    assert lumla["parents"]["division"] == "TAWANG ELECTRICAL DIVISION, TAWANG"
    bdl = d["dept:power_arunachal:division-bomdila"]
    assert bdl["post"] == "Executive Engineer" and bdl["email"] == "electdivn_bdl@yahoo.com"
    assert d["dept:power_arunachal:zone-central-electrical-zone"]["name"] == "Shri Modam Jini"
    assert not any(x["post"] == "Personal Assistant" for x in d.values())


def test_msedcl_ee():
    recs, _, why = power_msedcl.fetch({"reader": "power_msedcl", "kind": "ee"}, fake_g2({"executive-engineer": "msedcl_ee.html"}))
    assert not why
    d = check_g2(recs, "power_msedcl")
    assert all(x["level"] == "division" for x in d.values()) and len(d) == 16
    x = d["dept:power_msedcl:division-chhatrapati-sambhajinagar-rural-kannad"]
    assert x["name"] == "Shri. Ramesh Waghchaure" and x["phone"] == "7875764012" and x["last_updated"] == "2026-07-27"
    assert x["parents"] == {"zone": "Chatrapati Sambhajinagar", "circle": "Chhatrapati Sambhajinagar Rural"}
    assert not any("Admin" in x["area"] for x in d.values())


def test_msedcl_zone_pdf():
    p = {"reader": "power_msedcl", "kind": "zone", "zone": "Nanded", "url": "https://www.mahadiscom.in/x/Nanded-Zone-APIO-PIO-AA-English.pdf"}
    recs, files, why = power_msedcl.fetch(p, fake_g2({"Nanded": "tiny_rows.pdf"}))
    assert not why and files[0][2] == "application/pdf"
    assert recs[0][0] == "dept:power_msedcl:pdf-nanded-p1" and "Tura East" in recs[0][1]["text"]
    assert power_msedcl.fetch(p, fake_g2({"Nanded": "msedcl_ee.html"}))[2] == "not a pdf"


def test_goa():
    pages = json.loads((DATA / "goa_pages.json").read_text())
    d = check_g2(power_goa.parse_pages(pages), "power_goa")
    cee = next(x for x in d.values() if x.get("name") == "Shri Stephen Fernandes")
    assert cee["level"] == "state" and cee["phone"] == "7350611000, 2224680" and cee["email"] == "cee-elec.goa@nic.in"
    ae = next(x for x in d.values() if x.get("name") == "Arvind Gawade")
    assert ae["level"] == "subdivision" and ae["area"] == "Valpoi (Sub-Div-III)" and ae["phone"] == "8380015090"
    honda = next(x for x in d.values() if x.get("name") == "Ravish R. Majik")
    assert honda["level"] == "section" and honda["area"] == "Honda" and honda["parents"]["subdivision"] == "Valpoi (Sub-Div-III)"
    kudnem = [x for x in d.values() if x["area"] == "Kudnem"]
    assert kudnem and all(x["level"] == "section" for x in kudnem)
    assert any(x.get("email") == "aecom.sd3div5@goaelectricity.gov.in" for x in d.values())    # wrapped address joined


def test_mepdcl():
    pages = json.loads((DATA / "mepdcl_western_pages.json").read_text())
    d = check_g2(power_mepdcl.parse_pages(pages, "Western", "https://meecl.nic.in/x.pdf"), "power_mepdcl")
    assert len(d) == 26
    lv = [x["level"] for x in d.values()]
    assert lv.count("zone") == 1 and lv.count("circle") == 3 and lv.count("division") == 5 and lv.count("subdivision") == 17
    amp = next(x for x in d.values() if x["area"] == "Ampati")
    assert amp["phone"] == "7085647822" and amp["parents"]["circle"].startswith("West Garo Hills Distribution Circle")
    egh = next(x for x in d.values() if x["level"] == "circle" and x["area"] == "East Garo Hills")   # the wrapped row
    assert egh["phone"] == "7085647246"


def test_mepdcl_fetch_pdf():
    p = {"reader": "power_mepdcl", "zone": "Western", "url": "https://meecl.nic.in/x-Western-Zone.pdf"}
    recs, files, why = power_mepdcl.fetch(p, fake_g2({"Western": "tiny_rows.pdf"}))
    assert not why and len(recs) == 2 and files[0][0] == "depts/power/power_mepdcl/western-zone.pdf"
    assert {d["level"] for _, d in recs} == {"circle", "subdivision"}


def test_seeds_g2():
    keys = []
    for m in ("jvvnl", "tgspdcl", "apdcl", "arunachal", "msedcl", "goa", "mepdcl"):
        items = json.loads((ROOT / "seeds" / f"dept_power_{m}.json").read_text())
        assert items and all(i["payload"]["reader"] == f"power_{m}" and i["key"].startswith(f"power_{m}:") for i in items)
        keys += [i["key"] for i in items]
    assert len(keys) == len(set(keys)) == 25


# ---- Tamil Nadu, Kerala, Karnataka, Puducherry

from dforms import power_cescmysore, power_hescom, power_kseb, power_mescom, power_puducherry, power_tnpdcl  # noqa: E402



class Resp_g3:
    def __init__(self, b):
        self.content, self.status_code = b, 200
        self.text = b.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.text)


def fake_g3(routes):
    """get() that answers from saved files: routes = [(url substring, method or None, file name)]; logs every call."""
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, url, data))
        for part, meth, name in routes:
            if part in url and (meth is None or meth == method):
                return Resp_g3((DATA / name).read_bytes())
        return None
    get.calls = calls
    return get


def check_g3(recs, files):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids))
    assert all(r.startswith("dept:power_") for r in ids)
    for _, d in recs:
        assert d["type"] == "dept_office" and d["dept"] == "electricity"
        assert d["level"] in ("zone", "circle", "division", "subdivision", "section")
        assert d.get("area") and d.get("state") and d.get("source")
    assert files and all(f[0].startswith("depts/power/") for f in files)


def by_g3(recs, **kw):
    return [d for _, d in recs if all(d.get(k) == v for k, v in kw.items())]


def seeds_g3(name):
    items = json.loads((ROOT / "seeds" / f"dept_power_{name}.json").read_text())
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) and all(k.startswith(f"power_{name}:") for k in keys)
    assert all(i["payload"]["reader"] == f"power_{name}" for i in items)
    return items


def test_tnpdcl():
    recs, files, why = power_tnpdcl.fetch(seeds_g3("tnpdcl")[0]["payload"], fake_g3([("tnpdcl.org", None, "tnpdcl.html")]))
    assert why == "" and len(recs) == 13
    check_g3(recs, files)
    assert [d["level"] for _, d in recs][:4] == ["zone", "circle", "division", "subdivision"]
    sec = by_g3(recs, email="chn061ae@tnebnet.org")[0]
    assert sec["level"] == "section" and sec["area"] == "Perambur, East" and sec["phone"] == "044-25505002, 9280076237"
    assert sec["parents"] == {"zone": "Chennai", "circle": "North/Chennai", "division": "Perambur", "subdivision": "Perambur"}
    assert power_tnpdcl.split_office("Assistant Engineer / O and M/Thally,BDO Office Backside")[2] == "Thally"


def test_kseb():
    items = seeds_g3("kseb")
    assert all(i["payload"]["india_only"] for i in items)
    get = fake_g3([("/contact", "GET", "kseb_contact.html"), ("/searchsection", "POST", "kseb_search.html")])
    recs, files, why = power_kseb.fetch(items[0]["payload"], get)
    assert why == "" and get.calls[1][2]["_token"] == "TESTTOKEN" and get.calls[1][2]["selectcircle"] == "Alappuzha"
    check_g3(recs, files)
    s = by_g3(recs, level="section", office_id="5501")[0]
    assert s["area"] == "Alappuzha North" and s["phone"] == "4772245532" and s["email"] == "aenorthalp@gmail.com"
    assert s["parents"]["division"] == "Alappuzha" and s["parents"]["circle"] == "Alappuzha"
    assert len(by_g3(recs, level="section")) == 3 and len(by_g3(recs, level="circle")) == 1


def test_mescom():
    items = {i["payload"]["page"]: i["payload"] for i in seeds_g3("mescom")}
    get = fake_g3([("17/zonal", None, "mescom_zones.html"), ("14/divisional", None, "mescom_divisions.html"),
                ("15/subdivision", None, "mescom_sections.html")])
    z, zf, _ = power_mescom.fetch(items["zones"], get)
    d, df, _ = power_mescom.fetch(items["divisions"], get)
    s, sf, _ = power_mescom.fetch(items["sections"], get)
    for recs, files in ((z, zf), (d, df), (s, sf)):
        check_g3(recs, files)
    ce = by_g3(z, level="zone", area="Mangaluru")[0]
    assert ce["name"] == "Ravikanth R Kamath H" and ce["phone"] == "0824-2425888, 9448289424"
    assert by_g3(d, post="Executive Engineer (Ele)")[0]["name"] == "Santhosh Naik"
    jeppu = by_g3(s, area="Jeppu")[0]
    assert jeppu["level"] == "section" and jeppu["parents"] == {"subdivision": "Attavara"} and jeppu["email"] == "sojeppu@mesco.in"
    sagar = by_g3(s, level="subdivision", area="Sagar USD", post="Assistant Executive Engineer (Ele)")[0]
    assert "9448289516" in sagar["phone"]                                   # the phone on the row below (rowspan)
    assert by_g3(s, area="Vagga")[0]["level"] == "section"                     # section named without "Section"


def test_cescmysore():
    items = seeds_g3("cescmysore")
    assert len(items) == 25 and all(i["payload"]["india_only"] for i in items)
    p = next(i["payload"] for i in items if i["payload"]["office"] == "N R Mohalla Division")
    recs, files, why = power_cescmysore.fetch(p, fake_g3([("N%20R%20Mohalla", None, "cescmysore.html")]))
    assert why == ""
    check_g3(recs, files)
    ee = by_g3(recs, level="division", post="Executive Engineer ( Elecl)")[0]
    assert ee["area"] == "NR Mohalla" and ee["phone"] == "9448994740, 2434165" and ee["district"] == "Mysuru"
    so = by_g3(recs, area="Mandi Mohalla", post="Section Officer (AE)")[0]
    assert so["level"] == "section" and so["parents"] == {"division": "NR Mohalla", "subdivision": "Central"}
    assert by_g3(recs, area="Siddalingapura", post="Service Station")


def test_hescom_text():
    sec = power_hescom.parse_sections([(DATA / "hescom_sections_p1.txt").read_text()])
    assert len(sec) == 18
    assert by_g3(sec, office_id="6")[0]["area"] == "Grameen (Anchatageri)nulavi"
    a = by_g3(sec, office_id="2")[0]
    assert a["area"] == "Mantur Road" and a["phone"] == "9480881041, 0836-2364001, 2360753" and a["level"] == "section"
    off = power_hescom.parse_officers([(DATA / "hescom_officers_p1.txt").read_text()])
    ids = [r for r, _ in off]
    assert len(ids) == len(set(ids))
    assert by_g3(off, level="circle", area="Hubballi")[0]["phone"] == "9448370227"
    assert by_g3(off, level="subdivision", area="Hubli CSD-1")[0]["parents"]["division"] == "Hubli (U)"
    assert by_g3(off, level="subdivision", area="Karwar")[0]["phone"] == "9448149926"
    assert power_hescom.groups([1, 2, 3, 4, 5, 6, 7], [2, 5.5]) == [0, 0, 0, 1, 1, 1, 1]


def test_hescom_fetch(monkeypatch):
    items = {i["payload"]["file"]: i["payload"] for i in seeds_g3("hescom")}
    monkeypatch.setattr(power_hescom, "pdf_pages", lambda b: [(DATA / "hescom_sections_p1.txt").read_text()])
    recs, files, why = power_hescom.fetch(items["sections"], fake_g3([("Section%20Officers", None, "hescom_sections_p1.txt")]))
    assert why == "" and files[0][2] == "application/pdf" and files[0][0] == "depts/power/power_hescom/sections.pdf"
    check_g3(recs, files)


def test_puducherry():
    secs = power_puducherry.sections((DATA / "puducherry_index.html").read_text())
    assert list(secs)[:2] == ["AMBAGARATHUR SECTION", "ARIANKUPPAM SECTION"]
    assert secs["ARIANKUPPAM SECTION"]["url"] == "https://electricity.py.gov.in/ariyankuppam-area-contact-details"
    items = power_puducherry.items(fake_g3([("area-contact-information", None, "puducherry_index.html")]))
    p = next(i["payload"] for i in items if i["payload"]["section"] == "ARIANKUPPAM SECTION")
    recs, files, why = power_puducherry.fetch(p, fake_g3([("ariyankuppam-area", None, "puducherry_area.html")]))
    assert why == ""
    check_g3(recs, files)
    assert [d["level"] for _, d in recs] == ["division", "subdivision", "section"]
    je = recs[2][1]
    assert je["area"] == "Ariankuppam" and je["phone"] == "+91-94890 80375, 260 0340" and je["last_updated"] == "08-05-2026"
    assert je["parents"] == {"division": "Division IX (O&M)", "subdivision": "Rural South O&M"} and "Ariyankuppam" in je["areas"]
    assert len(seeds_g3("puducherry")) == 38


# ---- Andhra Pradesh, Bihar, Jharkhand

class Resp_g4:
    status_code = 200

    def __init__(self, content):
        self.content = content
        self.text = content.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.text)


def fake_g4(mapping):
    """get() that answers from saved files: the first mapping key found in the url wins; None (no answer) otherwise."""
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append(url)
        for part, name in mapping.items():
            if part in url:
                return Resp_g4((DATA / name).read_bytes())
        return None
    get.calls = calls
    return get


def check_g4(recs, files, why, module):
    assert why == ""
    assert files and all(f[0].startswith(f"depts/power/{module}/") for f in files)
    ids = [i for i, _ in recs]
    assert len(ids) == len(set(ids))
    assert all(i.startswith(f"dept:{module}:") for i in ids)
    for _, d in recs:
        assert d["type"] == "dept_office" and d["dept"] == "electricity"
        assert d["level"] in ("state", "zone", "circle", "division", "subdivision", "section")
    return {d.get("post"): d for _, d in recs}


def test_apspdcl():
    from dforms import power_apspdcl as m
    recs, files, why = m.fetch({"url": m.URL}, fake_g4({"phonenumbers": "apspdcl.html"}))
    by = check_g4(recs, files, why, "power_apspdcl")
    assert len(recs) == 27
    assert by["SE/O/TPT"]["level"] == "circle" and by["SE/O/TPT"]["area"] == "Tirupati"
    assert by["EE/Tirupati/Town/DO"]["level"] == "division"
    assert by["DEE/Town/1/Tirupati"]["level"] == "subdivision"
    sec = by["AE/BalajiColony/Tirupati"]
    assert sec["level"] == "section" and sec["phone"] == "9440814312" and sec["parents"] == {"circle": "Tirupati"}
    assert by["AE/Commercial/CO/TPT"]["staff_post"] and by["AE/Commercial/CO/TPT"]["level"] == "circle"
    assert by["COMPANY SECRETARY"]["level"] == "state"


def test_apepdcl():
    from dforms import power_apepdcl as m
    get = fake_g4({"Zone1": "apepdcl_zone1.html", "contactsNew": "apepdcl_index.html"})
    recs, files, why = m.fetch({"url": m.BASE + "contactsNew?type=VSP", "circle_code": "VSP"}, get)
    by = check_g4(recs, files, why, "power_apepdcl")
    assert any("Circle%20Office" in u for u in get.calls)       # asked, no saved copy: skipped
    assert len(recs) == 11
    assert by["EE/ O/ Zone-I/ Visakhapatnam"]["level"] == "division"
    assert by["EE/ O/ Zone-I/ Visakhapatnam"]["phone"] == "9440812488, 0891-2566367"
    sub = by["Dy.EE/ O/Seethammadhara"]
    assert sub["level"] == "subdivision" and sub["email"] == "dee_opn_stmd@apeasternpower.com"
    sec = by["AEE/O/Asilmetta"]
    assert sec["level"] == "section" and sec["area"] == "Asilmetta"
    assert sec["parents"] == {"circle": "Visakhapatnam", "division": "Zone1(Visakhapatnam)", "subdivision": "Seethammadhara"}


def test_apcpdcl():
    from dforms import power_apcpdcl as m
    url = "https://apcpdcl.in/contact-phno-guntur.php"
    recs, files, why = m.fetch({"url": url, "circle": "Guntur"}, fake_g4({"guntur": "apcpdcl_guntur.html"}))
    by = check_g4(recs, files, why, "power_apcpdcl")
    assert len(recs) == 15
    assert by["SE/Opn/Guntur"]["level"] == "circle" and by["SE/Opn/Guntur"]["email"] == "seopn_gnt@apcpdcl.in"
    assert by["EE/M&P-1/GUNTUR"]["staff_post"] and by["EE/M&P-1/GUNTUR"]["parents"]["wing"] == "M&P WING"
    assert by["EE O TENALI"]["level"] == "division"
    sec = by["AE DUGGIRALA"]
    assert sec["level"] == "section" and sec["phone"] == "9440812306"
    assert sec["parents"] == {"circle": "Guntur", "division": "Tenali", "subdivision": "RURAL 1 TENALI"}


def test_nbpdcl():
    from dforms import power_nbpdcl as m
    recs, files, why = m.fetch({"url": m.URL}, fake_g4({"frmHelplineNumbers": "nbpdcl.html"}))
    check_g4(recs, files, why, "power_nbpdcl")
    assert len(recs) == 32
    rows = [d for _, d in recs]
    lv = {d["level"] for d in rows}
    assert lv == {"state", "zone", "circle", "division", "subdivision", "section"}
    bach = next(d for d in rows if d["area"] == "Bachhwara" and d["level"] == "subdivision")
    assert bach["phone"] == "7763815241" and bach["parents"] == {"circle": "Begusarai", "division": "Barauni"}
    assert next(d for d in rows if d["level"] == "zone")["area"] == "Tirhut Area"
    assert any(d.get("name") == "Sri Ajay Yadav" for d in rows)
    telpa = next(d for d in rows if d["area"] == "Telpa")
    assert telpa["level"] == "section" and telpa["post"] == "SBO"


def test_sbpdcl():
    from dforms import power_sbpdcl as m
    recs, files, why = m.fetch({"url": m.URL}, fake_g4({"frmHelplineNumbers": "sbpdcl.html"}))
    check_g4(recs, files, why, "power_sbpdcl")
    rows = [d for _, d in recs]
    assert len(rows) == 30
    sub = next(d for d in rows if d["area"] == "MeenaBazar" and d["post"] == "AEE(Supply)")
    assert sub["level"] == "subdivision" and sub["phone"] == "7763814142"
    assert sub["parents"] == {"circle": "PESU(E)", "division": "Gulzarbagh"}
    sec = next(d for d in rows if d["area"] == "MeenaBazar 1")
    assert sec["level"] == "section"
    fuse = next(d for d in rows if d["area"] == "Khajpura")
    assert fuse["post"] == "Fuse Call Centre" and fuse["parents"] == {"division": "ASHIANA"}
    assert next(d for d in rows if d["post"] == "ESE")["level"] == "circle"


def test_jbvnl():
    from dforms import power_jbvnl as m
    get = fake_g4({"hqofficer": "jbvnl_hq.html", "know-your-officers": "jbvnl.html"})
    recs, files, why = m.fetch({"url": m.URL}, get)
    check_g4(recs, files, why, "power_jbvnl")
    rows = [d for _, d in recs]
    assert {d["level"] for d in rows} == {"section", "subdivision", "division", "circle", "zone"}
    adp = next(d for d in rows if d["area"] == "Adityapur-I" and d["level"] == "section")
    assert adp["phone"] == "9431135953" and adp["email"] == "jmeso.adpr1@jbvnl.co.in"
    assert adp["last_updated"] == "2026-02-21"
    assert not any(d["area"].upper().startswith("NOT OPEN") for d in rows)
    zone = next(d for d in rows if d["level"] == "zone")
    assert "phone" not in zone and zone["email"].count("@") == 2
    recs, files, why = m.fetch({"url": "https://jbvnl.co.in/hqofficer"}, get)
    check_g4(recs, files, why, "power_jbvnl")
    assert recs[0][1]["name"] == "Shri Sanjay Kumar" and recs[0][1]["level"] == "state"


def test_seeds_g4():
    for mod in ("apspdcl", "apepdcl", "apcpdcl", "nbpdcl", "sbpdcl", "jbvnl"):
        items = json.loads((ROOT / "seeds" / f"dept_power_{mod}.json").read_text())
        keys = [i["key"] for i in items]
        assert len(keys) == len(set(keys)) and all(k.startswith(f"power_{mod}:") for k in keys)
        assert all(i["payload"]["reader"] == f"power_{mod}" and i["payload"]["url"].startswith("https://") for i in items)
        assert all(bool(i["payload"].get("india_only")) == (mod == "apcpdcl") for i in items)
