"""BLO readers forms/blo2_dd.py (DNH and Daman and Diu), forms/blo2_mh.py (Raigad, Satara), forms/blo2_pb.py (Ludhiana).
Offline: small samples in tests/data/blo2/west_* only.
- west_dd_*.pdf: a few bands of the CEO's ruled tables, rebuilt with the same text, positions and rules (Helvetica, so the
  file stays small); they test the rule-based table reader (forms/blo2_in.ruled_tables).
- west_*_lines.json: [page, line] pairs as pypdf layout mode gives them for the district PDFs (a few rows each)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = Path(__file__).parent / "data" / "blo2"

import blo  # noqa: E402
from forms import blo2_dd, blo2_in, blo2_mh, blo2_pb  # noqa: E402


def lines(name):
    return [tuple(x) for x in json.loads((DATA / name).read_text())]


def pdf(name):
    return (DATA / name).read_bytes()


# ---- shared helpers ----

def test_helpers():
    assert blo2_in.mobiles("Mo.8530558419") == ["8530558419"]
    assert blo2_in.mobiles("9904144419/ 9979614810") == ["9904144419", "9979614810"]
    assert blo2_in.part_of("94.") == "94" and blo2_in.part_of("Dadra-1") is None
    assert blo2_in.split_name("Ranjik K. Patel, Asst. Teacher, GHS") == ("Ranjik K. Patel", "Asst. Teacher, GHS")
    assert blo2_in.cells("   1        Kulwant Kaur      9056868740") == ["1", "Kulwant Kaur", "9056868740"]


# ---- Dadra and Nagar Haveli and Daman and Diu ----

def test_dd_diu_two_lists_one_record_per_ps():
    t = blo2_in.ruled_tables(pdf("west_dd_diu_p1.pdf")) + [(3, r) for _, r in blo2_in.ruled_tables(pdf("west_dd_diu_p3.pdf"))]
    p = blo2_dd.items()[2]["payload"]
    rows = blo2_dd.rows_from_tables(t, p)
    assert [r["part_no"] for r in rows] == ["94", "95", "96"]
    r = rows[0]
    assert r["blo_name"] == "HEMLATA P. SIKOTARIYA" and r["blo_phone"] == "8530558419"
    assert r["designation"] == "GPS/GMS, BUCHARWADA"
    assert r["station"].startswith("GOVT. PRIMARY SCHOOL NO.2 BLDG.")
    assert r["cells"]["sr_no"] == "1" and r["cells"]["resident_address"] == "Kala Sheri Vanakbara"
    recs = blo.form_rows(p, rows)
    assert recs[0][0] == "blo:DD:2:94" and recs[0][1]["district"] == "Diu"


def test_dd_daman_wrapped_cells_and_merged_ps_cell():
    p = blo2_dd.items()[1]["payload"]
    rows = blo2_dd.rows_from_tables(blo2_in.ruled_tables(pdf("west_dd_daman_p1.pdf")), p)
    assert [int(r["part_no"]) for r in rows] == list(range(1, 14))
    assert rows[0]["station"] == "Govt. Primary School (New Building), Taiwad, Devka"
    assert rows[0]["blo_name"] == "Smt. Patel Dharmishaben Arvindbhai" and rows[0]["blo_phone"] == "8000451068"
    assert rows[0]["cells"]["address"] == "Kadaiya Near Devka Taiwad Orma Faliya Nani Daman"
    # PS 13: the PS no and the station share one cell
    assert rows[12]["station"] == "Panchayat Ghar, Marwad" and rows[12]["blo_name"] == "Shri. Jagdish Madhav Patel"
    assert all(r["blo_name"] and len(r["blo_phone"]) == 10 for r in rows)


def test_dd_fetch_through_blo_dispatch(monkeypatch):
    class S:
        headers = {}

        def get(self, url, timeout=None):
            class R:
                status_code, content, headers = 200, pdf("west_dd_daman_p1.pdf"), {}

                def raise_for_status(self):
                    pass
            assert url == "https://ceodaman.nic.in/Document-2023/DMNBLO.pdf"
            return R()
    monkeypatch.setattr(blo.aspnet, "session", lambda *a, **k: S())
    item = [i for i in blo2_dd.items() if i["key"] == "blo2-dd-daman"][0]
    recs, files, why = blo.run_form(item)
    assert why == "" and files == [] and len(recs) == 13
    rid, d = recs[0]
    assert rid == "blo:DD:2:1" and d["type"] == "blo" and d["state"] == "DD" and d["ac_name"] == "Daman and Diu"


# ---- Maharashtra ----

def test_mh_raigad_blo_and_supervisor():
    p = [i for i in blo2_mh.items() if i["key"] == "blo2-mh-raigad-191"][0]["payload"]
    rows = blo2_mh.parse_raigad(lines("west_raigad_lines.json"), p)
    by = {r["part_no"]: r for r in rows}
    assert set(by) == {"1", "2", "3", "213", "244", "289"}      # header and wrapped phone lines are skipped
    r = by["1"]
    assert (r["blo_name"], r["designation"], r["blo_phone"]) == ("Kashinath Narayan Thakur", "Grampanchayat Clerk", "9403319702")
    assert r["cells"]["Office Name"] == "Grampanchayat Dushmi"
    assert r["cells"]["Name of BLO Supervisor"] == "Prasad Mhatre" and r["cells"]["Supervisor Mobile Number"] == "8805173661"
    # office spilled over two cells ("Panchayat Samiti", "Sudhagad")
    assert by["213"]["cells"]["Office Name"] == "Panchayat Samiti Sudhagad" and by["213"]["blo_phone"] == "9595704257"
    # no designation printed: the one cell is the office
    assert by["244"]["designation"] == "" and by["244"]["cells"]["Office Name"] == "PMC PANVEL"
    recs = blo.form_rows(p, rows)
    assert recs[0][0] == "blo:MH:191:1" and recs[0][1]["ac_name"] == "Pen"


def test_mh_satara_all_acs_one_file():
    p = [i for i in blo2_mh.items() if i["key"] == "blo2-mh-satara"][0]["payload"]
    rows = blo2_mh.parse_satara(lines("west_satara_lines.json"), p)
    assert [(r["ac_no"], r["part_no"]) for r in rows] == [(255, "1"), (255, "2"), (255, "3")]
    r = rows[2]
    assert (r["ac_name"], r["station"], r["blo_name"], r["blo_phone"]) == ("PHALTAN (SC)", "PADEGAON FARM", "ROHINI DATTATREYA ADASUL", "7350114290")
    assert blo.form_rows(p, rows)[0][0] == "blo:MH:255:1"


# ---- Punjab ----

def test_pb_ludhiana(monkeypatch):
    item = [i for i in blo2_pb.items() if i["key"] == "blo2-pb-ludhiana-58"][0]
    monkeypatch.setattr(blo2_pb, "download", lambda s, url: b"%PDF-")
    monkeypatch.setattr(blo2_pb, "layout_lines", lambda content: lines("west_ludhiana_ac58_lines.json"))
    recs, files, why = blo.run_form(item)
    assert why == "" and len(recs) == 6
    rid, d = recs[1]
    assert rid == "blo:PB:58:2" and (d["ac_name"], d["blo_name"], d["blo_phone"]) == ("Samrala", "SANDEEP KUMAR", "7973966036")
    assert d["cells"]["source_note"] == "Know your BLO Ludhiana, 20-08-2026"


# ---- seeds ----

def test_seeds_match_items():
    for st, mod, n in [("dd", blo2_dd, 3), ("mh", blo2_mh, 8), ("pb", blo2_pb, 13)]:
        seed = json.loads((ROOT / "seeds" / f"blo2_{st}.json").read_text())
        assert seed == mod.items() and len(seed) == n
        assert len({i["key"] for i in seed}) == n
        for i in seed:
            assert i["key"].startswith("blo2-") and i["payload"]["kind"] == f"form-blo2_{st}"
            assert i["payload"]["state"] == st.upper() and i["payload"]["url"].startswith("https://")
