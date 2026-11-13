"""Uttar Pradesh: every ASHA (Accredited Social Health Activist) of the rural districts, by village, from the "District-wise ASHA
Data base" of the UP National Health Mission (https://nhm.up.gov.in/upnrhm/ASHADatabase.html; upnrhm.gov.in redirects there).
The page links one PDF per district ("Compiled <District>", /assets/site-files/asha/Compiled_<District>.pdf): 75 links on
2026-11-14 (checked from Mumbai and from abroad: both answer). The files are Excel sheets printed to PDF, with a text layer.

Template (measured on the whole Hapur file, 9 pages, created 2016-05-18): title "ASHA Database <District>", then the columns
S.No. | Name Of District | Name Of Block | Name Of CHC/BPHC | Name Of Sub-Centre | ID No.of ASHA | Name Of ASHA | Husband's Name |
Name Of Village | Population Covered, a number row "1 2 ... 10" on the first page, and the header repeated on each page. No phone
column. A row whose last cells do not fit on the page goes on at the top of the next page (a line without a serial number).

How a row is read (pdftotext -layout, else pypdf layout; both keep the x position of a cell): a line that starts with a serial
number and holds the ASHA's ID (5-9 digits). Cells are text runs with single spaces; the ID splits them into the left cells
(district, block, CHC/BPHC, sub-centre) and the right cells (ASHA, husband, village, population). The x centre of each cell
column is learned on each page from its complete rows (all cells there), so a row with an empty cell (no husband name, no
population) puts each of its cells in the column whose centre is nearest. A line without a serial number that is not a header
line and lies right of the ID column continues the last row: its cells are added to the last row's cells of the same columns.
A left side with an other number of cells than the page's usual number keeps its cells in order (district, block, ...).

Records (dept health, level village, layer village_worker): one per ASHA row: post "ASHA", post_regional "आशा", name, husband_name,
asha_id, area = village = the village as written, sub_centre (centre), facility (CHC / BPHC), block, district (the LGD name from the seed; the file's own spelling in
district_as_written), lgd_district_code, state UP,
population_covered, the raw cells (table_row), src_pos = page + line + line text. Nothing is masked.
Ids dept:vil_up_asha:<district slug>:<ASHA ID> (an ID seen twice in one file: :<ID>-r<serial>).
One queue item = one district file (1 GET). The file is kept in the bucket (depts/vil_up_asha/<district slug>.pdf).
"""
import re
from statistics import median

from dforms import _esw, _field
import provenance

METHOD = "pdf text (pdftotext -layout, else pypdf layout); ASHA ID splits the row; cell columns learned per page from complete rows"

MODULE = "vil_up_asha"
PAGE = "https://nhm.up.gov.in/upnrhm/ASHADatabase.html"
LEFT = ("district", "block", "facility", "sub_centre")
RIGHT = ("name", "husband_name", "village", "population_covered")
ROW = re.compile(r"^\s*(\d{1,5})\.?\s{2,}\S")
ID = re.compile(r"^\d{5,9}$")
CHUNK = re.compile(r"\S+(?: \S+)*")
HEAD = re.compile(r"(?i)name\s+of|s\.?\s*no\b|covered|population|asha\s+data\s*base|chc\s*/\s*bphc|husband|^\s*1\s+2\s+3\b")


def chunks(line):
    """[(x centre, x start, text)] of the cell texts of one line."""
    return [((m.start() + m.end()) / 2, m.start(), m.group()) for m in CHUNK.finditer(line)]


def split(line):
    """(serial, left cells, ID, right cells) of a data line, else None. Cells are (x centre, text)."""
    m = ROW.match(line)
    if not m:
        return None
    ch = chunks(line)[1:]
    at = next((i for i, (_, _, t) in enumerate(ch) if ID.match(t)), None)
    if at is None:
        return None
    return m.group(1), [(x, t) for x, _, t in ch[:at]], ch[at][2], [(x, t) for x, _, t in ch[at + 1:]]


def centres(rows, side, n):
    """Median x centre of each of the n columns of one side, from the rows that fill all n cells; None when none do."""
    full = [r[side] for r in rows if len(r[side]) == n]
    if not full:
        return None
    return [median(c[i][0] for c in full) for i in range(n)]


def place(cells, cs, n):
    """Cells -> n column texts: by order when the count fits or no centres are known, else each to the nearest centre."""
    out = [""] * n
    if len(cells) == n or not cs:
        for i, (_, t) in enumerate(cells[:n]):
            out[i] = t
        if len(cells) > n:
            out[-1] = " ".join([out[-1]] + [t for _, t in cells[n:]])
        return out
    for x, t in cells:
        i = min(range(n), key=lambda k: abs(cs[k] - x))
        out[i] = f"{out[i]} {t}".strip()
    return out


def parse(text, url="", p=None):
    """(records, stats) from the layout text of one district file."""
    p = p or {}
    dslug = _esw.slug(p.get("district") or "") or "x"
    pages = text.split("\f")
    rows = []           # dicts: serial, left, id, right, pos, cells by column
    for pg, pt in enumerate(pages, 1):
        lines = pt.split("\n")
        parsed = [(n, ln, split(ln)) for n, ln in enumerate(lines, 1)]
        page_rows = [{"serial": s[0], "left": s[1], "id": s[2], "right": s[3], "pg": pg, "ln": n, "line": ln}
                     for n, ln, s in parsed if s]
        lc = centres(page_rows, "left", len(LEFT)) or (rows and rows[-1].get("lc"))
        rc = centres(page_rows, "right", len(RIGHT)) or (rows and rows[-1].get("rc"))
        idx = {r["ln"]: r for r in page_rows}
        for n, ln, s in parsed:
            if s:
                r = idx[n]
                r["lc"], r["rc"] = lc, rc
                r["L"] = place(r["left"], lc, len(LEFT))
                r["R"] = place(r["right"], rc, len(RIGHT))
                rows.append(r)
                continue
            if not ln.strip():
                provenance.skipped("empty")
                continue
            if HEAD.search(ln):
                provenance.skipped("header")
                continue
            ch = chunks(ln)
            last = rows[-1] if rows else None
            idx_x = None
            if last and last.get("rc"):
                idx_x = last["rc"][0] - (last["rc"][1] - last["rc"][0]) / 2
            if last and idx_x is not None and ch and all(x >= idx_x for x, _, _ in ch):
                more = place([(x, t) for x, _, t in ch], last["rc"], len(RIGHT))
                last["R"] = [f"{a} {b}".strip() for a, b in zip(last["R"], more)]
                last.setdefault("more", []).append(provenance.line_pos(pg, n, ln))
                provenance.skipped("text line")      # counted as a part of the row above, not a row of its own
                continue
            provenance.skip_line(ln, "no serial number and no ASHA ID")
    recs, seen, stats = [], {}, {"rows": 0, "continued": 0, "no_name": 0}
    for r in rows:
        L, R = dict(zip(LEFT, r["L"])), dict(zip(RIGHT, r["R"]))
        stats["rows"] += 1
        stats["continued"] += bool(r.get("more"))
        if not R["name"]:
            stats["no_name"] += 1
            provenance.skipped("no ASHA name")
            continue
        provenance.used()
        k = r["id"] if r["id"] not in seen else f"{r['id']}-r{r['serial']}"
        seen[r["id"]] = 1
        pop = R["population_covered"]
        pos = provenance.line_pos(r["pg"], r["ln"], r["line"])
        if r.get("more"):
            pos["continued_on"] = r["more"]
        recs.append(_esw.record(
            MODULE, f"{dslug}:{k}", dept="health", level="village", layer="village_worker", post="ASHA", post_regional="आशा",
            name=R["name"], husband_name=R["husband_name"], asha_id=r["id"], area=R["village"], village=R["village"],
            centre=L["sub_centre"], sub_centre=L["sub_centre"], facility=L["facility"], block=L["block"],
            district=p.get("district") or L["district"], district_as_written=L["district"],
            lgd_district_code=p.get("lgd_district_code"), state="UP",
            population_covered=int(pop) if re.fullmatch(r"\d{1,6}", pop or "") else (pop or None),
            serial=int(r["serial"]), source=url, src_url=url, page_url=p.get("page") or PAGE, src_pos=pos,
            table_row={"serial": r["serial"], "left": [t for _, t in r["left"]], "id": r["id"],
                       "right": [t for _, t in r["right"]]}))
    return recs, stats


def items(get=None):
    return _field.seed(MODULE)


def fetch(p, get):
    url = p["url"]
    f = get(url)
    if f is None:
        return [], [], "no answer"
    if f.content[:5] != b"%PDF-":
        return [], [], "the district file is not a PDF"
    dslug = _esw.slug(p.get("district") or "") or "x"
    files = [(f"depts/{MODULE}/{dslug}.pdf", f.content, "application/pdf")]
    text, engine = _field.pdf_text_engine(f.content)
    if not text.strip():
        return [], files, "no text layer (scanned PDF: needs OCR)"
    recs, stats = parse(text, url, p)
    src = provenance.at(f, url)
    for _, d in recs:
        d.update(src)
        d["method"] = f"pdf text ({engine}); ASHA ID splits the row; cell columns learned per page"
    return recs, files, "" if recs else f"no ASHA rows ({stats['rows']} rows seen)"
