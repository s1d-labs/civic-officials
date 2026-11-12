"""Bihar chief / deputy chief councillors (cforms/br_head.py): SEC Bihar ResultP1 answer for post 1 (मुख्य पार्षद), Araria."""
import json
from pathlib import Path

from cforms import br_head
from cforms.br import _result

DATA = Path(__file__).parent / "data"


def test_araria_chief():
    _, rows, _ = _result((DATA / "br_head_araria_p1_post1.html").read_text())
    d = br_head.head_record(rows, {"body_value": "290", "type": "2", "body_type": "नगर परिषद"}, "chair", "ResultP1", "u", "L")
    assert d["position"] == "Chairperson" and d["ward_no"] == "chair" and d["post"] == "मुख्य पार्षद"
    assert d["name"] and "विजेता" not in d["name"] and d["candidates"] == len(rows) > 5
    assert d["votes"] == max(int(r["कुल प्राप्त मत"]) for r in rows) and d["margin"] > 0
    assert d["src_pos"]["table_id"] == "ctl00_ContentPlaceHolder1_RPDetails" and d["src_pos"]["row"] >= 2


def test_positions():
    assert br_head.position("chair", "1") == "Mayor" and br_head.position("vice", "1") == "Deputy Mayor"
    assert br_head.position("chair", "3") == "Chairperson" and br_head.position("vice", "2") == "Vice Chairperson"


def test_seed():
    root = Path(__file__).parent.parent / "seeds"
    br = json.loads((root / "councillors_br.json").read_text())
    items = json.loads((root / "councillors_br_head.json").read_text())
    assert len(items) == len(br) == 260 and items == br_head.seed_items(br)
    assert all(i["payload"]["kind"] == "form-br_head" and i["key"].startswith("brh-") for i in items)
