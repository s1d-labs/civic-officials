"""West Bengal: members of the 18th West Bengal Legislative Assembly (2026-) from the NeVA member directory (wbla.neva.gov.in;
shared reader dforms/_leg_neva.py). 294 members (2026-11-11): 294 with phone, 290 with email, 1 with an address. The list is in
Bengali by default; the reader reads it again in English. No AC number: the English name decides.
"""
from dforms import _leg_neva

MODULE = "leg_wb"
HOST = "wbla.neva.gov.in"
ALIAS = {}


def items(get=None):
    return [_leg_neva.item(MODULE, "WB", HOST, 18, "West Bengal Legislative Assembly (18th)")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
