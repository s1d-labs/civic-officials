"""Andaman and Nicobar Islands: fair price shops (ration shops) and their dealers from the SMART-PDS ePoS portal https://epos.andamannicobar.gov.in.
Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list (fps_id, dealer,
nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office, which gives the area (block / circle).
No shop address and no coordinates. One queue item per district (3 districts in seeds/dept_civic_fps2_an.json, saved
2026-11-11); an item without "dist_code" reads every district.
The site masks the dealer mobile (XXXXXX1344) and gives no nominees in Nicobar (57 shops). Record ids: dept:civic_fps2_an:<fps_id>.
"""
from dforms import _civic_fps

MODULE = "civic_fps2_an"
STATE = "AN"
BASE = "https://epos.andamannicobar.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
