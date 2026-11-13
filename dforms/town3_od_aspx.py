"""Odisha: the office staff of town bodies whose own website is made by one ASP.NET vendor ("Welcome to <Town> NAC /
Municipality", menu "Holding Tax Administration System", "Incumbency Chart of Executive Officer", "Executive Officer's Message").

The staff page is Administration.aspx, Staff.aspx, Staff_details.aspx or Employee.aspx (the menu of each site names it: "Staff
Details", "Administration", "Employee"). The page is one table: SL No | Staff Name (or Name of the Staff / Name) | Designation |
Mobile No. (or Contact No. / Phone No.; Karanjia also Office Phone No. and E-Mail Address). The Executive Officer comes first
(role head), then the engineers (Assistant / Junior Engineer), Sanitary Inspector, Tax Collector, Accountant, Revenue
Inspector, Junior Assistant, Peon. Every named row is kept. The page shows no date.
Sites (dforms/town3_sites.json, reader town3_od_aspx; found as dforms/_town3.py says, 2026-11-13): Balangir, Banki, Gudari,
Hindol, Jayapur (jeyporemunicipality.in), Karanjia, Koraput, Rairangpur, Sunabeda, Udala. Samples (live from India, dev-vps-3
Mumbai, 2026-11-13): Balangir Administration.aspx 138 rows, Udala Administration.aspx 20 rows.
Route "direct" (answered dev-vps-3; not checked from abroad), india_only. One queue item = one site.
Records: dept town_body, level body, area = LGD body name, lgd_code; ids dept:town3_od_aspx:<site>:<post slug>:<name slug>.
"""
from dforms import _town3

METHOD = "html table"

MODULE = "town3_od_aspx"
SITES = _town3.sites(MODULE)


def items(get=None):
    return _town3.items(MODULE, SITES)


def fetch(p, get):
    return _town3.fetch(MODULE, p, get)
