"""Lakshadweep: UT-level posts from the Lakshadweep Administration portal (lakshadweep.gov.in, S3WaaS).

Pages (HTML, checked 2026-11-13 from dev-vps-3, Mumbai; about 135 KB each):
- /about-lakshadweep/whos-who/: four tables, Profile Picture | Name | Designation | Email | Address | Phone | Fax
  (Administrator, Collector, Deputy Collectors of the islands ...).
- /directory/: one table, Sl No | Department Name | Contact Number | email Address (37 departments of the Secretariat, no
  names).
Lakshadweep is one LGD district (553): records are level state (the UT) with district Lakshadweep. The table reader is the
one of st_py_portal (header names the columns). One queue item = one page. Ids: dept:st_ld_portal:<page>:<row n>.
"""
from dforms import _esw, st_py_portal
from provenance import at

METHOD = "html table (header names the columns)"

MODULE = "st_ld_portal"
PAGES = [("whos-who", "https://lakshadweep.gov.in/about-lakshadweep/whos-who/", "Lakshadweep Administration", "secretariat"),
         ("directory", "https://lakshadweep.gov.in/directory/", "Lakshadweep Administration, Secretariat", "department")]


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": u, "name": k, "body": b, "body_kind": bk,
                                                 "level": "state", "state": "LD", "district": "Lakshadweep",
                                                 "district_code": "553", "india_only": True, "route": "direct"}}
            for k, u, b, bk in PAGES]


def parse(html, url, p):
    return st_py_portal.parse_table(html, url, p, MODULE)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.status_code != 200:
        return [], [], f"http {r.status_code}"
    recs = [(k, {**d, **at(r, p["url"])}) for k, d in parse(r.text, p["url"], p)]
    return recs, [_esw.keep(MODULE, p["name"], r.content)], "" if recs else "no rows"
