"""East police readers (dforms/police3_*.py: Assam, Odisha, West Bengal ...) on saved samples (tests/data/police3_*): no network."""
import json
import shutil
import sys
from pathlib import Path

import pytest

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
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, method="GET", data=None, headers=None):
        self.calls.append((method, url, data))
        hit = self.routes.get(url)
        if hit is None:
            return None
        return Answer((DATA / hit).read_bytes(), url)


# ---------- Assam ----------
def test_as_items():
    from dforms import police3_as as a
    items = a.items(FakeGet({a.OFFICES: "police3_as/offices.html"}))
    forms = {i["payload"]["form"]: i["payload"]["url"] for i in items}
    assert forms["landline"].endswith("/all_districts-land-line_number.pdf")
    assert forms["directory"].endswith("/directory_ason-23102026.pdf")
    seed = json.loads((ROOT / "seeds" / "dept_police3_as.json").read_text())
    assert {s["key"] for s in seed} == {"police3_as:landline", "police3_as:directory"}


def test_as_landline():
    from dforms import police3_as as a
    text = (DATA / "police3_as" / "landline.txt").read_text()
    recs = dict(a.parse_landline(text, "https://police.assam.gov.in/x.pdf"))
    st = [d for d in recs.values() if d["level"] == "police_station"]
    assert len(st) >= 380
    assert len({d["district"] for d in st if d.get("district")}) >= 30
    d = recs["dept:police3_as:ll:nagaon:o-c-nagaon-p-s"]
    assert (d["area"], d["post"], d["phone"], d["district"], d["office_type"]) == ("Nagaon P.S", "O.C", "03672-235606", "Nagaon",
                                                                                    "police station")
    assert d["src_pos"]["page"] == 1 and "Nagaon P.S." in d["src_pos"]["line_text"]
    # a number printed above and below the row line (Morigaon S.P., three numbers)
    sp = recs["dept:police3_as:ll:morigaon:s-p-morigaon"]
    assert "03678-240238" in sp["phone"] and "03678-241162" in sp["phone"] and sp["district"] == "Marigaon"
    # Guwahati numbers get 0361
    assert recs["dept:police3_as:ll:commissioner-of-police-guwahati:chandmari-p-s"]["phone"] == "0361-2660204"
    assert recs["dept:police3_as:ll:commissioner-of-police-guwahati:chandmari-p-s"]["district"] == "Kamrup Metro"
    assert recs["dept:police3_as:ll:commissioner-of-police-guwahati:all-women-p-s"]["office_type"] == "women police station"
    assert recs["dept:police3_as:ll:nagaon:i-c-traffic"]["office_type"] == "traffic"
    assert recs["dept:police3_as:ll:nagaon:police-control-room-broad-band"]["office_type"] == "control room"
    assert recs["dept:police3_as:ll:morigaon:dharamtul-ps"].get("phone") is None
    assert recs["dept:police3_as:ll:morigaon:ci-laharighat"]["area"] == "Laharighat"


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext not installed")
def test_as_directory_fetch():
    from dforms import police3_as as a
    url = "https://police.assam.gov.in/sites/default/files/public_utility/directory_ason-23102026.pdf"
    recs, files, why = a.fetch({"reader": "police3_as", "form": "directory", "url": url}, FakeGet({url: "police3_as/directory.pdf"}))
    assert why == "" and files[0][0] == "depts/police/police3_as/directory.pdf.gz"
    sp = {d["district"]: d for _, d in recs if d["level"] == "district" and d.get("district")}
    assert len(sp) == 35
    b = sp["Bongaigaon"]
    assert b["name"] == "Shri Numal Mahatta, APS" and "6026900207" in b["phone"] and b["email"] == "sp-bongaigaon@assampolice.gov.in"
    n = sp["Nagaon"]
    assert n["post"] == "Senior Supdt. of Police, Nagaon" and "03672-235624" in n["phone"] and n["fax"] == "03672-237939"
    dgp = next(d for _, d in recs if d["post"] == "DGP, Assam")
    assert dgp["level"] == "state" and dgp["email"] == "dgp@assampolice.gov.in"
    assert all(d.get("src_pos", {}).get("page") for _, d in recs)


# ---------- Odisha ----------
def test_od_commissionerate():
    from dforms import police3_od as o
    recs, files, why = o.fetch({"reader": "police3_od", "url": o.URL}, FakeGet({o.URL: "police3_od/important-contact-number.html"}))
    recs = dict(recs)
    assert why == "" and len(recs) >= 80
    cp = recs["dept:police3_od:officer:1-commissioner-of-police-bhubaneswar-kataka-bhubanes"]
    assert cp["name"] == "Dr. Suresh Dev Datta Singh, IPS" and cp["district"] == "Khordha"
    assert cp["phone"] == "8280338300, 0674-2530035" and cp["fax"] == "0674-2530001" and cp["email"] == "commissioneratepolice@od.gov.in"
    assert recs["dept:police3_od:officer:5-deputy-commissioner-of-police-kataka"]["district"] == "Cuttack"
    z = recs["dept:police3_od:bhubaneswar:zone-i"]
    assert (z["level"], z["name"], z["phone"]) == ("circle", "Ramesh Chandra Bisoi", "8280338306")
    assert "Capital PS" in z["stations"]
    s = recs["dept:police3_od:bhubaneswar:zone-i:capital-ps"]
    assert s["level"] == "police_station" and s["circle"] == "Bhubaneswar UPD Zone I" and s["district"] == "Khordha"
    assert recs["dept:police3_od:kataka:zone-ii:mangalabag-ps"]["district"] == "Cuttack"


# ---------- West Bengal ----------
def test_wb_bidhannagar():
    from dforms import police3_wb as w
    recs, files, why = w.fetch({"reader": "police3_wb", "url": w.URL}, FakeGet({w.URL: "police3_wb/bidhannagar.html"}))
    recs = dict(recs)
    st = [d for d in recs.values() if d["level"] == "police_station"]
    assert len(st) == 15 and all(d.get("phone") for d in st)
    e = recs["dept:police3_wb:bidhannagar:bidhannagar-east-ps"]
    assert (e["phone"], e["email"], e["zone"], e["district"]) == ("9147889496, 9147889451", "psbdneast@policewb.gov.in",
                                                                   "Bidhannagar Zone", "North 24 Parganas")
    assert recs["dept:police3_wb:bidhannagar:cyber-crime-ps"]["office_type"] == "cyber police station"
    assert recs["dept:police3_wb:bidhannagar:women-ps"]["office_type"] == "women police station"
    assert recs["dept:police3_wb:bidhannagar:airport-traffic-guard"]["phone"] == "9147889435"
    assert recs["dept:police3_wb:bidhannagar:control-room-24x7"]["phone"] == "033-23358788, 033-23410465"
    assert "dept:police3_wb:bidhannagar:bidhannagar-traffic" not in recs
