"""Municipal Corporation Pathankot (mcpathankot.punjab.gov.in, Punjab e-Nigam MC site): its staff directory, from the PDF
"Municipal Corporation Pathankot Staff Directory" (menu link on the home page; e-Nigam Azure store; "UPTO 26.02.2026", 1 page,
60 rows; live sample 2026-11-13, answers from abroad).
Rows: Sr.No. | Full Name | Designation | Mobile No. Commissioner, Joint Commissioner, engineers, junior engineers, health and
sanitation officers, chief sanitary and sanitary inspectors, town planners, draftsmen and building inspectors by zone, clerks.
Records: a row whose designation names zones ("DRAFTSMAN (ZONE 2,4)", "... BUILDING INSPECTOR ZONE 1,2 &4") -> level "zone"
(zone = "Zones 2, 4", every zone named in the cell); other rows -> level "body". The PDF does not say which wards a zone holds.
Record ids: dept:ward3_pathankot:<post slug>:<mobile or name slug>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_northb as h

METHOD = "pdf text (pypdf layout) rows"     # source trail (provenance.py)

MODULE = "ward3_pathankot"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Pathankot", "248256", "PB", "Pathankot"
HOME = "https://mcpathankot.punjab.gov.in/Home"
PDF = ("https://enigambackuprestore.blob.core.windows.net/securefilestructure/MC/Pathankot/MCSubMenu/pdf/"
       "linkpdf_2_26_2026_6_904.MC%20STAFF%20DIRECTORY%20UPTO%2026.02.2026.pdf")
LINK = re.compile(r"(?i)staff\s*directory")
POST = re.compile(r"\b(COMMISSIONER|JOINT|ASSISTANT|SECRETARY|CORPORATION|JUNIOR|SENIOR|MUNICIPAL|HEALTH|CHIEF|SANITARY|"
                  r"INSPECTOR|DRAFTSMAN|HEAD|CLERK|ACCOUNTANT|SUB\s+FIRE|SUPERIENTENDENT|SUPERINTENDENT)\b")
ZONE = re.compile(r"(?i)zone\s*((?:\d\s*(?:[,&]|and)?\s*)+)")


def items(get=None):
    return [{"key": f"{MODULE}-staff", "payload": {"reader": MODULE, "url": HOME, "pdf": PDF, "state": STATE}}]


def zones_of(text):
    out = []
    for m in ZONE.finditer(text):
        out += [z for z in re.findall(r"\d", m.group(1)) if z not in out]
    return sorted(out)


def parse(pages, p):
    seen, recs = set(), []
    for r in h.rows(pages, post=POST):
        post = _esw.clean(" ".join(x for x in (r["mid"], r["mid_extra"], r["name_extra"]) if x)).strip(" -")
        if not post:
            continue
        zones = zones_of(post)
        level = "zone" if zones else "body"
        area = (("Zone " if len(zones) == 1 else "Zones ") + ", ".join(zones)) if zones else BODY
        key = f"{_esw.slug(post)[:60]}:{re.sub(r'[^0-9]', '', r['phone']) or _esw.slug(r['name'])}"
        recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area,
                                 zone=area if zones else None, post=post, name=r["name"],
                                 phone=r["phone"] if re.search(r"\d{6}", r["phone"]) else "", source=p.get("pdf") or PDF,
                                 src_pos=provenance.line_pos(r["page"], r["line"], r["line_text"], row=int(r["sr"]))))
    return recs


def fetch(p, get):
    url = p.get("pdf") or PDF
    home = get(p["url"]) if p.get("url") else None
    if home is not None:
        for a in _esw.soup(home.text).find_all("a", href=True):
            if LINK.search(a.get_text(" ")) and a["href"].lower().endswith(".pdf"):
                url = a["href"].replace(" ", "%20")
                break
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "staff-directory", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, dict(p, pdf=url))
    return _ward.tag(recs, r, url, METHOD), files, "" if recs else "no rows"
