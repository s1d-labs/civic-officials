"""Odisha: the office staff of town bodies whose own website is one WordPress theme of one vendor ("<Town> NAC" /
"<Town> Municipality", menu "Section (Staff List)", "Ward Officer", "Incumbency Chart of Executive Officer", "Contact Us").

The staff page is the "Section (Staff List)" page (/?page_id=<n> or /section-staff-list/; Dhenkanal has two staff pages). The page
is one table: Sl. No. | Name of the staff | Section | Designation | Mobile Number (Section and Designation change places on
some sites). The Section column (Administration, Engineering, Sanitation, Revenue, Accounts ...) goes into the record's
section. Rows with only a serial number (the theme leaves 10-15 empty rows) are not data. The page shows no date.
Sites (dforms/town3_sites.json, reader town3_od_wp): Bhuban, Bijepur, Dhenkanal, Jaleswar, Kamakhyanagar, Khandapada,
Nimapada, Rayagada, Remuna. Pattamundai and Bhawanipatna have the same theme with only the Executive Officer filled in
(2026-11-13): not seeded. Samples (live from India, dev-vps-3 Mumbai, 2026-11-13): Bhuban 22 rows, Dhenkanal 17 + 5 rows.
Route "direct" (answered dev-vps-3; not checked from abroad), india_only. One queue item = one site.
Records: dept town_body, level body, area = LGD body name, lgd_code, section; ids dept:town3_od_wp:<site>:<post>:<name>.
"""
from dforms import _town3

METHOD = "html table"

MODULE = "town3_od_wp"
SITES = _town3.sites(MODULE)


def items(get=None):
    return _town3.items(MODULE, SITES)


def fetch(p, get):
    return _town3.fetch(MODULE, p, get)
