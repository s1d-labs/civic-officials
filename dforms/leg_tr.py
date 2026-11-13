"""Tripura: members of the 13th Legislative Assembly (2023-) from the state portal (tripura.gov.in/members-legislative-assembly,
one table, "Page last updated 13-05-2026"). Saved in archive.s1d.me (2026-11-04).

Columns: Name | Constituency | Constituency No. | Party Name. No phone, no email, no address on this page. The assembly's own
site (tripuraassembly.nic.in) refuses connections from Germany and India (2026-11-11), so it is not read.
One queue item = the page. Record ids: dept:leg_tr:TR-AC-<no>.
"""
from dforms import _esw, _leg, _leg_se
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_tr"
URL = "https://tripura.gov.in/members-legislative-assembly"


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "TR", "india_only": False}}]


def parse(html, url):
    recs = []
    for table in _esw.soup(html).find_all("table"):
        tp = []
        for row, pos in zip(_esw.grid(table, pos=tp), tp):
            if len(row) < 4 or not row[2].strip().isdigit():
                provenance.skip_row(row, 'skip: len(row) < 4 or not row[2].strip().isdigit()')
                continue
            nm, cons, no, party = (_esw.clean(x.replace(" | ", " ")) for x in row[:4])
            seat, note = _leg_se.seat("TR", no, cons)
            recs.append(_leg.member(MODULE, "TR", "AC", seat, _leg_se.name(nm), constituency=cons, party=party, source=url,
                                    note=note, house="Tripura Legislative Assembly (13th)", src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "members", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no members in the page"
