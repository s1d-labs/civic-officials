"""Uttar Pradesh Legislative Council (Vidhan Parishad): its members from the NeVA member directory (uplc.neva.gov.in; shared
reader dforms/_leg_neva.py). 99 members of 100 seats (2026-11-11), each with phone, email and address (mostly a Lucknow MLC
residence). Constituency = graduates', teachers', local authorities' or MLA-elected seat ("Agra Division Teachers -Teachers'
Constituency"): area = the seat, district = the kind of seat. The list is in Hindi by default; the reader reads it again in
English. Record ids: dept:leg_uplc:UP-LC-<name>.
"""
from dforms import _leg_neva

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_uplc"
HOST = "uplc.neva.gov.in"
ALIAS = {}


def items(get=None):
    return [_leg_neva.item(MODULE, "UP", HOST, 1, "Uttar Pradesh Vidhan Parishad", kind="LC")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
