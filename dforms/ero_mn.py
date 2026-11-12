"""Manipur: the ERO and the AEROs of all 60 assembly constituencies and the 16 District Election Officers, from the CEO's Who's Who of
Election Officials, ceomanipur.nic.in/officers_contact (officers_contact.aspx answers 301 to it). Answers from Germany and India.

One GET; three tables: DEOs (district, name "Dr. Nivedita Lairenlakpam, IAS DC/DEO", telephone, email), EROs (GridView1: district,
"1 - Khundrakpam", name, designation, email) and AEROs (GridView2: the same columns, email mostly empty). Emails are written as
[at]/[dot]. EROs have no phone on this page. The page shows no date. One queue item.
Record ids: dept:ero_mn:MN-AC-<no>:ero, dept:ero_mn:MN-AC-<no>:aero:<slug of designation>, dept:ero_mn:MN-DEO-<district>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_mn"
URL = "https://ceomanipur.nic.in/officers_contact"
NO = re.compile(r"^\s*(\d{1,3})\s*[-–.]\s*(.+?)\s*$")
POST = {"ero": "Electoral Registration Officer", "aero": "Assistant Electoral Registration Officer"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "MN"}}]


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()

    def add(key, **f):
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="elections", state="MN", source=url, **f))

    for t in soup.find_all("table"):
        g = pgrid(t)
        if not g:
            continue
        head = [h.lower() for h in g[0]]
        if any("district election officer" in h for h in head):
            for r in g[1:]:
                c = dict(zip(head, r))
                dist = next((v for h, v in c.items() if h.startswith("district name")), "")
                name = next((v for h, v in c.items() if "officers" in h), "")
                if not dist or not name:
                    continue
                name, desig = re.subn(r"\s*\bDC\s*/\s*DEO\s*$", "", name)
                key = f"MN-DEO-{_esw.slug(dist)}"
                add(key, level="district", area=dist, post="District Election Officer",
                    designation="Deputy Commissioner" if desig else None, name=name,
                    phone=_esw.phones(c.get("telephone number")), email=_esw.emails(c.get("email id")), district=dist, office_id=key,
                    src_pos=r.pos)
            continue
        tid = t.get("id") or ""
        role = "ero" if tid.endswith("GridView1") else "aero" if tid.endswith("GridView2") else None
        if not role or "ac name" not in head:
            continue
        for r in g[1:]:
            c = dict(zip(head, r))
            m = NO.match(c.get("ac name", ""))
            if not m or not c.get("name"):
                continue
            no, ac = int(m.group(1)), m.group(2)
            office = f"MN-AC-{no}"
            desig = c.get("designation", "")
            key = f"{office}:ero" if role == "ero" else f"{office}:aero:{_esw.slug(desig) or _esw.slug(c['name'])}"
            add(key, level="ac", area=f"{no} - {ac}", post=POST[role], designation=desig, name=c["name"],
                email=_esw.emails(c.get("email")), district=c.get("district"), office_id=office, src_pos=r.pos)
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url", URL))
    return recs, [_esw.keep(MODULE, "officers_contact", r.content)], "" if recs else "no rows"
