"""Jamnagar Municipal Corporation (mcjamnagar.com): its civic centres, the area offices where citizens pay taxes and file
complaints (Main Office, Saru Section, Ranjit Nagar, Gulab Nagar, Green City, Samarpan). One page, /Services/trn_civiccentre.aspx
(ASP.NET; answers from Germany; archive.s1d.me copy saved 2026-11-06, live check 2026-11-11; the page footer shows "Last Update
:24/08/2026"): one table CIVIC CENTER NAME | ADDRESS | CONTACT NO | LOCATION (all cells are <th>). The page names no officers and
no wards. The site's department pages (Departments/*.aspx) and the RTI chapters name no ward staff, and the RTI PDFs are set in a
legacy Gujarati font (no Unicode text). Records: level "zone" (an office over a part of the city), post "Civic Centre".
Record ids: dept:ward2n_jamnagar:<centre slug>:civic-centre.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_jamnagar"
BODY, LGD, STATE, DISTRICT = "Jamnagar Municipal Corporation", "251133", "GJ", "Jamnagar"
URL = "https://www.mcjamnagar.com/Services/trn_civiccentre.aspx?SID=INFO"


def items(get=None):
    return [{"key": f"{MODULE}-civic-centres", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    seen, recs = set(), []
    m = re.search(r"Last\s*Update\s*:\s*(\d{2})/(\d{2})/(\d{4})", html)
    updated = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
    for head, rows in _ward.header_tables(html, "civic center name", "contact"):
        for r in rows:
            name = _ward.col(r, "civic center name")
            if not re.search(r"(?i)civic\s*cent(er|re)", name) or re.search(r"(?i)civic center name", name):
                provenance.skip_row(r, 'skip: not re.search(r"(?i)civic\\s*cent(er|re)", name) or re.search(r"(?i)...')
                continue
            area = re.sub(r"(?i)\s*civic\s*cent(er|re)\s*$", "", name).strip() or name
            recs.append(_ward.record(MODULE, f"{_esw.slug(area)}:civic-centre", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=f"{area} Civic Centre", post="Civic Centre",
                                     phone=_ward.col(r, "contact"), address=_ward.col(r, "address"), wing="administration",
                                     last_updated=updated, source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "civic-centres", r.content)], "" if recs else "no civic centre table"
