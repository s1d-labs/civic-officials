"""Karnataka: GESCOM (Kalaburagi) office contacts, gescom.karnataka.gov.in (India only: no answer from Germany; samples fetched
from India 2026-11-11; archive.s1d.me holds only cut copies of these pages). The KA (CeG/KRN 4.0) template, menu "CONTACT US":
- /198/o&m-division/en  "O&M Division": one table Place/District | Designation | Mobile, 17 O&M divisions (Executive Engineer El;
  Shorapur has an AEE). No names.
- /163/o-and-m-zones/en and /200/o-and-m-circles/en: the same template (the circles page answered HTTP 500 to the archive crawl);
  read with the same table rule (level from the page).
- /uploads/Mail%20ids_1763634117.pdf "Email IDs" (4 pages, text layer): blocks "Sl no | <block> | Webmail ID | Gmail ID" for the
  corporate office (36), zones (2), circles (5), divisions (16), sub-divisions (54), C&M divisions (6), vigilance (9). E-mails only.
No section offices and no officer names are published. The emergency-contact page on gescomglb.org is a complaint form (Angular
app that needs a consumer account number), not an office list.
Records: dept:power2_gescom:<page>:<level>:<office>.
"""
import re

from bs4 import BeautifulSoup

import provenance
from dforms._power import tr_pos, Out, cells, clean, email, pdf_pages, phone, raw

METHOD = "html table + pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_gescom"
BASE = "https://gescom.karnataka.gov.in/"
PAGES = {"divisions": ("198/o&m-division/en", "division"), "zones": ("163/o-and-m-zones/en", "zone"),
         "circles": ("200/o-and-m-circles/en", "circle"), "emails": ("uploads/Mail%20ids_1763634117.pdf", None)}
BLOCKS = (("corporate", "state"), ("zone", "zone"), ("circle", "circle"), ("subdivision", "subdivision"),
          ("construction", "division"), ("vigilance", "state"), ("division", "division"))
PREFIX = re.compile(r"^(CEE|SEE|EEE|AEE|EE|SE|CE)(?=[A-Z_\- ]|$)", re.I)


def parse_table(html, level, url):
    out = Out(MODULE, "KA", url, discom="GESCOM")
    soup = BeautifulSoup(html, "lxml")
    for tb in soup.find_all("table"):
        head = None
        for tr in tb.find_all("tr"):
            c = [clean(x) or "" for x in cells(tr)]
            tpos = tr_pos(tr)
            low = [x.lower() for x in c]
            if "designation" in low:
                head = low
                continue
            if not head or len(c) < len(head):
                provenance.skip_row(tr, 'skip: not head or len(c) < len(head)')
                continue
            d = dict(zip(head, c))
            place = d.get("place/district") or d.get("place") or c[0]
            post = d.get("designation")
            if not place or not post:
                provenance.skip_row(tr, 'skip: not place or not post')
                continue
            area = re.sub(r"\s*\b(DIVISION|DVN|CIRCLE|ZONE)\b\s*$", "", place, flags=re.I) or place
            out.add(f"{level}:{place}:{post}", level, area, post=re.sub(r"\s+El$", " (Elec.)", post),
                    phone_=phone(d.get("mobile")), office_name=place, src_pos=tpos, method="html table")
    return out.recs


def _block_level(title):
    t = title.lower()
    for word, lvl in BLOCKS:
        if word in t:
            return lvl, word
    return None, None


def _area(name):
    """'AEECSD-1Klb' -> 'CSD-1Klb', 'CEEZoneKalaburagi' -> 'Kalaburagi', 'SEECircleRaichur' -> 'Raichur'."""
    a = PREFIX.sub("", name).strip(" -_")
    a = re.sub(r"^(O&M)?(CircleOffice|Zone|Circle|Circel)", "", a, flags=re.I).strip(" -_")
    return a or name


def parse_emails(pages, url):
    out = Out(MODULE, "KA", url, discom="GESCOM")
    level = kind = None
    for pn, pg in enumerate(pages, 1):
        for ln, line in enumerate(pg.splitlines(), 1):
            m = re.match(r"\s*Sl\s*no\s+(.+?)\s{2,}Webmail ID", line, re.I)
            if m:
                level, kind = _block_level(m.group(1))
                continue
            m = re.match(r"\s*(\d{1,3})\s+(\S.*)$", line)
            if not m or not level:
                provenance.skip_line(line, 'skip: not m or not level')
                continue
            parts = [p for p in re.split(r"\s{2,}", m.group(2).strip()) if p]
            mails = [p for p in parts if "@" in p or re.search(r"gmail\.?com$", p)]
            name = " ".join(p for p in parts if p not in mails and p != "_")
            if not name:
                provenance.skip_line(line, 'skip: not name')
                continue
            area = name if kind in ("corporate", "vigilance", "construction") else _area(name)
            post = {"zone": "Chief Engineer (Elec.)", "circle": "Superintending Engineer (Elec.)",
                    "division": "Executive Engineer (Elec.)", "subdivision": "Assistant Executive Engineer (Elec.)"}.get(kind)
            out.add(f"email:{kind}:{m.group(1)}:{name}", level, area, post=post or name, email_=email(" ".join(mails)),
                    office_name=name, office_id=m.group(1), src_pos=provenance.line_pos(pn, ln, line),
                    method="pdf text (pypdf layout)")
    return out.recs


def fetch(p, get):
    page = p.get("page", "divisions")
    path, level = PAGES[page]
    url = p.get("url") or BASE + path
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if page == "emails":
        files = [raw(MODULE, page, r.content, "pdf")]
        if not r.content.startswith(b"%PDF"):
            return [], files, "not a PDF"
        recs = parse_emails(pdf_pages(r.content), url)
    else:
        files = [raw(MODULE, page, r.content, "html")]
        recs = parse_table(r.text, level, url)
    return recs, files, "" if recs else "no rows"
