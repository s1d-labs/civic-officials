"""Aizawl Municipal Corporation (amcmizoram.com, Laravel; behind Cloudflare): its engineers, planners and inspectors. One page,
/page/list-of-officers-staff (saved in archive.s1d.me 2026-11-08; shows no "Last Updated" date): table "List of Officers"
(Sl. No | Name of Officer | Designation: Commissioner, Town Planners, Executive Engineer, Assistant Engineers ...) and table
"LIST OF STAFF" (Sl.No | Name of Employees | Designation: Junior Engineers, Planning Assistants, Enforcement Inspectors, clerks,
drivers, Group D). No phones, and no ward or zone for anyone (Aizawl has 19 elected wards and 83 local councils): records are level
"body" (a body-wide staff list). Kept: the officers' table in full and, from the staff table, only the field posts (engineers,
planning assistants, inspectors, IT programme officers); clerks (UDC, LDC), stenographers, drivers and Group D are left out.
The whoswho task already reads the officers' table; the staff table is new.
Records: extra key "list" ("officers" / "staff"). Record ids: dept:ward2s_aizawl:<list>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_aizawl"
BODY, LGD, STATE, DISTRICT = "Aizawl Municipal Corporation", "277318", "MZ", "Aizawl"
URL = "https://amcmizoram.com/page/list-of-officers-staff"
FIELD = re.compile(r"(?i)engineer|\bJE\b|\bAE\b|inspector|planning|planner|architect|\bAPO\b|supervisor|sanitary")


def items(get=None):
    return [{"key": f"{MODULE}-officers-staff", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


POSTS = {"JE": "Junior Engineer", "APO": "Assistant Programme Officer", "APO(IT)": "Assistant Programme Officer (IT)"}


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for t in soup.find_all("table"):
        g = [[_esw.clean(c) for c in r] for r in _esw.grid(t)]
        if not g:
            continue
        lst = "staff" if any("staff" in c.lower() or "employees" in c.lower() for r in g[:2] for c in r) else "officers"
        for r in g:
            if len(r) < 3 or not r[0].isdigit():
                continue
            name, post = r[1], POSTS.get(r[2].replace(" ", ""), r[2])
            if not name or not post or (lst == "staff" and not FIELD.search(r[2] + " " + post)):
                continue
            recs.append(_ward.record(MODULE, f"{lst}:{_esw.slug(post)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="body", area=BODY, post=post, name=name, list=lst,
                                     source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "list-of-officers-staff", r.content)], "" if recs else "no staff tables"
