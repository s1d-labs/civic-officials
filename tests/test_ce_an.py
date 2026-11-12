"""Sri Vijaya Puram (Port Blair) MC councillors from the council's RTI 4(1)(b) disclosure (cforms/ce_an.py)."""
import json
from pathlib import Path

from cforms import ce_an

DATA = Path(__file__).parent / "data"


def test_svpmc_councillors():
    recs = dict(ce_an.parse((DATA / "ce_an_svpmc_rti.txt").read_text()))
    assert len(recs) == 24
    assert recs["councillor:AN:sri-vijaya-puram-mc:1"]["name"] == "Shri. S Shahul Hameed"
    assert recs["councillor:AN:sri-vijaya-puram-mc:13"]["position"] == "Chairperson"
    assert recs["councillor:AN:sri-vijaya-puram-mc:9"]["position"] == "Sr Vice Chairperson"
    assert recs["councillor:AN:sri-vijaya-puram-mc:20"]["position"] == "Junior Vice Chairperson"
    assert recs["councillor:AN:sri-vijaya-puram-mc:24"]["name"] == "Smti. U Kavitha"
    assert all(d["lgd_code"] == "253098" for d in recs.values())


def test_seed():
    items = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_ce_an.json").read_text())
    assert items[0]["payload"]["kind"] == "form-ce_an"
