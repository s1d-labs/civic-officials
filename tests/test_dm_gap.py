"""seeds/directories_missing2.json (district portals of districts with no official, 2026-11-13): file = builder output, unique
keys, every item a District administration item with an LGD district code and a route; dm-abroad lists the abroad items."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _builder():
    spec = importlib.util.spec_from_file_location("build_dm_gap", ROOT / "seeds" / "build_dm_gap.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_dm2_seed_file_is_builder_output():
    items = json.loads((ROOT / "seeds" / "directories_missing2.json").read_text())
    assert items == _builder().items()
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) == 47 and all(k.startswith("dm2:") for k in keys)
    for i in items:
        p = i["payload"]
        assert p["kind"] == "District administration" and p["district_code"].isdigit() and p["route"] in ("abroad", "direct")
        assert p["url"].startswith("https://") and (p.get("read_start") == "1") == ("/" in i["key"][4:])
    assert len({i["payload"]["district_code"] for i in items}) == 17


def test_dm2_in_dm_abroad_project():
    import family
    pr = {p["name"]: p for p in family.PROJECTS}
    ab = {i["key"] for i in pr["civic-officials-dm-abroad"]["items"]}
    assert "dm2:ahmedabad.nic.in" in ab and "dm2:balod.gov.in/en/directory" in ab
    assert not any(k.startswith("dm2:aurangabad.bih.nic.in") for p in pr.values() for k in (i["key"] for i in p["items"]))
