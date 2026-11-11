"""Telangana: fair price shops (ration shops) and their dealers from the SMART-PDS ePoS portal https://smartpds.telangana.gov.in.
Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list (fps_id, dealer,
nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office, which gives the area (block / circle).
No shop address and no coordinates. One queue item per district (33 districts in seeds/dept_civic_fps2_tg.json, saved
2026-11-11); an item without "dist_code" reads every district.
The site masks the dealer mobile; nominee mobiles are in full (Hyderabad: 574 of 655 shops have a nominee 1 mobile, 379 a nominee 2
mobile). Where the dealer name is "NA" (a vacant or nominee-run shop) the record names nominee 1 with post "FPS nominee".
epos.telangana.gov.in (the old AePDS site) has no public dealer list. Record ids: dept:civic_fps2_tg:<fps_id>.
"""
from dforms import _civic_fps

MODULE = "civic_fps2_tg"
STATE = "TG"
BASE = "https://smartpds.telangana.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
