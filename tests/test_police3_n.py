"""North police readers (dforms/police3_*.py) on saved samples (tests/data/police3_*): no network.
FakeGet answers each (method, url) from a file, so fetch(payload, get) runs as it does on the pool."""
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
    """routes: {(method, url) or url: file in tests/data}; a POST route may also name the form value it needs."""

    def __init__(self, routes, post=None):
        self.routes = routes
        self.post = post or {}
        self.calls = []

    def __call__(self, url, method="GET", data=None, headers=None):
        self.calls.append((method, url, data))
        if method == "POST":
            for (field, value), f in self.post.items():
                if (data or {}).get(field) == value:
                    return Answer((DATA / f).read_bytes(), url)
            return None
        hit = self.routes.get(url)
        return Answer((DATA / hit).read_bytes(), url) if hit else None


def by(recs, **kw):
    return [d for _, d in recs if all(d.get(k) == v for k, v in kw.items())]


# --- Delhi -----------------------------------------------------------------------------------------------------------------

def dl_get():
    from dforms import police3_dl as m
    return FakeGet({m.URL: "police3_dl/form.html"},
                   {(m.SELECT, "CENTRAL DISTRICT"): "police3_dl/central-district.html",
                    (m.SELECT, "TRAFFIC"): "police3_dl/traffic.html"})


def test_dl_items():
    from dforms import police3_dl as m
    items = m.items(dl_get())
    units = [i["payload"]["unit"] for i in items]
    assert len(items) == 59 and "CENTRAL DISTRICT" in units and "TRAFFIC" in units and "POLICE CONTROL ROOM" in units
    assert all(i["payload"]["reader"] == "police3_dl" for i in items)


def test_dl_central():
    from dforms import police3_dl as m
    get = dl_get()
    recs, files, why = m.fetch({"unit": "CENTRAL DISTRICT", "state": "DL"}, get)
    assert why == "" and len(recs) == 59 and files[0][0] == "depts/police/police3_dl/central-district.gz"
    assert [c[0] for c in get.calls] == ["GET", "POST"]
    assert get.calls[1][2]["__EVENTTARGET"] == m.SELECT and "__VIEWSTATE" in get.calls[1][2]
    sho = by(recs, post="SHO", area="Karol Bagh")[0]
    assert sho["level"] == "police_station" and sho["district"] == "Central" and sho["state"] == "DL"
    assert sho["phone"].startswith("8750870430") and "011-28726870" in sho["phone"]
    assert sho["email"] == "sho.karolbagh@delhipolice.gov.in, sho-karolbagh-dl@nic.in"
    assert sho["src_pos"] == {"table": 0, "row": 15} and sho["src_url"] == m.URL and len(sho["src_sha256"]) == 64
    assert len(by(recs, post="SHO")) == 19
    assert len(by(recs, post="Inspector (Law & Order)")) == 15 and len(by(recs, post="Inspector (Investigation)")) == 15
    acp = by(recs, level="subdivision", area="Patel Nagar")[0]
    assert acp["post"] == "ACP" and acp["phone"].startswith("8750870408") and "011-25873401" in acp["phone"]
    dcp = by(recs, post="DCP")[0]
    assert dcp["level"] == "district" and dcp["area"] == "Central" and dcp["email"] == "dcp.central@delhipolice.gov.in"
    assert by(recs, post="Addl. DCP-I")[0]["phone"].startswith("9818099064")
    assert by(recs, area="Anand Parbat", post="SHO")       # 'PS ANAND PARBAT' row (second SHO row of the station)


def test_dl_traffic_unit():
    from dforms import police3_dl as m
    recs, _, why = m.fetch({"unit": "TRAFFIC"}, dl_get())
    assert why == "" and len(recs) == 31
    assert all(d["level"] == "state" and d["office_type"] == "traffic" and "district" not in d for _, d in recs)
    assert len({rid for rid, _ in recs}) == 31


def test_dl_std():
    from dforms.police3_dl import std
    assert std("91-11- 25873401,1125873400") == "011-25873401,011-25873400"
    assert std("9211260428, 011-23531734") == "9211260428, 011-23531734"


# --- Haryana ---------------------------------------------------------------------------------------------------------------

def test_hr_fatehabad():
    from dforms import police3_hr as m
    url = "https://fatehabad.haryanapolice.gov.in/contactus.html"
    recs, files, why = m.fetch({"url": url, "district": "Fatehabad", "std": "01667"}, FakeGet({url: "police3_hr/fatehabad.html"}))
    assert why == "" and len(recs) == 38 and files[0][0] == "depts/police/police3_hr/fatehabad.gz"
    sp = by(recs, post="SP, Fatehabad")[0]
    assert sp["level"] == "district" and sp["name"] == "Ms. Nikita Khattar, IPS" and sp["email"] == "spftb@hry.nic.in"
    assert sp["phone"] == "8814011700, 01667-230005, 01667-230006" and sp["src_pos"]["row"] > 0
    sho = by(recs, post="SHO", area="Bhuna")[0]
    assert sho["level"] == "police_station" and sho["name"] == "P/SI Kawar Singh" and sho["phone"].startswith("8814011710")
    assert by(recs, post="SHO", area="PS Women Fatehabad") or by(recs, post="SHO", office_type="women")
    assert by(recs, level="subdivision", area="Bhuna")[0]["name"] == "Sh. Nar Singh, HPS"
    assert len(by(recs, office_type="police post")) == 12


def test_hr_rank_only_and_names():
    from dforms import police3_hr as m
    url = "https://charkhidadri.haryanapolice.gov.in/Contacts.html"
    recs, _, _ = m.fetch({"url": url, "district": "Charkhi Dadri", "std": "01250"}, FakeGet({url: "police3_hr/charkhidadri.html"}))
    assert len(recs) == 13
    city = by(recs, post="SHO", area="City Charkhi Dadri")[0]
    assert city["phone"] == "7419301104, 01250-220863" and city["email"] == "shodadricity-hry@nic.in" and "name" not in city
    assert by(recs, level="district", office_type="office")[0]["phone"].startswith("7419301100")
    url = "https://yamunanagar.haryanapolice.gov.in/Contactus.html"
    recs, _, _ = m.fetch({"url": url, "district": "Yamunanagar"}, FakeGet({url: "police3_hr/yamunanagar.html"}))
    sp = by(recs, post="SP Yamunanagar")[0]
    assert sp["name"] == "Sh. Kamal Deep Goyal, IPS" and sp["phone"].startswith("8818000100")
    assert len(by(recs, level="subdivision")) == 5


# --- Jammu and Kashmir -----------------------------------------------------------------------------------------------------

def test_jk_stations():
    from dforms import police3_jk as m
    recs, files, why = m.fetch({"page": "stations"}, FakeGet({m.URL: "police3_jk/stations.html"}))
    assert why == "" and files[0][0] == "depts/police/police3_jk/stations.gz"
    ps = by(recs, level="police_station")
    assert len(ps) == 194 and len(by(recs, level="subdivision")) == 57
    assert len({d["district"] for d in ps}) == 20                      # 23 police districts -> 20 LGD districts
    b = by(recs, area="PS Bijbehara")[0]
    assert b["district"] == "Anantnag" and b["phone"] == "01932-234221, 234100" and b["subdivision"] == "Bijbehara"
    assert b["src_pos"] == {"table": 0, "row": 1}
    z = by(recs, area="PS Zakoora")[0]
    assert z["address"] == "Near JKHPMC Srinagar" and z["district"] == "Srinagar"
    assert by(recs, police_district="Sopore")[0]["district"] == "Baramulla"
    assert by(recs, police_district="Awantipora")[0]["district"] == "Pulwama"
    assert by(recs, level="subdivision", area="West")


def test_jk_women():
    from dforms import police3_jk as m
    recs, _, why = m.fetch({"page": "women"}, FakeGet({m.WOMEN: "police3_jk/women.html"}))
    assert why == "" and len(recs) == 10 and all(d["office_type"] == "women" for _, d in recs)
    assert by(recs, area="PS Women Rajouri")[0]["district"] == "Rajouri"
    assert by(recs, area="PS Women Rambagh, Srinagar")[0]["phone"] == "9596770601, 9596770602"


def test_seeds_n():
    for st, reader, n in (("dl", "police3_dl", 59), ("hr", "police3_hr", 4), ("up", "police_up", 8), ("hp", "police2n_dir", 5),
                          ("uk", "police2n_dir", 1), ("jk", None, 4)):
        items = json.loads((ROOT / "seeds" / f"dept_police3_{st}.json").read_text())
        assert len(items) == n and len({i["key"] for i in items}) == n
        assert all(i["payload"]["reader"] == reader for i in items) if reader else True
