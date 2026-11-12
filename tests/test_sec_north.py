"""SEC readers for the northern / eastern gap states (worktree sec-north, 2026-11-12)."""
import gzip
import json
from pathlib import Path

from cforms import cw_wb

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


class R:
    def __init__(self, b):
        self.content = b
        self.text = b.decode("utf-8")


def wb_get(mid):
    """Answers of portal.wbme.org saved 2026-11-12 (Alipurduar 220, KMC borough I 162)."""
    calls = []

    def get(url, method="GET", data=None, headers=None):
        body = json.loads(data)
        calls.append((url.rsplit("/", 1)[1], body))
        name = "prd" if url.endswith("PollResultDate") else "res"
        return R(gzip.decompress((DATA / f"cw_wb_{name}{mid}.json.gz").read_bytes()))
    get.calls = calls
    return get


def test_wb_alipurduar():
    p = {"wbme_id": 220, "lgd_code": "249958", "body_en": "Alipurduar", "district": "ALIPURDUAR"}
    get = wb_get(220)
    recs, files, why = cw_wb.fetch(p, get)
    assert why == "" and len(recs) == 20 and len(files) == 2
    assert get.calls[1] == ("SelectCandidateVotesinFavourPortalList",
                            {"MunicipalityDirectoryID": "220", "MunicipalitySeatID": "0", "PanchayatPollDateID": "3"})
    r = dict(recs)["councillor:WB:249958:1"]
    assert r["name"] == "PRASENJIT KAR" and r["party"] == "AITC" and r["votes"] == "1863" and r["margin"] == "1429"
    assert r["father_or_husband"] == "LATE PRAKASH KAR" and r["n_candidates"] == 3 and r["result_date"] == "02/03/2022"
    assert dict(recs)["councillor:WB:249958:2"]["name"] == "SRILA DUTTA (MAM)"


def test_wb_kolkata_borough():
    recs, _, why = cw_wb.fetch({"wbme_id": 162, "lgd_code": "250299"}, wb_get(162))
    assert why == "" and sorted(int(d["ward_no"]) for _, d in recs) == list(range(1, 10))
    assert all(d["result_date"] == "21/12/2021" for _, d in recs)


def test_wb_tie_and_bye_election():
    poll = {"ID": 9, "ElectionType": "Bye Elections", "PollResultDate": "01/01/2024"}
    c = [{"SeatName": "WARD-4", "SeatIndex": 1, "CandidateName": "A", "VoteInFavour": 10},
         {"SeatName": "WARD-4", "SeatIndex": 2, "CandidateName": "B", "VoteInFavour": 10}]
    d = cw_wb.winners(c, poll, {})["4"]
    assert d["tie"] is True and d["name"] == "A" and "margin" not in d


def test_wb_seed():
    items = json.loads((SEEDS / "councillors_cw_wb.json").read_text())
    assert len(items) == 128 and len({i["key"] for i in items}) == 128
    codes = {i["payload"]["wbme_id"]: i["payload"]["lgd_code"] for i in items}
    assert codes[220] == "249958" and codes[162] == codes[177] == "250299" and 179 not in codes
    assert all(codes.values())


def test_mp_ocr_seed():
    """The 122 OCR items the seed item seed-cw_mp-gazette listed on the hub (20 gazette issues, 456 pages, all saved in the bucket)."""
    items = json.loads((SEEDS / "ocr_councillors_cw_mp.json").read_text())
    assert len(items) == 122 and len({i["key"] for i in items}) == 122
    assert all(i["payload"]["kind"] == "form-cw_mp" and i["payload"]["stored"].startswith("civic-officials-councillors/councillors/MP/")
               for i in items)
    assert sum(i["payload"]["last"] - i["payload"]["first"] + 1 for i in items) == 456


def test_listed_seeds_ga_dd():
    """Items that the seed items seed-cw_ga / seed-cw_dd listed on the hub (2026-11-12) but that were never queued."""
    ga = json.loads((SEEDS / "councillors_cw_ga_listed.json").read_text())
    dd = json.loads((SEEDS / "ocr_councillors_cw_dd.json").read_text())
    assert len(ga) == 7 and {i["payload"]["kind"] for i in ga} == {"form-cw_ga"}
    assert len(dd) == 79 and {i["payload"]["kind"] for i in dd} == {"form-cw_dd"}
    assert len({i["key"] for i in ga + dd}) == 86
