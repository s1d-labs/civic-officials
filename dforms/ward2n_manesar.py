"""Municipal Corporation Manesar (mcmanesar.in): its officers, engineers and sanitary staff, from
the page "Officers Directory" (/index.php/officers-directory; HKCL template; live sample 2026-11-11, answers from Germany; archive.s1d.me
has only /index.php/elected-members). One table: Sr. No. | Name of Officer | Designation | Contact No. | Mail Id. The page names no wards or zones: records are at level "body". Parser: dforms/ward2n_sonipat.parse.
Record ids: dept:ward2n_manesar:hq:<post slug>:<name slug>.
"""
from dforms import _esw, ward2n_sonipat

METHOD = "pdf text (pypdf) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_manesar"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Manesar", "297117", "HR", "Gurugram"
URL = "https://mcmanesar.in/index.php/officers-directory"


def items(get=None):
    return [{"key": f"{MODULE}-officers-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    return ward2n_sonipat.parse(html, p, module=MODULE, body=BODY, lgd=LGD, district=DISTRICT)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "officers-directory", r.content)], "" if recs else "no directory table"
