"""National point readers (dforms/points_*.py, dforms/_points.py) on saved slices of the real files: tests/data/points/<file>_rg0_head400
.parquet = the first 400 rows of row group 0 of each ramSeraph/indian_facilities release asset (read 2026-11-14 with HTTP range
requests, schema and GeoParquet metadata kept; the whole files are 7-92 MB and are read by the hub items, not here). Seeds:
seeds/dept_points_<kind>_all.json, checked against the row counts of the files' footers on 2026-11-14.
"""
import io
import json
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import provenance
from dforms import _points, points_aadhaar_gm, points_atm_dfs, points_awc_gs, points_bank_dfs, points_csc_meity, points_fps_dofd, \
    points_school_bm

DATA = Path(__file__).parent / "data" / "points"
SEEDS = Path(__file__).parent.parent / "seeds"
FILES = {points_school_bm: "Bharatmaps_Schooldata", points_awc_gs: "GatiShakti_ICDS_Anganvadis", points_fps_dofd: "Bharatmaps_DoFD_PDS_2023",
         points_csc_meity: "Bharatmaps_MeitY_CSCs_2022", points_bank_dfs: "Bharatmaps_DFS_Bank_Branches_2022",
         points_atm_dfs: "Bharatmaps_DFS_Bank_ATMs_2022", points_aadhaar_gm: "Bharatmaps_Grammanchitra_Aadhar_Centers"}
# module -> (records of the 400 rows, {state: n}, first record id, record ids of rows 101 and 250)
WANT = {
    points_school_bm: (400, {"KA": 373, "LD": 27}, "dept:points_school_bm:31010100202", "29160400903", "29160503014"),
    points_awc_gs: (400, {"KA": 388, "LD": 12}, "dept:points_awc_gs:31587010108", "29569031107", "29569010704"),
    points_fps_dofd: (400, {"KA": 397, "LD": 3}, "dept:points_fps_dofd:LD-158700900003", "KA-1802414", "KA-1822821"),
    points_csc_meity: (400, {"KA": 400}, "dept:points_csc_meity:336112250011", "342165250018", "617376230012"),
    points_bank_dfs: (400, {"KA": 392, "LD": 8}, "dept:points_bank_dfs:SYNB0009954", "SYNB0000174", "CSBK0000549"),
    points_atm_dfs: (400, {"KA": 392, "LD": 7, "KL": 1}, "dept:points_atm_dfs:SBIN-S1BB005080002", "CORP-CBMN073201", "BKID-CML9001"),
    points_aadhaar_gm: (400, {"KA": 391, "LD": 8, "KL": 1}, "dept:points_aadhaar_gm:6", "9306", "13599"),
}
FOOTER_ROWS = {"school": 1466160, "awc": 1224038, "fps": 423738, "csc": 401268, "bank": 168955, "atm": 196360, "aadhaar": 79023}


class Resp:
    def __init__(self, content):
        self.content = content


def run(mod, content, **p):
    provenance.rows_reset()
    pay = {"url": "https://github.com/ramSeraph/indian_facilities/releases/download/x/y.parquet", "rg": 0, "lo": 0, "hi": 400,
           "n_file": 400, **p}
    recs, files, why = mod.fetch(pay, lambda url: Resp(content))
    return recs, why, provenance.rows(len(recs))


@pytest.mark.parametrize("mod", list(FILES), ids=lambda m: m.MODULE)
def test_full_slice(mod):
    n, states, first, _, _ = WANT[mod]
    recs, why, rows = run(mod, (DATA / f"{FILES[mod]}_rg0_head400.parquet").read_bytes())
    assert why == "" and len(recs) == n and len({r for r, _ in recs}) == n
    assert dict(Counter(d.get("state") for _, d in recs)) == states
    assert recs[0][0] == first
    assert rows["rows_seen"] == 400 and rows["rows_used"] == n and not rows["rows_skipped"]
    for rid, d in recs:
        assert d["type"] == "dept_office" and d["level"] == "facility" and d["dept"] and d["area"]
        assert 6 <= d["lat"] <= 37.6 and 68 <= d["lon"] <= 97.5 and not d.get("no_location")
        assert d["src_pos"]["rg"] == 0 and 1 <= d["src_pos"]["row"] <= 400 and d["src_url"].endswith(".parquet")
    assert [d["src_pos"]["row"] for _, d in recs] == sorted(d["src_pos"]["row"] for _, d in recs)


@pytest.mark.parametrize("mod", list(FILES), ids=lambda m: m.MODULE)
def test_part_of_row_group(mod):
    _, _, _, a, b = WANT[mod]
    recs, why, _ = run(mod, (DATA / f"{FILES[mod]}_rg0_head400.parquet").read_bytes(), lo=100, hi=250)
    assert len(recs) == 150 and recs[0][0].endswith(":" + a) and recs[-1][0].endswith(":" + b)
    assert recs[0][1]["src_pos"] == {"row": 101, "rg": 0} and recs[-1][1]["src_pos"] == {"row": 250, "rg": 0}


def test_fields():
    content = (DATA / "Bharatmaps_DFS_Bank_Branches_2022_rg0_head400.parquet").read_bytes()
    d = run(points_bank_dfs, content)[0][0][1]
    assert (d["area"], d["post"], d["name"], d["ifsc"], d["pin"], d["state"]) == \
        ("Canara Bank, AGATHY", "Branch Manager", "S MOHAMMED", "SYNB0009954", "673553", "LD")
    assert (d["lat"], d["lon"]) == (10.868011, 72.194842)
    d = run(points_csc_meity, (DATA / "Bharatmaps_MeitY_CSCs_2022_rg0_head400.parquet").read_bytes())[0][0][1]
    assert (d["area"], d["name"], d["pin"], d["lgd_code"]) == ("CSC Hubbangeri", "Naveen Naik", "581351", "603433")
    d = run(points_fps_dofd, (DATA / "Bharatmaps_DoFD_PDS_2023_rg0_head400.parquet").read_bytes())[0][0][1]
    assert (d["fps_id"], d["gp"], d["lgd_code"], d["block_lgd"]) == ("158700900003", "KILTAN", "627033", "5947")
    assert (d["lat"], d["lon"]) == (11.4769, 73.0093)      # the bbox point; the file's latitude / longitude columns are not degrees
    d = run(points_awc_gs, (DATA / "GatiShakti_ICDS_Anganvadis_rg0_head400.parquet").read_bytes())[0][0][1]
    assert (d["office_id"], d["area"], d["icds_project"]) == ("31587010108", "Anganwadi C.NO.8", "WCD-Agatti")
    d = run(points_school_bm, (DATA / "Bharatmaps_Schooldata_rg0_head400.parquet").read_bytes())[0][0][1]
    assert (d["udise"], d["area"], d["mgmt"], d["category"]) == ("31010100202", "GJBS SOUTH AGATTI", "Department of Education", "Primary")


def test_atm_bank_from_code():
    recs = run(points_atm_dfs, (DATA / "Bharatmaps_DFS_Bank_ATMs_2022_rg0_head400.parquet").read_bytes())[0]
    c = Counter(d["bank"] for _, d in recs)
    assert c["Canara Bank"] == 58 and c["Corporation Bank"] == 44       # 111 rows give only the bank code (CNRB 55, CORP 21 ...)


def test_point_outside_india_kept_without_location():
    t = pq.read_table(DATA / "Bharatmaps_DFS_Bank_Branches_2022_rg0_head400.parquet")
    bb = t.column("bbox").to_pylist()
    bb[0] = {"xmin": 67.74, "ymin": 5.32, "xmax": 67.74, "ymax": 5.32}
    t = t.set_column(t.schema.get_field_index("bbox"), "bbox", pa.array(bb, type=t.schema.field("bbox").type))
    buf = io.BytesIO()
    pq.write_table(t, buf)
    recs, why, _ = run(points_bank_dfs, buf.getvalue())
    assert len(recs) == 400 and recs[0][1]["no_location"] is True and "lat" not in recs[0][1]
    assert sum(1 for _, d in recs if d.get("no_location")) == 1


def test_changed_or_wrong_file():
    content = (DATA / "Bharatmaps_DoFD_PDS_2023_rg0_head400.parquet").read_bytes()
    assert run(points_fps_dofd, content, n_file=423738)[:2] == ([], "file changed: 400 rows, seeded 423738")
    assert run(points_fps_dofd, b"<html>not found</html>")[:2] == ([], "not a Parquet file")
    assert run(points_fps_dofd, content, lo=300, hi=500)[1] == "rows 300-500 are not in row group 0 (0-400)"


def test_val_and_state():
    assert [_points.val(x) for x in (" ", "NA", "\\N", "0", 627033.0, "31587010108.0", " Agatti ")] == \
        [None, None, None, None, "627033", "31587010108", "Agatti"]
    assert _points.state_of(None, "9") == "UP" and _points.state_of("", "Tamil Nadu") == "TN" and _points.state_of("99") == ""


@pytest.mark.parametrize("kind", list(FOOTER_ROWS))
def test_seeds_cover_each_file_once(kind):
    items = json.loads((SEEDS / f"dept_points_{kind}_all.json").read_text())
    assert len({i["key"] for i in items}) == len(items)
    lo = 0
    for i in items:
        p = i["payload"]
        assert p["lo"] == lo and p["hi"] - p["lo"] == p["expected"] <= 50_000 and p["n_file"] == FOOTER_ROWS[kind]
        assert p["open"] is True and not p["india_only"] and p["url"].startswith("https://github.com/ramSeraph/indian_facilities/")
        lo = p["hi"]
    assert lo == FOOTER_ROWS[kind]


def test_atm_owning_branch():
    """The owning branch from the ATM id (SBI, Canara, Syndicate), on the 400 rows: 129 ids give one (SBI 67, Canara 38 + old
    Syndicate 24); the other banks' ids give none. Owner and operator cells without a value (NA, Not Applicable, &nbsp;) are left out."""
    recs = run(points_atm_dfs, (DATA / "Bharatmaps_DFS_Bank_ATMs_2022_rg0_head400.parquet").read_bytes())[0]
    by = {r.split(":")[-1]: d for r, d in recs}
    assert Counter(d["branch_ifsc"][:4] for d in by.values() if d.get("branch_ifsc")) == {"SBIN": 67, "CNRB": 62}
    assert by["SBIN-S1BB005080002"]["branch_ifsc"] == "SBIN0005080"
    assert by["SYNB-A9950002"]["branch_ifsc"] == "CNRB0019950" and by["SYNB-A0199001"]["branch_ifsc"] == "CNRB0010199"
    assert by["CNRB-13336148"]["branch_ifsc"] == "CNRB0001333"
    assert "branch_ifsc" not in by["UCBA-DA224001"] and "branch_ifsc" not in by["KARB-KBL11026"]
    assert Counter(d["branch_ifsc"] for d in by.values() if d.get("branch_ifsc")).most_common(1) == [("SBIN0000871", 51)]
    assert sum(1 for d in by.values() if d.get("atm_owner")) == 256 and sum(1 for d in by.values() if d.get("atm_operator")) == 72
    assert by["UTIB-SWCW07733"]["atm_owner"] == "BROWN LABEL" and by["UTIB-SWCW07733"]["atm_operator"] == "AGS"
    assert points_atm_dfs.branch_ifsc("SBMY", "S1OG400739001") == "SBIN0400739" and points_atm_dfs.branch_ifsc("SBIN", "FBBX000871122") is None
    assert points_atm_dfs.branch_ifsc("SBIN", "S10K000871100") == "SBIN0000871" and points_atm_dfs.branch_ifsc("IOBA", "IOB9330") is None
