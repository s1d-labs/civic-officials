"""Mumbai (MCGM / BMC): Hindu Hridaysamrat Balasaheb Thackeray (HBT) Aapla Dawakhana clinics, polyclinics and diagnostic centres,
from the Public Health Department list on the MCGM portal ("List of Disp English version.pdf", 4 pages, 107 rows, no date on the
file; fetched 2026-11-11). Sections: porta cabins, existing dispensaries, polyclinic and diagnostic centres, ready structures.
Columns: Sr No (all), Sr No (in section), location (CITY / WESTERN / EASTERN), zone (I-VII), ward (MCGM administrative ward: FN, GN,
HE ...), name of the clinic, postal address, timing. Location, zone and ward are merged cells: the PDF prints each once, near the
middle of its group, so a row has a ward only when the label is printed on that row's own lines (ward_printed). The list names no
doctor and no phone; post "Medical Officer" (the officer in charge). One queue item (one GET).

pypdf layout text: a row starts with "<Sr No>  <Sr No>"; cells are centred vertically, so a cell's lines can stand above and below
the start line. Each line between two start lines goes to the nearer start line (ties: the one above); an address line goes to the
row above while that row's address has no Mumbai PIN (400xxx) yet.
Records: dept health, level facility, layer clinic, area = clinic name, facility_type (from the section), address, pin, ward
(when printed), zone, timing. Record ids: dept:civic_clinic_mumbai:MCGM-HBT-<Sr No>.
"""
import re

from dforms import _esw

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_clinic_mumbai"
URL = ("https://portal.mcgm.gov.in/irj/go/km/docs/documents/MCGM%20Department%20List/Public%20Health%20Department/Docs/"
       "List%20of%20Disp%20English%20version.pdf")
CHUNK = re.compile(r"\S+(?: \S+)*")
START = re.compile(r"^\s{0,3}(\d{1,3})\s+(\d{1,3})\s{2,}")
SECTION = re.compile(r"(?i)^\s*(?:hbt aapla dawakhana\s*[-–]?\s*(.+?)|(polyclinic and diagnostic cent(?:er|re)))\s*$")
TITLE = re.compile(r"(?i)^\s*functional\b")
HEADER = re.compile(r"(?i)^\s*(sr\s+sr|no\s+no)\b")
WARD = re.compile(r"^(A|B|C|D|E|FN|FS|GN|GS|HE|HW|KE|KW|KN|KS|L|ME|MW|N|PN|PS|PE|RC|RN|RS|S|T)$")
ZONE = re.compile(r"^(I|II|III|IV|V|VI|VII)$")
LOCATION = re.compile(r"(?i)^(city|western|eastern)$")
PIN = re.compile(r"\b4\d{2}\s?\d{3}\b")
# column bounds (characters) of the layout text; the header line gives the same positions on every page
NAME_X, ADDR_X, TIME_X = 38, 68, 140


def chunks(line):
    return [(m.start(), m.group()) for m in CHUNK.finditer(line)]


def kind(section):
    s = section.lower()
    if "porta" in s:
        return "HBT clinic (porta cabin)"
    if "ready" in s:
        return "HBT clinic (ready structure)"
    if "poly" in s or "diagnos" in s:
        return "HBT polyclinic / diagnostic centre"
    if "dispens" in s:
        return "HBT clinic (dispensary)"
    return "HBT clinic"


def blank(sno, sec_no, section):
    return {"sno": sno, "sec_no": sec_no, "section": section, "name": [], "addr": [], "time": [], "ward": "", "zone": "",
            "location": ""}


def put(row, line, address_only=False):
    for x, t in chunks(line):
        if x < NAME_X:
            if not address_only:
                for w in t.split():
                    if WARD.match(w):
                        row["ward"] = w
                    elif ZONE.match(w):
                        row["zone"] = w
                    elif LOCATION.match(w):
                        row["location"] = w.title()
        elif x < ADDR_X:
            if not address_only:
                row["name"].append(t)
        elif x < TIME_X:
            row["addr"].append(t)
        elif not address_only:
            row["time"].append(t)


def rows(pages):
    """Rows as dicts (in order). Lines between two start lines go to the nearer start line (ties: the one above)."""
    out, section = [], ""
    for page in pages:
        lines = [ln for ln in page.splitlines() if ln.strip()]
        starts, body = [], []
        for ln in lines:
            m = SECTION.match(ln)
            if m and not START.match(ln):
                body.append(("section", m.group(1) or m.group(2)))
                continue
            if HEADER.match(ln) or TITLE.match(ln):
                continue
            s = START.match(ln)
            body.append(("start", ln, s.group(1), s.group(2)) if s else ("line", ln))
        idx = [i for i, b in enumerate(body) if b[0] == "start"]
        sec_at = {}
        for i, b in enumerate(body):
            if b[0] == "section":
                section = b[1]
            sec_at[i] = section
        page_rows = {i: blank(body[i][2], body[i][3], sec_at[i]) for i in idx}
        for i, b in enumerate(body):
            if b[0] == "start":
                put(page_rows[i], b[1])
            if b[0] != "line":
                continue
            above = max((j for j in idx if j < i), default=None)
            below = min((j for j in idx if j > i), default=None)
            # a section heading between the line and a start line cuts it off from that row
            if above is not None and any(body[k][0] == "section" for k in range(above, i)):
                above = None
            if below is not None and any(body[k][0] == "section" for k in range(i, below)):
                below = None
            if above is None and below is None:
                continue
            if below is None or (above is not None and i - above <= below - i):
                put(page_rows[above], b[1])
                continue
            # nearer to the row below; an address line still goes up while the row above has no PIN
            if above is not None and not PIN.search(" ".join(page_rows[above]["addr"])):
                put(page_rows[above], b[1], address_only=True)
                put(page_rows[below], re.sub(r"\S", " ", b[1][ADDR_X:TIME_X]).join([b[1][:ADDR_X], b[1][TIME_X:]]))
            else:
                put(page_rows[below], b[1])
        out += [page_rows[i] for i in idx]
    return out


def parse(pages, url=URL):
    recs, seen = [], set()
    for r in rows(pages):
        name = _esw.clean(" ".join(r["name"]))
        if not name:
            continue
        addr = _esw.clean(" ".join(r["addr"]))
        pin = PIN.search(addr)
        key = f"MCGM-HBT-{r['sno']}"
        if key in seen:
            continue
        seen.add(key)
        timing = _esw.clean(" ".join(r["time"]))
        timing = "; ".join(dict.fromkeys(_esw.clean(t) for t in re.findall(
            r"(?i)((?:morning|evening)?[a-z ]*?(?:opd)?\s*(?:timing:)?\s*\d{1,2}[:.]\d{2}\s*[ap]m\s*to\s*\d{1,2}[:.]\d{2}\s*[ap]m)", timing)))
        recs.append(_esw.record(MODULE, key, dept="health", level="facility", layer="clinic", area=name, post="Medical Officer",
                                facility_type=kind(r["section"]), section=_esw.clean(r["section"]), address=addr,
                                pin=re.sub(r"\s", "", pin.group()) if pin else "", ward=r["ward"],
                                ward_printed=bool(r["ward"]), zone=r["zone"], location=r["location"], timing=timing,
                                state="MH", district="Mumbai", body="Municipal Corporation of Greater Mumbai", office_id=key,
                                source=url))
    return recs


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "MH"}}]


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "hbt-aapla-dawakhana-list", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
