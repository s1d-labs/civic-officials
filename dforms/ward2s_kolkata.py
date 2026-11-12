"""Kolkata Municipal Corporation (www.kmcgov.in, the KMCPortal JSP site): the Solid Waste Management (SWM-I) officers of its 16
boroughs. The KMC home page (/KMCPortal/jsp/KMCPortalHome1.jsp) links the PDF
/KMCPortal/downloads/DETAILS_OF_DEPUTY_DIRECTORS_ASSISTANT_DIRECTORS_AND_COMPACTOR_STATIONS.pdf (6 pages, 14 MB, file date
2026-10-24). Page 1 is text: "DETAILS OF DEPUTY DIRECTORS AND ASSISTANT DIRECTORS UNDER S.W.M.-I, K.M.C.", columns SL. NO | NAME |
DESIGNATION | DEPARTMENT | BOROUGH NO. | MOBILE NO.: 2 Deputy Directors (boroughs I to VIII, IX to XVI) and 18 Assistant Directors
(one or two per borough). In pdftotext -layout each row is a block between blank lines, the designation split over the line
above and the line below the numbered line, a second mobile on the next line. Pages 2-6 (the compactor stations) are images.
Answers from Germany (live 200 on 2026-11-11). Not in archive.s1d.me. The borough-to-ward mapping is not in the file, so records
have no "wards" key; zone = "Borough <roman>". KMC's own borough office and ward pages moved to kmc.wb.gov.in
(contact-us/boroughOffices, knowYourWard), which gave no answer from Germany or India on 2026-11-11.
Records: level "zone". Record ids: dept:ward2s_kolkata:<borough slug>:<post slug>:<name slug>.
"""
import re

import provenance
from dforms import _esw, _ward

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_kolkata"
BODY, LGD, STATE, DISTRICT = "Kolkata Municipal Corporation", "250299", "WB", "Kolkata"
URL = "https://www.kmcgov.in/KMCPortal/downloads/DETAILS_OF_DEPUTY_DIRECTORS_ASSISTANT_DIRECTORS_AND_COMPACTOR_STATIONS.pdf"
ROW = re.compile(r"^\s*(\d{1,2})\.\s+(\S.*?)\s{2,}(.*)$")
ROMAN = r"(?:XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)"
BOROUGH = re.compile(rf"\b({ROMAN}(?:\s+TO\s+{ROMAN})?)\b")
PHONE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-swm-borough-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(pages, p):
    seen, recs = set(), []
    text = "\n".join(pages[:2])
    at = _ward.joined_at(pages[:2])
    spans, last = [], 0                 # the blocks of re.split(r"\n\s*\n", text), with where each starts
    for m in re.finditer(r"\n\s*\n", text):
        spans.append((last, m.start()))
        last = m.end()
    spans.append((last, len(text)))
    for b0, b1 in spans:
        block = text[b0:b1]
        lines = [ln for ln in block.split("\n") if ln.strip()]
        row = next((ROW.match(ln) for ln in lines if ROW.match(ln)), None)
        if not row:
            continue
        gi = text.count("\n", 0, b0) + next(i for i, ln in enumerate(block.split("\n")) if ROW.match(ln))
        pos = provenance.line_pos(at[gi][0], at[gi][1], row.group(0), lines_in_block=len(lines)) if gi < len(at) else None
        name = row.group(2).strip()
        rest = re.sub(r"S\.W\.M\.-I", " ", row.group(3))
        words = " ".join(re.sub(r"S\.W\.M\.-I|\d|/", " ", ln) for ln in lines if not ROW.match(ln))
        post = " ".join(w for w in words.split() if re.fullmatch(r"(?i)(deputy|assistant|director(-[iv]+)?)", w)).title()
        post = re.sub(r"-([iv]+)\b", lambda m: "-" + m.group(1).upper(), post, flags=re.I)
        bm = BOROUGH.search(rest.replace(name, " "))
        phones = PHONE.findall(block)
        if not post or not bm:
            continue
        b = bm.group(1)
        zone = f"Boroughs {b.replace(' TO ', ' to ')}" if " TO " in b else f"Borough {b}"
        post = f"{post} (Solid Waste Management)"
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:{_esw.slug(post)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone, post=post, name=name,
                                 phone=", ".join(phones), wing="sanitation", source=p["url"], src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    pages = _ward.layout_pages(r.content)
    recs = parse(pages, p)
    return recs, [_esw.keep(MODULE, "swm-borough-officers", r.content, "pdf")], "" if recs else "no officer rows on page 1"
