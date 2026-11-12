"""Tamil Nadu: fair price shops (ration shops) and their dealers from the SMART-PDS ePoS portal https://smartpds.tn.gov.in.
Platform and endpoints: dforms/_civic_fps.py (SMART-PDS). Per district: the "FPS Dealer & Device Details" list (fps_id, dealer,
nominee 1 and 2 with their mobiles) joined with the "Search" list of each supply office, which gives the area (block / circle).
No shop address and no coordinates. One queue item (seeds/dept_civic_fps2_tn.json, saved
2026-11-11); an item without "dist_code" reads every district.
NOT VERIFIED: smartpds.tn.gov.in resolves to the SMART-PDS server range (103.195.218.61) but on 2026-11-11 it did not answer from
this box (timeout) and refused the connection from the India server vpsin. tnpds.gov.in is an Angular app behind a bot manager
(Radware ShieldSquare). The seed has one item for the whole state; when the host answers, items() gives one item per district.
"""
from dforms import _civic_fps

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_tn"
STATE = "TN"
BASE = "https://smartpds.tn.gov.in"
INDIA_ONLY = True


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
