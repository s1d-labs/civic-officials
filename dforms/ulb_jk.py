"""Jammu and Kashmir, Kashmir division: Directorate of Urban Local Bodies Kashmir, "List of Chief Executive Officers/Executive
Officers/Contact details of Urban Local Bodies Kashmir", https://ulbk.jk.gov.in/Key Contacts Urban Local Bodies of Kashmir Division.pdf
(one page, text PDF, made 2026-09-02 (last_updated = the PDF's creation date); linked from ulbk.jk.gov.in). 40 rows: S.No, Name of Office ("Municipal Committee Achabal"),
Name of Officer with the kind of charge in brackets ("Mirza Asif Ali (Posted)", "(Addl)", "(BDO Soibugh)", "(Tehsildar)"), email
ID, Designation (Executive Officer; CEO for Sopore), Contact No. One officer often holds several bodies (additional charge).
Srinagar Municipal Corporation is not in it. Jammu division: dforms is not needed (directories.json "jk-jammu-whoswho", ULB Jammu).
The site answers only from India (no answer from Germany on 2026-11-11). archive.s1d.me holds a cut copy (the first 7 KB of the
file, 2026-11-05), so the reader needs the live file.
No district column: area = the office name with the type split off ("Achabal", body_type "Municipal Committee"); sql/87 ties it by
name in the state. The kind of charge goes to the key "charge". Emails are kept as written (some have typing errors: jk.gpv.in).
The elected councils' terms ended in 2023 and no new election has been held (2026-11): the list names no chairpersons. The
"Contact Details of Presidents of ULBs.pdf" on the same site (April 2025) has no text layer.
"""
import re

from dforms import _esw, _ulb
import provenance

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_jk"
STATE = "JK"
URL = "https://ulbk.jk.gov.in/Key%20Contacts%20Urban%20Local%20Bodies%20of%20Kashmir%20Division.pdf"
TYPE = re.compile(r"(?i)^(mun\w*\s+(?:committee|council|corporation))\s+(.+)$")
ROW = re.compile(r"^\s*(\d{1,3})\s{2,}(.+)$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def split_type(office):
    """'Municipal Committee  Achabal' -> ('Achabal', 'Municipal Committee'); 'Muncipa Council Sopore' -> ('Sopore', 'Muncipa Council')."""
    office = _esw.clean(office)
    m = TYPE.match(office)
    return (m.group(2), m.group(1)) if m else (office, None)


def rows(text, where=None):
    """[(sno, office, officer, email, designation, phone)] from the layout text of the PDF. where: a list; when given, it gets
    (line number in the text, 1-based; raw line) for each row."""
    out = []
    for lno, line in enumerate(text.splitlines(), 1):
        raw = line
        line = re.sub(r"\s*\(\s*", " (", line)
        line = re.sub(r"\s+@", "@", line)
        m = ROW.match(line)
        if not m:
            continue
        cols = [c.strip() for c in re.split(r"\s{3,}", m.group(2).strip()) if c.strip()]
        if len(cols) < 4 or not re.search(r"(?i)munic|muncip", cols[0]):
            continue
        phone = cols[-1] if re.fullmatch(r"[\d\s,/+-]{6,}", cols[-1]) else ""
        rest = cols[:-1] if phone else cols
        email = next((c for c in rest if "@" in c), "")
        other = [c for c in rest[1:] if c != email]
        officer, post = (other[0], " ".join(other[1:])) if other else ("", "")
        out.append((int(m.group(1)), rest[0], officer, email, post, phone))
        if where is not None:
            where.append((lno, raw))
    return out


def made(content):
    """The PDF's creation date (yyyy-mm-dd) from its metadata, or None."""
    import io
    from pypdf import PdfReader
    try:
        d = (PdfReader(io.BytesIO(content)).metadata or {}).get("/CreationDate", "")
    except Exception:
        return None
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", d or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def parse(content, url=URL):
    pages = _esw.pdf_pages(content) if isinstance(content, bytes) else [content]
    last = made(content) if isinstance(content, bytes) else None
    recs, seen = [], set()
    found = []
    for pno, page in enumerate(pages, 1):
        where = []
        found += [(r, provenance.line_pos(pno, *w)) for r, w in zip(rows(page, where), where)]
    for (sno, office, officer, email, post, phone), pos in found:
        body, btype = split_type(office)
        m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", officer)
        name, charge = (m.group(1), m.group(2)) if m else (officer, None)
        recs.append(_ulb.record(MODULE, STATE, body, post or "Executive Officer", seen, name=name, phone=phone, email=email,
                                body_type=btype, source=url, charge=_esw.clean(charge) or None, list_name=_esw.clean(office),
                                last_updated=last, src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [_esw.keep(MODULE, "key-contacts-ulb-kashmir", r.content, "pdf")]
    recs = parse(r.content, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
