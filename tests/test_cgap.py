"""Gap round 2026-11-14: readers and seeds for wards without a councillor (cforms/cgap_mp.py, seeds/councillors_gap_*.json)."""
import json
from pathlib import Path

import provenance
from cforms import cgap_mp

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


def test_ratlam_full_file():
    """rmcratlam.in Janpratinidhi_List.pdf (archive copy 2026-11-06), all 3 pages: mayor, chair, 48 ward councillors."""
    provenance.rows_reset()
    rows = cgap_mp.ratlam_rows(cgap_mp.pdf_lines((DATA / "cgap_mp_ratlam.pdf").read_bytes()))
    p = {"body": "Ratlam", "lgd_code": "250843", "district": "Ratlam", "url": "http://rmcratlam.in/assets/uploads/Janpratinidhi_List.pdf",
         "election": "e"}
    recs = dict(cgap_mp.records(rows, p))
    c = provenance.rows(len(recs))
    assert len(rows) == 50 and len(recs) == 50 and c["rows_used"] == 50 and c["rows_skipped"] == {}
    wards = sorted(int(d["ward_no"]) for d in recs.values() if d.get("ward_no"))
    assert len(wards) == 48 and set(range(1, 50)) - set(wards) == {12}      # the file has no row for ward 12
    m = recs["councillor:MP:250843:mayor"]
    assert m["name"] == "श्री प्रहलाद पटेल" and m["position"] == "Mayor" and m["phone"] == "7354933111, 9827351355, 6232006700"
    assert recs["councillor:MP:250843:chair"]["position"] == "Chairperson"
    w2 = recs["councillor:MP:250843:2"]
    assert w2["name"] == "श्रीमती कविता सुनील महावर" and w2["address"] == "52/2, चादमल की चाॅल लक्ष्मणपुरा रतलाम"
    assert recs["councillor:MP:250843:17"]["name"] == "श्रीमती अनिता कटारा" and recs["councillor:MP:250843:17"]["mic_member"]
    assert sum(1 for d in recs.values() if d.get("mic_member")) == 10
    assert recs["councillor:MP:250843:mayor"]["src_pos"]["page"] == 1 and recs["councillor:MP:250843:49"]["src_pos"]["page"] == 3


def test_gap_seeds():
    for f in sorted(SEEDS.glob("councillors_gap_*.json")):
        items = json.loads(f.read_text())
        assert items and len({i["key"] for i in items}) == len(items), f
        for i in items:
            p = i["payload"]
            assert i["key"].startswith("cgap-") and p["kind"].startswith("form-") and p["state"] and p["url"].startswith("http")
            assert p.get("lgd_code") and p.get("route") in ("abroad", "direct") and isinstance(p.get("india_only"), bool)
