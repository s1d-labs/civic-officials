"""Jammu and Kashmir: members of the 1st Legislative Assembly of the Union Territory (2024-) from the NeVA member directory
(jkla.neva.gov.in; shared reader dforms/_leg_neva.py). 90 members (2026-11-11), list in English: 89 with phone, 84 with email,
59 with an address. The list names no AC number. The site's AC layer has the seats from before the 2022 delimitation, so the name
decides (dforms/_leg.py); about 23 new or renamed seats (Anantnag West, Ramgarh, Trehgam ...) get no number ("JK-AC-x-<name>").
"""
from dforms import _leg_neva

MODULE = "leg_jk"
HOST = "jkla.neva.gov.in"
# the site's spellings (normalised) -> the names of dforms/ac_no.json
ALIAS = {"chrarisharief": "chrarshar", "budgam": "badgam", "khanyar": "khaniyar", "dooru": "doru", "rajouri": "rajauri",
         "baramulla": "baramula", "khansahib": "khansaheb", "habbakadal": "habbakada", "nowshera": "naushehra"}


def items(get=None):
    return [_leg_neva.item(MODULE, "JK", HOST, 1, "Jammu and Kashmir Legislative Assembly (1st, 2024-)")]


def fetch(p, get):
    return _leg_neva.fetch(MODULE, p, get, alias=ALIAS)
