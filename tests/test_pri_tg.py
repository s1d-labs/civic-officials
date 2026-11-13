"""cforms/pri_tg.py: Telangana 2025 gram panchayat results (TSEC rural dashboard), fixtures saved 2026-11-13 in tests/data/pri_tg/."""
import json
from pathlib import Path

from cforms import pri_tg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "data" / "pri_tg"
SEEDS = {i["key"]: i["payload"] for i in json.loads((ROOT / "seeds" / "pri_tg.json").read_text())}


class R:
    def __init__(self, text):
        self.text, self.content, self.url, self.status_code = text, text.encode(), pri_tg.POST_URL, 200


def test_summary_and_seeds():
    s = pri_tg.summary((DATA / "summary_sarpanch_2025.html").read_text())
    assert len(s) == 31 and s[0] == ("01", "Adilabad", "21", "472") and s[-1][:2] == ("33", "Narayanpet")
    assert len(SEEDS) == 62 and all(p["kind"] == "form-pri_tg" and p["lgd_district"] for p in SEEDS.values())
    assert sum(p["expected"] for p in SEEDS.values() if p["post"] == "sarpanch") == 12702
    assert SEEDS["pri-tg-189-ward-23"]["lgd_district"] == "Rangareddi"


def test_sarpanch_mulugu():
    p = SEEDS["pri-tg-189-sarpanch-32"]
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append((url, method, data))
        return R((DATA / "sarpanch_2025_d32_mulugu.html").read_text())
    recs, files, why = pri_tg.fetch(p, get)
    assert why == "" and len(recs) == 146 == p["expected"] and len(calls) == 1
    assert calls[0][1] == "POST" and calls[0][2]["property(sdistrictId)"] == "32"
    assert calls[0][2]["property(election_for)"] == "GP#4#GRAMPANCHAYAT"
    assert files[0][0] == "pri/TG/189-sarpanch-32-mulugu.html.gz"
    rid, d = recs[0]
    assert rid == "pri:TG:gp:278306:head" and d["type"] == "pri_member" and d["head"] is True
    assert (d["name"], d["body"], d["block"], d["post"], d["reservation"]) == ("PALAKA MAHA LAKSHMI", "Allamvari Ghanpur",
                                                                               "Eturnagaram", "Sarpanch", "ST(W)")
    assert d["src_pos"] == {"table_id": "GridView1", "row": 3, "sl_no": "1"} and "src_sha256" in d
    assert sum(1 for _, x in recs if x["lgd_code"]) >= 140
    assert len({r for r, _ in recs}) == len(recs)


def test_ward_members_adilabad_part():
    p = SEEDS["pri-tg-189-ward-01"]
    recs = pri_tg.records((DATA / "ward_2025_d01_adilabad_part.html").read_text(), p)
    assert len(recs) == 32 and all(d["post"] == "Ward Member" and "head" not in d for _, d in recs)
    rid, d = recs[0]
    assert rid == "pri:TG:gp:280865:w1" and d["ward_no"] == "1" and d["result_status"] == "Unanimous"
    assert d["src_pos"]["gram_panchayat"] == "Allikori" and d["block"] == "Adilabad Rural"


def test_no_data():
    p = SEEDS["pri-tg-189-ward-01"]
    recs, files, why = pri_tg.fetch(p, lambda *a, **k: R("<html>Data Not Available</html>"))
    assert recs == [] and why == "data not available"
