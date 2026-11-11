"""Himachal Pradesh: fair price shops (ration shops) and their dealers from the SMART-PDS ePoS portal https://smartpds.hp.gov.in.
Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list (fps_id, dealer,
nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office, which gives the area (block / circle).
No shop address and no coordinates. One queue item per district (12 districts in seeds/dept_civic_fps2_hp.json, saved
2026-11-11); an item without "dist_code" reads every district.
The site masks the dealer mobile and gives no nominees in the sample (Kinnaur, 67 shops: nominee fields "NA"), so most HP
records have no phone. HP shop numbers are short ("2411") and can repeat in another district, so the record id carries the
district code: dept:civic_fps2_hp:<dist_code>-<fps_id>.
"""
from dforms import _civic_fps

MODULE = "civic_fps2_hp"
STATE = "HP"
BASE = "https://smartpds.hp.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def rekey(recs):
    """Record ids with the district code: HP shop numbers are short and are not unique in the state."""
    out = []
    for rid, d in recs:
        out.append((f"dept:{MODULE}:{d.get('dist_code', '')}-{d['fps_id']}", d))
    return out


def fetch(p, get):
    recs, files, why = _civic_fps.sp_fetch(p, get, MODULE, STATE)
    return rekey(recs), files, why
