"""Write seeds/pri_kl.json: Kerala panchayat queue items (cforms/pri_kl.py).
Input: a folder with the 28 SEC list pages saved as wyrlb_<d>_<G|B>.html (sec.kerala.gov.in/public/wyrlb/<d>/<G|B>, d = 1..14).
Run: .venv/bin/python seeds/build_pri_kl.py <folder>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cforms import pri_kl  # noqa: E402


def main(folder):
    f = Path(folder)
    lists = {}
    for d in range(1, 15):
        for t in ("G", "B"):
            p = f / f"wyrlb_{d}_{t}.html"
            if not p.exists() or not pri_kl.body_list(p.read_text(encoding="utf-8")):
                sys.exit(f"missing or empty list page {p}")
            lists[(d, t)] = p.read_text(encoding="utf-8")
    items = pri_kl.sec_items(lists) + [pri_kl.seed_item()]
    out = Path(__file__).resolve().parent / "pri_kl.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sec = [i["payload"] for i in items if i["payload"].get("part") == "sec"]
    for lev in ("zp", "ps", "gp"):
        s = [p for p in sec if p["level"] == lev]
        print(lev, len(s), "lgd matched", sum(1 for p in s if p.get("lgd_code")), "members listed", sum(p.get("expected", 0) for p in s))


if __name__ == "__main__":
    main(sys.argv[1])
