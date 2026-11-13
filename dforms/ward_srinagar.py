"""Srinagar Municipal Corporation (smcsrinagar.jk.gov.in): "Know Your Ward Officers", one ward officer (with mobile) per SMC ward.
One page, /Home/KnowWardOfficer (ASP.NET MVC; answers from Germany; saved in archive.s1d.me 2026-11-05). Table: S.No | Ward No. |
Name of Area | Name of Ward Officer | Cell No. The page has 35 wards: these are the SMC's administrative wards (its ward offices), not
the 74 electoral wards of the 2018 delimitation; "ward_kind" says so. Some officers hold two wards (one record with both).
Records: level "ward", post "Ward Officer". Record ids: dept:ward_srinagar:ward-officer:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_srinagar"
BODY, LGD, STATE, DISTRICT = "Srinagar Municipal Corporation", "248156", "JK", "Srinagar"
URL = "https://smcsrinagar.jk.gov.in/Home/KnowWardOfficer"


def items(get=None):
    return [{"key": f"{MODULE}-ward-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    groups = {}
    for head, rows in _ward.header_tables(html, "ward no", "ward officer"):
        for r in rows:
            w = _ward.wards_of(_ward.col(r, "ward no"))
            name = re.sub(r"\s*\((SBI|JBI)\)\s*$", "", _ward.col(r, "ward officer")).strip()
            phone = _ward.col(r, "cell", "mobile", "phone")
            if not w or not (name or phone):
                provenance.skip_row(r, 'skip: not w or not (name or phone)')
                continue
            k = re.sub(r"\D", "", phone) or name.lower()
            g = groups.setdefault(k, {"name": name, "phone": phone, "wards": [], "areas": [], "rank": [], "at": []})
            g["at"].append(r.pos)
            g["wards"] += [x for x in w if x not in g["wards"]]
            g["areas"].append(_ward.col(r, "area"))
            m = re.search(r"\((SBI|JBI)\)", _ward.col(r, "ward officer"))
            if m:
                g["rank"].append(m.group(1))
    seen, recs = set(), []
    for g in groups.values():
        area = "; ".join(f"Ward {w} {a}".strip() for w, a in zip(g["wards"], g["areas"]))
        recs.append(_ward.record(MODULE, f"ward-officer:{_esw.slug(g['name']) or 'n'}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="ward", area=area, post="Ward Officer", name=g["name"], phone=g["phone"],
                                 wards=g["wards"], wing="administration", ward_kind="SMC administrative ward (35), not electoral",
                                 cadre=" ".join(sorted(set(g["rank"]))) or None, source=p["url"],
                                 src_pos={"rows": g["at"], "note": "one officer summed over these table rows"}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "ward-officers", r.content)], "" if recs else "no ward officer table"
