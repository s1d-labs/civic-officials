"""dforms/vil_od_ganjam_gp.py: Ganjam (Odisha) PEO + Sarpanch + PS / ZP member per gram panchayat. Fixtures 2026-11-13:
Surada block PDF (Excel print) and the Buguda block detail page (HTML)."""
from collections import Counter
from pathlib import Path

from dforms import _field, vil_od_ganjam_gp as m

DATA = Path(__file__).parent / "data"
PDF_URL = "https://ganjam.odisha.gov.in/sites/default/files/2023-06/Surada%20block%20contact%20details.pdf"


def test_pdf_block():
    recs = dict(m.pdf_records(_field.pdf_text((DATA / "vil_od_ganjam_surada.pdf").read_bytes()), {"block": "Surada"}, PDF_URL))
    c = Counter(d["post"] for d in recs.values())
    assert c["Panchayat Executive Officer"] >= 25 and c["Sarpanch"] >= 25
    peo = recs["dept:vil_od_ganjam_gp:surada:p1-l6:peo"]
    assert (peo["name"], peo["phone"], peo["area"]) == ("Sibaram Nayak", "9668439474", "Amrutulu")
    assert peo["level"] == "gram_panchayat" and peo["kind"] == "official" and peo["src_pos"]["page"] == 1
    ps = recs["dept:vil_od_ganjam_gp:surada:p1-l8:ps"]
    assert (ps["name"], ps["phone"]) == ("Bajandri Nayak", "9078661393")
    zp = recs["dept:vil_od_ganjam_gp:surada:p1-l8:zp"]
    assert (zp["name"], zp["phone"], zp["kind"]) == ("Kasturi Sethi", "9583116313", "elected")


def test_html_block():
    recs = dict(m.html_records((DATA / "vil_od_ganjam_buguda.html").read_text(encoding="utf-8"), {"block": "Buguda"}, "u"))
    peo = recs["dept:vil_od_ganjam_gp:buguda:t2-r22:peo"]
    assert (peo["name"], peo["phone"], peo["area"]) == ("Aruna Kumar Bisoyi", "9937545388", "Turumu")
    assert peo["src_pos"] == {"table": 2, "row": 22}
    assert recs["dept:vil_od_ganjam_gp:buguda:t1-r1:zp"]["phone"] == "8342804373"
    assert sum(d["post"] == "Panchayat Executive Officer" for d in recs.values()) == 22


class R:
    def __init__(self, content, url):
        self.content, self.url = content, url
        self.text = content.decode("utf-8", "replace")


def test_fetch_pdf_item():
    out, files, why = m.fetch({"url": PDF_URL, "block": "Surada"}, lambda u, **k: R((DATA / "vil_od_ganjam_surada.pdf").read_bytes(), u))
    assert why == "" and out and files[0][0].endswith(".pdf") and out[0][1]["src_sha256"]
