"""Electricity-office readers of the third round (dforms/power3_<discom>.py) on the FULL saved pages and PDFs in
tests/data/power3: no network. Exact record and row counts."""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "tests" / "data" / "power3"

import provenance  # noqa: E402


class Resp:
    def __init__(self, content, url=""):
        self.content, self.status_code, self.url = content, 200, url
        self.text = content.decode("utf-8", "replace")


def fake_get(routes):
    def get(url, method="GET", data=None, headers=None):
        for sub, f in routes:
            if sub in url:
                return Resp((DATA / f).read_bytes(), url)
        return None
    return get


def check(recs, module):
    ids = [i for i, _ in recs]
    assert len(ids) == len(set(ids)), "record ids must be unique"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:")
        assert d["type"] == "dept_office" and d["dept"] == "electricity"
        assert d["level"] in ("state", "zone", "circle", "division", "subdivision", "section")
        assert d.get("area")
    return Counter(d["level"] for _, d in recs)


def run(module, payload, routes):
    import importlib
    provenance.rows_reset()
    recs, files, why = importlib.import_module("dforms." + module).fetch(payload, fake_get(routes))
    return recs, files, why, provenance.rows(len(recs))


# ---- UPCL (Uttarakhand)

def test_upcl_se():
    recs, files, why, rows = run("power3_upcl", {"part": "se"}, [("contact-list-of-se-and-above", "upcl_se.html")])
    assert why == "" and files[0][0] == "depts/power/power3_upcl/contact-list-of-se-and-above.html.gz"
    assert check(recs, "power3_upcl") == {"state": 23, "circle": 14, "zone": 4}
    assert rows == {"rows_seen": 48, "rows_used": 41, "rows_skipped": {}, "rows_not_data": {"header": 7}}
    d = dict(recs)["dept:power3_upcl:se-superintending-engineer-edc-haldwani"]
    assert d["level"] == "circle" and d["area"] == "EDC Haldwani" and d["name"] == "Ravi Rajora"
    assert d["phone"] == "05946-298343" and d["email"] == "edc.haldwani@upcl.org" and d["parents"] == {"zone": "Kumaon Zone"}
    z = dict(recs)["dept:power3_upcl:se-chief-engineer-distribution-kumaon-zone"]
    assert z["level"] == "zone" and z["email"] == "ce.kumaon_zone@upcl.org, upcl_gmdh@yahoo.co.in"


def test_upcl_zone_layout_a():
    recs, files, why, rows = run("power3_upcl", {"part": "zone", "zone": "Haridwar"}, [("202507041315929139", "upcl_haridwar.pdf")])
    assert why == "" and files[0][0] == "depts/power/power3_upcl/distribution-offices-Haridwar.pdf"
    assert check(recs, "power3_upcl") == {"section": 43, "subdivision": 19, "division": 5}
    assert rows == {"rows_seen": 270, "rows_used": 263, "rows_skipped": {"feeder row without a JE phone": 3},
                    "rows_not_data": {"header": 4}}
    d = dict(recs)
    assert d["dept:power3_upcl:haridwar-div-haridwar-urban"]["phone"] == "9412073700"
    sd = d["dept:power3_upcl:haridwar-sd-haridwar-rural-bhadrabad"]
    assert sd["level"] == "subdivision" and sd["phone"] == "9411111253" and sd["parents"]["division"] == "HARIDWAR RURAL"
    je = d["dept:power3_upcl:haridwar-je-haridwar-rural-bhadrabad-9412073711"]
    assert je["level"] == "section" and je["area"] == "Bhadrabad" and je["substations"] == [{"name": "Bhadrabad", "phone": "7535026995"}]
    assert je["parents"] == {"zone": "Haridwar Zone", "division": "HARIDWAR RURAL", "subdivision": "BHADRABAD"}
    assert "Town Bahadrabad" in je["feeders"]


def test_upcl_zone_layout_a_kumaon():
    recs, files, why, rows = run("power3_upcl", {"part": "zone", "zone": "Kumaon"}, [("202507041607222727", "upcl_kumaon.pdf")])
    assert check(recs, "power3_upcl") == {"section": 66, "subdivision": 27, "division": 10}
    assert rows == {"rows_seen": 338, "rows_used": 333, "rows_skipped": {}, "rows_not_data": {"header": 5}}
    d = dict(recs)
    assert d["dept:power3_upcl:kumaon-div-almora"]["phone"] == "9412093006"
    assert d["dept:power3_upcl:kumaon-sd-almora-almora-2"]["phone"] == "9412093007, 9412093010"


def test_upcl_zone_layout_b():
    recs, files, why, rows = run("power3_upcl", {"part": "zone", "zone": "Garhwal"}, [("20250704215953182", "upcl_garhwal.pdf")])
    assert check(recs, "power3_upcl") == {"section": 192, "subdivision": 65, "division": 17}
    assert rows == {"rows_seen": 730, "rows_used": 679, "rows_skipped": {"feeder row without a JE phone": 31},
                    "rows_not_data": {"header": 20}}
    d = dict(recs)
    # "<EE phone><division>" read as one piece, and "<division> <EE phone>": both split
    assert d["dept:power3_upcl:garhwal-div-mohanpur"]["phone"] == "7900992777"
    assert d["dept:power3_upcl:garhwal-div-doiwala"]["phone"] == "9412056121"
    sd = d["dept:power3_upcl:garhwal-sd-dehradun-central-sdo-9412075907"]
    assert sd["area"] == "SDO: BINDAL, GOVIND GARH, GHANTA GHAR" and sd["phone"] == "9412075907"
    je = d["dept:power3_upcl:garhwal-je-dehradun-central-sdo-9412075907-9412075914"]
    assert je["area"] == "BINDAL" and je["substations"] == [{"name": "BINDAL", "phone": "01352716105"}]


# ---- MSEDCL (Maharashtra) telephone diary

def test_msedcl_diary():
    recs, files, why, rows = run("power3_msedcl", {}, [("Mahavitaran_Index_Diary", "msedcl_diary.pdf")])
    assert why == "" and files[0][0] == "depts/power/power3_msedcl/Mahavitaran_Index_Diary.pdf"
    assert check(recs, "power3_msedcl") == {"section": 5229, "subdivision": 2956, "division": 969, "circle": 218, "zone": 113,
                                            "state": 56}
    assert rows == {"rows_seen": 18143, "rows_used": 13365,
                    "rows_skipped": {"head office pages": 1753, "not a field office": 225, "heading printed twice": 7,
                                     "pages after the field offices": 2327},
                    "rows_not_data": {"header": 354, "empty": 112}}
    d = dict(recs)
    offices = Counter(r["level"] for r in d.values() if r["level"] != "section" and not r.get("post") and not r.get("name"))
    assert offices == {"subdivision": 659, "division": 152, "circle": 44, "zone": 16, "state": 4}
    z = d["dept:power3_msedcl:zone-latur-zone"]
    assert z["phone"] == "7875762021" and z["email"] == "celatur@mahadiscom.in, celatur@gmail.com"
    ce = d["dept:power3_msedcl:zone-latur-zone-chief-engineer-arvind-bulbule"]
    assert ce["post"] == "Chief Engineer" and ce["phone"] == "7875762111 (M)"
    # the designation in regular type under a name
    assert d["dept:power3_msedcl:zone-latur-zone-admn-safety-rajabhau-wadane"]["post"] == "(Admn. & Safety)"
    sd = d["dept:power3_msedcl:subdivision-jalna-o-m-dn-1-badnapur-sub-dn"]
    assert sd["phone"] == "261212" and sd["address"] == "STD: 02482"
    sec = d["dept:power3_msedcl:section-badnapur-sub-dn-badnapur-rural-unit-no-1"]
    assert sec["area"] == "Badnapur Rural Unit No.1" and sec["phone"] == "7875764202"
    assert sec["parents"] == {"region": "CHHATRAPATI SAMBHAJINAGAR REGION", "zone": "CHHATRAPATI SAMBHAJINAGAR ZONE",
                              "circle": "JALNA O&M CIRCLE", "division": "Jalna O&M Dn.1", "subdivision": "Badnapur Sub Dn"}
    ae = d["dept:power3_msedcl:subdivision-ambajogai-o-m-dn-kaij-sub-dn-a-e-recovery"]
    assert ae["post"] == "A.E.Recovery" and ae["phone"] == "7875273378" and ae["parents"]["circle"] == "BEED O&M CIRCLE"
    # the invisible OCR layer is not read ("AE (Recovery-Il)")
    assert not any("Recovery-Il" in (r.get("post") or "") for r in d.values())
