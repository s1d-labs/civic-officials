"""Lakshadweep: fair price shops (ration shops) and their dealers from the SMART-PDS ePoS portal https://epos.utl.gov.in.
Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list (fps_id, dealer,
nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office, which gives the area (block / circle).
No shop address and no coordinates. One queue item (seeds/dept_civic_fps2_ld.json, saved
2026-11-11); an item without "dist_code" reads every district.
Lakshadweep is one district (587) with 32 shops on 10 islands (the UT's food department page says 29). This site gives the dealer
mobile IN FULL and both nominee mobiles. The vendor test shop 123456789121 is left out. Record ids: dept:civic_fps2_ld:<fps_id>.
"""
from dforms import _civic_fps

METHOD = "json api (SMART-PDS device list + supply office search)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_ld"
STATE = "LD"
BASE = "https://epos.utl.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
