"""Seeds for cforms/pri_ka.py in other states (seeds/pri_egs.json): eGramSwaraj elected members, one item per district panchayat
of Goa, Gujarat, Kerala, Maharashtra and Telangana (states with members in the eGramSwaraj state report, 2026-11-13).
Run: .venv/bin/python seeds/build_pri_egs.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "seeds"))
from build_pri_ka import items  # noqa: E402

STATES = {"GA": "30", "GJ": "24", "KL": "32", "MH": "27", "TG": "36"}

if __name__ == "__main__":
    it = []
    for st, code in STATES.items():
        for i in items(st, code):
            i["key"] = i["key"].replace("pri_ka:egs:", f"pri_egs:{st.lower()}:")
            it.append(i)
    (ROOT / "seeds" / "pri_egs.json").write_text(json.dumps(it, ensure_ascii=False, indent=1) + "\n")
    print(len(it), "items,", sum(i["payload"]["bodies"] for i in it), "bodies")
