"""Vapi Municipal Corporation (vapicity.in; corporation since 2025): the Sub Sanitary Inspector (SSI) of each of its wards, with
mobile. One page, /contactdetailsofsubsanitaryinspectors (answers from Germany; live sample 2026-11-11, not in archive.s1d.me), in
Gujarati: one table અ. નં | કર્મચારીનું નામ અને હોદ્દો (name and post, "..., SSI") | સુપરવાઈઝર (the column holds the mobile) |
વોર્ડ નંબર (ward). Digits are Gujarati (converted). A serial cell like "૧૦, ૧૧ વોર્ડ" names the wards that the SSI covers.
Names stay in Gujarati (name and name_regional); post is English, post_regional as written. Records: level "ward".
Record ids: dept:ward2n_vapi:ward-<n>:ssi.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_vapi"
BODY, LGD, STATE, DISTRICT = "Vapi Municipal Corporation", "251264", "GJ", "Valsad"
URL = "https://vapicity.in/contactdetailsofsubsanitaryinspectors"
GU = str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789")


def items(get=None):
    return [{"key": f"{MODULE}-ssi", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    seen, recs = set(), []
    for t in _esw.soup(html).find_all("table"):
        g = _esw.grid(t)
        if not g or not any("વોર્ડ" in c for c in g[0]):
            continue
        for r in g[1:]:
            if len(r) < 4:
                continue
            sr, who, phone, ward = (_esw.clean(c).translate(GU) for c in r[:4])
            wards = _ward.wards_of(ward)
            if "વોર્ડ" in sr:
                wards = list(dict.fromkeys(_ward.wards_of(sr.replace("વોર્ડ", "")) + wards))
            if not wards:
                continue
            name, _, post_regional = who.partition(",")
            name = _esw.clean(name)
            recs.append(_ward.record(MODULE, f"ward-{wards[0]}:ssi", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                     level="ward", area=f"Ward {wards[0]}", wards=wards, post="Sub Sanitary Inspector",
                                     post_regional=_esw.clean(post_regional) or None, name=name, name_regional=name or None,
                                     phone=phone, wing="sanitation", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "ssi", r.content)], "" if recs else "no SSI table"
