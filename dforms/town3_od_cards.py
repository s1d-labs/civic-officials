"""Odisha: the office staff of town bodies whose own website is the municipal WordPress theme with a "Staff Position" page
(/about-us/staff-position/, menu About Us -> Staff Position; the same theme has "Directory of Municipality Official").

The page has no table: one card per person, <div class="single-author staff-position"> with the name (<p class="author-name">),
the post (<p class="deg">) and "Contact No.: +91 ..." (<p class="cont">). The Executive Officer comes first (role head), then
the Additional Executive Officer, Health Officer, engineers, Sanitary Inspectors, Revenue Inspectors, Accountant, clerks,
peons and sweepers. Every card with a name and a post is kept; "Contact No.: +91" with no number gives no phone. src_pos =
{"card": n}. The page shows no date.
Sites (dforms/town3_sites.json, reader town3_od_cards; found as dforms/_town3.py says, 2026-11-13): Jharsuguda (62 cards) and
Paralakhemundi (31 cards), live from India, dev-vps-3 Mumbai, 2026-11-13. Route "direct" (not checked from abroad), india_only.
Records: dept town_body, level body, area = LGD body name, lgd_code; ids dept:town3_od_cards:<site>:<post slug>:<name slug>.
"""
from dforms import _town3

METHOD = "html cards"

MODULE = "town3_od_cards"
SITES = _town3.sites(MODULE)


def items(get=None):
    return _town3.items(MODULE, SITES)


def fetch(p, get):
    return _town3.fetch(MODULE, p, get, rows=_town3.card_rows)
