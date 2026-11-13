"""Write seeds/pri_ap.json from cforms/pri_ap.items() (17 items: 13 GP district files + MPTC, ZPTC, MPP, ZPP)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cforms import pri_ap  # noqa: E402

items = pri_ap.items()
(Path(__file__).parent / "pri_ap.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n")
print(len(items))
