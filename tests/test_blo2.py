"""BLO readers for the states that had no list (blo2, 2026-11-11). Offline: small saved samples in tests/data/blo2/."""
import json
from pathlib import Path

import blo
from forms import blo2_mz

HERE = Path(__file__).parent
DATA = HERE / "data" / "blo2"


def read(name):
    return (DATA / name).read_text(encoding="utf-8")


def test_mizoram_cards():
    h = read("mz_p87.html")
    rows = blo2_mz.parse(h)
    assert len(rows) == 3                     # the DEO card on the other tab is skipped
    r = rows[0]
    assert (r["ac_no"], r["district"], r["part_no"], r["blo_name"], r["designation"]) == \
        (10, "Aizawl", "CHALTLANG LILY VENG - I", "Zosangzuali", "Teacher")
    assert rows[2]["ac_no"] == 3 and rows[2]["ac_name"] == "Mamit (ST)"
    assert blo2_mz.last_page(h) == 86
    rid, rec = blo.form_rows({"state": "MZ", "url": "u"}, rows)[0]
    assert rid == "blo:MZ:10:CHALTLANG LILY VENG - I" and rec["type"] == "blo" and rec["station"] == "CHALTLANG LILY VENG - I"


def test_mizoram_ac_names():
    assert blo2_mz.ACS[blo2_mz.ac_key("Aizawl West III (ST)")] == 17
    assert blo2_mz.ACS[blo2_mz.ac_key("Siaha (ST)")] == 39
    assert len(set(blo2_mz.ACS.values())) == 40


def test_seed_keys():
    for f in sorted((HERE.parent / "seeds").glob("blo2_*.json")):
        items = json.loads(f.read_text())
        assert items, f
        keys = [i["key"] for i in items]
        assert all(k.startswith("blo2-") for k in keys), f
        assert len(keys) == len(set(keys)), f
        for i in items:
            p = i["payload"]
            assert p.get("state") and p.get("kind"), (f, i)


def test_haryana_nuh_links():
    from forms import blo2_hr
    rows = blo2_hr.parse(read("hr_nuh.html"), "Nuh")
    assert len(rows) == 9                     # 3 ACs x 3 rows; the repeated Punhana table adds nothing
    r = rows[0]
    assert (r["ac_no"], r["part_no"], r["blo_name"], r["blo_phone"], r["station"]) == (79, "1", "PANKAJ KUMAR", "9812327160", "GGMS Atta (RW)")
    assert r["cells"]["lat"].startswith("28.2192") and r["cells"]["lon"].startswith("77.0827")
    assert {x["ac_no"] for x in rows} == {79, 80, 81}
    assert blo.form_rows({"state": "HR", "url": "u"}, rows)[0][0] == "blo:HR:79:1"
