"""Haryana: the own sites of town bodies that civic.official has no row for (gap list of 2026-11-11). Haryana bodies run sites of
several vendors (mc<town>.in, Drupal "officers-directory" / "elected-members" pages; mcpalwal.in "employee_data"; mcg.gov.in).

The Directorate of Urban Local Bodies names officers of the bodies only in "Nodal Officers (Litigation Policy)" (read by
ulb_hr); its Transfer / Additional Charge / President Notification pages list orders of 2018-2022 (junior engineers, seat
reservations), not the officers in post. The State Election Commission site has no result lists of the 2025 municipal
elections in archive.s1d.me (municipal-elections pages saved 2026-11-06 show forms and orders only).
Sites of bodies that the hub read already (mcmanesar.in, mcnarnaul.in, mcradaur.com) are left out: rows in civic.official,
not tied (see the report). Hosts from found_sites.csv and DNS (mc + LGD name + .in). One item per site: _ulb2_nw.crawl().
Not India-only: mcpalwal.in answered from Germany on 2026-11-11 (its "Office Directory" tables were empty on that day, so the
item gives the office email and phone only).
"""
from dforms import _ulb2_nw
from dforms.ulb2_hp import site_items

MODULE = "ulb2_hr"
STATE = "HR"
SITES = """https://mcambala.in/|248491|Ambala|Ambala|Municipal Corporation|
https://www.mcg.gov.in/|248576|Gurugram|Gurugram|Municipal Corporation|Gurugram|Gurgaon
https://mcpalwal.in/|248586|Palwal|Palwal|Municipal Council|
https://mcfarukhnagar.in/|248574|Gurugram|Farrukhnagar|Municipal Committee|Farrukhnagar|Farukhnagar|Farrukh Nagar|Farukh Nagar"""


def items(get=None):
    return site_items(MODULE, STATE, SITES)


def fetch(p, get):
    return _ulb2_nw.crawl(p, get, MODULE, STATE)
