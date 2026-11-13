"""Write seeds/pri_gj.json (one item per district panchayat portal) from cforms/pri_gj.items(). Run: .venv/bin/python seeds/build_pri_gj.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cforms import pri_gj  # noqa: E402

items = pri_gj.items()
(ROOT / "seeds" / "pri_gj.json").write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(len(items))
