"""Offline tests of the West Bengal CEO officials reader (dforms/sub3_wb.py) on saved PDFs in tests/data/sub3_wb/ (fetched
2026-11-12 from ceowestbengal.wb.gov.in): Hooghly and Purulia district lists (Google Sheets), Kolkata North (Not Applicable
rows, AC in the designation, AEO section), the ERO list of 04.02.2026 (Excel) and the CEO office list. Needs poppler (pdftotext)."""
import json
import shutil

import pytest

from esw_common import *  # noqa: F401,F403

pytestmark = pytest.mark.skipif(not shutil.which("pdftotext"), reason="poppler (pdftotext) not installed")
D = DATA / "sub3_wb"


def _recs(name, **p):
    m = mod("sub3_wb")
    return {k: d for k, d in m.parse((D / name).read_bytes(), p)}


def test_sub3_wb_seeds():
    m = mod("sub3_wb")
    seeds = json.loads((ROOT / "seeds" / "dept_sub3_wb.json").read_text())
    assert seeds == m.items() and len(seeds) == 28 and len({s["key"] for s in seeds}) == 28
    assert all(s["payload"]["india_only"] and s["payload"]["route"] == "direct" for s in seeds)
    assert "Officials/NORTH%2024%20PARGANAS.pdf" in seeds[16]["payload"]["url"]


def test_sub3_wb_hooghly():
    r = _recs("hooghly.pdf", file="hooghly", district="Hooghly")
    posts = [d["post"] for d in r.values()]
    assert len(r) == 44 and posts.count("Block Development Officer") == 18 and posts.count("Returning Officer") == 18
    a = r["dept:sub3_wb:hooghly:adm:additional-district-magistrate-gen-hooghly"]
    assert (a["name"], a["service"], a["mobile"], a["email"]) == ("Tarun Bhattacharyya", "WBCS (Exe.)", "9231847777", "admghoog@gmail.com")
    b = r["dept:sub3_wb:hooghly:bdo:balagarh"]
    assert (b["name"], b["area"], b["level"], b["dept"]) == ("MAHASWETA BISWAS NAYEK", "Balagarh", "block", "rural_development")
    assert r["dept:sub3_wb:hooghly:bdo:goghat-ii"]["area"] == "Goghat- II"
    s = r["dept:sub3_wb:hooghly:sdo:chandernagar"]
    assert s["phone"] == "9433901415, 033-2683-5324" and s["name"] == "Ashutosh Kumar"
    ro = r["dept:sub3_wb:hooghly:ro:197"]
    assert (ro["name"], ro["ac_name"], ro["designation"]) == ("Mouli Sanyal", "Dhanekhali (SC)", "DYO, Hooghly")
    ro = r["dept:sub3_wb:hooghly:ro:196"]
    assert ro["service"] == "WBCS (Exe)" and ro["designation"] == "Secretary, ZP, Hooghly"
    assert r["dept:sub3_wb:hooghly:ro:200"]["ac_name"] == "Arambag (SC)"


def test_sub3_wb_purulia_bdo_short_form():
    r = _recs("purulia.pdf", file="purulia", district="Purulia")
    para = [d for d in r.values() if d.get("designation") == "BDO, Para"][0]
    assert para["area"] == "Para" and para["mobile"] == "8373068647" and para["phone"] == "8373068647, 03251-266234"


def test_sub3_wb_kolkata_not_applicable():
    r = _recs("kolkata_north.pdf", file="kolkata-north", district="Kolkata North")
    assert not any("Not Applicable" in json.dumps(d) for d in r.values())
    ro = r["dept:sub3_wb:kolkata-north:ro:162"]
    assert (ro["ac_name"], ro["name"], ro["service"], ro["email"]) == ("Chowrangee", "Mufti Samim Saukat", "W.B. C.S. (Exe.)",
                                                                       "ero162c@gmail.com")
    assert sum(d["post"] == "Assistant Election Officer" for d in r.values()) == 5


def test_sub3_wb_ero_list():
    r = _recs("ro_2024.pdf", file="ero2024")
    assert len(r) == 294 and {d["ac_no"] for d in r.values()} == {str(i) for i in range(1, 295)}
    e = r["dept:sub3_wb:ero2024:ero:4"]
    assert (e["name"], e["ac_name"], e["district"], e["mobile"], e["email"], e["last_updated"]) == (
        "Gobinda Nandi", "Cooch Behar Dakshin", "Coochbehar", "7601912737", "sdo.sadar.cbrelection@gmail.com", "04.02.2026")
    assert e["address"].startswith("Office of the Sub-Divisional officer, Sadar Sub Division")


def test_sub3_wb_ceo_office():
    r = _recs("ceo_office.pdf", file="ceo")
    assert len(r) == 11
    c = [d for d in r.values() if d["designation"] == "Chief Electoral Officer"][0]
    assert (c["name"], c["level"], c["phone"], c["fax"]) == ("Smt. Neelam Meena", "state", "033-2231-0880", "033-2231-0840")
