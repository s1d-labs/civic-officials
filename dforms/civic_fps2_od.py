"""Odisha: fair price shops (ration shops) and their dealers from the state's SMART-PDS ePoS portal https://smartpds.odisha.gov.in
(the NIC React app). Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list
(fps_id such as 0601G005, dealer, nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office (block or
NAC), which gives the area. Many shops are run by a gram panchayat: the dealer name is then the panchayat officer ("PEO SAGADA G.P.")
and the nominee is the person who runs the shop. The site masks the dealer mobile ("XXXXX-XNA"), so the dealer record has no phone;
the nominee mobiles are in full and stay as the site shows them. No shop address and no coordinates (the licence list on
portal.pdsodisha.gov.in has addresses: see the report of 2026-11-11). One queue item per district (seeds/dept_civic_fps2_od.json,
30 district codes from the site's own list, saved 2026-11-11); an item without "dist_code" reads every district.
Record ids: dept:civic_fps2_od:<fps_id>.
"""
from dforms import _civic_fps

METHOD = "json api (SMART-PDS device list + supply office search)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_od"
STATE = "OD"
BASE = "https://smartpds.odisha.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
