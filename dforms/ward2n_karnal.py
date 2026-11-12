"""Municipal Corporation Karnal (mckarnal.co.in): its officers, engineers and sanitary inspectors, from the page "Office Directory"
(/index.php/office-directory; HKCL template, the same table as Sonipat without the Branch and Ward columns: S/N | Name of Employee |
Designation | Mobile No.; in archive.s1d.me, saved 2026-11-11; the site footer shows "Last updated: 5/11/2026"). The page names no
wards or zones: all records are at level "body" (Joint Commissioners, EEs, AEs, JEs, CSI, sanitary inspectors, ZTO, Assistant Town
Planner). The ward-wise sweeper PDFs (/sites/default/files/2026-07/Ward NN.pdf) answered 404 in the archive. Parser:
dforms/ward2n_sonipat.parse. Record ids: dept:ward2n_karnal:hq:<post slug>:<name slug>.
"""
from dforms import _esw, ward2n_sonipat

METHOD = "pdf text (pypdf) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_karnal"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Karnal", "248517", "HR", "Karnal"
URL = "https://mckarnal.co.in/index.php/office-directory"


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
