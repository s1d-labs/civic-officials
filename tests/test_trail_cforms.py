"""Source trail of the councillor readers in cforms/ (provenance.py): METHOD, src_pos and src on saved fixtures."""
import gzip
import hashlib
import json
from pathlib import Path

import provenance
from cforms import cn_hr, cw_mp, dl, gj, hr, mh, tn, tn_text, upch

DATA = Path(__file__).parent / "data"


def test_methods_name_the_engine():
    assert "Tamil font map" in tn_text.METHOD and "pdftotext" in tn_text.METHOD
    assert tn.METHOD.startswith("ocr tesseract tam")
    assert "ocr tesseract hin" in cw_mp.METHOD and "ocr tesseract hin" in upch.METHOD and "eng" in cn_hr.METHOD
    assert "guj" in gj.METHOD and "mar" in mh.METHOD


def test_tn_text_winner_line_and_bucket_copy():
    raw = gzip.decompress((DATA / "tn_text_tp_ari.txt.gz").read_bytes()).decode("utf-8")
    p = {"url": "https://tnsec.tn.gov.in/x.pdf", "type": "tp", "district_code": "1",
         "_src": provenance.file_src(b"%PDF-1", "https://tnsec.tn.gov.in/x.pdf", "proj/councillors/TN/abc.pdf")}
    recs = tn_text.records(tn_text.parse_text(raw), p)
    pages = raw.split("\f")
    for _, d in recs:
        sp = d["src_pos"]
        assert sp["page"] == d["page"] or sp["page"] >= d["page"]
        assert pages[sp["page"] - 1].splitlines()[sp["line"] - 1] == sp["line_text"]
        assert sp["line_text"].strip().startswith(sp["serial"])
        assert d["src"] == {"sha256": hashlib.sha256(b"%PDF-1").hexdigest(), "url": p["url"], "file": "proj/councillors/TN/abc.pdf"}


def test_hr_text_rows_and_grid_rows():
    text = ("   Sr. District  Name of Council   W. No  Name of Elected   Father's Name   Name of Office  Category  Political Party\n"
            "   1   Hisar     Hansi             3      Suman Bala        Ram Lal         Member          BCA       BJP\n")
    rows = hr.body_fill(hr.text_rows(text), {})
    assert rows[0]["_pos"] == {"line": 2, "line_text": text.splitlines()[1]}
    rid, d = hr.record({"url": "https://x/1.pdf"}, {}, rows[0], 4, "text layer")
    assert d["src_pos"]["page"] == 4 and d["src_pos"]["line"] == 2 and d["method"] == "pdf text (pdftotext -layout)"
    assert "_pos" not in d
    assert hr.row_pos({"row": 3, "y": 410, "conf": [88, None, 61]}) == {"row": 3, "y": 410, "conf": 61}
    rid, d = hr.record({"url": "u"}, {}, {"body": "Hansi", "ward": "3", "name": "A", "_pos": {"row": 3}}, 2, "ocr")
    assert d["src_pos"] == {"page": 2, "row": 3} and d["method"].startswith("ocr tesseract")


def test_dl_text_rows_positions():
    text = ("Sr. Ward No  Ward Name     Reservation   Name of the Councillor   Party\n"
            "1.  12       MALKA GANJ    SC WOMAN      REKHA                    BHARATIYA JANATA PARTY\n"
            "\fSr. Ward No  Ward Name     Reservation   Name of the Councillor   Party\n"
            "2.  13       SADAR         GENERAL       RAM                      AAM AADMI PARTY\n")
    pos = []
    rows = dl.text_rows(text, 1, pos)
    assert [r[-1] for r in rows] == [1, 2] and [x["line"] for x in pos] == [2, 2]
    rid, d = dl.record({"url": "u", "source": "bye2025"}, *rows[1], "text layer", pos[1])
    assert d["src_pos"] == {"page": 2, "line": 2, "line_text": text.split("\n")[3]} and d["method"] == "pdf text (pdftotext -layout)"


def test_cw_mp_table_row_positions():
    blocks = json.loads((DATA / "cw_mp_blocks_p9_p10.json").read_text())
    found = cw_mp.read_pages(blocks)
    b, m, page = found[3]
    rid, d = cw_mp.record({"url": "https://govtpress.mp.gov.in/x.pdf"}, b, m, page)
    assert d["src_pos"]["page"] == page and d["src_pos"]["table"] >= 1 and d["src_pos"]["row"] >= 1
    kinds = [kind for kind, _ in dict(blocks)[page]]
    rows = [v for kind, v in dict(blocks)[page] if kind == "rows"][d["src_pos"]["table"] - 1]
    assert m["name"].split()[0] in " ".join(rows[d["src_pos"]["row"] - 1]) and "rows" in kinds
