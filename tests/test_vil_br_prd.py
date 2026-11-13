"""dforms/vil_br_prd.py: Bihar gram panchayat staff (Panchayat Secretary, Executive Assistant, Technical Assistant,
Accountant-cum-IT Assistant). Fixture: 6 pages (1, 6, 57, 83, 131, 213) of the 257-page PDF of 2026-11-13 and the directory page."""
from pathlib import Path

from dforms import _field, vil_br_prd as m

DATA = Path(__file__).parent / "data"
URL = "https://betastate.bihar.gov.in/file_2/FileUpload/2024/May/07-May-2024/44/DyPage/787de287-61a0-482f-9f19-5404b680f4bc.pdf"


def recs():
    out, stats = m.parse(_field.pdf_text((DATA / "vil_br_prd.pdf").read_bytes()), URL)
    return dict(out), stats


def test_first_row_four_posts():
    r, stats = recs()
    ps = r["dept:vil_br_prd:p1-l4:ps"]
    assert ps["name"] == "SHRI DINESH KUMAR SINGH" and ps["phone"] == "7764053979"
    assert ps["area"] == "ARARIA BASTI" and ps["block"] == "Araria" and ps["district"] == "Araria"
    assert ps["lgd_gp_code"] == "93638" and ps["level"] == "gram_panchayat" and ps["dept"] == "rural_development"
    assert ps["bpro_phone"] == "8051997373"
    assert ps["src_pos"]["page"] == 1 and "ARARIA BASTI" in ps["src_pos"]["line_text"]
    assert r["dept:vil_br_prd:p1-l4:ea"]["name"] == "RAUSHAN KUMAR SAH"
    assert r["dept:vil_br_prd:p1-l4:ta"]["phone"] == "9891472569"
    assert r["dept:vil_br_prd:p1-l4:acc"]["name"] == "Surbhi Singh"
    assert stats["rows"] > 150 and stats["rows_lgd"] > 100


def test_sheet_without_block_column_takes_heading_block():
    r, _ = recs()
    rows = [d for d in r.values() if d["post"] == "Panchayat Secretary" and d.get("area") == "SAKRI"]
    assert rows and rows[0]["district"] == "Arwal" and rows[0]["lgd_gp_code"] == "238476"


def test_cells_and_phones():
    row = m.split_row("ARAILA                  SANJAY KUMAR                     9570556609 MD. SARFARAJ          9262368625 "
                      "RAUSHAN KUMAR SINGH     6200710279 SANTOSH KUMAR YADAV          7370880121")
    assert row["gp"] == "ARAILA" and row["posts"]["ps"] == {"name": "SANJAY KUMAR", "phone": "9570556609"}
    assert row["posts"]["acc"]["name"] == "SANTOSH KUMAR YADAV"
    assert m.split_row("9128618202          7779997362") is None


def test_heading():
    assert m.heading("District…Araria     Block…Bhargama      BPRO Name & Mobile No .. Ajay Kumar Jha & 8051997373") == \
        ("Araria", "Bhargama", "8051997373")
    assert m.heading("ARWAL                  KURTHA            BPRO          CHANDESHWAR NARAYAN SINGH, 9199806401")[1] == "KURTHA"


class R:
    def __init__(self, content):
        self.content = content
        self.text = content.decode("utf-8", "replace")
        self.url = ""


def test_fetch_follows_the_directory_row():
    seen = []

    def get(url, **kw):
        seen.append(url)
        return R((DATA / ("vil_br_prd.pdf" if url.endswith(".pdf") else "vil_br_prd_page.html")).read_bytes())

    out, files, why = m.fetch({"reader": "vil_br_prd", "url": m.PAGE}, get)
    assert why == "" and len(out) > 600 and seen[1] == URL
    assert any(f[0].endswith(".pdf") for f in files)
    assert out[0][1]["src_url"] == URL and out[0][1]["src_sha256"]
