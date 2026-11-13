"""Raipur Municipal Corporation: the revenue (property tax) coordinator of each of its 10 zones. The corporation's own site
(nagarnigamraipur.nic.in) does not answer (from Germany or from India, 2026-11-11); its property tax system mcraipur.in (PTS, Yii)
has a contact page, /site/contactus, with the table "Zone Wise Contact List": Zone Number | Revenue Coordinator | Mobile Number
(answers from Germany; live sample 2026-11-11, not in archive.s1d.me). The page gives no zone names and no ward lists.
Records: level "zone". Ids: dept:ward2n_raipur:zone-<n>:revenue-coordinator.
"""
from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_raipur"
BODY, LGD, STATE, DISTRICT = "Raipur Municipal Corporation", "250653", "CG", "Raipur"
URL = "https://mcraipur.in/site/contactus"


def items(get=None):
    return [{"key": f"{MODULE}-zone-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "zone", "coordinator"):
        for r in rows:
            z = _ward.col(r, "zone")
            if not z.isdigit():
                provenance.skip_row(r, 'skip: not z.isdigit()')
                continue
            recs.append(_ward.record(MODULE, f"zone-{int(z)}:revenue-coordinator", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=f"Zone {int(z)}", zone=f"Zone {int(z)}",
                                     post="Revenue Coordinator (Property Tax)", name=_ward.col(r, "coordinator"),
                                     phone=_ward.col(r, "mobile"), wing="revenue", source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contactus", r.content)], "" if recs else "no zone contact table"
