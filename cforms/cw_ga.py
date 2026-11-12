"""Goa municipal councils: elected councillors from the Goa State Election Commission (sec.goa.gov.in), "winning candidates" /
"elected members" PDFs of each general election (India only).

State in 2026-11: the 11 councils elected in 2021 (Mapusa, Margao, Mormugao, Bicholim, Canacona, Curchorem-Cacora, Cuncolim,
Pernem, Quepem, Sanguem, Valpoi) have no elected council: their term ended on 25-26 May 2026, the government appointed
administrators, and the SEC notified the draft ward division for their next poll in Nov 2026. Ponda (15 wards) and Sanquelim
(12 wards) were elected on 5 May 2023 and are the only councils in office. Panaji (CCP 2026) is read by cforms/city.py.
items(get) reads the SEC's previous and ongoing election pages, finds the municipal council elections of 2023 or later, and
lists their winners PDFs. So a new general election of the 11 councils is found when its results are on the site.
fetch(p, get) reads the PDF's text layer: one block per "Ward No. <roman or digits>" (the SEC's layout, as in the CCP file),
the name in capitals, the seat category in brackets, "Unopposed" when no poll was held.
Record id councillor:GA:<council slug>:<ward>.
"""
import hashlib
import io
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

METHOD = "pdf text (pypdf layout)"     # seed step (items): html pages     # source trail (provenance.py): how this reader reads its sources

BASE = "https://sec.goa.gov.in/"
START = ("elections/previous/municipal-council/", "elections/ongoing/")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
# "Ward No. I", "Ward No.XII" (Ponda 2023), "WARD I (ONE)", "WARD XII" (Sanquelim 2023), "Ward IX" (Sanquelim bye-election)
WARD = re.compile(r"\b(?:Ward|WARD)\s*(?:No\.?)?\s*[:\-]?\s*([IVXLC]+|\d{1,2})\b")
# the number in words after a roman ward number: "WARD XII (TWELEVE)"; not the seat category
NUMBER_WORD = re.compile(r"(?i)^(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twel\w*|\w+teen|twenty[\w -]*)$")
# column heads and titles: never part of a name
HEADWORDS = re.compile(r"(?i)\b(sr\.?\s*no|mun?icipality|name of|candidate|address|category|ward name|elected candidates|election|"
                       r"municipal|council)\b|^&$|^\d+$")
COUNCIL = re.compile(r"(?:General|Bye)[\s-]*Election\s+to\s+(?:the\s+)?([A-Z][A-Za-z\- ]+?)\s+Municipal\s+Council\s*[-–,]?\s*(20\d\d)?", re.I)
BYE_TITLE = re.compile(r"Ward\s*No\.?\s*[IVXLC\d]+\s+of\s+([A-Z][A-Za-z\- ]+?)\s+Municipal\s+Council()", re.I)   # "... for Ward No.IX of Sanquelim Municipal Council"
DISTRICT = {"ponda": "South Goa", "sanquelim": "North Goa", "mapusa": "North Goa", "bicholim": "North Goa", "pernem": "North Goa",
            "valpoi": "North Goa", "margao": "South Goa", "mormugao": "South Goa", "cuncolim": "South Goa", "canacona": "Kushavati",
            "curchorem": "Kushavati", "quepem": "Kushavati", "sanguem": "Kushavati"}


def roman(s):
    if s.isdigit():
        return int(s)
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = ROMAN[a]
        total += -v if b != " " and ROMAN.get(b, 0) > v else v
    return total


def clean(s):
    return " ".join((s or "").split())


def links(html, url):
    """(absolute url, text) of every link on a page of the site."""
    soup = BeautifulSoup(html, "lxml")
    b = soup.find("base", href=True)              # the site's pages carry <base href="../../">: links are relative to it
    base = urljoin(url, b["href"]) if b else url
    return [(urljoin(base, a["href"]), clean(a.get_text(" "))) for a in soup.find_all("a", href=True)]


def year_of(*texts):
    ys = [int(y) for t in texts for y in re.findall(r"(20\d\d)", t or "")]
    return max(ys) if ys else None


def election_pages(html, url):
    """Pages of single municipal council elections linked from a list page (deeper than the list itself)."""
    out = []
    for u, t in links(html, url):
        if u.startswith(BASE) and "/elections/" in u and "municipal" in (u + " " + t).lower() and not u.lower().endswith(".pdf") \
                and u.rstrip("/").count("/") > url.rstrip("/").count("/") and "panaji" not in u.lower():
            out.append((u, t))
    return list({u: (u, t) for u, t in reversed(out)}.values())[::-1]      # one entry per url (first text wins)


def winners_pdfs(html, url):
    return [(u, t) for u, t in links(html, url) if u.lower().endswith(".pdf")
            and re.search(r"winning|elected|winner|result", (u + " " + t).lower()) and not re.search(r"sheet|panaji|ccp", u.lower())
            and not re.search(r"order|number of|no-of-|dma-ward", (u + " " + t).lower())]   # orders fixing the number of seats


def items(get):
    """Winners PDFs of municipal council elections of 2023 or later; a page without PDFs is followed one level deeper."""
    todo = []
    for s in START:
        r = get(urljoin(BASE, s))
        if r is not None:
            todo += [(u, t, 0) for u, t in election_pages(r.text, urljoin(BASE, s))]
    out, seen, visited = [], set(), set()
    while todo:
        u, t, depth = todo.pop(0)
        y = year_of(u, t)
        if u in visited or (y is not None and y < 2023):    # 2021 councils: term over (May 2026), not in office
            continue
        visited.add(u)
        r = get(u)
        if r is None:
            continue
        pdfs = winners_pdfs(r.text, u)
        if not pdfs and depth < 1:
            todo += [(v, vt, depth + 1) for v, vt in election_pages(r.text, u)]
        for pdf, pt in pdfs:
            y2 = year_of(pdf, pt) or y
            if pdf in seen or (y2 is not None and y2 < 2023):
                continue
            seen.add(pdf)
            out.append({"key": "ga-" + hashlib.sha1(pdf.encode()).hexdigest()[:10],
                        "payload": {"kind": "form-cw_ga", "state": "GA", "url": pdf, "page": u, "title": pt or t,
                                    "year": y2}})
    return out


def parse(text, p, pages=None):
    """[(record id, record)] from the text of one winners PDF. pages: the page texts (joined by "\n" = text), for src_pos."""
    m = COUNCIL.search(text) or COUNCIL.search(p.get("title") or "") or BYE_TITLE.search(p.get("title") or "")
    council = clean(m.group(1)).title() if m else (p.get("body") or "")
    year = (m.group(2) if m and m.group(2) else None) or p.get("year")
    slug = re.sub(r"[^a-z0-9]+", "-", council.lower()).strip("-") or "x"
    marks = list(WARD.finditer(text))
    cols = column_names(text, marks)
    recs, seen = [], set()
    for k, w in enumerate(marks):
        block = text[w.end(): marks[k + 1].start() if k + 1 < len(marks) else len(text)]
        block = COUNCIL.sub(" ", block)
        cat = next((c for c in re.finditer(r"(?<!\S)\(([^)]{2,40})\)", block) if not NUMBER_WORD.match(c.group(1).strip())), None)
        unopposed = bool(re.search(r"unopposed", block, re.I))
        rest = re.sub(r"\([^)]*\)|[-–]\s*unopposed|unopposed|Elected Candidates?( for)?|Sr\.?\s*No\.?|Name of (the )?(elected )?candidate"
                      r"|Category|Ward|Party|\b\d+\b", " ", block, flags=re.I)
        caps = re.findall(r"[A-Z][A-Z.'\-]+(?:\s+[A-Z][A-Z.'\-]+)+", rest)
        name = cols.get(k) or (clean(max(caps, key=len)) if caps else clean(rest))
        ward = str(roman(w.group(1)))
        if not name or ward in seen or len(name) > 80:
            continue
        seen.add(ward)
        recs.append((f"councillor:GA:{slug}:{ward}",
                     {"type": "councillor", "state": "GA", "body": f"{council} Municipal Council", "body_en": council,
                      "body_type": "Municipality", "district": DISTRICT.get(slug.split("-")[0], ""), "ward_no": ward,
                      "ward_roman": w.group(1), "name": name, "reservation": clean(cat.group(1)) if cat else None,
                      "unopposed": unopposed or None, "election": f"Goa municipal councils {year}" if year else None,
                      "url": p["url"], "page_url": p.get("page"), "src_pos": ward_pos(text, w.start(), pages)}))
    return recs


def _chunks(line):
    """(start, end, text) of each run of words in a layout line (words split by 2+ spaces)."""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def column_names(text, marks):
    """{index of ward mark: name} read by column, for the SEC's table layout (ward | name | address in columns side by side; the
    name and the address can each run over 2-3 lines). The ward heading and the "(Category)" lines fix the ward column; lines
    with two cells right of it give the name column (left) and the address column (right); every other cell goes to the
    nearer of the two. {} when the text has no such layout (then parse() takes the longest run of capitals)."""
    lines = text.split("\n")
    starts, n = [], 0
    for ln in lines:
        starts.append(n)
        n += len(ln) + 1
    line_of = lambda at: max(i for i, s in enumerate(starts) if s <= at)     # noqa: E731
    blocks = []
    for k, w in enumerate(marks):
        a, b = line_of(w.start()), (line_of(marks[k + 1].start()) if k + 1 < len(marks) else len(lines))
        cells = []
        for i in range(a, b):
            for s, e, c in _chunks(lines[i]):
                if i == a and s <= w.start() - starts[a] < e:
                    cells.append((i, s, e, c, "ward"))
                elif re.fullmatch(r"\([^)]*\)", c):
                    cells.append((i, s, e, c, "ward"))
                elif not HEADWORDS.search(c) and not WARD.search(c):
                    cells.append((i, s, e, c, None))
        blocks.append(cells)
    ward_c = [(s + e) / 2 for cells in blocks for _, s, e, _, kind in cells if kind == "ward"]
    if not ward_c:
        return {}
    wc = sorted(ward_c)[len(ward_c) // 2]
    left, right = [], []
    for cells in blocks:
        by_line = {}
        for i, s, e, c, kind in cells:
            if kind is None and (s + e) / 2 > wc + 8:
                by_line.setdefault(i, []).append((s + e) / 2)
        for cs in by_line.values():
            if len(cs) == 2:
                left.append(min(cs))
                right.append(max(cs))
    if not left:
        return {}
    nc, ac = sorted(left)[len(left) // 2], sorted(right)[len(right) // 2]
    out = {}
    for k, cells in enumerate(blocks):
        parts = [c for i, s, e, c, kind in cells if kind is None and (s + e) / 2 > wc + (nc - wc) / 2
                 and abs((s + e) / 2 - nc) < abs((s + e) / 2 - ac)]
        name = clean(re.sub(r"\s*[-–]?\s*unopposed\b", " ", " ".join(parts), flags=re.I)).strip(" -–,")
        if name:
            out[k] = name
    return out


def ward_pos(text, at, pages=None):
    """src_pos of the ward heading at char `at`: page (when the page texts are known), 1-based line in that page, the line."""
    n = text.count("\n", 0, at) + 1
    line = text.split("\n")[n - 1]
    for pg, t in enumerate(pages or [], 1):
        k = t.count("\n") + 1
        if n <= k:
            return {"page": pg, "line": n, "line_text": line}
        n -= k
    return {"line": n, "line_text": line}


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    from pypdf import PdfReader
    try:
        pages = [pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(io.BytesIO(r.content)).pages]
        text = "\n".join(pages)
    except Exception as e:  # noqa: BLE001
        return [], [], f"pdf: {type(e).__name__}"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    files = [(f"councillors/GA/{key}.pdf", r.content, "application/pdf")]
    recs = parse(text, p, pages)
    return recs, files, "" if recs else ("no text layer" if len(text.strip()) < 50 else "no wards read")
