"""Meghalaya: fair price shops (ration shops) and their dealers from the state's SMART-PDS ePoS portal https://epos.megfcsca.gov.in
(the NIC React app, on the same server as Manipur's epos.mn.gov.in; the older AePDS site epos.nic.in/meghalaya is gone and
megrcms.nic.in "Fair Price Shop Detail" does not answer). Platform and endpoints: dforms/_civic_fps.py (SMART-PDS): per district the
"FPS Dealer & Device Details" list (fps_id, dealer, nominees with their mobiles) joined with the "Search" list of each supply office.
The site masks the dealer mobile; nominee mobiles stay as the site shows them. No shop address and no coordinates.
Status 2026-11-11: the site's TLS certificate (*.megfcsca.gov.in) expired on 2026-11-11 06:03 UTC, so every request fails the
certificate check (we never turn the check off) and no answer of this site is saved yet. The seed is one item for the whole state
(no "dist_code": the reader reads the district list first); after the certificate is renewed, items() gives one item per district.
Record ids: dept:civic_fps2_ml:<fps_id>.
"""
from dforms import _civic_fps

METHOD = "json api (SMART-PDS device list + supply office search)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps2_ml"
STATE = "ML"
BASE = "https://epos.megfcsca.gov.in"
INDIA_ONLY = False


def items(get):
    return _civic_fps.sp_items(MODULE, STATE, BASE, INDIA_ONLY, _civic_fps.sp_districts(get, BASE))


def fetch(p, get):
    return _civic_fps.sp_fetch(p, get, MODULE, STATE)
