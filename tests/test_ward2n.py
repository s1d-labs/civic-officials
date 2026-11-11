"""Offline tests of the ward / zone office readers of North and West India corporations (dforms/ward2n_<city>.py) and their seeds
(seeds/dept_ward2n_<city>.json). Same case format as test_ward_cities.py, with the files in tests/data/ward2n/:
  {"module": "ward2n_<city>", "payload": {...queue item payload...},
   "routes": {"<url>" or "POST <url>": "<saved file in tests/data/ward2n/>"},  # answers for fake_get (other urls answer None)
   or "pages": "<file>.pages"              # a PDF reader: its parse(pages, payload) on the page texts (a JSON list)
   "min_records": n, "min_wards": n,
   "expect": [{"post": "<regex>", "name": "<regex>", "wards": ["31", ...], "level": "ward"}]}
The saved files are small cuts of the archive.s1d.me copies (or one live answer).
"""
import json
import re

import pytest
from esw_common import ROOT, DATA, fake_get, mod

WARD = DATA / "ward2n"
CASES = sorted(WARD.glob("*.json"))
LEVELS = {"zone", "ward", "body", "division", "circle"}


def routes_of(case):
    out = {}
    for k, v in case.get("routes", {}).items():
        out[("POST", k[5:]) if k.startswith("POST ") else k] = f"ward2n/{v}"
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
        if d["level"] == "ward":    # a ward office lists its wards, or says why it cannot (wards_note)
            assert d.get("wards") or d.get("wards_note"), d


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_reader(path):
    case = json.loads(path.read_text())
    m = mod(case["module"])
    if case.get("pages"):
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


SEEDS = sorted((ROOT / "seeds").glob("dept_ward2n_*.json"))


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
    m_ = mod(m)
    assert hasattr(m_, "fetch")
    if hasattr(m_, "items"):
        assert [i["key"] for i in m_.items()] == keys, "seed file and items() differ"


def test_every_reader_has_a_case_and_a_seed():
    readers = {p.stem for p in (ROOT / "dforms").glob("ward2n_*.py")}
    cased = {json.loads(p.read_text())["module"] for p in CASES}
    seeded = {p.stem[len("dept_"):] for p in SEEDS}
    assert readers <= cased, readers - cased
    assert readers <= seeded, readers - seeded


def test_seeds_unique_across_files():
    keys = [i["key"] for p in sorted((ROOT / "seeds").glob("dept_ward*.json")) for i in json.loads(p.read_text())]
    assert len(keys) == len(set(keys))
