"""Manipur: fair price shops (ration shops) and their dealers from the state's SMART-PDS ePoS portal https://epos.mn.gov.in (the NIC
React app; the older host epos.manipur.gov.in refuses connections). Platform and endpoints: dforms/_civic_fps.py (SMART-PDS).
Per district: the "FPS Dealer & Device Details" list (fps_id, dealer, nominee 1 and 2 with their mobiles) joined with the "Search"
list of each supply office (subdivision, for example "Subdivn Lamphel"), which gives the area. The site masks the dealer mobile, so
the dealer record has no phone; the nominee mobiles are in full and stay as the site shows them. No shop address and no coordinates.
The site's district list has 18 codes: the 16 districts, with Jiribam and Kangpokpi under an old and a new code each; a shop under
both codes gets one record id. One queue item per district code (seeds/dept_civic_fps2_mn.json, saved 2026-11-11); an item without
"dist_code" reads every district. Record ids: dept:civic_fps2_mn:<fps_id>.
"""
from dforms import _civic_fps

MODULE = "civic_fps2_mn"
STATE = "MN"
BASE = "https://epos.mn.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
