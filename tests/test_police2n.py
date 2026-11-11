"""North and East police officer readers (dforms/police2n_*.py) on saved samples (tests/data/police2n_*): no network.
FakeGet answers each url from a file, so fetch(payload, get) runs as it does on the pool."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = Path(__file__).parent / "data"


class Answer:
    def __init__(self, content, url):
        self.content = content if isinstance(content, bytes) else content.encode("utf-8")
        self.text = self.content.decode("utf-8", "replace")
        self.url = url
        self.status_code = 200
        self.encoding = "utf-8"

    def json(self):
        return json.loads(self.text)


class FakeGet:
    """routes: {url: file name in tests/data}. Unknown urls answer None (as get() does on an error)."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, method="GET", data=None, headers=None):
        self.calls.append((method, url, data))
        hit = self.routes.get(url)
        if hit is None:
            return None
        return Answer((DATA / hit).read_bytes(), url)


def by_area(recs, level=None):
    return {r["area"]: r for _, r in recs if level is None or r["level"] == level}


def test_up_officials_circles():
    from dforms import police2n_up as m
    url = "https://uppolice.gov.in/frmOfficials.aspx?aligarh&cd=MwAwADkA"
    recs, files, why = m.fetch({"url": url, "state": "UP", "unit": "aligarh", "district": "Aligarh"},
                               FakeGet({url: "police2n_up_aligarh.html"}))
    assert why == "" and files[0][0] == "depts/police/police2n_up/aligarh.gz"
    c = by_area(recs, "circle")
    assert c["Gabhan"]["name"] == "SHRUSTI JAIN" and c["Gabhan"]["phone"] == "9454402803"
    assert c["Gabhan"]["email"] == "co-gabhana.al@up.gov.in" and c["Gabhan"]["post"] == "CO Gabhan"
    assert c["City I"]["name"] == "KAMLESH KUMAR"
    assert "Traffic" not in " ".join(c)                       # a function, not a circle
    ssp = dict(recs)["dept:police2n_up:aligarh:ssp-aligarh"]
    assert ssp["level"] == "district" and ssp["name"] == "NEERAJ KUMAR JADAUN" and ssp["phone"].startswith("9454400247")
    assert not any("Reserve" in (r.get("post") or "") or r.get("post") == "RI" for _, r in recs)


def test_up_items_menu():
    from dforms import police2n_up as m
    items = m.items(FakeGet({m.MENU: "police2n_up_aligarh.html"}))
    units = [i["payload"]["unit"] for i in items]
    assert units == ["aligarh", "commlko"]                    # range and zone pages are not items
    assert items[1]["payload"]["district"] == "Lucknow"


def test_up_commissionerate_acp():
    from dforms import police2n_up as m
    url = "https://uppolice.gov.in/frmOfficials.aspx?commlko&cd=NAA0ADQANgA%3D"
    recs, _, _ = m.fetch({"url": url, "unit": "commlko", "district": "Lucknow"}, FakeGet({url: "police2n_up_commlko.html"}))
    rid = dict(recs)
    cp = rid["dept:police2n_up:lucknow:commissioner-of-police"]
    assert cp["name"] == "TARUN GAUBA" and cp["office_type"] == "office"     # "COMMISSIONER" is not "mission"
    acp = rid["dept:police2n_up:lucknow:acp-gomati-nagar"]
    assert acp["level"] == "circle" and acp["post"] == "ACP Gomati Nagar" and acp["phone"] == "9454401499"
    assert rid["dept:police2n_up:lucknow:acp-traffic"]["level"] == "district"


def test_pb_shos_and_officers():
    from dforms import police2n_pb as m
    u1, u2 = "https://barnala.punjabpolice.gov.in/shos-mhcs", "https://barnala.punjabpolice.gov.in/officers-list"
    get = FakeGet({u1: "police2n_pb_barnala_shos.html", u2: "police2n_pb_barnala_officers.html"})
    recs, _, why = m.fetch({"url": u1, "state": "PB", "district": "Barnala"}, get)
    s = by_area(recs)
    assert s["City-1 Barnala"]["name"] == "Lakhvir Singh" and s["City-1 Barnala"]["rank"] == "INSP"
    assert s["City-1 Barnala"]["phone"] == "7508179014" and s["City-1 Barnala"]["mhc_phone"] == "8699987805"
    assert s["City-1 Barnala"]["email"] == "ps.cty.brn.police@punjab.gov.in"
    assert "name" not in s["Tallewal"]                        # "ADDITIONAL CHARGE" is not a name
    recs, _, _ = m.fetch({"url": u2, "state": "PB", "district": "Barnala"}, get)
    sub = by_area(recs, "subdivision")
    assert sub["Tapa"]["name"] == "Sh. Jaskaran Singh Brar" and sub["Tapa"]["phone"] == "7508179006"
    assert any(r["level"] == "district" and r["name"] == "Sh. Md. Sarfaraz Alam" for _, r in recs)


def test_pb_jalandhar_commissionerate():
    from dforms import police2n_pb as m
    u = "https://jalandharcity.punjabpolice.gov.in/officers-contact/"
    recs, _, _ = m.fetch({"url": u, "district": "Jalandhar"}, FakeGet({u: "police2n_pb_jalandhar.html"}))
    ps = by_area(recs, "police_station")
    assert ps["Div. 1"]["name"] == "Jaspal Singh" and ps["Div. 1"]["belt_no"] == "19/JR" and ps["Div. 1"]["rank"] == "INSP"
    assert ps["Div. 1"]["phone"] == "9592914111, 9876343560"
    pp = [r for _, r in recs if r.get("office_type") == "police post"]
    assert pp and pp[0]["area"] == "Bus Stand" and pp[0]["parent_station"] == "Div. 6"
    cp = [r for _, r in recs if r["level"] == "district" and r["post"].startswith("Commissioner")]
    assert cp and cp[0]["name"] == "Sh. Satinder Singh"


def test_ml_jowai_contacts():
    from dforms import police2n_ml as m
    u = "https://jowaipolice.gov.in/contacts.html"
    recs, _, why = m.fetch({"url": u, "form": "contacts", "district": "West Jaintia Hills"}, FakeGet({u: "police2n_ml_jowai.html"}))
    ps = by_area(recs, "police_station")
    assert ps["Jowai"]["name"] == "S. Manner" and ps["Jowai"]["post"] == "OC" and ps["Jowai"]["phone"] == "7005208211"
    assert ps["Saitsama OP"]["office_type"] == "police post" and ps["Saitsama OP"]["name"] == "K. Rani"
    sub = by_area(recs, "subdivision")
    assert sub["Amlarem"]["name"] == "Shri. K.N.Sangma, MPS" and sub["Amlarem"]["email"] == "sdpo-amlarem@meghalaya.gov.in"
    assert not any("Reserve" in (r.get("designation") or "") for _, r in recs)


def test_ml_shillong_rowspan():
    from dforms import police2n_ml as m
    u = "https://shillongpolice.gov.in/contacts.html"
    recs, _, _ = m.fetch({"url": u, "form": "shillong"}, FakeGet({u: "police2n_ml_shillong.html"}))
    ps = by_area(recs, "police_station")
    assert ps["Lumdiengjri"]["email"] == "oc.lumdiengjri-meg@nic.in"     # one rowspan cell names three stations
    assert ps["Lumdiengjri"]["phone"] == "7085875556, 0364-2548151"
    assert ps["Sadar"]["last_updated"] == "2026-06-03"
    assert by_area(recs, "subdivision")["Sohra"]["phone"] == "03637-235935"


def test_ml_stations_and_directory():
    from dforms import police2n_ml as m
    u1, u2 = "https://megpolice.gov.in/know-your-police-station", "https://megpolice.gov.in/telephone-directory"
    get = FakeGet({u1: "police2n_ml_stations.html", u2: "police2n_ml_directory.html"})
    recs, _, _ = m.fetch({"url": u1, "form": "stations"}, get)
    s = by_area(recs)
    assert s["Shillong Sadar"]["district"] == "East Khasi Hills" and s["Nongstoin"]["district"] == "West Khasi Hills"
    recs, _, _ = m.fetch({"url": u2, "form": "directory"}, get)
    d = {r["district"]: r for _, r in recs}
    assert d["West Garo Hills"]["name"] == "Shri A. T. Sangma, IPS" and "9436116900" in d["West Garo Hills"]["phone"]
    assert "Ri-Bhoi" in d and "North Garo Hills" in d


def test_wb_purba_medinipur():
    from dforms import police2n_wb as m
    u1 = "https://www.purbamedinipurpolice.gov.in/police-stations/"
    u2 = "https://www.purbamedinipurpolice.gov.in/telephone-directory/"
    get = FakeGet({u1: "police2n_wb_pmdp_stations.html", u2: "police2n_wb_pmdp_dir.html"})
    recs, _, _ = m.fetch({"url": u1, "form": "stations", "district": "Purba Medinipur"}, get)
    s = by_area(recs)
    assert s["Haldia"]["post"] == "IC" and s["Haldia"]["name"] == "Shri Md. Kudrute Khoda" and s["Haldia"]["phone"] == "9147888671"
    assert s["Kolaghat"]["post"] == "OC" and s["Kolaghat"]["name"] == "Kajal Dutta"
    recs, _, _ = m.fetch({"url": u2, "form": "directory", "district": "Purba Medinipur"}, get)
    assert by_area(recs, "subdivision")["Tamluk"]["name"] == "Shri Avisek Chakraborty"
    assert by_area(recs, "subdivision")["Tamluk"]["phone"] == "9147888654, 03228-266063, 03228-269970"
    assert by_area(recs, "circle")["Nandakumar"]["post"] == "Circle Inspector"
    ps = by_area(recs, "police_station")
    assert ps["Moyna"]["rank"] == "SI" and ps["Moyna"]["name"] == "Arkadeep Halder" and ps["Moyna"]["police_subdivision"] == "Tamluk"
    assert ps["Choukhali Bazer OP"]["office_type"] == "police post"
    assert "Court Inspr. TML" not in " ".join(r.get("post") or "" for _, r in recs)


def test_od_commissionerate_zones():
    from dforms import police2n_od as m
    recs, _, _ = m.fetch({"url": m.URL}, FakeGet({m.URL: "police2n_od_bbsr.html"}))
    rid = dict(recs)
    assert rid["dept:police2n_od:commissionerate:commissioner-of-police"]["name"] == "DR. SURESH DEV DATTA SINGH"
    cap = rid["dept:police2n_od:bhubaneswar-urban-police-district:zone-1:capital"]
    assert cap["circle"] == "Bhubaneswar Urban Police District Zone 1" and cap["district"] == "Khordha"
    assert rid["dept:police2n_od:bhubaneswar-urban-police-district:zone-1"]["level"] == "circle"


def test_dir_purulia_ic_oc_ci():
    from dforms import police2n_dir as m
    u = "https://purulia.gov.in/police/"
    recs, _, why = m.fetch({"url": u, "state": "WB", "district": "Purulia", "max_pages": 1}, FakeGet({u: "police2n_dir_purulia.html"}))
    ps = by_area(recs, "police_station")
    assert ps["Adra PS"]["post"] == "IC" and ps["Adra PS"]["name"] == "Insp. Asish Majumder" and ps["Adra PS"]["phone"] == "9147888781"
    circles = [r for _, r in recs if r["level"] == "circle"]
    assert any(r["area"] == "Sadar" and r["name"] == "Insp. Bappa Mitra" for r in circles)
    assert all(r["level"] in ("police_station", "circle", "subdivision", "district") for _, r in recs)
    assert not any("Control Room" in (r.get("area") or "") for _, r in recs)


def test_dir_araria_sdpo_names():
    from dforms import police2n_dir as m
    u = "https://araria.nic.in/directory/"
    recs, _, _ = m.fetch({"url": u, "state": "BR", "district": "Araria", "max_pages": 1}, FakeGet({u: "police2n_dir_araria.html"}))
    sub = by_area(recs, "subdivision")
    assert sub["Forbesganj"]["name"] == "Shri Raj Kishore Kumar" and sub["Forbesganj"]["post"] == "SDPO"
    assert by_area(recs, "circle")["Raniganj"]["name"] == "Satish Kumar Singh"


def test_dir_name_filter():
    from dforms.police2n_dir import person
    assert person("Incharge") is None and person("S.O.") is None and person("SHO Jaurkian") is None
    assert person("Superintendent Of Police") is None and person("Vacant") is None
    assert person("Insp. Srikanta Mula (In-Charge)") == "Insp. Srikanta Mula (In-Charge)"
    assert person("Shri Sushil Kumar") == "Shri Sushil Kumar"


def test_seeds_valid():
    import importlib
    keys = set()
    for f in sorted((ROOT / "seeds").glob("dept_police2n_*.json")):
        for x in json.loads(f.read_text()):
            assert x["key"].startswith("police2n_") and x["key"] not in keys
            keys.add(x["key"])
            p = x["payload"]
            assert p["reader"].startswith("police2n_") and p["url"].startswith("https://") and p["state"]
            assert hasattr(importlib.import_module("dforms." + p["reader"]), "fetch")
    assert len(keys) > 150
