"""Haryana: members of the 15th Haryana Vidhan Sabha (2024-) from the NeVA member directory (hrla.neva.gov.in; shared reader
dforms/_leg_neva.py). 90 members (2026-11-11). The list is in Hindi by default; the reader reads it again in English. Contacts
are thin: 5 phones, 6 emails and 5 addresses of 90 (the Hindi list of 2026-11-11). No AC number: the English name decides.
"""
from dforms import _leg_neva

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_hr"
HOST = "hrla.neva.gov.in"
ALIAS = {}


def items(get=None):
    return [_leg_neva.item(MODULE, "HR", HOST, 15, "Haryana Vidhan Sabha (15th)")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
