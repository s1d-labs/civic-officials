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
            # Jharkhand items keep the key that cforms/ce_jh.py page_items() gives (a later seed run then finds them queued)
            assert i["key"].startswith(("cgap-", "ce-jh26-")) and p["kind"].startswith("form-") and p["state"]
            assert p["url"].startswith("http") and (p.get("lgd_code") or p.get("district") or p.get("stored"))
            assert p.get("route") in ("abroad", "direct") and isinstance(p.get("india_only"), bool)


def test_jh_gap_seeds():
    """7 result files (Jamtara, Koderma, Garhwa district sites) that the Jharkhand seed did not list: no election page was known
    for Jamtara and Koderma, Garhwa's vice-chair file sits on its English page."""
    items = json.loads((SEEDS / "councillors_gap_jh.json").read_text())
    assert len(items) == 7 and {i["payload"]["district"] for i in items} == {"Jamtara", "Koderma", "Garhwa"}
    assert sum(i["payload"].get("post") == "Vice Chairperson" for i in items) == 5
    assert all(i["payload"]["route"] == "abroad" for i in items)


def test_gj25_gap_seeds():
    """The 30 Gujarat Feb 2025 OCR items (stored_councillors_gj25.json) all ended "gave up after 3 attempts", 0 records: they
    read the saved copy under civic-officials-councillors-ocr/, but the save items ran in civic-officials-india-direct, and the hub
    keeps a project's files under that project. The gap items name the india-direct copy (same file name: sha1 of the url)."""
    import hashlib
    old = {i["payload"]["url"]: i for i in json.loads((SEEDS / "stored_councillors_gj25.json").read_text())}
    items = json.loads((SEEDS / "councillors_gap_gj.json").read_text())
    assert len(items) == 30 and {i["payload"]["url"] for i in items} == set(old)
    for i in items:
        p = i["payload"]
        assert i["key"] == "cgap-" + old[p["url"]]["key"]
        assert p["stored"] == f"civic-officials-india-direct/councillors/GJ/{hashlib.sha1(p['url'].encode()).hexdigest()[:12]}.pdf"
        assert p["kind"] == "form-cw_gj" and p["route"] == "abroad" and p["ocr"] is True
