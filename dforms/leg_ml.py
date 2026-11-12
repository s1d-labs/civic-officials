"""Meghalaya: members of the 11th Legislative Assembly (2023-) with their phones, from the state portal's key contacts
(meghalaya.gov.in/key-contacts/mla, 2 pages of 30: ?page=0 and ?page=1). Saved in archive.s1d.me (2026-11-10).

Each row: "Number : 1 / Constituency : Nartiang (ST)", name + party, "Phone : +91-..., 0364-..." (one row also has "Email ID").
No addresses. One queue item = one page. Record ids: dept:leg_ml:ML-AC-<no>.
"""
import re

from dforms._trail import tr_pos
from dforms import _esw, _leg, _leg_se

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_ml"
URL = "https://meghalaya.gov.in/key-contacts/mla?page={}"


def items(get=None):
    return [{"key": f"{MODULE}-page-{n}", "payload": {"reader": MODULE, "url": URL.format(n), "state": "ML", "page": n,
                                                    "india_only": False}} for n in (0, 1)]


def parse(html, url):
    recs = []
    for tr in _esw.soup(html).select("table tbody tr"):
        c = tr.select_one("td.views-field-field-constituency")
        if not c:
            continue
        t = _esw.clean(c.get_text(" "))
        m = re.search(r"Number\s*:\s*(\d+)", t)
        k = re.search(r"Constituency\s*:\s*(.+)", t)
        nm = tr.select_one(".mla-title")
        party = tr.select_one(".mla-party")
        contact = tr.select_one("td.views-field-nothing")
        ct = _esw.clean(contact.get_text(" ")) if contact else ""
        ph = re.search(r"Phone\s*:\s*(.*?)(?:Email|$)", ct)
        if not nm:
            continue
        cons = _esw.clean(k.group(1)) if k else ""
        no, note = _leg_se.seat("ML", m.group(1) if m else None, cons)
        recs.append(_leg.member(MODULE, "ML", "AC", no, _leg_se.name(nm.get_text(" ")), constituency=cons,
                                party=_esw.clean(party.get_text(" ")) if party else "", source=url,
                                phone=ph.group(1) if ph else "", email=_esw.emails(ct), note=note,
                                house="Meghalaya Legislative Assembly (11th)", src_pos=tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, f"page-{p.get('page', 'x')}", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no members in the page"
