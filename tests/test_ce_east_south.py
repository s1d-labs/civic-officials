"""Offline tests for the ce_ readers (East, North-East and South India councillors) and their seed files."""
import json
from pathlib import Path

from cforms import ce_ne

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


class Resp:
    def __init__(self, text):
        self.text = text
        self.content = text.encode()


def test_roman():
    assert [ce_ne.roman(s) for s in ("I", "IV", "IX", "XIV", "XIX", "xviii")] == [1, 4, 9, 14, 19, 18]
    assert ce_ne.roman("12") is None and ce_ne.roman("") is None


def test_amc_rows():
    rows = ce_ne.amc_rows((DATA / "ce_mz_aizawl.html").read_text(encoding="utf-8"))
    assert [r["ward_no"] for r in rows] == ["1", "2", "3", "4", "18", "19"]
    assert rows[0] == {"name": "Vanlalhriata", "ward_no": "1", "ward_roman": "I", "position": "Corporator", "party": "ZPM"}
    assert rows[2]["position"] == "Executive Corporator"
    assert rows[-1]["name"] == "Dr. Lalmalsawma Nghaka" and rows[-1]["party"] == "INC"


def test_amc_fetch():
    item = json.loads((SEEDS / "councillors_ce_mz.json").read_text())[0]
    html = (DATA / "ce_mz_aizawl.html").read_text(encoding="utf-8")
    recs, files, why = ce_ne.fetch(item["payload"], lambda url, **kw: Resp(html))
    assert why == "" and len(recs) == 6
    rid, d = recs[0]
    assert rid == "councillor:MZ:aizawl-municipal-corporation:1"
    assert d["type"] == "councillor" and d["body_en"] == "Aizawl Municipal Co-Operation" and d["lgd_code"] == "277318"
    assert files[0][0] == "councillors/MZ/aizawl-municipal-corporation.html.gz"
    assert ce_ne.fetch(item["payload"], lambda url, **kw: None) == ([], [], "no answer")
    assert ce_ne.fetch(item["payload"], lambda url, **kw: Resp("<html><table><tr><td>x</td></tr></table></html>"))[2] == \
        "no corporators table"


KL_MEMBER = """<html><body><p>Active Representative</p><p>Prasanth S</p><p>Councillor</p><p>Age: 41</p><p>LDF</p><p>CPI(M)</p>
<p>Local Body Name</p><p>Thiruvananthapuram Municipal Corporation</p><p>Ward Number / Name</p><p>Ward No. 001 (Kazhakkoottam)</p>
<p>Ward Reservation / Code</p><p>General • C01001</p><p>Election Code</p><p>GE-2025</p></body></html>"""


def test_kl_corporation_items():
    """seeds/councillors_ce_kl.json: the district page /public/wyrlb/<d>/C of a district with one corporation is that
    corporation's ward table, which the built-in kl-body reader (councillors.kl_body) reads."""
    import councillors
    items = json.loads((SEEDS / "councillors_ce_kl.json").read_text())
    assert len(items) == 6 and sum(i["payload"]["expected"] for i in items) == 421
    p = items[0]["payload"]
    assert p["kind"] == "kl-body" and p["url"].endswith("/public/wyrlb/14/C") and p["lgd_name"] == "Thiruvananthapuram"
    table = (DATA / "ce_kl_wyrlb_14_C.html").read_text(encoding="utf-8")
    recs, files, why = councillors.kl_body(p, lambda url, **kw: Resp(table if url == p["url"] else KL_MEMBER))
    assert why == "" and len(recs) == 3 and files[0][0] == "councillors/KL/body-C14.html.gz"
    rid, d = recs[0]
    assert rid == "councillor:KL:C01001" and d["party"] == "CPI(M)" and d["ward_no"] == "001"
    assert d["body"] == "Thiruvananthapuram Municipal Corporation" and d["row_ml"][0] == "001"


def test_seed_files():
    for name in ("councillors_ce_mz.json", "councillors_ce_jh.json", "councillors_ce_kl.json"):
        items = json.loads((SEEDS / name).read_text())
        keys = [i["key"] for i in items]
        assert len(keys) == len(set(keys)) and all(k.startswith("ce-") for k in keys)
        for i in items:
            p = i["payload"]
            assert p["url"].startswith("https://") and p["state"] in ("MZ", "JH", "KL")
            assert p["kind"] in ("pdf", "form-ce_ne", "kl-body")
