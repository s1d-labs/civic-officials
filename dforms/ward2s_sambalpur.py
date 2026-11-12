"""Sambalpur Municipal Corporation (smcsambalpur.nic.in, WordPress on the NIC Odisha platform): the ward officer of each of its 41
wards. One page, /ward-officer-list/ ("SMC Ward Officer"): one table Ward No | Name of Ward Officer | Phone No, one row per ward
(41 rows). The page shows no "Last Updated" date. Answers from Germany and India (live 200 from Germany 2026-11-11; saved in
archive.s1d.me 2026-11-08). The other officer page (/smc-officers-directory/: Commissioner, 6 Deputy Commissioners, engineers) does not
say which zone or ward each officer holds; the whoswho task reads it.
Records: level "ward", post "Ward Officer", wards = [the ward]. Record ids: dept:ward2s_sambalpur:w<ward>:ward-officer:<name slug>.
"""
from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_sambalpur"
BODY, LGD, STATE, DISTRICT = "Sambalpur Municipal Corporation", "253100", "OD", "Sambalpur"
URL = "https://smcsambalpur.nic.in/ward-officer-list/"


def items(get=None):
    return [{"key": f"{MODULE}-ward-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "ward", "officer"):
        for r in rows:
            ward = _ward.wards_of(_ward.col(r, "ward no"))
            name, phone = _ward.col(r, "name"), _ward.col(r, "phone")
            if len(ward) != 1 or not (name or phone):
                continue
            w = ward[0]
            recs.append(_ward.record(MODULE, f"w{w}:ward-officer:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="ward", area=f"Ward {w}", post="Ward Officer",
                                     name=name, phone=phone, wards=[w], source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "ward-officer-list", r.content)], "" if recs else "no ward officer table"
