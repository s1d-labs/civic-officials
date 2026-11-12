"""SEC heads and new results, west / central states (worktree sec-new-west, 2026-11-12)."""
import gzip
import json
from pathlib import Path

from cforms import rj_chair

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


def _html(name):
    return gzip.decompress((DATA / name).read_bytes()).decode("utf-8")


def test_rj_chair_winners():
    url = rj_chair.BASE_URL + rj_chair.PAGES["chair"]
    recs = rj_chair.parse(_html("rj_chair_winner.html.gz"), "chair", url)
    assert len(recs) == 309 and len(dict(recs)) == 309
    d = dict(recs)["councillor:RJ:ajmer-nagar-nigam:chair"]
    assert d["name"] == "अनामिका शर्मा" and d["position"] == "Mayor" and d["position_local"] == "महापौर"
    assert d["party"] == "भारतीय जनता पार्टी" and d["votes"] == "43" and d["electorate"] == "80" and d["unopposed"] is False
    assert d["src_pos"] == {"table": "#tabs-5 (Winner)", "row": 2} and d["ward_no"] == "chair"
    k = dict(recs)["councillor:RJ:kekri-nagar-palika:chair"]
    assert k["position"] == "Chairperson" and k["position_local"] == "अध्यक्ष"
    pos = {d["position"] for _, d in recs}
    assert pos == {"Mayor", "Chairperson"} and sum(d["position"] == "Mayor" for _, d in recs) == 10
    # the head ids use the ward reader's body slugs (cforms/rj.py; Laxmangarh and Rajgarh carry the district)
    seeds = {i["payload"]["slug"] for i in json.loads((SEEDS / "councillors_rj.json").read_text())}
    assert {r.split(":")[2] for r, _ in recs} == seeds


def test_rj_vice_winners():
    url = rj_chair.BASE_URL + rj_chair.PAGES["vice"]
    recs = rj_chair.parse(_html("rj_dychair_winner.html.gz"), "vice", url)
    assert len(recs) == 309
    d = dict(recs)["councillor:RJ:ajmer-nagar-nigam:vice"]
    assert d["name"] == "हेमन्त सांखला" and d["position"] == "Deputy Mayor" and d["votes"] == "40" and "party" not in d
    assert rj_chair.METHOD


def test_rj_chair_fetch_postbacks():
    pages = {"chair": _html("rj_chair_winner.html.gz")}
    calls = []

    class R:
        def __init__(self, t):
            self.text, self.content, self.url, self.status_code = t, t.encode(), "", 200

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, (data or {}).get("__EVENTTARGET"), (data or {}).get(rj_chair.P + "btnSubmit")))
        return R(pages["chair"])
    recs, files, why = rj_chair.fetch({"post": "chair", "period": "61"}, get)
    assert why == "" and len(recs) == 309 and len(files) == 1
    assert calls == [("GET", None, None), ("POST", rj_chair.P + "Election", None), ("POST", rj_chair.P + "Period", None),
                     ("POST", "", "Submit")]
    assert recs[0][1]["src_sha256"]
    seeds = json.loads((SEEDS / "councillors_rj_heads.json").read_text())
    assert [s["payload"]["post"] for s in seeds] == ["chair", "vice"]
