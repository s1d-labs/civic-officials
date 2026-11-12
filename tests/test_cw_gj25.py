"""Gujarat February 2025 results from the Gujarat Government Gazette (cforms/cw_gj.py, egazette.gujarat.gov.in).
Sample: cw_gj25_ex89_p12.pdf = pages 1-2 of Extra No. 89 (18 Feb 2025, Junagadh Municipal Corporation), saved 2026-11-12."""
import json
import pathlib

from cforms import cw_gj, gj

DATA = pathlib.Path(__file__).parent / "data"
SEEDS = pathlib.Path(__file__).parent.parent / "seeds"


def test_gj25_notice_reads_like_2026():
    recs = gj.parse(str(DATA / "cw_gj25_ex89_p12.pdf"), {"url": "x", "first": 1, "last": 2, "slug": "gj25-ex89"}, use_ocr=False)
    assert len(recs) == 16 and len({k for k, _ in recs}) == 16
    k, r = recs[0]
    assert k.startswith("councillor:GJ:gj25-ex89-") and k.endswith(":1-1")
    assert r["body"] == "જૂનાગઢ મહાનગરપાલિકા" and r["ward_no"] == "1" and r["party"] == "BJP"
    assert [d["ward_no"] for _, d in recs] == [str(w) for w in range(1, 5) for _ in range(4)]
    assert dict(recs)[k.replace(":1-1", ":4-2")]["party"] == "INC"


class _R:
    def __init__(self, content):
        self.content = content


def test_save_only_keeps_the_file_and_makes_no_records():
    pdf = (DATA / "cw_gj25_ex89_p12.pdf").read_bytes()
    p = {"kind": "form-cw_gj", "url": "https://egazette.gujarat.gov.in/ViewPdf2.aspx?docid=a.pdf", "save_only": True}
    recs, files, why = cw_gj.fetch(p, lambda url, **kw: _R(pdf))
    assert recs == [] and why == "" and len(files) == 1 and files[0][0].startswith("councillors/GJ/")
    assert cw_gj.fetch(p, lambda url, **kw: _R(b"<html>"))[2] == "not a pdf"


def test_gj25_seeds_pair_up():
    save = json.loads((SEEDS / "ocr_councillors_gj25_save.json").read_text())
    ocr = json.loads((SEEDS / "stored_councillors_gj25.json").read_text())
    assert len(save) == len(ocr) == 30
    import hashlib
    for s, o in zip(save, ocr):
        assert s["payload"]["url"] == o["payload"]["url"] and s["payload"]["save_only"] and "save_only" not in o["payload"]
        key = hashlib.sha1(o["payload"]["url"].encode()).hexdigest()[:12]
        assert o["payload"]["stored"] == f"civic-officials-councillors-ocr/councillors/GJ/{key}.pdf"
