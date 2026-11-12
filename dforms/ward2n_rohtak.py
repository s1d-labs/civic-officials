"""Municipal Corporation Rohtak (mcrohtak.in): its officers, engineers and sanitary staff, from
the page "Officer Directory" (/index.php/officer-directory; HKCL template; live sample 2026-11-11, answers from Germany; archive.s1d.me
has only /elected-members-0). One table: Sr. No. | Name of Officer/Official | Designation | Mob. No.. The page names no wards or zones: records are at level "body". Parser: dforms/ward2n_sonipat.parse.
Record ids: dept:ward2n_rohtak:hq:<post slug>:<name slug>.
"""
from dforms import _esw, ward2n_sonipat

METHOD = "pdf text (pypdf) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_rohtak"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Rohtak", "248557", "HR", "Rohtak"
URL = "https://mcrohtak.in/index.php/officer-directory"


def items(get=None):
    return [{"key": f"{MODULE}-officer-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    return ward2n_sonipat.parse(html, p, module=MODULE, body=BODY, lgd=LGD, district=DISTRICT)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "officer-directory", r.content)], "" if recs else "no directory table"
