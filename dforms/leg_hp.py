"""Himachal Pradesh: members of the 14th Himachal Pradesh Vidhan Sabha (2022-) from the NeVA member directory (hpvs.neva.gov.in;
shared reader dforms/_leg_neva.py). 68 members (2026-11-11): 68 with phone, 68 with email, 67 with an address (mostly the
MLA's set in the Vidhayak Sadan, Shimla). The list is in Hindi by default; the reader reads it again in English. No AC number:
the English name decides.
"""
from dforms import _leg_neva

MODULE = "leg_hp"
HOST = "hpvs.neva.gov.in"
ALIAS = {}


def items(get=None):
    return [_leg_neva.item(MODULE, "HP", HOST, 14, "Himachal Pradesh Vidhan Sabha (14th)")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
