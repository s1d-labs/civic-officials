"""BLO readers for the east and north (forms/blo2_pdf.py: district BLO PDFs of UP, Bihar, West Bengal; forms/blo2_od.py:
Odisha polling stations with lat/lon) on saved samples in tests/data/blo2/: no network."""
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forms import blo2_od, blo2_pdf  # noqa: E402

DATA = Path(__file__).parent / "data" / "blo2"


def pages(name):
    return (DATA / name).read_text(encoding="utf-8").split("\f")


def test_up_gorakhpur_columns_and_glued_numbers():
    p = {"state": "UP", "ac_no": 328, "ac_name": "Chillupar", "district": "Gorakhpur", "list_date": "2026-10"}
    rows = blo2_pdf.rows_from_pages(pages("up_gorakhpur_328.txt"), p)
    assert len(rows) == 10
    r = rows[0]
    assert (r["ac_no"], r["part_no"], r["blo_name"], r["blo_phone"]) == (328, 1, "Somai Prasad", "8601480995")
    assert r["station"] == "PRIMARY SCHOOL CHADI PURAV" and r["designation"] == "Contract Teacher"
    assert r["cells"]["Officer Type"] == "BLO" and r["cells"]["_list_date"] == "2026-10"
    # "KAUSHLEN DRA BAHADUR RAITeacher": name and designation glued in the PDF; the part number still comes out
    assert rows[1]["part_no"] == 2 and rows[1]["blo_phone"] == "9794370471"
    assert all(isinstance(r["part_no"], int) and len(r["blo_phone"]) == 10 for r in rows)
    assert [r["part_no"] for r in rows[-4:]] == [37, 38, 39, 40]   # page 2


def test_br_muzaffarpur_wrapped_cells():
    rows = blo2_pdf.rows_from_pages(pages("br_muzaffarpur_98.txt"), {"state": "BR", "ac_no": 98, "district": "Muzaffarpur"})
    assert len(rows) >= 5
    r = rows[0]
    assert (r["part_no"], r["blo_name"], r["blo_phone"], r["ac_name"]) == (1, "JAHIDA KHATOON", "9031289931", "Sahebganj")
    assert r["designation"] == "Anganwadi worker"            # "Anganwadi" sits on the line above
    assert r["station"] == "Madhya Vidyalay, Ahiyapur Dakshini Bhag"
    assert rows[1]["blo_name"] == "Rajesh Mishra" and rows[1]["designation"] == "Teacher"


def test_wb_dakshin_dinajpur_ac_from_column_and_page_without_header():
    rows = blo2_pdf.rows_from_pages(pages("wb_ddinajpur.txt"), {"state": "WB", "district": "Dakshin Dinajpur"})
    assert len(rows) == 10
    r = rows[0]
    assert (r["ac_no"], r["ac_name"], r["part_no"]) == (37, "Kushmandi (SC)", 1)
    assert (r["station"], r["blo_name"], r["blo_phone"], r["designation"]) == (
        "Minapara F.P. School-Room No-1", "Matibur Rahaman", "9593205036", "AT")
    assert [x["part_no"] for x in rows[5:]] == [141, 142, 143, 144, 145]   # second page: header of page 1 still applies
    assert rows[8]["blo_name"] == "Subhash Sarkar"


def test_pdf_fetch_refuses_scanned_and_reads_text():
    from pypdf import PdfWriter
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(buf)

    class R:
        content = buf.getvalue()

        def raise_for_status(self):
            pass

    class S:
        def get(self, url, timeout=None):
            return R()

    try:
        blo2_pdf.fetch(S(), {"url": "https://cdn.s3waas.gov.in/x.pdf", "state": "MN"})
        raise AssertionError("expected 'scanned'")
    except RuntimeError as e:
        assert "scanned" in str(e)


def test_od_wfs_points():
    doc = json.loads((DATA / "od_wfs_ac1.json").read_text(encoding="utf-8"))
    rows = blo2_od.rows_from_geojson(doc, {"ac_no": 1})
    assert len(rows) == 3
    r = next(x for x in rows if x["part_no"] == 36)
    assert (r["ac_no"], r["ac_name"], r["district"]) == (1, "Padampur", "Bargarh")
    assert r["station"] == "Badkunjari PUPS" and r["blo_name"] == ""
    assert (r["cells"]["lat"], r["cells"]["lon"]) == (21.12181, 82.92167)
    assert r["cells"]["part_number_old"] == 34 and r["cells"]["pin_code"] == "768036"


def test_blo_py_record_ids():
    import blo
    doc = json.loads((DATA / "od_wfs_ac1.json").read_text(encoding="utf-8"))
    p = {"kind": "form-blo2_od", "state": "OD", "ac_no": 1, "url": blo2_od.WFS}
    recs = dict(blo.form_rows(p, blo2_od.rows_from_geojson(doc, p)))
    assert "blo:OD:1:36" in recs and recs["blo:OD:1:36"]["cells"]["lat"] == 21.12181
    p = {"kind": "form-blo2_pdf", "state": "UP", "ac_no": 328, "url": "u"}
    recs = dict(blo.form_rows(p, blo2_pdf.rows_from_pages(pages("up_gorakhpur_328.txt"), p)))
    assert recs["blo:UP:328:1"]["blo_name"] == "Somai Prasad" and recs["blo:UP:328:1"]["blo_phone"] == "8601480995"


def test_seeds():
    seen = set()
    for st, n in (("od", 147), ("up", 80), ("br", 33), ("mn", 13), ("wb", 1)):
        items = json.loads((ROOT / "seeds" / f"blo2_{st}.json").read_text(encoding="utf-8"))
        assert len(items) == n
        for i in items:
            assert i["key"].startswith("blo2-") and len(i["key"]) <= 200 and i["key"] not in seen
            seen.add(i["key"])
            pl = i["payload"]
            assert pl["state"] == st.upper() and pl["url"].startswith("https://")
            assert pl["kind"] in ("form-blo2_pdf", "form-blo2_od", "pdf")
        acs = [i["payload"]["ac_no"] for i in items if "ac_no" in i["payload"]]
        assert len(acs) == len(set(acs))       # one file per AC, so record ids never collide
