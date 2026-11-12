"""Puducherry: members of the 16th Legislative Assembly (2026-) with address, mobile and official email, from the UT portal
(py.gov.in/mlas, one page, "Page last updated 05-11-2026"). Saved in archive.s1d.me (2026-11-07).

Each block: "Member of Legislative Assembly, <Constituency>, Puducherry" (h2), name (h3), "Address :", "Mobile :",
"Email :" (written x[at]py[dot]gov[dot]in). No AC number: the name decides. No party, no office address. The 3 nominated
members are not on the page. One queue item = the page. Record ids: dept:leg_py:PY-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_se

METHOD = "html page (one block per <h2> member heading)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_py"
URL = "https://py.gov.in/mlas"
ALIAS = {"kamarajnagar": "kamrajnagar", "neravytrpattinam": "neravytrpattin", "orleanpeth": "orleampeth"}


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "PY", "india_only": False}}]


def parse(html, url):
    recs = []
    for k, h2 in enumerate(_esw.soup(html).find_all("h2"), 1):
        m = re.match(r"Member of Legislative Assembly,\s*(.+?),\s*(?:Puducherry|Pondicherry)\s*$", _esw.clean(h2.get_text(" ")), re.I)
        if not m:
            continue
        box = h2.find_parent("div")
        h3 = box.find("h3") if box else None
        if not h3:
            continue
        fields = {}
        for p in box.find_all("p"):
            t = re.sub(r",(\s*,)+", ",", _esw.cell_text(p).replace(" | ", ", "))
            f = re.match(r"(Address|Mobile|Phone|Email)\s*:\s*(.*)", t, re.I)
            if f:
                fields[f.group(1).lower()] = f.group(2).strip()
        cons = _esw.clean(m.group(1))
        no, note = _leg_se.seat("PY", None, cons, alias=ALIAS)
        recs.append(_leg.member(MODULE, "PY", "AC", no, _leg_se.name(h3.get_text(" ")), constituency=cons, source=url,
                                mobile=fields.get("mobile", "") + (", " + fields["phone"] if fields.get("phone") else ""),
                                email=fields.get("email", ""), residence_address=fields.get("address", ""), note=note,
                                house="Puducherry Legislative Assembly (16th)", src_pos={"selector": "h2", "h2": k}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "mlas", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no members in the page"
