"""Kerala Police: the statewide connectivity directory (keralapolice.gov.in, "connectivity 21.05.2025", 200 pages, updated up
to 31 March 2025). Works from outside India. Each PDF page also carries the text of its neighbour pages outside the page box
(CorelDRAW imposition), so the text is rebuilt from pypdf's positioned fragments inside the page box, one line per y.
Rows: "<NAME> PS  <VPN>  94979 xxxxx  <STD>  <office>"; a next line with only numbers is the station's own CUG mobile
(the first mobile is the SHO's CUG). The police district comes from the section heading above the rows (THIRUVANANTHAPURAM
CITY, KOLLAM RURAL ...). Railway police stations (rows "RPSI <code>" / "IRP <code>" under RAILWAY POLICE) and the
Sabarimala stations are kept with that heading as the unit; the coastal and women station lists repeat district rows. Record id dept:police_kl:<district or unit>:<station>."""
import io
import re

from provenance import line_pos
from dforms._police import clean, gz, phones, rec, slug, uniq
import provenance

METHOD = "pdf text (pypdf, text pieces put in lines by position)"     # source trail (provenance.py): how this reader reads its sources

M = "police_kl"
URL = "https://keralapolice.gov.in/storage/pages/custom/ckFiles/file/RDBrCgXQ7yDQqKfazhg9MphN8DWUdgGcXFThGhoy.pdf"
DISTRICTS = {"THIRUVANANTHAPURAM CITY", "THIRUVANANTHAPURAM RURAL", "KOLLAM CITY", "KOLLAM RURAL", "PATHANAMTHITTA", "ALAPPUZHA",
             "KOTTAYAM", "IDUKKI", "KOCHI CITY", "ERNAKULAM RURAL", "THRISSUR CITY", "THRISSUR RURAL", "PALAKKAD", "MALAPPURAM",
             "KOZHIKODE CITY", "KOZHIKODE RURAL", "WAYANAD", "KANNUR CITY", "KANNUR RURAL", "KASARAGOD"}
UNITS = {"RAILWAY POLICE", "SABARIMALA"}
RLY = re.compile(r"^(RPSI|IRP)\s")       # railway police station rows (Inspector / SI in charge, station code)
END = "SENIOR POLICE OFFICERS ON DEPUTATION"
HEAD = re.compile(r"^[A-Z][A-Z .&,()'-]{3,}$")
MOB = r"(?:9\d{4}\s?\d{5}|[6-9]\d{3}\s?\d{6})"
ROW = re.compile(rf"^(?P<name>.*?)\s+(?:(?P<vpn>\d{{5}})\s+)?(?P<mob>{MOB})?\s*(?:(?P<std>0\d{{2,4}})\s+(?P<off>\d{{5,8}}))?$")
ONLY_NUM = re.compile(rf"^(?:\d{{5}}\s+)?(?P<mob>{MOB})(?:\s+0\d{{2,4}}\s+\d{{5,8}})?$")
PS = re.compile(r"\bP\.?S\b|Police Station", re.I)


def lines_of(page):
    """Text lines of one page from fragments inside the page box, top to bottom, left to right."""
    x0, y0, x1, y1 = [float(v) for v in page.mediabox]
    frags = []

    def visit(t, cm, tm, fd, fs):
        if not t or not t.strip():
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        if x0 - 1 <= x < x1 and y0 <= y <= y1:
            for i, part in enumerate(t.split("\n")):
                if part.strip():
                    frags.append((round(y - i * (fs or 10)), x, part))
    page.extract_text(visitor_text=visit)
    rows = {}
    for y, x, t in frags:
        k = next((k for k in rows if abs(k - y) <= 2), y)
        rows.setdefault(k, []).append((x, t))
    return [clean("  ".join(t.strip() for _, t in sorted(v))) for _, v in sorted(rows.items(), key=lambda kv: -kv[0])]


def text_lines(content, where=None):
    """All pages' lines; where (a list) gets (page, line in page) for each line, 1-based (source trail)."""
    from pypdf import PdfReader
    out = []
    for pn, page in enumerate(PdfReader(io.BytesIO(content)).pages, 1):
        ls = lines_of(page)
        out.extend(ls)
        if where is not None:
            where.extend((pn, k) for k in range(1, len(ls) + 1))
    return out


def parse(lines, url=URL, where=None):
    recs, head, last = [], None, None
    started = False
    for li, ln in enumerate(lines):
        if not ln:
            provenance.skipped("empty")
            continue
        if HEAD.match(ln) and not PS.search(ln):
            h = clean(ln)
            if h == END:
                break
            head, last = h, None
            started = started or h in DISTRICTS or h in UNITS
            continue
        if not started or head not in DISTRICTS | UNITS:
            provenance.skip_line(ln, 'skip: not started or head not in DISTRICTS | UNITS')
            continue
        m = ONLY_NUM.match(ln)
        if m and last is not None:
            d = last[1]
            ph = phones(d.get("phone"), m.group("mob"))
            if ph:
                d["phone"] = ph
                d["station_mobile"] = phones(m.group("mob"))
            last = None
            continue
        m = ROW.match(ln)
        if not m or not (PS.search(m.group("name") or "") or (head == "RAILWAY POLICE" and RLY.match(ln))):
            last = None
            continue
        name = clean(m.group("name"))
        station = re.sub(r"^SHO\s*,?\s*", "", name, flags=re.I)
        district = head if head in DISTRICTS else None
        landline = f"{m.group('std')}-{m.group('off')}" if m.group("std") else None
        r = rec(M, f"{slug(head)}:{slug(station)}", area=station, post="SHO", phone=phones(m.group("mob"), landline),
                vpn=m.group("vpn"), state="KL", district=district.title() if district else None,
                unit=None if district else head.title(), source=url, last_updated="2025-03-31",
                src_pos=line_pos(*where[li], ln) if where and li < len(where) else {"line": li + 1, "line_text": ln})
        recs.append(r)
        last = r
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [(f"depts/police/{M}/connectivity-2025.pdf", r.content, "application/pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    try:
        where = []
        lines = text_lines(r.content, where)
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    files.append(gz(M, "connectivity-2025.txt", "\n".join(lines)))
    recs = parse(lines, url, where)
    return recs, files, "" if recs else "no rows"
