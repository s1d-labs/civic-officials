"""Karnataka State Fire and Emergency Services (ksfes.karnataka.gov.in): "216 FIRE STATION LIST", a PDF linked from the menu
"About Us -> Fire Station List" (uploads/media_to_upload1745835964.pdf, 8 pages, printed with "Microsoft: Print To PDF").
Columns: row | CHIEF FIRE OFFICER (zone: East, West, Mangalore, Hubli ...) | REGIONAL FIRE OFFICER | DISTRICT FIRE OFFICER |
station no. | FIRE STATION. A CFO / RFO / DFO cell is written only on the first row of its group, so the reader carries the
last one down. Rows without a station number are units of a station (Vidhan Soudha, Raj Bhavan, High Court ...).
The list names no officer and gives no phone: it is the station network with its command chain (CFO zone -> RFO region ->
DFO district office -> station). No date on the PDF.
Access: India only (no connection from Germany on 2026-11-11), and the server does not send its intermediate certificate
(GlobalSign GCC R46 OV TLS CA 2025): certs_trust.py completes the chain from certs/, verification stays on. archive.s1d.me
holds only a cut copy (13 KB, no trailer).
Record ids: dept:emerg_fire_ka:st-<station no.>, unit-<slug>.
"""
import re

from dforms import _emerg, _pdftext
from provenance import line_pos
import provenance

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_ka"
URL = "https://ksfes.karnataka.gov.in/uploads/media_to_upload1745835964.pdf"


def items(get=None):
    return _emerg.seed(MODULE)


def rows(text, where=None, at=None):
    """[(cfo, rfo, dfo, station no. or None, station or unit)] from the layout text of the PDF. where (a list) gets each row's
    src_pos; at = (page, line in page) of each text line when known."""
    out, cfo, rfo, dfo = [], None, None, None
    for li, line in enumerate(text.splitlines()):
        m = re.match(r"^\s*(\d{1,3})\s+(.*\S)\s*$", line) or re.match(r"^\s{4,}((?:CFO|RFO|DFO|COMMAND|HEAD)\b.*\S)\s*$", line)
        if not m:
            provenance.skip_line(line, 'skip: not m')
            continue
        rest = m.group(m.lastindex)
        toks = [t.strip() for t in re.split(r"\s{2,}", rest) if t.strip()]
        no, name = None, None
        i = 0
        while i < len(toks):
            t = toks[i]
            if re.match(r"(?i)^(CFO|COMMANDENT|COMMANDANT|HEAD OFFICE)\b", t):
                cfo, rfo, dfo = t, None, None
            elif re.match(r"(?i)^RFO\b", t):
                rfo, dfo = t, None
            elif re.match(r"(?i)^DFO\b", t):
                dfo = t
            elif re.fullmatch(r"\d{1,3}", t) and i + 1 < len(toks):
                no, name = int(t), toks[i + 1]
                i += 1
            else:
                name = t
            i += 1
        if name:
            out.append((cfo, rfo, dfo, no, _emerg.clean(name).rstrip(".")))
            if where is not None:
                where.append(line_pos(*at[li], line) if at and li < len(at) else {"line": li + 1, "line_text": line})
    return out


def tidy(post):
    """'RFO South' -> ('Regional Fire Officer', 'South')."""
    if not post:
        return None
    m = re.match(r"(?i)^(CFO|RFO|DFO)\s+(.+)$", post)
    if not m:
        return _emerg.clean(post).title()
    return _emerg.clean(m.group(2)).title()


def records(text, url, at=None, engine=None):
    recs, seen, where = [], set(), []
    for n, (cfo, rfo, dfo, no, name) in enumerate(rows(text, where, at)):
        unit = no is None
        if unit and not re.search(r"(?i)\(units?\)|academy|workshop", name):
            provenance.skipped('skip: unit and not re.search(r"(?i)\\(units?\\)|academy|workshop", name)')
            continue
        key = _emerg.unique(f"st-{no}" if not unit else f"unit-{_emerg.slug(name)}", seen)
        recs.append(_emerg.record(
            MODULE, key, "fire", dept="fire", level="facility", area=re.sub(r"(?i)\s*\(units?\)", "", name),
            post="Station Officer", station_no=no, unit=True if unit else None,
            zone=tidy(cfo), region=tidy(rfo), district_office=tidy(dfo), state="KA", office_id=key, source=url,
            src_pos=where[n], **({"method": f"pdf text ({engine})"} if engine else {})))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_emerg.keep(MODULE, "station-list", r.content, "pdf")]
    pages, engine = _pdftext.layout_pages(r.content)
    at = [(pn, k) for pn, pg in enumerate(pages, 1) for k, _ in enumerate(pg.split("\n"), 1)]
    recs = records("\n".join(pages), url, at, _emerg.ENGINE.get(engine))
    return recs, files, "" if recs else "no rows"
