"""Municipal Corporation Patiala (mcpatiala.punjab.gov.in, the Punjab e-Nigam MC site, mcid=1002): its officers and the
ward-wise sanitary inspectors, from the PDF "MC PATIALA EMPLOYEES DETAIL" (menu link on the home page, a Word export in the
e-Nigam Azure store enigambackuprestore.blob.core.windows.net; file of 2026-08-10, 3 pages, 73 rows; live sample 2026-11-13,
home page in archive.s1d.me (pool vantage, 2026-11-11): answers from abroad).
Rows: Sr. No. | Name (post under the name for rows 56-73) | Designation, or the ward list / branch | Mobile No.
  "Ward No 1 to 9 & 59" in the second column -> level "ward" with those wards (sanitary inspectors and supervisors);
  every other row -> level "body" (commissioners, engineers, JEs, town planning, superintendents, fire officers).
The home page link is followed when it is there (the file name changes with each upload); else the known file is read.
Record ids: dept:ward3_patiala:<post slug>:<mobile or name slug>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_northb as h

METHOD = "pdf text (pypdf layout) rows"     # source trail (provenance.py)

MODULE = "ward3_patiala"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Patiala", "248399", "PB", "Patiala"
HOME = "https://mcpatiala.punjab.gov.in/Home/Index?mcid=1002&lng="
PDF = ("https://enigambackuprestore.blob.core.windows.net/securefilestructure/MC/Patiala/MCSubMenu/pdf/"
       "linkpdf_8_10_2026_27_553.mc%20patiala%20officer.pdf")
LINK = re.compile(r"(?i)employees?\s*detail|officers?\s*detail")
AREA = re.compile(r"(?i)^(ward\b|wards\b|w\.?\s*no)|\bbranch\b|fire\s*brigade|office\s*work")


def items(get=None):
    return [{"key": f"{MODULE}-employees", "payload": {"reader": MODULE, "url": HOME, "pdf": PDF, "state": STATE}}]


def parse(pages, p):
    seen, recs = set(), []
    for r in h.rows(pages):
        mid, nx, mx = r["mid"], r["name_extra"], r["mid_extra"]
        wards = _ward.wards_of(mid) if re.match(r"(?i)ward", mid) else []
        if AREA.search(mid) and nx:
            post, section = nx, (mid if not wards else None)
        else:
            post, section = mid, _esw.clean(" ".join(x for x in (nx, mx) if x)) or None
        if not post:
            continue
        level = "ward" if wards else "body"
        area = ("Ward " if len(wards) == 1 else "Wards ") + ", ".join(wards) if wards else BODY
        key = f"{_esw.slug(post)}:{re.sub(r'[^0-9]', '', r['phone'].split(',')[0]) or _esw.slug(r['name'])}"
        recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area,
                                 post=post, name=r["name"], phone=r["phone"], wards=wards, section=section,
                                 wards_text=mid if wards else None, source=p.get("pdf") or PDF,
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
    files = [_esw.keep(MODULE, "employees", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, dict(p, pdf=url))
    return _ward.tag(recs, r, url, METHOD), files, "" if recs else "no rows"
