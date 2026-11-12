"""Punjab: members of the Punjab Vidhan Sabha (16th) from the NeVA member directory (pvs.neva.gov.in; shared reader
dforms/_leg_neva.py). The list comes in Punjabi first; the reader reads it again in English. Answers from abroad
(archive.s1d.me pool copies, 2026-11) and from Mumbai (2026-11-12: 117 member cards).
"""
from dforms import _leg_neva

MODULE = "leg_pb"
HOST = "pvs.neva.gov.in"
ALIAS = {}


def items(get=None):
    return [_leg_neva.item(MODULE, "PB", HOST, 16, "Punjab Vidhan Sabha (16th)")]


def fetch(p, get):
    recs, files, why = _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
    return [(k, d) for k, d in recs if d.get("name", "").strip().lower() != "vacant"], files, why   # an empty seat's card
