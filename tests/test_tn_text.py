"""Tamil Nadu 2022 urban results from the text layer (cforms/tn_text.py, cforms/cn_mpdf_ta.py), on saved pdftotext -layout output
of two tnsec.tn.gov.in files: tp_ari.pdf (Ariyalur town panchayats, whole file) and corp_cbe.pdf (Coimbatore, pages 1-3)."""
import gzip
from pathlib import Path

from cforms.cn_mpdf_ta import convert, is_mpdf_ta
from cforms.tn_text import parse_text, records

DATA = Path(__file__).parent / "data"


def raw(name):
    return gzip.decompress((DATA / name).read_bytes()).decode("utf-8")


def test_convert_glyphs_and_order():
    # visual order ெ + வ, ி as a PUA glyph after ற: "வெற்றி"; தி.மு.க with the PUA glyphs for ி and மு
    assert convert("ெவற்ற") == "வெற்றி"
    assert convert("த..க") == "தி.மு.க"
    assert convert("ேகாயம்த்ர்") == "கோயம்புத்தூர்"
    assert convert("ெகௗர") == "கௌரி"
    assert convert("Makkal Needhi 12.5") == "Makkal Needhi 12.5"
    assert is_mpdf_ta("ெவற்ற") and not is_mpdf_ta("வெற்றி")


def test_ariyalur_town_panchayats():
    wards = parse_text(raw("tn_text_tp_ari.txt.gz"))
    assert len(wards) == 30
    assert all(len(w["winners"]) == 1 for w in wards)
    # every ward's candidate votes add up to its valid votes
    assert all(sum(c["votes"] for c in w["candidates"]) == w["valid"] for w in wards[:-1])     # the last ward goes on to page 4
    p = {"type": "tp", "district_code": "ari", "district": "அரியலூர்", "url": "https://x/tp_ari.pdf"}
    recs = dict(records(wards, p))
    r = recs["councillor:TN:tx:tp-ari:உடையார்பாளையம்:1"]
    assert (r["name"], r["father_or_husband"], r["party"], r["votes"], r["reservation"]) == \
        ("இராதிகா.இரா", "இராயர்", "DMK", 343, "பொது (பெண்கள்)")
    assert r["electors"] == 639 and len(r["candidates"]) == 3
    # a party name that wraps above and below an empty row cell
    r = recs["councillor:TN:tx:tp-ari:உடையார்பாளையம்:4"]
    assert (r["name"], r["party_local"], r["party"]) == ("கீதா.கொ", "சுயேட்சை வேட்பாளர்", "Independent")
    # elected unopposed
    r = recs["councillor:TN:tx:tp-ari:உடையார்பாளையம்:13"]
    assert r["unopposed"] and r["name"] == "மலர்விழி.ர"
    # a tie decided by lot: "வெற்றி (குலுக்கல் முறை)" over three lines
    r = recs["councillor:TN:tx:tp-ari:வரதராஜன்-பேட்டை:5"]
    assert r["name"] == "ஜோசப்.அ" and "குலுக்கல்" in r["result"]


def test_coimbatore_wrapped_cells():
    wards = parse_text(raw("tn_text_corp_cbe_p1-3.txt.gz"))
    assert [w["ward_no"] for w in wards][:3] == ["1", "2", "3"]
    w1 = wards[0]
    assert w1["body"] == "கோயம்புத்தூர்" and w1["body_type"] == "மாநகராட்சி"
    assert [c["name"] for c in w1["winners"]] == ["கற்பகம்.இரா"]
    by = {c["serial"]: c for c in w1["candidates"]}
    assert by["3"]["party_local"] == "Makkal Needhi Maiam"
    assert by["6"]["father_or_husband"] == "கே. கவிசந்திர மோகன்"
    assert by["1"]["result"] == "வைப்புத் தொகை இழப்பு"
    assert all(sum(c["votes"] for c in w["candidates"]) == w["valid"] for w in wards[:-1])     # the last ward goes on to page 4
