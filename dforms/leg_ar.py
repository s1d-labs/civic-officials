"""Arunachal Pradesh: members of the 8th Arunachal Pradesh Legislative Assembly (2024-; the site's house number 7) from the NeVA
member directory (arla.neva.gov.in; shared reader dforms/_leg_neva.py). 59 cards (2026-11-11) for 60 seats: three seats show two
members (by-elections; the list does not say who sits now), so those get no office_id. 57 with phone, 37 with email, 13 with
an address. List in English; no AC number: the name decides (ALIAS: the site's spellings -> dforms/ac_no.json).
"""
from dforms import _leg_neva

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_ar"
HOST = "arla.neva.gov.in"
# the site's spellings (normalised) -> the names of dforms/ac_no.json
ALIAS = {"tutingyingkiong": "tutingyinkgkiong", "pakkekessang": "pakkekasang", "hayuliang": "hauyuliang",
         "pongchauwakka": "pongchouwakka", "aaloeast": "alongeast", "aalowest": "alongwest", "dumporijo": "damporijo",
         "bordumsadiyun": "bordumsadiyum", "borduriabogapani": "borduriabagapani"}


def items(get=None):
    return [_leg_neva.item(MODULE, "AR", HOST, 7, "Arunachal Pradesh Legislative Assembly (8th)")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
