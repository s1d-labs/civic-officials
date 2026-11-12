"""Kerala: fair price shops (ration shops) and their dealers from the state's AePDS ePoS portal https://epos.kerala.gov.in.
Platform: dforms/_civic_fps.py (AePDS JSP). Per district: FPS_Device_Mapping.jsp -> POST fps_device.action (dist_code) = the "FPS Dealer
& Device Details" table: shop number, terminal, dealer name, nominee I, nominee II. The page source comments out the dealer mobile
column, so no phone. The table gives no shop address; area = the district. One queue item per district (seeds/dept_civic_fps_kl.json, codes
from the page's district list, saved 2026-11-11). Record ids: dept:civic_fps_kl:<shop number>.
"""
from dforms import _civic_fps

METHOD = "json api (SMART-PDS device list + supply office search)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps_kl"
STATE = "KL"
BASE = "https://epos.kerala.gov.in"
INDIA_ONLY = False


def items(get):
    page = get(BASE + "/FPS_Device_Mapping.jsp")
    return _civic_fps.jsp_items(MODULE, STATE, BASE, _civic_fps.jsp_districts(page.text) if page is not None else [], INDIA_ONLY)


def fetch(p, get):
    return _civic_fps.jsp_fetch(p, get, MODULE, STATE)
