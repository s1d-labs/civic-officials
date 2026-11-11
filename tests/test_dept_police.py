"""Police readers (dforms/police_<xx>.py) on saved samples (tests/data/police_*): no network. FakeGet answers each url from
a file, so fetch(payload, get) runs as it does on the pool."""
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
    """routes: {url or url prefix: file name in tests/data, or bytes/str}. Unknown urls answer None (as get() does on an error)."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, method="GET", data=None, headers=None):
        self.calls.append((method, url, data))
        hit = self.routes.get(url)
        if hit is None:
            hit = next((v for k, v in sorted(self.routes.items(), key=lambda kv: -len(kv[0])) if url.startswith(k)), None)
        if hit is None:
            return None
        if callable(hit):
            hit = hit(url, method, data)
            if hit is None:
                return None
        if isinstance(hit, str) and len(hit) < 200 and "\n" not in hit and (DATA / hit).exists():
            hit = (DATA / hit).read_bytes()
        return Answer(hit, url)


def data(name):
    return (DATA / name).read_text(encoding="utf-8")


def ids_unique(recs):
    ids = [r for r, _ in recs]
    return len(ids) == len(set(ids))


def check_common(recs, module, state):
    assert recs and ids_unique(recs)
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:")
        assert d["type"] == "dept_office" and d["dept"] == "police" and d.get("level")
        assert d.get("area") and d.get("state") == state and d.get("source")


def check_seed(module):
    items = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    keys = [i["key"] for i in items]
    assert items and len(keys) == len(set(keys))
    for i in items:
        assert i["key"].startswith(module) and i["payload"]["reader"] == module


# --- Ladakh ---------------------------------------------------------------------------------------------------------------
def test_la():
    from dforms import police_la
    get = FakeGet({police_la.URL: "police_la.html"})
    recs, files, why = police_la.fetch({"reader": "police_la", "url": police_la.URL}, get)
    check_common(recs, "police_la", "LA")
    d = dict(recs)
    assert d["dept:police_la:leh:ps-leh"]["name"] == "Manzoor Hussain"
    assert d["dept:police_la:leh:ps-leh"]["phone"] == "9541900283"
    assert d["dept:police_la:kargil:pp-rangdum"]["phone"] == "01895-232275, 6006909918"
    assert d["dept:police_la:kargil:pp-rangdum"]["office_type"] == "police post"
    assert files and files[0][0].startswith("depts/police/police_la/") and not why
    check_seed("police_la")


# --- Statewide India-only APIs and lists: AP, Bihar, Karnataka (KSP + BCP), Tamil Nadu, Punjab, Haryana, Jharkhand ----
def test_ap():
    from dforms import police_ap
    get = FakeGet({police_ap.BASE + "/public/session/init": b"{}", police_ap.BASE + "/public/organization/police-station-table": "police_ap.json"})
    recs, files, why = police_ap.fetch({"reader": "police_ap", "url": police_ap.URL}, get)
    check_common(recs, "police_ap", "AP")
    assert len(recs) == 3 and not why and get.calls[0][1].endswith("/public/session/init")
    d = dict(recs)["dept:police_ap:alluri-sitharama-raju:annavaram"]
    assert d["phone"] == "9440904237" and d["circle"] == "Chintapalli Circle" and d["lat"] == 17.79058
    assert d["last_updated"] == "2026-07-14"
    assert police_ap.fetch({"reader": "police_ap"}, FakeGet({}))[2] == "session/init did not answer"
    check_seed("police_ap")


def test_br():
    from dforms import police_br
    p = {"reader": "police_br", "district_id": 2, "district": "Arwal",
         "url": police_br.BASE + "?action=search&districtId=2&lang=en"}
    recs, files, why = police_br.fetch(p, FakeGet({police_br.BASE: "police_br.json"}))
    check_common(recs, "police_br", "BR")
    d = dict(recs)["dept:police_br:13"]
    assert d["area"] == "Arwal" and d["area_regional"] == "अरवल" and d["phone"] == "9031826455"
    assert d["email"] == "sho-arwal-bih@gov.in" and d["district"] == "Arwal"
    items = police_br.items(FakeGet({police_br.BASE: b'{"districts": [{"id": 26, "name": "Patna", "station_count": 88}]}'}))
    assert items[0]["key"] == "police_br:26-patna" and items[0]["payload"]["expected"] == 88
    check_seed("police_br")


def test_ka_ksp():
    from dforms import police_ka
    p = {"reader": "police_ka", "district_id": "17", "district": "Gadag", "url": police_ka.fetch_url(17)}
    recs, files, why = police_ka.fetch(p, FakeGet({police_ka.fetch_url(17): "police_ka_17.html"}))
    check_common(recs, "police_ka", "KA")
    d = dict(recs)
    b = d["dept:police_ka:17:betageri-ps"]
    assert b["phone"] == "08372-246333" and b["email"] == "betagerigdg@ksp.gov.in" and b["circle"] == "Betageri Circle"
    assert b["lat"] == 15.445417
    cen = d["dept:police_ka:17:gadag-cen-crime-ps"]          # placeholders left out
    assert "phone" not in cen and "email" not in cen
    dcre = d["dept:police_ka:17:gadag-dcre-ps"]
    assert "lat" not in dcre and "address" not in dcre
    check_seed("police_ka")


def test_ka_bcp():
    from dforms import police_ka
    recs, files, why = police_ka.fetch({"reader": "police_ka", "kind": "bcp", "url": police_ka.BCP}, FakeGet({police_ka.BCP: "police_ka_bcp.html"}))
    check_common(recs, "police_ka", "KA")
    assert len(recs) == 8                                      # the page's second copy is dropped
    d = dict(recs)
    assert d["dept:police_ka:bcp:dcp-central"]["level"] == "division"
    assert d["dept:police_ka:bcp:acp-seshadripuram"]["level"] == "subdivision"
    s = d["dept:police_ka:bcp:pi-seshadripuram-ps"]
    assert s["level"] == "police_station" and s["phone"] == "9480801125, 080-22942586, 080-22942082" and s["division"] == "CENTRAL"


def test_tn():
    from dforms import police_tn
    p = {"reader": "police_tn", "unit_id": 3, "dist_id": "70000517", "district": "ARIYALUR"}
    recs, files, why = police_tn.fetch(p, FakeGet({police_tn.grid_url(3, "70000517"): "police_tn.json"}))
    check_common(recs, "police_tn", "TN")
    d = dict(recs)
    assert d["dept:police_tn:70000517:ariyalur:selvakumar-s"]["level"] == "district"
    assert "phone" not in d["dept:police_tn:70000517:ariyalur:selvakumar-s"]           # 98429..: not the CUG series
    sd = d["dept:police_tn:70000517:jayankondam-sd:velmurugan-a"]
    assert sd["level"] == "subdivision" and sd["phone"] == "9498214528" and "email" not in sd   # generic police@ left out
    st = d["dept:police_tn:70000517:andimadam:gunasekaran-m"]
    assert st["level"] == "police_station" and st["phone"] == "9498100717" and "email" not in st  # gmail left out
    assert "phone" not in d["dept:police_tn:70000517:t-palur:pushparaj-g-s"]
    assert d["dept:police_tn:70000517:pew-ariyalur:santhi-v"]["office_type"] == "wing"
    check_seed("police_tn")


def test_pb():
    from dforms import police_pb
    get = FakeGet({police_pb.details_url(25883, "PSOC"): "police_pb_psoc.json", police_pb.details_url(25883, "WOMEN_PS"): "police_pb_women.json"})
    recs, files, why = police_pb.fetch({"reader": "police_pb", "district_code": "25883", "district": "BARNALA"}, get)
    check_common(recs, "police_pb", "PB")
    assert len(recs) == 3 and len(files) == 2                       # the CIA row without station and SHO is left out
    d = dict(recs)
    t = d["dept:police_pb:25883:60"]
    assert t["area"] == "TAPPA MANDI" and t["name"] == "Amrik Singh" and t["rank"] == "SI" and t["phone"] == "7508018190"
    assert (t["lat"], t["lon"]) == (30.2980608, 75.368883)          # scaled values fixed
    dh = d["dept:police_pb:25883:54"]
    assert (dh["lat"], dh["lon"]) == (30.278126, 75.5769)           # swapped values fixed
    assert dh["phone"] == "7508179016, 01679264523" and dh["mhc_mobile"] == "7508031900"
    assert d["dept:police_pb:25883:999"]["office_type"] == "women police station"
    check_seed("police_pb")


def test_hr_state():
    from dforms import police_hr
    recs, files, why = police_hr.fetch({"reader": "police_hr", "url": police_hr.URL}, FakeGet({police_hr.URL: "police_hr_state.html"}))
    check_common(recs, "police_hr", "HR")
    d = dict(recs)
    f = d["dept:police_hr:faridabad:p-s-old-faridabad"]
    assert f["phone"] == "9582200123, 0129-2296824" and f["email"] == "shooldfbd-hry@nic.in" and f["last_updated"] == "2025-04-01"
    assert any(x.get("office_type") == "Women Police Stations" and "district" not in x for x in d.values())
    assert any(x.get("district") == "Ambala" for x in d.values())
    check_seed("police_hr")


def test_hr_sho():
    from dforms import police_hr
    url = "https://jind.haryanapolice.gov.in/SHOContact.html"
    recs, files, why = police_hr.fetch({"reader": "police_hr", "kind": "sho", "district": "jind", "url": url}, FakeGet({url: "police_hr_jind.html"}))
    check_common(recs, "police_hr", "HR")
    d = dict(recs)
    c = d["dept:police_hr:sho:jind:ps-city-jind"]
    assert c["name"] == "Parveen Kumar" and c["rank"] == "Insp." and c["phone"] == "8814011511" and c["mhc_mobile"] == "8814011565"
    assert c["email"] == "shojindcity-hry@nic.in"
    pp = d["dept:police_hr:sho:jind:pp-rohtak-road-jind"]
    assert pp["office_type"] == "police post" and pp["rank"] == "ASI" and pp["name"] == "Amit Kumar"


def test_hr_phone_workaround():
    from dforms.police_hr import ph
    assert ph("08372-278213") == "08372-278213"
    assert ph("(0129)- 2296824", "9582200123") == "0129-2296824, 9582200123"


def test_jh():
    from dforms import police_jh
    p = {"reader": "police_jh", "nid": "397", "district": "Pakur", "url": police_jh.district_url(397)}
    recs, files, why = police_jh.fetch(p, FakeGet({police_jh.district_url(397): "police_jh.html"}))
    check_common(recs, "police_jh", "JH")
    d = dict(recs)["dept:police_jh:397:amrapadha-ps"]
    assert d["phone"] == "9798922221" and d["district"] == "Pakur" and d["office_id"].startswith("amrapadha-ps-")
    assert police_jh.landline("0651", "2242132") == "0651-2242132"
    check_seed("police_jh")


# --- PDFs and small states/UTs: Kerala, A&N, Puducherry, Mizoram, Sikkim, Lakshadweep, DNH&DD, Arunachal, J&K ---------
# --- Kerala ---------------------------------------------------------------------------------------------------------------
def test_kl():
    from dforms import police_kl
    recs, files, why = police_kl.fetch({"reader": "police_kl", "url": police_kl.URL}, FakeGet({police_kl.URL: "police_kl.pdf"}))
    check_common(recs, "police_kl", "KL")
    d = dict(recs)
    museum = d["dept:police_kl:thiruvananthapuram-city:museum-ps"]
    assert museum["phone"] == "9497987006, 0471-2315096, 9497980039" and museum["station_mobile"] == "9497980039"
    assert museum["vpn"] == "10121" and museum["district"] == "Thiruvananthapuram City"
    assert d["dept:police_kl:railway-police:rpsi-tvc"]["unit"] == "Railway Police"
    assert not any("eow" in r for r in d)          # the neighbour page's text outside the page box is dropped
    assert not any("dcp" in r or "igp" in r for r in d)
    assert files[0][0].endswith(".pdf") and not why
    check_seed("police_kl")


# --- Andaman and Nicobar --------------------------------------------------------------------------------------------------
def test_an():
    from dforms import police_an
    recs, files, why = police_an.fetch({"reader": "police_an", "url": police_an.URL}, FakeGet({police_an.URL: "police_an.pdf"}))
    check_common(recs, "police_an", "AN")
    d = dict(recs)
    assert len(recs) == 32                         # 25 PS + 7 OP; the fire stations after them are not read
    assert d["dept:police_an:ps-ograbraj"]["phone"] == "03192-224934, 9531856271"
    assert d["dept:police_an:op-badam-nalla"]["office_type"] == "out post"
    assert not any("fs-" in r for r in d) and not why
    check_seed("police_an")


# --- Puducherry -----------------------------------------------------------------------------------------------------------
def test_py():
    from dforms import police_py
    get = FakeGet({"https://police.py.gov.in/get_station.php": "police_py_list.json",
                   "https://police.py.gov.in/station.php?id=12": "police_py_station.html"})
    recs, files, why = police_py.fetch({"reader": "police_py", "url": "https://police.py.gov.in/get_station.php"}, get)
    check_common(recs, "police_py", "PY")
    d = dict(recs)["dept:police_py:26001012"]
    assert d["name"] == "R. Marie Christian Paul" and d["rank"] == "Inspector of Police"
    assert d["phone"] == "04368-224750" and d["email"] == "coastl.kkl@py.gov.in" and d["district"] == "Karaikal"
    assert len(recs) == 3 and len(get.calls) == 4 and not why     # stations whose page did not answer keep the list fields
    check_seed("police_py")


# --- Mizoram --------------------------------------------------------------------------------------------------------------
def test_mz():
    from dforms import police_mz
    recs, files, why = police_mz.fetch({"reader": "police_mz"}, FakeGet({police_mz.URL: "police_mz.html"}))
    check_common(recs, "police_mz", "MZ")
    d = dict(recs)
    assert d["dept:police_mz:aizawl:aizawl-ps"]["phone"] == "6909316438"
    assert d["dept:police_mz:aizawl:zonuam-op"]["office_type"] == "out post"
    assert d["dept:police_mz:lunglei:lunglei-ps"]["district"] == "Lunglei"      # rowspan district carried down
    check_seed("police_mz")


# --- Sikkim ---------------------------------------------------------------------------------------------------------------
def test_sk():
    from dforms import police_sk
    recs, files, why = police_sk.fetch({"reader": "police_sk"}, FakeGet({police_sk.URL: "police_sk.html"}))
    check_common(recs, "police_sk", "SK")
    d = dict(recs)
    assert d["dept:police_sk:pakyong:sho-pakyong"]["email"] == "ocpakyong@sikkimpolice.nic.in"
    assert d["dept:police_sk:pakyong:sdpo-rangpo"]["level"] == "subdivision"
    assert d["dept:police_sk:gangtok:sp-gangtok"]["level"] == "district"
    assert not any(":dgp" in r for r in d)          # headquarters posts above the first district are left out
    check_seed("police_sk")


# --- Lakshadweep ----------------------------------------------------------------------------------------------------------
def test_ld():
    from dforms import police_ld
    get = FakeGet({police_ld.URL: "police_ld.html", police_ld.CHARTER: "police_ld.pdf"})
    recs, files, why = police_ld.fetch({"reader": "police_ld", "url": police_ld.URL, "charter": police_ld.CHARTER}, get)
    check_common(recs, "police_ld", "LD")
    d = dict(recs)
    assert len(recs) == 9
    assert d["dept:police_ld:kavaratti"]["name"] == "Shri RM Ali Akber"
    assert d["dept:police_ld:kavaratti"]["phone"] == "04896-262232, 04896-262146"
    assert d["dept:police_ld:agatti"]["email"] == "ps.oicagt-lk@nic.in"          # Agatti / Agathi joined
    assert d["dept:police_ld:kadmath"]["name"] == "Shri Girish Kumar" and d["dept:police_ld:kadmath"]["notes"]
    check_seed("police_ld")


# --- Dadra and Nagar Haveli and Daman and Diu -----------------------------------------------------------------------------
def test_dh():
    from dforms import police_dh
    recs, files, why = police_dh.fetch({"reader": "police_dh"}, FakeGet({police_dh.URL: "police_dh.html"}))
    check_common(recs, "police_dh", "DH")
    d = dict(recs)
    assert len(recs) == 7
    s = d["dept:police_dh:silvassa-police-station"]
    assert s["phone"] == "0260-2652033" and s["district"] == "Dadra and Nagar Haveli" and s["last_updated"] == "2021-03-05"
    assert d["dept:police_dh:diu-police-station"]["address"] == "1st floor, Fort Road, near Collector office, Diu"
    check_seed("police_dh")


# --- Arunachal Pradesh ----------------------------------------------------------------------------------------------------
def _ar(file, district, form):
    from dforms import police_ar
    url = "https://example.nic.in/police/"
    return police_ar.fetch({"reader": "police_ar", "url": url, "district": district, "form": form}, FakeGet({url: file}))


def test_ar():
    recs, files, why = _ar("police_ar_tirap.html", "Tirap", "cards")
    check_common(recs, "police_ar", "AR")
    assert dict(recs)["dept:police_ar:tirap:police-station-borduria"]["phone"] == "9862810168"
    recs, _, _ = _ar("police_ar_changlang.html", "Changlang", "tables")
    d = dict(recs)
    assert d["dept:police_ar:changlang:changlang"]["name"] == "C A Namchoom"
    assert not any("s-p" in r or "dsp" in r for r in d)                        # SP and DSP rows are not stations
    recs, _, _ = _ar("police_ar_itanagar.html", "Itanagar Capital", "list")
    d = dict(recs)
    assert d["dept:police_ar:itanagar-capital:ps-chimpu"]["email"] == "ps-chimpu@arn.gov.in"
    assert d["dept:police_ar:itanagar-capital:naharlagun"]["level"] == "subdivision"
    assert not any("traffic" in r for r in d)
    recs, _, _ = _ar("police_ar_tawang.html", "Tawang", "blocks")
    assert dict(recs)["dept:police_ar:tawang:tawang-police-station"]["phone"] == "03794-222235"
    check_seed("police_ar")


# --- Jammu and Kashmir ----------------------------------------------------------------------------------------------------
def _jk(file, district):
    from dforms import police_jk
    url = "https://example.nic.in/police/"
    return police_jk.fetch({"reader": "police_jk", "url": url, "district": district}, FakeGet({url: file}))


def test_jk():
    recs, files, why = _jk("police_jk_jammu.html", "Jammu")
    check_common(recs, "police_jk", "JK")
    d = dict(recs)
    assert d["dept:police_jk:jammu:p-s-arnia"]["phone"] == "01923-272236"
    assert d["dept:police_jk:jammu:p-s-arnia"]["subdivision"] == "RS Pura"
    assert d["dept:police_jk:jammu:sdpo-akhnoor"]["level"] == "subdivision"
    recs, _, _ = _jk("police_jk_udhampur.html", "Udhampur")
    u = dict(recs)["dept:police_jk:udhampur:ps-udhampur"]
    assert u["name"] == "Raghubir Singh" and u["rank"] == "Insp." and u["phone"] == "9419134268, 01992-270725"
    recs, _, _ = _jk("police_jk_ganderbal.html", "Ganderbal")
    d = dict(recs)
    assert d["dept:police_jk:ganderbal:pp-nagbal"]["office_type"] == "police post"
    assert not any("ssp" in r for r in d)
    check_seed("police_jk")


# --- Maharashtra cities (Mumbai, Pune, Thane, Nagpur, Jalgaon), Goa, Gujarat ------------------------------------------
def test_mumbai():
    from dforms import police_mumbai as m
    url = m.URL.format(5)
    recs, files, why = m.fetch({"reader": m.M, "url": url, "page": 5}, FakeGet({url: "police_mumbai_p5.html"}))
    check_common(recs, m.M, "MH")
    d = dict(recs)["dept:police_mumbai:ताडदेव"]
    assert d["name"] == "मीना जगताप" and d["mobile"] == "8976947218"
    assert d["landline"] == "022-23512109, 022-23525527" and d["email"] == "ps.tardeo.mum@mahapolice.gov.in"
    assert files[0][0] == "depts/police/police_mumbai/police_incharge-p5.html.gz" and not why
    check_seed(m.M)


def test_pune():
    from dforms import police_pune as m
    get = FakeGet({m.API + "?ps=1": "police_pune_1.json", m.API + "?ps=21": lambda *a: None, m.API: "police_pune_list.json"})
    recs, files, why = m.fetch({"reader": m.M, "url": m.API}, get)
    check_common(recs, m.M, "MH")
    d = dict(recs)
    one = d["dept:police_pune:1"]
    assert one["area"] == "Alankar" and one["area_regional"] == "अलंकार"
    assert one["name"] == "Ulhas Guabrao kadam" and one["mobile"] == "8888821877" and one["division"] == "Sinhagad Road Division"
    assert abs(one["lat"] - 18.4984) < 0.001
    assert d["dept:police_pune:1:chowki-2"]["area"] == "Dahanukar"
    assert d["dept:police_pune:21"]["landline"] == "02025536263"    # list row only (detail did not answer): digits from entities
    assert len(files) == 2 and not why
    check_seed(m.M)


def test_thane():
    from dforms import police_thane as m
    sid = "da708b94-c4ef-4250-9cac-295a8867f1fa"

    def action(url, method, body):
        return data("police_thane_stations.rsc").encode() if method == "POST" else None
    get = FakeGet({m.MAP + "/" + sid: "police_thane_ambernath.html", m.MAP: "police_thane_map.html",
                   m.BASE + "/_next/static/immutable/chunks/bbb222.js": "police_thane_chunk.js", m.BASE + "/en": action})
    recs, files, why = m.fetch({"reader": m.M, "url": m.MAP}, get)
    check_common(recs, m.M, "MH")
    assert any(c[0] == "POST" for c in get.calls)
    d = dict(recs)
    a = d[f"dept:police_thane:{sid}"]
    assert a["name"] == "Shri. Shabbir Sayyed" and a["mobile"] == "8007965786" and a["rank"] == "Senior Inspector of Police"
    assert a["landline"] == "0251-2682310" and a["area_regional"] == "अंबरनाथ" and a["lat"] == 19.211315
    assert len(recs) == 2 and not why
    assert m.stations("0:{}\n1:not json") == []
    check_seed(m.M)


def test_nagpur():
    from dforms import police_nagpur as m
    recs, files, why = m.fetch({"reader": m.M, "url": m.URL}, FakeGet({m.URL: "police_nagpur.html"}))
    check_common(recs, m.M, "MH")
    d = dict(recs)
    assert d["dept:police_nagpur:अजनी-पोलीस-ठाणे"]["phone"] == "0712-2746555, 0712-2706361"
    assert d["dept:police_nagpur:अंबाझरी-पोलीस-स्टेशन"]["name"] == "Shri Vinod Godbole"
    assert len(recs) == 3 and not why
    check_seed(m.M)


def test_jalgaon():
    from dforms import police_jalgaon as m
    items = m.items(FakeGet({m.LIST: "police_jalgaon_list.html"}))
    assert len(items) == 37 and {i["key"] for i in items} >= {"police_jalgaon:10", "police_jalgaon:36"}
    url = m.URL.format(10)
    recs, files, why = m.fetch({"reader": m.M, "url": url, "id": "10"}, FakeGet({url: "police_jalgaon_10.html"}))
    check_common(recs, m.M, "MH")
    d = recs[0][1]
    assert d["area"] == "नशिराबाद पोलीस ठाणे" and d["name"] == "योगिता म नारखेडे"
    assert "mobile" not in d and d["mobile_as_published"] == "88579 7016"     # one digit short on the page
    assert d["email"] == "ps.nashirabad.jal@mahapolice.gov.in" and d["digipin"] == "3MM-936-K4K7"
    assert d["subdivision"].startswith("उपविभागीय") and abs(d["lat"] - 21.0039) < 0.001
    check_seed(m.M)


def test_goa():
    from dforms import police_ga as m
    items = m.items(FakeGet({m.HOME: "police_ga_home.html"}))
    assert items and all(" " not in i["payload"]["url"] for i in items)
    url = "https://citizen.goapolice.gov.in/web/guest/anjuna-police-station"
    recs, files, why = m.fetch({"reader": m.M, "url": url}, FakeGet({url: "police_ga_anjuna.html"}))
    check_common(recs, m.M, "GA")
    d = recs[0][1]
    assert recs[0][0] == "dept:police_ga:anjuna-police-station"
    assert d["name"] == "SURAJ H. GAWAS" and d["rank"] == "Police Inspector" and d["mobile"] == "7875756027"
    assert d["email"] == "pianjuna@goapolice.gov.in" and d["address"].startswith("Anjuna Police Station")
    check_seed(m.M)


def test_gujarat():
    from dforms import police_gj as m
    org = m.ORG.format(u="cpahmedabad")
    base = org.split("CMS.aspx")[0]
    get = FakeGet({base + "CMS.aspx?orgchart=true&designation_id=1852": "police_gj_ahd_1852.html", org: "police_gj_ahd_org.html"})
    recs, files, why = m.fetch({"reader": m.M, "url": org, "unit": "cpahmedabad", "district": "Ahmedabad"}, get)
    check_common(recs, m.M, "GJ")
    d = dict(recs)["dept:police_gj:cpahmedabad:1852"]
    assert d["level"] == "police_station" and d["area"] == "નવરંગપુરા" and d["name"] == "શ્રી એન.એ.દેસાઈ"
    assert d["mobile"] == "9898500943, 6359625205" and d["email"] == "polstn-navrang-ahd@gujarat.gov.in"
    assert d["subdivision"].endswith("બી ડીવીઝન") and d["zone"].endswith("ઝોન-૧")
    # the org chart's levels
    assert m.level("પોલીસ ઇન્સ્પેક્ટર (એલ.સી.બી.)") is None
    assert m.level("પોલીસ સબ ઇન્સ્પેક્ટર, વલ્લભીપુર") == "police_station"
    assert m.level("સર્કલ પોલીસ ઇન્સ્પેક્ટર (તળાજા)") == "circle"
    assert m.level("નાયબ પોલીસ કમિશ્નર ઝોન-૧") == "zone" and m.level("નાયબ પોલીસ કમિશ્નર ક્રાઈમ") is None
    assert m.area_of("પોલીસ ઇન્સ્પેક્ટર ( નિલમબાગ પોલીસ સ્ટેશન )") == "નિલમબાગ"
    check_seed(m.M)


# --- Madhya Pradesh (KML maps), Jodhpur, Chhattisgarh, Uttar Pradesh, Telangana, Tripura, Odisha ----------------------
def test_mp():
    from dforms import police_mp
    url = "https://bhopal.mppolice.gov.in/"
    get = FakeGet({url: "police_mp_bhopal.html", "https://www.google.com/maps/d/kml?mid=": "police_mp_bhopal.kml"})
    recs, files, why = police_mp.fetch({"reader": "police_mp", "url": url, "state": "MP", "district": "Bhopal"}, get)
    check_common(recs, "police_mp", "MP")
    d = dict(recs)["dept:police_mp:bhopal:tt-nagar-police-station"]
    assert d["phone"] == "9479990444, 0755-2677344" and d["email"] == "sho.psttnagar-bpl@mppolice.gov.in"
    assert d["zone"] == "Zone - I" and abs(d["lat"] - 23.2359122) < 1e-6 and abs(d["lon"] - 77.4000175) < 1e-6
    assert "mid=1B6Ui99x-DXx_TDO3EGDPPfmtzF4ij6w" in get.calls[1][1]
    assert len(files) == 2 and not why and len(recs) == 3
    check_seed("police_mp")


def test_rj():
    from dforms import police_rj
    get = FakeGet({police_rj.URL: "police_rj_jodhpur.html"})
    recs, files, why = police_rj.fetch({"reader": "police_rj", "url": police_rj.URL}, get)
    check_common(recs, "police_rj", "RJ")
    d = dict(recs)["dept:police_rj:jodhpur:airport"]
    assert d["phone"] == "0291-2944312" and round(d["lat"], 4) == 26.265 and d["area"] == "Police Station Airport"
    check_seed("police_rj")


def test_cg():
    from dforms import police_cg
    get = FakeGet({"https://durg.gov.in/en/police/": "police_cg_durg.html",
                   "https://raipur.gov.in/en/police-station/": "police_cg_raipur.html"})
    recs, files, why = police_cg.fetch({"reader": "police_cg", "url": "https://durg.gov.in/en/police/", "district": "Durg"}, get)
    check_common(recs, "police_cg", "CG")
    d = dict(recs)
    assert d["dept:police_cg:durg:sp-durg"]["level"] == "district"
    assert d["dept:police_cg:durg:sp-durg"]["phone"] == "9479192099, 0788-2322071, 0788-2211999"
    assert d["dept:police_cg:durg:csp-durg"]["level"] == "subdivision"
    st = d["dept:police_cg:durg:mohan-nagar"]
    assert st["level"] == "police_station" and st["phone"] == "9479192020, 0788-2210570"
    assert d["dept:police_cg:durg:o-p-anjora"]["office_type"] == "police post"
    assert st["last_updated"]
    recs, _, _ = police_cg.fetch({"reader": "police_cg", "url": "https://raipur.gov.in/en/police-station/", "district": "Raipur",
                                  "std_prefix": "771"}, get)
    assert dict(recs)["dept:police_cg:raipur:civil-line-police-station"]["phone"] == "0771-4247123"
    check_seed("police_cg")


def test_up():
    from dforms import police_up
    url = "https://prayagraj.nic.in/police/"
    recs, files, why = police_up.fetch({"reader": "police_up", "url": url, "district": "Prayagraj"}, FakeGet({url: "police_up_prayagraj.html"}))
    check_common(recs, "police_up", "UP")
    d = dict(recs)
    k = d["dept:police_up:prayagraj:khuldabad"]
    assert k["phone"] == "9454402837, 0532-2655603" and k["email"] == "so-khuldabad.ah@nic.in" and k["circle"] == "A.C.P. (Kotwali)"
    assert d["dept:police_up:prayagraj:commissioner-of-police"]["level"] == "district"
    assert any(v["level"] == "circle" for v in d.values())
    check_seed("police_up")


def test_tg():
    from dforms import police_tg
    base = "https://hyderabad.telangana.gov.in/public-utility-category/police-stations/"
    get = FakeGet({base: "police_tg_hyd_p1.html", base + "page/2/": "police_tg_hyd_p2.html",
                   "https://medak.telangana.gov.in/police/": "police_tg_medak.html",
                   "https://siddipet.telangana.gov.in/police/": "police_tg_siddipet.html"})
    recs, files, why = police_tg.fetch({"reader": "police_tg", "url": base, "district": "Hyderabad"}, get)
    check_common(recs, "police_tg", "TG")
    d = dict(recs)
    a = d["dept:police_tg:hyderabad:abids-police-station"]
    assert a["phone"] == "9490616303" and a["email"] == "sho_abd@hyd.tspolice.gov.in" and a["pincode"] == "500001"
    assert len(files) >= 2 and any(":bowenpally-police-station" in r for r, _ in recs)     # page 2 followed
    recs, _, _ = police_tg.fetch({"reader": "police_tg", "url": "https://medak.telangana.gov.in/police/", "district": "Medak"}, get)
    d = dict(recs)
    t = d["dept:police_tg:medak:toopran-ps"]
    assert t["level"] == "police_station" and t["post"] == "Sub-Inspector of Police" and t["email"] == "sho-tpn-mdk@tspolice.gov.in"
    assert t["phone"] == "8712657928, 08454-235333" and t["subdivision"] == "Toopran Sub-Division"
    assert d["dept:police_tg:medak:dsp-toopran"]["level"] == "subdivision"
    recs, _, _ = police_tg.fetch({"reader": "police_tg", "url": "https://siddipet.telangana.gov.in/police/", "district": "Siddipet"}, get)
    s = dict(recs)["dept:police_tg:siddipet:siddipet-1town"]                  # SHO row and the station's own row merged
    assert s["phone"] == "8712667311, 8712667450" and s["level"] == "police_station"
    check_seed("police_tg")


def test_tr():
    from dforms import police_tr
    west, south = "https://westpolice.tripura.gov.in/node/96", "https://southpolice.tripura.gov.in/contact"
    get = FakeGet({west: "police_tr_west.html", south: "police_tr_south.html"})
    recs, files, why = police_tr.fetch({"reader": "police_tr", "url": west, "district": "West Tripura"}, get)
    check_common(recs, "police_tr", "TR")
    w = dict(recs)["dept:police_tr:west-tripura:west-agartala-ps"]
    assert w["name"] == "Sanjit Sen" and w["rank"] == "Inspr." and w["post"] == "O/C"
    assert w["phone"] == "6033434070, 0381-2385765" and w["email"] == "ocwestagt@tripurapolice.nic.in"
    assert w["last_updated"] == "2026-09-28"
    recs, _, _ = police_tr.fetch({"reader": "police_tr", "url": south, "district": "South Tripura"}, get)
    d = dict(recs)
    assert d["dept:police_tr:south-tripura:wmn-ps"]["name"] == "Swapna Bhowmik"
    assert d["dept:police_tr:south-tripura:p-r-bari-ps"]["phone"] == "9402329219, 03823-264365"
    check_seed("police_tr")


def test_od():
    from dforms import police_od
    url = "https://jharsuguda.odisha.gov.in/en/administartive-setup/distrcit-police"
    recs, files, why = police_od.fetch({"reader": "police_od", "url": url, "district": "Jharsuguda"}, FakeGet({url: "police_od_jharsuguda.html"}))
    check_common(recs, "police_od", "OD")
    d = dict(recs)
    j = d["dept:police_od:jharsuguda:jharsuguda-p-s"]
    assert j["name"] == "S.Bala" and j["post"] == "IIC" and j["phone"] == "06645-272736" and j["last_updated"] == "2026-11-10"
    assert d["dept:police_od:jharsuguda:sdpo-jharsuguda"]["level"] == "subdivision"
    check_seed("police_od")


# --- Nagaland and Manipur (S3WaaS helpline pages, Manipur control rooms) -------------------------------------------------
def test_nl():
    from dforms import police_nl
    url = "https://kohima.nic.in/helpline/"
    recs, files, why = police_nl.fetch({"reader": "police_nl", "url": url, "state": "NL", "district": "Kohima"},
                                       FakeGet({url: "police_nl_kohima.html"}))
    check_common(recs, "police_nl", "NL")
    d = dict(recs)
    assert d["dept:police_nl:kohima:north"]["phone"] == "7005986008, 7005986018"      # OC first, then the station line
    assert d["dept:police_nl:kohima:women"]["area"] == "Women PS"
    assert d["dept:police_nl:kohima:superintendent-of-police"]["level"] == "district"
    assert d["dept:police_nl:kohima:north"]["last_updated"] == "2026-06-05"
    assert not any("traffic" in r for r in d) and files and not why
    url = "https://phek.nic.in/helpline/"
    recs, _, _ = police_nl.fetch({"url": url, "state": "NL", "district": "Phek"}, FakeGet({url: "police_nl_phek.html"}))
    d = dict(recs)
    assert d["dept:police_nl:phek:pfutsero"]["phone"] == "8794804021"
    assert d["dept:police_nl:phek:outpost-chatheba"]["office_type"] == "police post"
    assert "dept:police_nl:phek:police" not in d                                      # the "Police | Office" row of another table
    check_seed("police_nl")


def test_mn():
    from dforms import police_mn
    url = "https://imphaleast.nic.in/?p=2780"
    recs, _, why = police_mn.fetch({"reader": "police_mn", "form": "helpline", "url": url, "district": "Imphal East"},
                                   FakeGet({url: "police_mn_imphaleast.html"}))
    check_common(recs, "police_mn", "MN")
    assert dict(recs)["dept:police_mn:imphal-east:porompat"]["phone"] == "0385-2442447" and len(recs) == 4
    url = "https://manipurpolice.gov.in/?page_id=3257"
    recs, files, why = police_mn.fetch({"form": "controlrooms", "url": url}, FakeGet({url: "police_mn_controlrooms.html"}))
    d = dict(recs)
    assert len(recs) == 17 and d["dept:police_mn:control-room:imphal-west"]["phone"] == "0385-2450214, 6009030422"
    assert d["dept:police_mn:control-room:dg"]["level"] == "state" and files and not why
    check_seed("police_mn")
