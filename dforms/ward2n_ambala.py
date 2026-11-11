"""Municipal Corporation Ambala (mcambala.in): its officers, engineers and sanitary staff, from
the page "Office Directory" (/directory/office-directory; HKCL template; live sample 2026-11-11, answers from Germany; not in
archive.s1d.me). One table per branch: Sr. No. | Name | Designation | Contact No. | Email ID. The page names no wards or zones: records are at level "body". Parser: dforms/ward2n_sonipat.parse.
Record ids: dept:ward2n_ambala:hq:<post slug>:<name slug>.
"""
from dforms import _esw, ward2n_sonipat

MODULE = "ward2n_ambala"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Ambala", "248491", "HR", "Ambala"
URL = "https://mcambala.in/directory/office-directory"


def items(get=None):
    return [{"key": f"{MODULE}-office-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    return ward2n_sonipat.parse(html, p, module=MODULE, body=BODY, lgd=LGD, district=DISTRICT)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "office-directory", r.content)], "" if recs else "no directory table"
