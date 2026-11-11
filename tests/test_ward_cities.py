"""Offline tests of the city ward / zone office readers (dforms/ward_<city>.py) and their seeds (seeds/dept_ward_<city>.json).

Each case is tests/data/ward/<case>.json:
  {"module": "ward_<city>", "payload": {...queue item payload...},
   "routes": {"<url>" or "POST <url>": "<saved file in tests/data/ward/>"},  # answers for fake_get (other urls answer None)
   or "pages": "<file>.pages"              # a PDF reader: its parse(pages, payload) on the page texts (a JSON list)
   "min_records": n,                       # at least n records from this answer
   "min_wards": n,                         # (optional) at least n distinct ward numbers across the records
   "expect": [{"post": "<regex>", "name": "<regex>", "wards": ["31", ...], "level": "ward"}]}  # (optional) rows that must exist
A reader with items() also gets its seed checked. The saved files are small cuts of the archive.s1d.me copies (or one live answer).
"""
import json
import re

import pytest
from esw_common import ROOT, DATA, fake_get, mod

WARD = DATA / "ward"
CASES = sorted(WARD.glob("*.json"))
LEVELS = {"zone", "ward", "body", "division", "circle"}


def routes_of(case):
    out = {}
    for k, v in case.get("routes", {}).items():
        out[("POST", k[5:]) if k.startswith("POST ") else k] = f"ward/{v}"
    return out


def check(recs, module):
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:"), rid
        assert d["type"] == "dept_office" and d["dept"] == "town_body", d
        assert d.get("level") in LEVELS and d.get("source") and d.get("state") and d.get("body") and d.get("local_body_code"), d
        assert d.get("post") and d.get("area"), d
        assert d.get("name") or d.get("name_regional") or d.get("phone") or d.get("email") or d.get("address") or d.get("vacant"), d
        assert all(isinstance(w, str) and re.fullmatch(r"\d{1,3}[A-Z]?(-[A-Z0-9]+)?", w) for w in d.get("wards") or []), d
        if d["level"] == "ward":
            assert d.get("wards"), d


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_reader(path):
    case = json.loads(path.read_text())
    m = mod(case["module"])
    if case.get("pages"):
        # a PDF reader tested on the page texts of its file (pypdf layout mode, saved as JSON: the PDF itself is too big to keep)
        recs, why = m.parse(json.loads((WARD / case["pages"]).read_text()), case["payload"]), ""
    else:
        recs, files, why = m.fetch(case["payload"], fake_get(routes_of(case)))
    assert len(recs) >= case.get("min_records", 1), (why, len(recs))
    check(recs, case["module"])
    wards = {w for _, d in recs for w in d.get("wards") or []}
    assert len(wards) >= case.get("min_wards", 0), sorted(wards)
    for e in case.get("expect", []):
        hit = [d for _, d in recs
               if re.search(e.get("post", ""), d.get("post", ""), re.I) and re.search(e.get("name", ""), d.get("name", ""), re.I)
               and (not e.get("level") or d["level"] == e["level"]) and set(e.get("wards", [])) <= set(d.get("wards") or [])]
        assert hit, e


SEEDS = sorted((ROOT / "seeds").glob("dept_ward_*.json"))


@pytest.mark.parametrize("path", SEEDS, ids=[p.stem for p in SEEDS])
def test_seed(path):
    m = path.stem[len("dept_"):]
    items = json.loads(path.read_text())
    keys = [i["key"] for i in items]
    assert items and len(keys) == len(set(keys)), path
    for i in items:
        p = i["payload"]
        assert i["key"].startswith(m) and len(i["key"]) <= 200, i
        assert p.get("reader") == m and p.get("url") and p.get("state"), i
    assert hasattr(mod(m), "fetch")


def test_every_reader_has_a_case_and_a_seed():
    readers = {p.stem for p in (ROOT / "dforms").glob("ward_*.py")}
    cased = {json.loads(p.read_text())["module"] for p in CASES}
    seeded = {p.stem[len("dept_"):] for p in SEEDS}
    assert readers <= cased, readers - cased
    assert readers <= seeded, readers - seeded


def test_seeds_unique_across_files():
    keys = [i["key"] for p in SEEDS for i in json.loads(p.read_text())]
    assert len(keys) == len(set(keys))


def test_wards_of():
    from dforms._ward import wards_of, wing_of, role_of
    assert wards_of("31, 32, 46") == ["31", "32", "46"]
    assert wards_of("Ward No. 1 to 5 & 7") == ["1", "2", "3", "4", "5", "7"]
    assert wards_of("12A, 13") == ["12A", "13"]
    assert wards_of("Wards 101-103") == ["101", "102", "103"]
    assert wing_of("Assistant Engineer") == "engineering" and wing_of("Sanitary Inspector") == "sanitation"
    assert wing_of("Water Supply AE") == "water" and wing_of("Bill Collector") == "revenue"
    assert wing_of("Assistant Town Planning Officer") == "planning" and wing_of("Assistant Commissioner") == "administration"
    assert role_of("Zonal Officer") == "head" and role_of("Junior Engineer") == "staff"


def test_kanpur_zone_wards():
    """Kanpur's zone-to-ward list (zonewardlist.pdf, saved here as its pdftotext -layout text): 6 zones, 109 of the 110 wards
    (ward 49 is missing in the file itself: a stray "," stands in its cell in ZONE-4)."""
    zw = mod("ward_kanpur").zone_wards((WARD / "kanpur_zonewardlist.txt").read_text())
    assert {z: len(w) for z, w in zw.items()} == {1: 18, 2: 21, 3: 18, 4: 14, 5: 18, 6: 20}
    assert "1" in zw[1] and "11" in zw[2] and "110" in zw[4] and "8" in zw[6]


def test_kamrc_phone_out_of_name():
    # Ballari writes "MAHINDRA, 8073055190" and "RAMANJI/TIRUPAL, 9980634475/7348898878" in one cell: the numbers leave the name
    case = json.loads((WARD / "kamrc_ballari_eng.json").read_text())
    recs = dict(mod("ward_kamrc").fetch(case["payload"], fake_get(routes_of(case)))[0])
    assert not [d["name"] for d in recs.values() if re.search(r"\d", d["name"])]
    by = {(d["post"], d["name"]): d for d in recs.values()}
    assert by[("Supervisor", "MAHINDRA")]["phone"] == "8073055190"
    assert by[("Valve man", "RAMANJI")]["phone"] == "9980634475" and by[("Valve man", "TIRUPAL")]["phone"] == "7348898878"
    # "DASHARATH ,DEVENDRA, 9980722483": two names, one number: the number is the group's
    assert by[("Valve man", "DASHARATH")].get("phone") in (None, "") and by[("Valve man", "DASHARATH")]["group_phones"] == "9980722483"
    people = mod("ward_kamrc").people
    assert people("KUBENDRA RAVI PRASAD, 7411129910 9686401467") == [("KUBENDRA RAVI PRASAD", "7411129910, 9686401467", None, None)]


def test_kamrc_names_on_lines_and_label():
    # Davanagere: "Veeresh | Nagaraj | ..." are several valve men; "From Jalsiri distribution channel" is a note, not a name
    case = json.loads((WARD / "kamrc_davanagere_eng.json").read_text())
    recs = dict(mod("ward_kamrc").fetch(case["payload"], fake_get(routes_of(case)))[0])
    assert not [d["name"] for d in recs.values() if "|" in d["name"] or "Jalsiri" in d["name"]]
    n = next(d for d in recs.values() if d["name"] == "Nagendrappa")
    assert n["note"] == "From Jalsiri distribution channel"


def test_trichy_zone_officers_only_on_their_zone():
    # every zonaladmins/N page shows the zone I (Srirangam) officers: zone 3 keeps none of them, zone 1 keeps all
    case = json.loads((WARD / "trichy_zone3.json").read_text())
    recs = dict(mod("ward_trichy").fetch(case["payload"], fake_get(routes_of(case)))[0])
    assert recs and all(d["level"] == "ward" and d["zone"] == "Zone 3" for d in recs.values())
    assert not [d for d in recs.values() if "Srirangam" in (d.get("address") or "") + d["area"] + d.get("zone", "")]
    one = dict(mod("ward_trichy").fetch(*(lambda c: (c["payload"], fake_get(routes_of(c))))(json.loads((WARD / "trichy_zone1.json").read_text())))[0])
    ac = [d for d in one.values() if d["post"] == "Asst. Commissioner"]
    assert len(ac) == 1 and ac[0]["name"] == "Tmt. T. Sasikala M.B.A., M.Phil."      # trailing "," dropped
