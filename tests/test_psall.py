"""Police station lists on S3WaaS district portals (dforms/psall_s3waas.py) on full saved pages (tests/data/psall_*): no network."""
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = Path(__file__).parent / "data"


class Answer:
    def __init__(self, content, url):
        self.content = content
        self.text = content.decode("utf-8", "replace")
        self.url = url
        self.status_code = 200
        self.encoding = "utf-8"


class FakeGet:
    def __init__(self, routes):
        self.routes = routes

    def __call__(self, url, method="GET", data=None, headers=None):
        hit = self.routes.get(url)
        return Answer(gzip.decompress((DATA / hit).read_bytes()), url) if hit else None


def run(routes, url, state, district):
    from dforms import psall_s3waas as m
    return m.fetch({"url": url, "state": state, "district": district}, FakeGet(routes))


def stations(recs):
    return {r["area"]: r for _, r in recs if r["level"] == "police_station"}


def test_ariyalur_cards_two_pages():
    u = "https://ariyalur.nic.in/public-utility-category/police-stations/"
    recs, files, why = run({u: "psall_ariyalur.html.gz", u + "page/2/": "psall_ariyalur_p2.html.gz"}, u, "TN", "Ariyalur")
    assert why == "" and len(files) == 2
    s = stations(recs)
    assert len(recs) == 18 and len(s) == 18
    assert s["All Women Police Station, Jayankondam"]["phone"] == "9498100725"
    assert s["Police Station, T.Palur"]["phone"] == "9498100719"
    assert all(r["dept"] == "police" and r["state"] == "TN" and r["src_pos"] for r in s.values())


def test_poonch_phone_in_name():
    u = "https://poonch.nic.in/police/"
    recs, _, why = run({u: "psall_poonch.html.gz"}, u, "JK", "Poonch")
    s = stations(recs)
    assert why == "" and sorted(s) == ["Mendhar", "Poonch", "Surankote"]
    assert s["Mendhar"]["phone"] == "01965-226125"
    assert dict(recs)["dept:psall_s3waas:poonch:surankote"]["area"] == "Surankote"


def test_narayanpet_she_team_out():
    u = "https://narayanpet.telangana.gov.in/police/"
    recs, _, why = run({u: "psall_narayanpet.html.gz"}, u, "TG", "Narayanpet")
    s = stations(recs)
    assert why == "" and len(recs) == 19 and len(s) == 12
    assert not any("SHE" in a for a in s)
    assert s["SHO Narayanpet Rural PS"]["phone"] == "8712670417"
    lv = sorted(r["level"] for _, r in recs)
    assert lv.count("circle") == 4 and lv.count("subdivision") == 2 and lv.count("district") == 1


def test_sepahijala_table():
    u = "https://sepahijala.nic.in/police/"
    recs, _, why = run({u: "psall_sepahijala.html.gz"}, u, "TR", "Sepahijala")
    s = stations(recs)
    assert why == "" and len(s) == 10 and "Bishalgarh Women PS" in s


def test_seeds():
    items = [i for f in sorted((ROOT / "seeds").glob("dept_psall_*.json")) for i in json.loads(f.read_text())]
    assert len(items) == 32 and len({i["key"] for i in items}) == 32
    assert all(i["payload"]["reader"] == "psall_s3waas" and i["payload"]["state"] and i["payload"]["district"] for i in items)
