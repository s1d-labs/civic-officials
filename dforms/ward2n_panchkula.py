"""Municipal Corporation Panchkula (mcpanchkula.in): its officers and engineers, from the page "Administrative Officers"
(/Administrative_Officer.aspx; ASP.NET; in archive.s1d.me, saved 2026-11-06; the page shows no date). One table: Sr. No. |
Name(Sh./Smt.) | Designation | Contact Number (Commissioner, Joint Commissioners I-II, EEs I-II, AEs I-II, JEs, CSI). The page
names no wards: records are at level "body". The ward-wise sanitation list (/PDF/Sanitation.pdf: ward, sector, supervisor, ASI)
is not read yet: its cells wrap and the ASI column is not aligned. Parser: dforms/ward2n_sonipat.parse.
Record ids: dept:ward2n_panchkula:hq:<post slug>:<name slug>.
"""
from dforms import _esw, ward2n_sonipat

METHOD = "pdf text (pypdf) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_panchkula"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Panchkula", "248489", "HR", "Panchkula"
URL = "https://mcpanchkula.in/Administrative_Officer.aspx"


def items(get=None):
    return [{"key": f"{MODULE}-administrative-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    return ward2n_sonipat.parse(html, p, module=MODULE, body=BODY, lgd=LGD, district=DISTRICT)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "administrative-officers", r.content)], "" if recs else "no officer table"
