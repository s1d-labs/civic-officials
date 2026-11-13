"""dforms/vil_up_asha.py: UP NHM district ASHA database. Fixtures: the layout text of the WHOLE Hapur file (Compiled_Hapur.pdf,
9 pages, 832,209 bytes, sha256 e774007eedc6..., fetched 2026-11-14 from Mumbai) by both engines the runners may use."""
import gzip
import json
from collections import Counter
from pathlib import Path

import provenance
from dforms import _field, vil_up_asha as m

DATA = Path(__file__).parent / "data"
ROOT = Path(__file__).parent.parent
URL = "https://nhm.up.gov.in/assets/site-files/asha/Compiled_Hapur.pdf"
P = {"district": "Hapur", "lgd_district_code": "661"}


def text(engine):
    return gzip.decompress((DATA / f"vil_up_asha_hapur_{engine}.txt.gz").read_bytes()).decode()


def test_hapur_whole_file_pdftotext():
    recs, stats = m.parse(text("pdftotext"), URL, P)
    r = dict(recs)
    assert len(recs) == len(r) == 737 and stats == {"rows": 737, "continued": 2, "no_name": 0}
    assert Counter(d["block"] for d in r.values()) == {"Hapur": 237, "Dhaulana": 168, "Simbhaoli": 166, "Garh Mukteshwar": 166}
    a = r["dept:vil_up_asha:hapur:3403001"]
    assert (a["name"], a["husband_name"], a["village"], a["population_covered"]) == ("Alka khan", "Sonkhan", "Domi", 1346)
    assert (a["sub_centre"], a["facility"], a["block"], a["district"], a["lgd_district_code"]) == \
        ("Domi", "CHC Hapur", "Hapur", "Hapur", "661")
    assert a["dept"] == "health" and a["level"] == "village" and a["layer"] == "village_worker" and a["post"] == "ASHA"
    assert a["src_pos"]["page"] == 1 and "3403001" in a["src_pos"]["line_text"] and a["serial"] == 1
    # row 478: its last cells go on at the top of the next page
    b = r["dept:vil_up_asha:hapur:3401075"]
    assert (b["name"], b["village"], b["population_covered"]) == ("Pushpa", "Kheda", 1147) and b["src_pos"]["continued_on"]
    # no husband name, no population: the village stays in its column
    c = r["dept:vil_up_asha:hapur:3401168"]
    assert c["name"] == "Imrana" and c["village"] == "Dhera" and "husband_name" not in c
    assert sum(1 for d in r.values() if "population_covered" not in d) == 73
    assert all(d.get("village") and d.get("block") and d.get("sub_centre") for d in r.values())
    assert sorted(d["serial"] for d in r.values()) == list(range(1, 738))


def test_hapur_whole_file_pypdf_same_rows():
    a = dict(m.parse(text("pdftotext"), URL, P)[0])
    b = dict(m.parse(text("pypdf"), URL, P)[0])
    assert set(a) == set(b)
    same = sum(1 for k in a if (a[k]["name"], a[k].get("village"), a[k]["block"]) == (b[k]["name"], b[k].get("village"), b[k]["block"]))
    assert same == 737


def test_row_counts_in_trail():
    provenance._rows.c = None
    m.parse(text("pdftotext"), URL, P)
    c = provenance._counts()
    assert c["used"] == 737 and not c["skipped"].get("no serial number and no ASHA ID")


def test_split():
    s = m.split(" 36          Hapur             Hapur       CHC Hapur        Badnoli               3403036            Bimlesh"
                "         Vijendra          Badnoli")
    assert s[0] == "36" and [t for _, t in s[1]] == ["Hapur", "Hapur", "CHC Hapur", "Badnoli"] and s[2] == "3403036"
    assert [t for _, t in s[3]] == ["Bimlesh", "Vijendra", "Badnoli"]
    assert m.split(" 1             2                 3             4") is None


class R:
    def __init__(self, content):
        self.content = content
        self.url = URL


def test_fetch(monkeypatch):
    monkeypatch.setattr(_field, "pdf_text_engine", lambda b: (text("pdftotext"), "pdftotext -layout"))
    recs, files, why = m.fetch(dict(P, url=URL), lambda u, **kw: R(b"%PDF-1.4 fake"))
    assert why == "" and len(recs) == 737 and files[0][0] == "depts/vil_up_asha/hapur.pdf"
    assert all(d["src_url"] == URL and d["src_sha256"] and d["method"].startswith("pdf text (pdftotext") for _, d in recs)
    assert m.fetch(dict(P, url=URL), lambda u, **kw: None)[2] == "no answer"
    assert m.fetch(dict(P, url=URL), lambda u, **kw: R(b"<html>"))[2] == "the district file is not a PDF"


def test_seeds():
    items = json.loads((ROOT / "seeds" / "dept_vil_up_asha.json").read_text())
    assert len(items) == 75 and len({i["key"] for i in items}) == 75
    assert len({i["payload"]["lgd_district_code"] for i in items}) == 75
    for i in items:
        p = i["payload"]
        assert p["reader"] == "vil_up_asha" and p["url"].startswith("https://nhm.up.gov.in/assets/site-files/asha/")
        assert p["route"] == "abroad" and p["india_only"] is False and p["state"] == "UP" and p["district"]
    assert m.items() == items
