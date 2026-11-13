"""Municipal Corporation S.A.S. Nagar (Mohali) (mcmohali.punjab.gov.in, Punjab e-Nigam MC site, mcid=1001): its officers by
branch, with the zone (1-4) of each engineer, junior engineer, chief sanitary inspector and sanitary inspector, from the PDF
"List of official" (menu link "Employees" on the home page; e-Nigam Azure store; file of 2026-09-23, 3 pages, 74 rows; live
sample 2026-11-13, answers from abroad).
Rows: Sr. No. | Name of Officer | Designation | Branch Name | Phone No. The Branch cell often has several lines, centred on the
row; lines above a row cannot be told apart from the lines under the row before (pypdf and pdftotext both), so only the row's
own line and the one line right under it are read as its branch (the zone sits there: "Water Supply/Sewer/Storm" /
"(Zone no. 1 & 2)"). Admin rows with long branch lists therefore keep only part of them. Full-width section lines
(Administration, Engineering Branch, Sanitation Branch ...) start left of the Branch column.
Records: a row whose branch names zones ("Eng: Branch (Zone no: 1)", "Sanitation(Zone no: 1 & 2)") -> level "zone" (area
"Zone 1" / "Zones 1, 2", zone = the same); other rows -> level "body". The PDF does not say which wards each zone holds: no
wards key. pypdf sometimes puts two lines of a Branch cell on one line ("Sanitation(Zone no:  Branch3)"); the zone numbers are
read after the word "Branch" is taken out. Record ids: dept:ward3_mohali:<post slug>:<mobile or name slug>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_northb as h

METHOD = "pdf text (pypdf layout) rows, centred cells"     # source trail (provenance.py)

MODULE = "ward3_mohali"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation S.A.S. Nagar (Mohali)", "248325", "PB", "S.A.S Nagar"
HOME = "https://mcmohali.punjab.gov.in/Home"
PDF = ("https://enigambackuprestore.blob.core.windows.net/securefilestructure/MC/Mohali/MCSubMenu/pdf/"
       "linkpdf_9_23_2026_36_821.List%20of%20official.pdf")
LINK = re.compile(r"(?i)^\s*employees?\s*$|list\s*of\s*official")
ROW = re.compile(r"^\s*(\d{1,3})\.\s+(\S.*?)\s*$")
BRANCH_X = 70           # Branch column starts right of this; section lines start left of it
ZONE = re.compile(r"(?i)zone\s*no\W*((?:\d\s*(?:[,&]|and)?\s*)+)")


def items(get=None):
    return [{"key": f"{MODULE}-officials", "payload": {"reader": MODULE, "url": HOME, "pdf": PDF, "state": STATE}}]


def zones_of(text):
    t = re.sub(r"(?i)branch", " ", text)
    out = []
    for m in ZONE.finditer(t):
        out += [z for z in re.findall(r"\d", m.group(1)) if z not in out]
    return out


def table(pages):
    """[dict(sr, parts, phone, next, section, page, line, line_text)]: next = the first non-blank line under the row when it is a
    Branch-column line (not a row, not a section line)."""
    out, section = [], None
    for pn, pg in enumerate(pages, 1):
        cur = None
        for ln, raw in enumerate(h.lines_of(pg), 1):
            if not raw.strip():
                continue
            if re.search(r"(?i)name\s+of\s+officer|list\s+of\s+officers|municipal\s+corporation", raw):
                cur = None
                continue
            m = ROW.match(raw)
            if m:
                ph = h.PHONE_END.search(raw)
                body = raw[:ph.start()] if ph else raw
                parts = [(x.start() + m.start(2), _esw.clean(x.group(0)))
                         for x in re.finditer(r"\S+(?:\s{1,3}\S+)*", body[m.start(2):])]
                cur = {"sr": m.group(1), "parts": parts, "phone": ph.group(1) if ph else "", "section": section, "next": "",
                       "page": pn, "line": ln, "line_text": raw}
                out.append(cur)
                continue
            if len(raw) - len(raw.lstrip()) < BRANCH_X:
                section = _esw.clean(raw)
            elif cur is not None:
                cur["next"] = _esw.clean(raw)
            cur = None
    return out


def parse(pages, p):
    seen, recs = set(), []
    for r in table(pages):
        parts = r["parts"]
        name = parts[0][1] if parts else ""
        post = parts[1][1] if len(parts) > 1 else ""
        branch_main = " ".join(t for x, t in parts[2:])
        if len(parts) == 2 and parts[1][0] >= BRANCH_X:       # no designation: the second part is the branch
            post, branch_main = "", parts[1][1]
        branch = _esw.clean(" ".join(x for x in (branch_main, r["next"]) if x))
        if not post:
            post = r["section"] or "Officer"
        zones = zones_of(branch)
        level = "zone" if zones else "body"
        area = (("Zone " if len(zones) == 1 else "Zones ") + ", ".join(zones)) if zones else BODY
        key = f"{_esw.slug(post)}:{re.sub(r'[^0-9]', '', r['phone']) or _esw.slug(name)}"
        recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area,
                                 zone=area if zones else None, post=post, name=re.sub(r",\s*$", "", name), phone=r["phone"],
                                 branch=branch or None, section=r["section"], source=p.get("pdf") or PDF,
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
    files = [_esw.keep(MODULE, "officials", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, dict(p, pdf=url))
    return _ward.tag(recs, r, url, METHOD), files, "" if recs else "no rows"
