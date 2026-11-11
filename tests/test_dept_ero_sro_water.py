"""Seed files of every dept reader: valid, unique keys, known readers. The readers' own tests are test_dept_esw_g*.py."""
from esw_common import *  # noqa: F401,F403
from esw_common import ROOT, json  # noqa: F401


def test_seed_files():
    """Every seeds/dept_<module>.json of this group: unique stable keys, a reader that exists, a url and a state."""
    every = []
    for f in sorted((ROOT / "seeds").glob("dept_*.json")):
        m = f.stem[len("dept_"):]
        if not m.startswith(("ero_", "sro_", "water_")):
            continue
        items = json.loads(f.read_text())
        keys = [i["key"] for i in items]
        every += keys
        assert items and len(keys) == len(set(keys)), f
        assert all(k.startswith(m) and len(k) <= 200 for k in keys), f
        for i in items:
            p = i["payload"]
            assert p.get("reader") == m and p.get("url") and p.get("state"), (f, i)
            assert hasattr(mod(m), "fetch")
    assert len(every) == len(set(every))
