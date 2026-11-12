"""Delhi Fire Service (dfs.delhi.gov.in): every fire station with its sub-division, division and zone, and the officer of each
level: Assistant Divisional Officer (ADO) per sub-division, Divisional Officer (D.O.) per division, Deputy Chief Fire Officer
(DCFO) and Chief Fire Officer (CFO) per zone, each with the office email. Station phones come from a second PDF.

Sources (both saved on archive.s1d.me 2026-11-05):
- "Contact us" PDF .../Dfs/generic_multiple_files/update_contact_us.pdf (5 pages, 71 stations + HQ, FSMA, FPW). A ruled table
  with merged cells: Sl. No | Fire Stations | Sub Division | Division | DCFO Zone | CFO Zone. A sub-division cell spans the rows
  of its stations, so the text alone does not say which station belongs where. The reader takes each text piece with its
  position and the ruling lines from dforms/_util2_pdfgrid.page_parts() (imported, not changed): column borders = vertical
  lines, cell borders = the horizontal lines that cross the column. A station belongs to the sub-division / division / zone
  cells whose vertical extent holds the station's line.
- Station phone list .../inline-files/fire_station.pdf ("FIRE STATIONS  TEL.NO."): one line per station, read with
  dforms/_pdftext.layout_pages(); names are joined to the stations of the first PDF (spelling aliases + difflib).
The PDFs show no date. Station officers are not named (the PDF names ADOs and above).
Record ids: dept:emerg_fire_dl:st-<station>, sd-<sub-division>-<officer>, div-<division>-<officer>, zone-<zone>-<post>-<officer>.
"""
import difflib
import io
import re

from dforms import _emerg, _pdftext
from dforms._util2_pdfgrid import page_parts
from provenance import line_pos

METHOD = "pdf ruled table (pypdf text positions inside the drawn cell rules) + pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_dl"
BASE = "https://dfs.delhi.gov.in/sites/default/files/"
URL = BASE + "Dfs/generic_multiple_files/update_contact_us.pdf"
PHONES_URL = BASE + "inline-files/fire_station.pdf"
COLS = ("sn", "station", "subdivision", "division", "dcfo", "cfo")
POSTS = (  # (regex, post, level)
    (r"Dy\.?\s*CHIEF\s+FIRE\s+OFFICER", "Deputy Chief Fire Officer", "zone"),
    (r"CHIEF\s+FIRE\s+OFFICER", "Chief Fire Officer", "zone"),
    (r"D\.\s?O\.", "Divisional Officer", "division"),
    (r"ADO", "Assistant Divisional Officer", "subdivision"),
)
POST_RX = re.compile(r"(Dy\.?\s*CHIEF\s+FIRE\s+OFFICER|CHIEF\s+FIRE\s+OFFICER|D\.\s?O\.|\bADO\b)")
EMAIL_RX = re.compile(r"[\w.+-]+[@][\w-]+(?:\.[\w-]+)+")
ALIASES = {  # phone-list spelling -> contact-PDF spelling (letters only, lower case)
    "connaughtplace": "connaughtcircus", "kesavpuram": "keshavpuram", "telewara": "teliwara", "rpbhawan": "rashtrapatibhawan",
    "delhisectt": "delhisecretariat", "dawarka": "dwarka", "mandawlimipex": "mandawli", "mandawalimipex": "mandawli",
    "laxhminagar": "laxminagar", "bhikajikamaplace": "bhikajicamapalace", "bhikajicamaplace": "bhikajicamapalace",
    "safderjung": "safdarjung", "jwalaheri": "jawalaheri", "dsidcbawana": "dsiidcbawana", "udyognagar": "udhyognagar",
    "okhlaphasei": "okhlaphi", "rohinisec5": "rohinisec05", "fsma": "firesafetymanagementacademy", "tciws": "motinagartcws", "tcws": "motinagartcws", "jahangirpuri": "jahangirpuri",
    "headquarter": "headquarter", "sanjaygandhitransportnagar": "sanjaygandhitransportnagar",
    "chanakyapuri": "chanakyapuri", "roopnagar": "roopnagar", "spm": "spm", "townhall": "townhall",
}


def items(get=None):
    return _emerg.seed(MODULE)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def pdf_parts(content):
    """[(texts, hlines, vlines)] per page of a PDF (page space), [] if it is not a readable PDF."""
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(content))
        return [page_parts(reader, p) for p in reader.pages]
    except Exception:
        return []


def borders(vlines):
    """Column borders from the vertical lines: x positions merged within 3 points."""
    out = []
    for x in sorted(v[0] for v in vlines):
        if not out or x - out[-1] > 3:
            out.append(x)
    return out


def cells(texts, hlines, vlines):
    """{(col, top, bottom): text} for the six table columns of one page, below the header row."""
    xs = borders(vlines)
    if len(xs) < 7:
        return {}
    xs = xs[-7:]
    head = [t[1] for t in texts if re.match(r"\s*Fire\s+Stations", t[2])]
    if not head:
        return {}
    top = min(head) - 2
    out = {}
    for x, y, t in texts:
        if y >= top:
            continue
        k = next((i for i in range(6) if xs[i] - 1 <= x + 1 < xs[i + 1]), None)
        if k is None:
            continue
        cx = (xs[k] + xs[k + 1]) / 2
        ys = [hy for x0, x1, hy in hlines if x0 - 2 <= cx <= x1 + 2]
        hi = min([hy for hy in ys if hy > y + 0.5] or [top])
        lo = max([hy for hy in ys if hy < y - 0.5] or [0])
        out.setdefault((k, min(hi, top), lo), []).append((x, y, t))
    return {key: "\n".join(_emerg.clean(t) for x, y, t in sorted(v, key=lambda p: (-p[1], p[0]))) for key, v in out.items()}


def officers(text):
    """Cell text -> (area, [(post, level, name, extra_charge)], [emails]). 'Vacant' is kept as the name."""
    emails = EMAIL_RX.findall(text)
    t = _emerg.clean(EMAIL_RX.sub(" ", text.replace("\n", " ")))
    parts = POST_RX.split(t)
    area = _emerg.clean(parts[0]).strip(" -") if parts else ""
    out = []
    for i in range(1, len(parts) - 1, 2):
        post = next((p, lv) for rx, p, lv in POSTS if re.fullmatch(rx, parts[i]))
        rest = parts[i + 1]
        addl = bool(re.search(r"\(\s*Addl\.?\s*\)", rest))
        name = _emerg.clean(re.sub(r"\(\s*Addl\.?\s*\)", " ", rest)).strip(" ,-")
        name = re.sub(r"^\((Vacant)\)$", r"\1", name)
        if name or addl:
            out.append((post[0], post[1], name, addl))
    return area, out, emails


def stations_of(pages, where=None):
    """[(station, {col: cell text})] from the contact PDF's page parts. where (a list) gets each station's src_pos:
    {"page": 1-based, "cell": {"col": 1, "top", "bottom"} in PDF points}."""
    out = []
    for pn, (texts, hl, vl) in enumerate(pages, 1):
        cs = cells(texts, hl, vl)
        for (k, hi, lo), txt in sorted(cs.items(), key=lambda kv: -kv[0][1]):
            if k != 1:
                continue
            row = {}
            mid = (hi + lo) / 2
            for (k2, hi2, lo2), t2 in cs.items():
                if k2 >= 2 and lo2 <= mid <= hi2:
                    row[COLS[k2]] = t2
            name = _emerg.clean(txt.replace("\n", " ")).lstrip("*").strip()
            out.append((name, row))
            if where is not None:
                where.append({"page": pn, "cell": {"col": k, "top": round(hi, 1), "bottom": round(lo, 1)}})
    return out


def phone_list(content):
    """{normalised station name: (name as written, phone)} from the station phone PDF."""
    pages, _ = _pdftext.layout_pages(content)
    at = [(pn, k) for pn, pg in enumerate(pages, 1) for k, _ in enumerate(pg.split("\n"), 1)]
    return phone_lines("\n".join(pages), at)


def phone_lines(text, at=None):
    """phone_list() on the layout text of the PDF. Each value is (name, phone, src_pos of the phone's line); at = (page, line)
    of each line of text, when known."""
    out, pending = {}, None
    for i, line in enumerate(text.splitlines()):
        pos = line_pos(*at[i], line) if at and i < len(at) else {"line": i + 1, "line_text": line}
        m = re.match(r"^\s*(?:\d{1,3}\s+)?([A-Za-z][A-Za-z0-9 .()/&-]*?[A-Za-z0-9.)])\s{2,}(\d[\d /]*\d(?:\s*EXT\.?-?\s*\d+)?)\s*$", line)
        if m and not re.search(r"(?i)tel\.?\s*no|fire\s+stations", m.group(1)):
            out.setdefault(norm(m.group(1)), (_emerg.clean(m.group(1)), _emerg.clean(m.group(2)), pos))
            pending = None
            continue
        m = re.match(r"^\s*(?:\d{1,3}\s+)?([A-Za-z][A-Za-z .()/&-]+?)\s*$", line)
        if m and not re.search(r"(?i)tel\.?\s*no|fire\s+stations|annex|day time", line):
            pending = m.group(1)
            continue
        m = re.match(r"^\s*(?:\d{1,3})?\s{2,}(\d{6,}[\d /]*)\s*$", line)
        if m and pending:
            out.setdefault(norm(pending), (_emerg.clean(pending), _emerg.clean(m.group(1)), pos))
            pending = None
    return out


def match_phone(station, phones):
    n = norm(station)
    by = {ALIASES.get(k, k): v for k, v in phones.items()}
    if n in by:
        return by[n]
    close = difflib.get_close_matches(n, list(by), n=1, cutoff=0.8)
    return by[close[0]] if close else None


def records(pages, phones, url, phones_url=None):
    recs, seen, done = [], set(), set()

    def add(key, **f):
        recs.append(_emerg.record(MODULE, _emerg.unique(key, seen), "fire", dept="fire", state="DL", district=None,
                                  source=url, src_url=url, **f))

    def levels(row):
        sd = officers(row.get("subdivision", ""))
        dv = officers(row.get("division", ""))
        zn = officers(row.get("dcfo", "") or row.get("cfo", ""))
        return sd, dv, zn

    where = []
    for si, (station, row) in enumerate(stations_of(pages, where)):
        sd, dv, zn = levels(row)
        pos = where[si]
        if station and station != "---":
            ph = match_phone(station, phones) if phones else None
            add(f"st-{_emerg.slug(station)}", level="facility", area=station, post="Station Officer",
                phone=ph[1] if ph else None, phone_source=phones_url if ph else None,
                subdivision=sd[0] or None, division=dv[0] or None, zone=zn[0] or None,
                src_pos={**pos, **({"phone_file": phones_url, "phone_line": ph[2]} if ph and len(ph) > 2 else {})},
                method="pdf ruled table (pypdf text positions)" + (" + pdf text (layout) of the phone list" if ph else ""))
        for col, (area, offs, emails) in (("subdivision", sd), ("division", dv), ("dcfo", officers(row.get("dcfo", ""))),
                                          ("cfo", officers(row.get("cfo", "")))):
            if not row.get(col) or (col, row[col]) in done:
                continue
            done.add((col, row[col]))
            for i, (post, level, name, addl) in enumerate(offs):
                email = emails[i] if len(emails) == len(offs) else (emails[0] if len(emails) == 1 else ", ".join(emails))
                pre = {"subdivision": "sd", "division": "div"}.get(col, "zone")
                key = f"{pre}-{_emerg.slug(area or 'x')}-{_emerg.slug(post) if pre == 'zone' else ''}-{_emerg.slug(name or 'vacant')}"
                add(re.sub(r"-+", "-", key), level=level, area=area, post=post, name=None if name == "Vacant" else name,
                    vacant=True if name == "Vacant" else None, additional_charge=True if addl else None,
                    email=_emerg.emails(email), src_pos={**pos, "col": col}, method="pdf ruled table (pypdf text positions)")
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_emerg.keep(MODULE, "update_contact_us", r.content, "pdf")]
    pages = pdf_parts(r.content)
    if not pages:
        return [], files, "not a readable PDF"
    phones, purl = {}, p.get("phones_url", PHONES_URL)
    if purl:
        q = get(purl)
        if q is not None:
            files.append(_emerg.keep(MODULE, "fire_station", q.content, "pdf"))
            phones = phone_list(q.content)
    recs = records(pages, phones, url, purl)
    return recs, files, "" if recs else "no rows"
