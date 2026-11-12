"""Haryana: every polling station with its building and polling area (house-number ranges, town wards), from the CEO's lists of
polling stations. Two sets:
- ceoharyana.gov.in/WebCMS/Start/1867 "List of Polling Station as on 27-08-2024": 22 PDF links, one per district
  (/Website/ELECTIONCOMMISSION/Images/<uuid>.pdf). These are the seed items (items() reads the page).
- ceoharyana.gov.in/Website/ReviseListOfPollingBooth/<n>-<District>.pdf: the 2023 district files (one PDF per district, every AC
  of the district, ECI Annexure VI form: Sr. No., Locality, Building in which it will be located, Area of the P.S., separate
  entrance, Polling Areas, voters). Bhiwani: 84 pages, 4 ACs, dated 08-05-2023. Eight of these file names are known.
The site sends its certificate without the intermediate "GlobalSign GCC R46 AlphaSSL CA 2025": requests fails until that public
intermediate is in certs/ (certs_trust.py), see certs/globalsign_gcc_r46_alphassl_ca_2025.pem. Verification stays on.
Parsing (pdf_pages, pypdf layout mode): a row starts at a line whose first cell is the serial number; the cells of that first line
give the column starts; the next lines' cells join the column they start under. The AC comes from the "For 57-Bhiwani Assembly
Constituency" title, carried over pages. Town rows name the ward ("Town Bhiwani Ward No. 1"): kept as town / ward_no.
The district files differ a little in their columns; rows whose building cannot be found are left out. Only the 2023 Bhiwani
file is tested; the 2024 files were not fetched (3 live requests per source).
2024 district files (checked 2026-11-12 on Panipat, 89 pages, "Microsoft: Print To PDF" of an Excel sheet): Hindi. The titles are in
Kruti Dev ("& 24 ikuhir xzkeh.k fo/kkulHkk" = 24 Panipat Rural Vidhan Sabha; converted with dforms/_ward_kd), the cells in a
legacy Devanagari font map ("राजकȧय Ĥाईमरȣ èकू ल" = राजकीय प्राईमरी स्कूल; converted with dforms/sro_up.legacy, imported, not
changed; the PDF's own text is kept in station_raw / polling_area_raw). Columns: No. | polling station name (locality) | building |
polling area ("मतदाता ग्राम ...") | voters ("lHkh ernkrkvksa ds fy;s" = for all voters). Where a building takes two lines the
serial number stands on the second line, with the marks that hang below the first line: that number is moved up to the row.
Vowel signs that the PDF places on a line of their own (the "ु" of "रजापुर") are dropped: such names read "रजापर" (unchecked how
often). The note under each table ("उपरोक्त इन्द्राज तरतीबवार ...") ends the last row. Only the Panipat file was checked.
Record ids: dept:civic_pollst_hr:HR-<ac>-<part>. Layer "pollst". The PDF is kept in the bucket.
"""
import re

from provenance import line_pos
from dforms import _esw, _ward_kd
from dforms.sro_up import legacy

METHOD = "pdf text (pypdf layout), cells apart by 2+ spaces"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_pollst_hr"
INDEX = "https://ceoharyana.gov.in/WebCMS/Start/1867"
REVISE = "https://ceoharyana.gov.in/Website/ReviseListOfPollingBooth/"
KNOWN = ["4-Kurukeshtra", "5-Kaithal", "6-Karnal", "7-Panipat", "13-Bhiwani", "16-Jhajjar", "17-Narnaul", "19-Gurgoan"]
AC_RX = re.compile(r"(?i)For\s+(\d{1,3})\s*-\s*([A-Za-z .()&-]+?)\s*(?:\(\s*S\.?C\.?\s*\)\s*)?Assembly\s+Constituency")
ROW = re.compile(r"^\s{0,8}(\d{1,4})(?:\s{2,}|\s+(?=\d+\s*-)|$)")
AC_KD = re.compile(r"(?:&\s*)?(\d{1,3})\s*&?\s*([^\d&]+?)\s+fo/kkulHkk")      # Kruti Dev title of the 2024 files
MARKS = re.compile(r"[\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962\u0963]+")      # vowel signs alone (they hang below a line)
FOOT = re.compile(r"तरतीबवार|उपरो")            # the note under the table of the 2024 files
LEGACY = re.compile(r"[\u00a2-\u00ff\u0100-\u024f\u0250-\u02af\u0360-\u036f]")
AREA = re.compile(r"(?i)^(not\s+less|\d+\s*(sq|sqr|sq\.)|approx)")
YESNO = re.compile(r"(?i)^(yes|no)\b")
POLL = re.compile(r"(?i)^(part\s*no|voters?\b|ward\s*no|village|town|entire|मतदाता)")
WHOM = re.compile(r"(?i)^(for\s+all|all\s+voters|men\s+only|women\s+only|general)")
WHOM_KD = re.compile(r"^(lHkh\s+ernkrk|dsoy)")      # Kruti Dev "for all voters" / "only ..." (2024 files)


def item(url, district=""):
    name = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return {"key": f"{MODULE}-{_esw.slug(name)}"[:200], "payload": {"reader": MODULE, "url": url, "state": "HR",
                                                                    "district": district}}


def items(get=None):
    """Every PDF linked from the 2024 list page (one per district); without an answer, the 2023 district files. Both sets use
    the same record ids (AC and part), so only one set is queued at a time."""
    out = []
    r = get(INDEX) if get is not None else None
    if r is not None:
        for a in _esw.soup(r.text).find_all("a", href=True):
            h = a["href"]
            if h.lower().endswith(".pdf"):
                u = h if h.startswith("http") else "https://ceoharyana.gov.in" + ("" if h.startswith("/") else "/") + h
                it = item(u, _esw.clean(a.get_text(" ")))
                it["key"] = f"{MODULE}-2024-{_esw.slug(it['payload']['district'])}"
                it["payload"]["list"] = "2024-08-27"
                if all(o["key"] != it["key"] for o in out):
                    out.append(it)
    return out or [item(REVISE + n + ".pdf", n.split("-", 1)[1]) for n in KNOWN]


def cells(line):
    """(start column, text) of each cell of a layout line; cells are apart by 2+ spaces. "... H. For All" (the voters column
    one space after the polling area) is cut into two cells."""
    out = []
    for m in re.finditer(r"\S+(?:\s\S+)*", line):
        t, x = m.group(0), m.start()
        w = re.search(r"\s(For All(?: Voters)?)$", t)
        if w and w.start() > 0:
            out += [(x, t[:w.start()].strip()), (x + w.start(1), w.group(1))]
        else:
            out.append((x, t.strip()))
    return out


def split_first(cs):
    """Column roles of a row's first line: number cells first, then locality, building, area, entrance, polling areas, voters."""
    role, out = "num", []
    for x, t in cs:
        if MARKS.fullmatch(t):
            continue
        if role == "num" and re.fullmatch(r"\d{1,4}", t):
            out.append((x, "num", t))
            continue
        if AREA.match(t):
            role = "area"
        elif YESNO.match(t) and role in ("area", "building", "locality"):
            role = "entrance"
        elif POLL.match(t) and role in ("entrance", "area", "building", "locality"):
            role = "polling"
        elif WHOM.match(t) and role == "polling" or WHOM_KD.match(t):
            role = "whom"
        elif role == "num":
            role = "locality"
        elif role == "locality":
            role = "building"
        out.append((x, role, t))
    return out


def hindi(s):
    """Cell text of the 2024 files (legacy font map) -> Devanagari; English text is returned as it is."""
    return _esw.clean(legacy(s)) if LEGACY.search(s or "") else s


def number_up(lines):
    """Move a serial number that stands on the line under its row's first line (with the marks that hang below that line and,
    sometimes, the end of the polling area) up to that first line."""
    out = list(lines)
    for i, ln in enumerate(out):
        m = re.match(r"^\s{0,8}(\d{1,4})(?=\s|$)", ln)
        if not m or len([c for _, c in cells(ln) if not MARKS.fullmatch(c)]) >= 3:
            continue
        j = i - 1
        while j >= 0 and not out[j].strip():
            j -= 1
        num = m.group(1)
        if j < 0 or i - j > 2 or ROW.match(out[j]) or len(cells(out[j])) < 3 or out[j][:len(num) + 1].strip():
            continue
        out[j] = num + out[j][len(num):]
        out[i] = " " * len(num) + ln[len(num) + (m.start(1)):]
    return out


def parse(pages, url, district=""):
    recs, seen, ac, ac_name = [], set(), None, ""
    for pn, text in enumerate(pages, 1):
        lines = number_up(text.splitlines())
        rows, cur = [], None
        for ln_no, ln in enumerate(lines, 1):
            m = AC_RX.search(ln)
            if m:
                ac, ac_name = int(m.group(1)), _esw.clean(m.group(2))
                continue
            m = AC_KD.search(ln)
            if m:
                ac, ac_name = int(m.group(1)), _esw.clean(_ward_kd.convert(m.group(2)))
                continue
            if not ln.strip():
                continue
            if FOOT.search(ln):
                cur = None
                continue
            if ROW.match(ln) and len(cells(ln)) >= 3:
                cur = {"ac": ac, "ac_name": ac_name, "first": split_first(cells(ln)), "more": [], "pos": line_pos(pn, ln_no, ln)}
                rows.append(cur)
            elif cur is not None:
                cur["more"].append(cells(ln))
        for r in rows:
            cols = {}
            starts = [(x, role) for x, role, _ in r["first"] if role != "num"]
            for x, role, t in r["first"]:
                cols.setdefault(role, []).append(t)
            for cs in r["more"]:
                for x, t in cs:
                    if MARKS.fullmatch(t):
                        continue
                    if POLL.match(t) and all(role != "polling" for _, role in starts):
                        starts = sorted(starts + [(x, "polling")])
                    under = [role for sx, role in starts if sx <= x + 3]
                    if under:
                        cols.setdefault(under[-1], []).append(t)
            part = cols["num"][0] if cols.get("num") else ""
            building_raw = _esw.clean(" ".join(cols.get("building", [])))
            polling_raw = _esw.clean(" ".join(cols.get("polling", [])))
            building, polling = hindi(building_raw), hindi(polling_raw)
            locality = re.sub(r"^\d+\s*-\s*", "", hindi(_esw.clean(" ".join(cols.get("locality", [])))))
            if not part or not building or r["ac"] is None or (r["ac"], part) in seen:
                continue
            seen.add((r["ac"], part))
            town = re.search(r"\b(?:Town|City)\s+([A-Z][A-Za-z.]+(?:\s(?!Ward\b)[A-Z][A-Za-z.]+)?)", polling)
            ward = re.search(r"(?i)\bWard\s*No\.?\s*-?\s*(\d+)", polling)
            key = f"HR-{r['ac']}-{part}"
            recs.append(_esw.record(MODULE, key, dept="elections", level="polling_station", area=building, state="HR",
                                    district=district, office_id=key, source=url, layer="pollst", ac_no=r["ac"],
                                    ac_name=r["ac_name"], part_no=part, station=building, locality=locality,
                                    polling_area=polling[:1000], town=town.group(1) if town else None,
                                    ward_no=ward.group(1) if ward else None, src_pos=r["pos"],
                                    station_raw=building_raw if building_raw != building else None,
                                    polling_area_raw=polling_raw[:1000] if polling_raw != polling else None))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    name = _esw.slug(p["url"].rsplit("/", 1)[-1].rsplit(".", 1)[0])
    files = [_esw.keep(MODULE, name, r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a PDF"
    recs = parse(_esw.pdf_pages(r.content), p["url"], p.get("district", ""))
    return recs, files, "" if recs else "no rows"
