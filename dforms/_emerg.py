"""Shared helpers for the emergency and disaster service readers (dforms/emerg_<layer>_<xx>.py): fire stations, disaster management
authorities and emergency operation centres (DDMA / DEOC), police control rooms, women and child helplines, hospital casualty
numbers, home guards and civil defence. Built on dforms/_esw.py and dforms/_civic.py (neither is changed).

Every record carries layer="emerg_<layer>" (emerg_fire, emerg_ddma, emerg_pcr, emerg_help, emerg_hosp, emerg_hg), dept
"fire" / "disaster" / "police" / "health" / "women_child", level "facility" / "district" / "state" / "subdivision".
Seeds: seeds/dept_emerg_<layer>_<xx>.json, a list of {"key": "emerg_...", "payload": {"reader": ..., "url": ...}}.
"""
import json
import re
from pathlib import Path

from dforms import _civic, _esw

# source trail: the engine dforms/_pdftext.layout_pages() used -> the record's "method"
ENGINE = {"pdftotext": "pdftotext -layout", "pypdf": "pypdf layout"}
SEEDS = Path(__file__).resolve().parent.parent / "seeds"

state_code = _civic.state_code
lat = _civic.lat
lon = _civic.lon
unique = _civic.unique
clean = _esw.clean
phones = _esw.phones
emails = _esw.emails
slug = _esw.slug
keep = _esw.keep


def seed(module):
    """The queue items of seeds/dept_<module>.json."""
    return json.loads((SEEDS / f"dept_{module}.json").read_text())


def record(module, key, layer, **f):
    """(record id, data): _esw.record() with layer="emerg_<layer>"."""
    return _esw.record(module, key, layer=f"emerg_{layer}", **f)


def item(module, key, url, **payload):
    """One seed entry: {"key": "emerg_<...>", "payload": {"reader": module, "url": url, ...}}."""
    return {"key": key if key.startswith("emerg_") else f"emerg_{key}", "payload": {"reader": module, "url": url, **payload}}


def short_codes(text):
    """National short codes in a text (112, 100, 101, 108, 181, 1098, 1091, 1077, 1070 ...), as written, joined by ", "."""
    out = []
    for m in re.findall(r"(?<![\d-])(1(?:12|00|01|02|08|81|098|091|090|077|070|078))(?![\d-])", clean(text)):
        if m not in out:
            out.append(m)
    return ", ".join(out)
