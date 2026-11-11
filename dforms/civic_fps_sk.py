"""Sikkim: fair price shops (ration shops) and their dealers from the state's SMART-PDS ePoS portal epos.sikkim.gov.in.
Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list (fps_id, dealer, nominees;
the site masks the dealer mobile) joined with the "Search" list of each supply office (AFSO / block), which gives the area.
One queue item per district (seeds/dept_civic_fps_sk.json, district codes from the site's own list, saved 2026-11-11); an item without
"dist_code" reads every district. Record ids: dept:civic_fps_sk:<fps_id>.
"""
from dforms import _civic_fps

MODULE = "civic_fps_sk"
STATE = "SK"
BASE = "https://epos.sikkim.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
