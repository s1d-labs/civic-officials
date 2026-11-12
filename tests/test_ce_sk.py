"""Sikkim General Municipal Elections 2026 (cforms/ce_sk.py): pdftotext -layout text of Gazette Extraordinary No. 236 and 237."""
import collections
import json
from pathlib import Path

from cforms import ce_sk

DATA = Path(__file__).parent / "data"


def test_gazette_236():
    recs = dict(ce_sk.parse((DATA / "ce_sk_gazette_236.txt").read_text(), {"url": "u", "uncontested": True}))
    assert len(recs) == 61
    n = collections.Counter(d["lgd_code"] for d in recs.values())
    assert n == {"249694": 19, "249692": 7, "290460": 5, "249695": 5, "249689": 5, "249690": 5, "249693": 5, "306274": 5, "306273": 5}
    g9 = recs["councillor:SK:249694:9"]
    assert g9["name"] == "TSHERING PALDEN BHUTIA" and g9["ward_name"] == "Development Area" and g9["unopposed"]
    assert g9["src_pos"]["page"] == 1 and "TSHERING PALDEN BHUTIA" in g9["src_pos"]["line_text"]
    assert recs["councillor:SK:249692:6"]["name"] == "GANESH RAI"
    assert recs["councillor:SK:290460:3"]["name"] == "SANJEEV KUMAR KHATI"
    assert recs["councillor:SK:306273:5"]["ward_name"] == "Dikling-Chalamthang" and recs["councillor:SK:306273:5"]["src_pos"]["page"] == 3
    assert "councillor:SK:249694:10" not in recs and "councillor:SK:249694:17" not in recs


def test_gazette_237():
    recs = ce_sk.parse((DATA / "ce_sk_gazette_237.txt").read_text(), {"url": "u"})
    assert len(recs) == 1 and recs[0][0] == "councillor:SK:249694:10" and recs[0][1]["name"] == "SRIJANA CHETTRI"
    assert "unopposed" not in recs[0][1]


def test_seed():
    items = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_ce_sk.json").read_text())
    assert items == ce_sk.seed_items()
