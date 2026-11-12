"""MC Shimla councillors from the corporation's own list (cforms/cw_hp_shimla.py), saved page of 2026-11-12."""
import gzip
from pathlib import Path

from cforms.cw_hp_shimla import fetch, parse

PAGE = gzip.decompress((Path(__file__).parent / "data" / "cw_hp_shimla_members.html.gz").read_bytes()).decode("utf-8")


def test_shimla_members():
    recs = dict(parse(PAGE, "https://shimlamc.hp.gov.in/Members/Index"))
    assert len(recs) == 40 and not any("Test User" in d["name"] for d in recs.values())
    mayor = [d for d in recs.values() if d["position"] == "Mayor"]
    assert [(d["name"], d["ward_no"], d["ward_rows"]) for d in mayor] == [("Mr. Surinder Chauhan", "1", 3)]
    assert sum(1 for d in recs.values() if d.get("nominated")) == 4
    d = recs["councillor:HP:shimla-mc:17-1"]
    assert (d["name"], d["ward_name"], d["phone"]) == ("Mrs. K, Sheenam Kataria", "Benmore", "8091120142")
    assert len({d["ward_no"] for d in recs.values() if d.get("ward_no")}) == 30


def test_fetch_keeps_page():
    class R:
        content = PAGE.encode()
        text = PAGE
    recs, files, why = fetch({"url": "https://shimlamc.hp.gov.in/Members/Index"}, lambda u: R())
    assert why == "" and len(recs) == 40 and files[0][0] == "councillors/HP/shimla-mc-members.html.gz"
