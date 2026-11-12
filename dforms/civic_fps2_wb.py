"""West Bengal: fair price shops (ration shops; "MR shops" in the modified rationing areas of Kolkata and the industrial belt) and
their dealers from the state's SMART-PDS ePoS portal https://smartpds.wb.gov.in (the NIC React app; food.wb.gov.in and
wbpds.wb.gov.in do not answer from this box or the India server). Platform and endpoints: dforms/_civic_fps.py (SMART-PDS).
Per district: the "FPS Dealer & Device Details" list (fps_id, dealer, nominee 1 and 2 with their mobiles) joined with the "Search"
list of each supply office, which gives the area. The site's district list has 29 codes: the 23 districts plus the rationing areas
(Kolkata North, Kolkata South, Asansol, Barrackpore, Dumdum Bidhannagar, a second Howrah and Hooghly). The site masks the dealer
mobile, so the dealer record has no phone; nominee mobiles are in full and stay as the site shows them. No shop address and no
coordinates. One queue item per district code (seeds/dept_civic_fps2_wb.json, saved 2026-11-11); an item without "dist_code" reads
every district. Record ids: dept:civic_fps2_wb:<fps_id>.
"""
from dforms import _civic_fps

METHOD = "json api (SMART-PDS device list + supply office search)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_wb"
STATE = "WB"
BASE = "https://smartpds.wb.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
