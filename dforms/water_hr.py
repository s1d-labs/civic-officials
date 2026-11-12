"""Haryana: Public Health Engineering Department field office telephone directory, phedharyana.gov.in/Telephone_Dir/TelDir.aspx?id=w
(answers only from India). The URL redirects to TelDir?id=w and returns a one-page PDF (SSRS report) "Field Office(s) Telephone
Directory ... as on: DD/MM/YYYY": one line per office, Office Name | Person Name | Mobile No. | Desig. | E-Mail | Tel. (O) | Tel. (R):
15 SE circles ("Ambala Circle") and about 60 EE divisions ("Ambala City PHED", "Hisar PHED No. 2"). The WSSO list (id=c) holds the same
offices, so it is not read. One queue item. "Vacant" / "0000000000" = no officer.
Record ids: dept:water_hr:HR-PHED-<slug of office name>.
"""
import re

import provenance
from dforms import _esw
from dforms._pdftext import page_lines

METHOD = "pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_hr"
URL = "https://phedharyana.gov.in/Telephone_Dir/TelDir.aspx?id=w"
ORG = "Public Health Engineering Department, Haryana"
POSTS = {"SE": ("Superintending Engineer", "circle"), "EE": ("Executive Engineer", "division"), "CE": ("Chief Engineer", "zone"),
         "EIC": ("Engineer-in-Chief", "state"), "SDE": ("Sub Divisional Engineer", "subdivision")}
LINE = re.compile(r"^(?P<office>\S.*?)\s{2,}(?P<name>\S.*?)\s{2,}(?P<mobile>\d{10})\s+(?P<desig>[A-Z]{2,4})\s+(?P<email>\S+@\S+)"
                  r"(?:\s+(?P<tel>.*?))?\s*$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "HR", "india_only": True}}]


def parse_text(pages, url=URL):
    text = "\n".join(pages)
    m = re.search(r"as on:\s*(\d{2})/(\d{2})/(\d{4})", text)
    last = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
    recs, seen = [], set()
    for pn, ln, line in page_lines(pages):
        m = LINE.match(line.rstrip())
        if not m:
            continue
        office = _esw.clean(m.group("office"))
        post, level = POSTS.get(m.group("desig"), (m.group("desig"), "division"))
        name = _esw.clean(m.group("name"))
        tel = re.split(r"\s{3,}", (m.group("tel") or "").strip())
        mobile = m.group("mobile") if m.group("mobile").strip("0") else ""
        key = f"HR-PHED-{_esw.slug(office)}"
        if key in seen:
            continue
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="water", level=level, area=office, post=post,
                                name=None if re.match(r"(?i)vacant", name) else name, phone=_esw.phones(mobile, tel[0] if tel else ""),
                                phone_residence=_esw.phones(*tel[1:]) if len(tel) > 1 else None, email=_esw.emails(m.group("email")),
                                state="HR", office_id=key, org=ORG, source=url, last_updated=last,
                                src_pos=provenance.line_pos(pn, ln, line)))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "teldir-w", r.content, "pdf")]
    if not r.content[:5] == b"%PDF-":
        return [], files, "not a pdf"
    recs = parse_text(_esw.pdf_pages(r.content), p.get("url", URL))
    return recs, files, "" if recs else "no rows"
