"""Jharkhand: members of the 6th Jharkhand Vidhan Sabha (2024-) from the NeVA member directory (jhla.neva.gov.in; shared reader
dforms/_leg_neva.py). 80 members of 81 seats (2026-11-11): 80 with phone, 42 with email, 80 with an address (a Ranchi residence
or the home). The list gives the AC number ("76 - Daltonganj -Palamu"). It is in Hindi by default; the reader reads it again in
English.
"""
from dforms import _leg_neva

METHOD = "html cards (NeVA member list, div.search-item)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_jh"
HOST = "jhla.neva.gov.in"
ALIAS = {}


def items(get=None):
    return [_leg_neva.item(MODULE, "JH", HOST, 6, "Jharkhand Vidhan Sabha (6th)")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
