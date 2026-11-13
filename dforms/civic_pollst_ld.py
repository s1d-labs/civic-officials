"""Lakshadweep: every polling station of the one assembly constituency (1-Lakshadweep, 64 parts on 2026-11-11), from the CEO's page
ceolakshadweep.gov.in/polling-stations: Sl.No, Part No, Part Name (the building, e.g. "Govt. Senior Basic School, Bitra Island"),
Locality of Polling Station (the island), Polling Area ("Entire Part 1"). No BLO on this page (the CEO's ero-aero-blo page lists
BLO names without part numbers). The page answers from abroad. One queue item.
Record ids: dept:civic_pollst_ld:LD-1-<part>. Layer "pollst".
"""
from dforms import _esw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_pollst_ld"
URL = "https://ceolakshadweep.gov.in/polling-stations"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "LD"}}]


def parse(html, url=URL):
    recs, seen = [], set()
    for table in _esw.soup(html).find_all("table"):
        gp = []
        rows = _esw.grid(table, pos=gp)
        if not rows or not any("part" in c.lower() for c in rows[0]):
            continue
        head = [c.lower() for c in rows[0]]
        col = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("part no", "part name", "locality", "area")}
        for gi, r in enumerate(rows[1:], 1):
            get = lambda k: r[col[k]] if col[k] is not None and col[k] < len(r) else ""  # noqa: E731
            part, station = get("part no"), get("part name")
            if not part.isdigit() or not station or part in seen:
                provenance.skip_row(r, 'skip: not part.isdigit() or not station or part in seen')
                continue
            seen.add(part)
            key = f"LD-1-{part}"
            recs.append(_esw.record(MODULE, key, dept="elections", level="polling_station", area=station, state="LD",
                                    district="Lakshadweep", office_id=key, source=url, layer="pollst", ac_no=1,
                                    ac_name="Lakshadweep", part_no=part, station=station, locality=get("locality"),
                                    polling_area=get("area"), src_pos=gp[gi]))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url", URL))
    return recs, [_esw.keep(MODULE, "polling-stations", r.content)], "" if recs else "no rows"
