"""Gujarat: members of the Gujarat Legislative Assembly (15th) from the NeVA member directory (gujarat.neva.gov.in; shared reader
dforms/_leg_neva.py). The list comes in Gujarati first; the reader reads it again in English. Answers from abroad
(archive.s1d.me pool copies, 2026-11) and from Mumbai (2026-11-12: 182 member cards).
"""
from dforms import _leg_neva

METHOD = 'html cards (NeVA member list, div.search-item)'     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_gj"
HOST = "gujarat.neva.gov.in"
ALIAS = {"mahemdabad": "mehmedabad", "shahera": "shehra", "jamnagarrural": "jamnagar"}   # NeVA spelling -> layer name


def items(get=None):
    return [_leg_neva.item(MODULE, "GJ", HOST, 15, "Gujarat Legislative Assembly (15th)")]


def fetch(p, get):
    recs, files, why = _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
    return [(k, d) for k, d in recs if d.get("name", "").strip().lower() != "vacant"], files, why   # an empty seat's card
