"""Write seeds/pri_tg.json: one item per (post, district) of the TSEC 2025 gram panchayat results (election 189).
Input: the two summary answers (getDatanew for Sarpanch and Ward Member), saved as tests/data/pri_tg/summary_*_2025.html.
Run: .venv/bin/python seeds/build_pri_tg.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cforms import pri_tg  # noqa: E402

DATA = ROOT / "tests" / "data" / "pri_tg"
ALIAS = {"Rangareddy": "Rangareddi"}   # TSEC spelling -> LGD ZP name (close match is a tie with Sangareddy)


def items():
    zps = [r[2] for r in pri_tg.lgd().rows if r[1] == "zp"]
    out = []
    for post, f in (("sarpanch", "summary_sarpanch_2025.html"), ("ward", "summary_ward_2025.html")):
        for did, dist, mandals, total in pri_tg.summary((DATA / f).read_text(encoding="utf-8")):
            name = ALIAS.get(dist, dist)
            lg = name if name in zps else pri_tg._close(name, zps) or ""
            out.append({"key": f"pri-tg-189-{post}-{did}", "payload": {
                "kind": "form-pri_tg", "state": "TG", "url": pri_tg.URL, "post": post, "level": "gp", "district_id": did,
                "district": dist, "lgd_district": lg, "election_id": "189", "election_year": "2025",
                "election": "Telangana 2025 gram panchayat elections", "mandals": mandals,
                "expected": int(total) if total.isdigit() else 0, "india_only": True, "route": "direct"}})
    return out


if __name__ == "__main__":
    it = items()
    (ROOT / "seeds" / "pri_tg.json").write_text(json.dumps(it, indent=1, ensure_ascii=False) + "\n")
    print(len(it), sum(i["payload"]["expected"] for i in it if i["payload"]["post"] == "sarpanch"),
          sum(i["payload"]["expected"] for i in it if i["payload"]["post"] == "ward"),
          [i["payload"]["district"] for i in it if not i["payload"]["lgd_district"]])
