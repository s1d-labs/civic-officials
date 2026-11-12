"""Chandigarh: fair price shops (ration shops) and their dealers from the state's AePDS ePoS portal https://epos.chd.gov.in.
Platform: dforms/_civic_fps.py (AePDS JSP). Per district: FPS_Device_Mapping.jsp -> POST fps_device.action (dist_code) = the "FPS Dealer
& Device Details" table: shop number, terminal, dealer name, nominee I, nominee II. The page source comments out the dealer mobile
column, so no phone. The table gives no shop address; area = the district. One queue item per district (seeds/dept_civic_fps_ch.json, codes
from the page's district list, saved 2026-11-11). Record ids: dept:civic_fps_ch:<shop number>.
"""
from dforms import _civic_fps

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fps_ch"
STATE = "CH"
BASE = "https://epos.chd.gov.in"
INDIA_ONLY = True


def items(get):
    page = get(BASE + "/FPS_Device_Mapping.jsp")
    return _civic_fps.jsp_items(MODULE, STATE, BASE, _civic_fps.jsp_districts(page.text) if page is not None else [], INDIA_ONLY)


def fetch(p, get):
    return _civic_fps.jsp_fetch(p, get, MODULE, STATE)
