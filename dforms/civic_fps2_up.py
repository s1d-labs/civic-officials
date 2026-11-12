"""Uttar Pradesh: fair price shops (ration shops, "उचित दर विक्रेता") and their dealers from the state's SMART-PDS ePoS portal
https://smartpds.up.gov.in (the NIC React app; the older hosts epos.up.gov.in, fcs.up.gov.in and nfsa.up.gov.in do not answer from
this box or the India server). Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device
Details" list (fps_id, dealer name, nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office (block),
which gives the area. The site masks the dealer mobile (XXXXX-X4244), so the dealer record has no phone; the nominee mobiles are in
full and stay as the site shows them (in many shops the nominee 1 mobile ends with the same 4 digits as the dealer's masked one).
No shop address and no coordinates. One queue item per district (seeds/dept_civic_fps2_up.json, 75 district codes from the site's
own list, saved 2026-11-11); an item without "dist_code" reads every district. Record ids: dept:civic_fps2_up:<fps_id>.
"""
from dforms import _civic_fps

METHOD = "json api (SMART-PDS device list + supply office search)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_up"
STATE = "UP"
BASE = "https://smartpds.up.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
