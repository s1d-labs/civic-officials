"""last-gaps round (2026-11-15): cforms/cw_mp.py preamble slip "राज्य गें", the (body, district) aliases of Agar-Malwa, and
cforms/scan_prep.py (deskew, contrast) on a synthetic page."""
import pytest

from cforms import cw_mp


def test_preamble_ge_for_me():
    b = cw_mp.body_from("यह अधिसूचित किया जाता है कि राज्य गें नगर परिषद्‌ नयागांव\nजिला नीमच के गाह जुलाई 2022. में कराये गये")
    assert b["body_local"] == "नयागांव" and b["district_local"] == "नीमच" and b["year"] == "2022"


def _rec(body_local, district_local):
    body = {"body_local": body_local, "district_local": district_local, "body_type": "Nagar Parishad", "month": "जुलाई",
            "year": "2022"}
    m = {"name": "कमल सिंह राजपूत", "position": "Councillor", "ward_no": "5", "party": "BJP", "party_local": ""}
    return cw_mp.record({"url": "https://govtpress.mp.gov.in/x.pdf", "gazette_no": "432", "gazette_date": "01-08-2022"}, body, m, 17)[1]


def test_agar_malwa_district_aliases():
    assert _rec("बड़ौद", "आगरमालवा")["lgd_code"] == "250857"                     # Badod, not Bairad (Shivpuri)
    assert _rec("नगर-परिषद बड़ागांव", "आगरमालवा")["lgd_code"] == "250733"        # Badagaaon, not Dongar Parasia
    assert _rec("बड़ागांव", "टीकमगढ़")["lgd_code"] != "250733"                    # Badagaon of Tikamgarh is another body


def test_scan_prep_deskew_and_contrast(tmp_path):
    PIL = pytest.importorskip("PIL")
    from PIL import Image, ImageDraw
    from cforms import scan_prep
    img = Image.new("L", (1200, 1600), 255)
    d = ImageDraw.Draw(img)
    for y in range(200, 1400, 60):                       # ruled rows of a table
        d.line([(100, y), (1100, y)], fill=60, width=3)
    tilted = img.rotate(-1.5, resample=Image.BICUBIC, fillcolor=255)
    a = scan_prep.skew_angle(tilted)
    assert abs(a - 1.5) <= 0.15
    faint = tilted.point([min(255, 150 + v // 3) for v in range(256)])
    pdf = tmp_path / "p.pdf"
    faint.save(pdf, "PDF", resolution=150)
    out, angle = scan_prep.prep_page(str(pdf), 1, str(tmp_path), {"deskew": True, "contrast": 2.0, "dpi": 150})
    assert out and abs(angle - 1.5) <= 0.15
