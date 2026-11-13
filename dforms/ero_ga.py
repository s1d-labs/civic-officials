"""Goa: the ERO of each of the 40 assembly constituencies, from the CEO Goa page ceogoa.nic.in/appln/UIL/ERO.aspx. Answers only from
India (Germany times out). Plain GET, but slow: the server can take 60-100 s (get() waits 90 s; the hub retries a failed item).

One table per district (headings NORTH GOA, SOUTH GOA, KUSHAVATI DISTRICT): "NN-AC Name", Name, Designation, Mobile, Office No. / Fax,
Email ([at]/[dot]), Office Address. The page shows no date. AERO.aspx and DEO.aspx are sister pages, not read here. One queue item.
Record ids: dept:ero_ga:GA-AC-<no>:ero.
"""
import re

from dforms import _esw
from dforms._water import pgrid
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_ga"
URL = "https://ceogoa.nic.in/appln/UIL/ERO.aspx"
AC = re.compile(r"^\s*(\d{1,2})\s*[-–.]\s*(.+?)\s*$")
DISTRICT = re.compile(r"^\s*([A-Z ]+?)\s+DISTRICT\s*$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "GA", "india_only": True}}]


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs = {}
    for t in soup.find_all("table"):
        district = None
        for h in t.find_all_previous(string=DISTRICT, limit=1):
            district = DISTRICT.match(h).group(1).title()
        rows = pgrid(t)
        for row in rows[1:]:
            rp, row = row.pos, row + [""] * (7 - len(row))
            m = AC.match(row[0])
            if not m:
                provenance.skip_row(row, 'skip: not m')
                continue
            no, ac = int(m.group(1)), f"GA-AC-{int(m.group(1))}"
            recs[f"{ac}:ero"] = _esw.record(MODULE, f"{ac}:ero", dept="elections", level="ac", area=f"{no} - {m.group(2)}",
                                            post="Electoral Registration Officer", designation=row[2], name=row[1],
                                            phone=_esw.phones(row[3], row[4]), email=_esw.emails(row[5]), address=row[6],
                                            state="GA", district=district, office_id=ac, source=url, src_pos=rp)
    return list(recs.values())


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "ero", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
