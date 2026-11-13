"""Seeds for cforms/pri_ka.py (seeds/pri_ka.json): one item per Karnataka district panchayat (LGD zilla panchayats in
cforms/pri_lgd/ka.json.gz), each reading its taluk and gram panchayats from eGramSwaraj.
Run: .venv/bin/python seeds/build_pri_ka.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cforms import _pri, pri_ka  # noqa: E402


def items(state="KA", state_code="29"):
    lgd = _pri.Lgd(state)
    n_kids = {}
    for code, lev, _n, _l, parent in lgd.rows:
        n_kids[parent] = n_kids.get(parent, 0) + 1
    out = []
    for code, lev, name, _local, _parent in sorted(lgd.rows, key=lambda r: r[2]):
        if lev != "zp":
            continue
        gps = sum(n_kids.get(t[0], 0) for t in lgd.rows if t[4] == code and t[1] == "ps")
        out.append({"key": f"pri_ka:egs:{code}", "payload": {
            "kind": "form-pri_ka", "state": state, "state_code": state_code, "url": pri_ka.member_url(code, state_code, "zp"),
            "level": "zp", "district": name, "lgd_code": code, "year": pri_ka.YEAR, "election": pri_ka.ELECTION,
            "bodies": 1 + sum(1 for t in lgd.rows if t[4] == code) + gps,
            # dev-vps-3 (Mumbai) got answers on 2026-11-13; answers from GitHub runners abroad: not checked
            "route": "direct", "india_only": "unchecked"}})
    return out


if __name__ == "__main__":
    it = items()
    (ROOT / "seeds" / "pri_ka.json").write_text(json.dumps(it, ensure_ascii=False, indent=1) + "\n")
    print(len(it), "items,", sum(i["payload"]["bodies"] for i in it), "bodies")
