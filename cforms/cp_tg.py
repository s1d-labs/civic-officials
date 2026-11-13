"""Telangana: phones of ward members from each municipality's own site on *.telangana.gov.in (CDMA template, Telugu/English).
Page /pages/council-page: table "S.No | Member Name | Ward | Mobile Number | Photo" (2026 council). Some bodies fill only the
older CMS page /<ulb code>/council ("Sl. No. | W. No. | Name of the Elected Candidate | Contact No."): when the first page has
no rows, a link to such a page in the first page is read. The ward cell is free text ("01", "Ward No. 1", "1ST WARD /
Mallaipally", "Div.NO.4"); names often lose their spaces ("KOTAGALLARAMYA"), so sql/72 checks names without spaces.
One queue item = one body: payload {"kind": "form-cp_tg", "state": "TG", "url", "body" (the tsec.gov.in name), "lgd_code",
"slug" (cforms/tg.py's slug, for record_for), "guessed" (host made from the name, not seen in a site list)}.
These sites answer from outside India (checked 2026-11-11). Seeds: seeds/councillors_cp_tg.json (from civic.official_site and
civic.councillor; guessed hosts for bodies without a known site)."""
import gzip
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from cforms import cp_common as cp
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources


def parse(html, p, url):
    recs = []
    for head, cells in cp.table_rows(html):
        if not head:
            provenance.skipped('skip: not head')
            continue
        ni = cp.column(head, r"member name|name of the|^name")
        pi = cp.column(head, r"mobile|contact|phone")
        wi = cp.column(head, r"^w\.?\s*no|ward|div")
        if ni is None or pi is None or ni >= len(cells):
            provenance.skipped('skip: ni is None or pi is None or ni >= len(cells)')
            continue
        name = cells[ni]
        if not name or re.fullmatch(r"[\d\s.]*", name):
            provenance.skipped('skip: not name or re.fullmatch(r"[\\d\\s.]*", name)')
            continue
        label = cells[wi] if wi is not None and wi < len(cells) else None
        ward = cp.ward_no(label)
        phone = cp.phones(cells[pi]) if pi < len(cells) else None
        recs.append(cp.record("TG", p["body"], ward, name, url, phone=phone, ward_label=label, lgd_code=p.get("lgd_code"),
                              record_for=f"councillor:TG:{p['slug']}:{ward}" if ward and p.get("slug") else None,
                              pos=cells.pos, extra={"src_url": url}))
    return recs


def older_link(html, url):
    """The /<ulb code>/council page linked from the first page, if any."""
    for a in BeautifulSoup(html, "lxml").find_all("a", href=True):
        if re.search(r"/\d{3}/council/?$", a["href"]):
            return urljoin(url, a["href"])
    return None


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer" + (" (guessed host)" if p.get("guessed") else "")
    host = urlsplit(url).hostname
    files = [(f"councillors/TG/cp/{host}-council-page.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = parse(r.text, p, url)
    if not recs:
        u2 = older_link(r.text, url)
        r2 = get(u2) if u2 else None
        if r2 is not None:
            files.append((f"councillors/TG/cp/{host}-council.html.gz", gzip.compress(r2.content), "application/gzip"))
            recs = parse(r2.text, p, u2)
    good = cp.useful(recs)
    return cp.keyed("TG", p["slug"], good), files, "" if good else ("council page lists no members" if not recs else "no phones listed")
