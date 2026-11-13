"""Bihar: the Block Development Officer (BDO) of every block and the Circle Officer (CO, head of the anchal = LGD sub-district) of
every circle, with the official CUG mobile, from the state portal pages of two departments (betastate.bihar.gov.in; answers only
from India: this box gets a TLS reset, vpsin gets the pages).

- bdo: Rural Development Department, "MOBILE NUMBERS OF BLOCK DEVELOPMENT OFFICERS" (betastate.bihar.gov.in/rdd/DyPageView?
  PageTitleID=1573). The page (ASP.NET, table#GridView1) links one PDF (2026-11-11: /file_2/FileUpload/2026/Oct/09-Oct-2026/9/
  DyPage/ab30439c-....pdf, 13 pages, printed from Excel on 2024-07-24). Columns: S.No. | District Name | Block Name | DESIGNATION |
  Mobile No; 534 rows (one per block), 38 districts; no names. The district cell is merged over its blocks and its text sits in the
  middle of the merged cell, sometimes on its own line, and a district that runs over a page break is printed on one page or on
  both. So the reader uses the drawn grid: pypdf gives every text piece with its position and the table rules
  (dforms/_util2_pdfgrid.page_parts, imported, not changed); a block row is the band between the rules that cross the block
  column, the district is the text in the band between the rules that cross the district column. A band without district text at
  the top (bottom) of a page takes the district of the last (first) band of the page before (after).
- co: Revenue and Land Reforms Department, "LIST OF CIRCLE OFFICERS" (betastate.bihar.gov.in/lrc/DyPageView?PageTitleID=10428):
  one HTML table (DataTables_Table_0): Sl. No | District | ALLOTTEE POST NAME ("Circle Officer, Araria Sadar") | Mobile No;
  537 rows on 2026-11-11 (LGD: 537 sub-districts in Bihar). The page is 4.6 MB (inline styles), one GET.
- dclr: the same department's "LIST OF DCLR" (Deputy Collector Land Reforms, one per sub-division; PageTitleID=10424). NOT
  fetched while writing this reader (host request limit): read with the CO table rules, and if the page only links a file, that
  file is read with the BDO grid rules. Unverified.

Records: bdo -> dept rural_development, level block, post "Block Development Officer"; co -> revenue, subdistrict, "Circle
Officer"; dclr -> revenue, subdivision, "Deputy Collector Land Reforms". Area = the block / circle / sub-division as written
(title case), district = the LGD district name (district()). Phones are CUG numbers of the post (no names in these lists).
One queue item per list: bdo 2 GETs (page + PDF), co 1 GET, dclr 1-2 GETs. Record ids: dept:sub3_br:<kind>:<district slug>:<area slug>[:n].
"""
import io
import re

from dforms import _esw
import provenance

METHOD = "html table"     # co / dclr; the bdo list is read from its PDF: "pdf ruled table (pypdf text pieces + rules)"
METHOD_PDF = "pdf ruled table (pypdf text pieces + rules)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub3_br"
BASE = "https://betastate.bihar.gov.in"
SOURCES = {   # kind: (page, dept, level, post, expected rows)
    "bdo": (f"{BASE}/rdd/DyPageView?PageTitleID=1573", "rural_development", "block", "Block Development Officer", 534),
    "co": (f"{BASE}/lrc/DyPageView?PageTitleID=10428", "revenue", "subdistrict", "Circle Officer", 537),
    "dclr": (f"{BASE}/lrc/DyPageView?PageTitleID=10424", "revenue", "subdivision", "Deputy Collector Land Reforms", 101),
}
LGD = {"188": "Araria", "189": "Aurangabad", "190": "Banka", "191": "Begusarai", "192": "Bhagalpur", "193": "Bhojpur", "194": "Buxar",
       "195": "Darbhanga", "196": "Gaya", "197": "Gopalganj", "198": "Jamui", "199": "Jehanabad", "200": "Kaimur (Bhabua)",
       "201": "Katihar", "202": "Khagaria", "203": "Kishanganj", "204": "Lakhisarai", "205": "Madhepura", "206": "Madhubani",
       "207": "Munger", "208": "Muzaffarpur", "209": "Nalanda", "210": "Nawada", "211": "Pashchim Champaran", "212": "Patna",
       "213": "Purbi Champaran", "214": "Purnia", "215": "Rohtas", "216": "Saharsa", "217": "Samastipur", "218": "Saran",
       "219": "Sheikhpura", "220": "Sheohar", "221": "Sitamarhi", "222": "Siwan", "223": "Supaul", "224": "Vaishali", "611": "Arwal"}
_KEY = {re.sub(r"[^a-z]", "", n.lower()): (c, n) for c, n in LGD.items()}
ALIAS = {"auranagabad": "189", "kaimur": "200", "kaimurbhabua": "200", "bhabua": "200", "eastchamparan": "213",
         "westchamparan": "211", "purnea": "214", "paschimchamparan": "211", "purvichamparan": "213", "purbichamparan": "213",
         "pashchimchamparan": "211", "sekhpura": "219", "sheikpura": "219", "jahanabad": "199", "monghyr": "207", "purniya": "214"}
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
ROLE = (("sn", r"s\.?\s*no|sl\.?\s*no"), ("district", r"district"), ("area", r"block|circle|anchal|sub-?\s*div|post\s*name|allottee"),
        ("post", r"desig"), ("mobile", r"mobile|contact|phone|cug"))


def items(get=None):
    return [{"key": f"sub3_br_{k}", "payload": {"reader": MODULE, "url": url, "kind": k, "state": "BR", "india_only": True,
                                                "expected": n}}
            for k, (url, _, _, _, n) in SOURCES.items()]


def district(name):
    """(LGD name, LGD code) for the lists' spelling ("AURANAGABAD", "East Champaran", "KAIMUR (BHABUA)")."""
    k = re.sub(r"[^a-z]", "", (name or "").lower())
    if k in ALIAS:
        return LGD[ALIAS[k]], ALIAS[k]
    if k in _KEY:
        c, n = _KEY[k]
        return n, c
    return _esw.clean(name).title(), ""


def title(s):
    s = _esw.clean(s)
    return s.title() if s.isupper() or s.islower() else s


# ---------------------------------------------------------------- the BDO PDF (merged district cells)

def _role(text):
    t = _esw.clean(text).lower()
    for role, rx in ROLE:
        if re.search(rx, t):
            return role
    return ""


def _columns(texts, vlines):
    """[(x0, x1, role)] from the header row (the line that holds 'Mobile' and 'Block'/'District'); None without a header."""
    head = [t for t in texts if re.search(r"(?i)mobile|contact", t[2])]
    if not head:
        return None
    y = head[0][1]
    words = sorted((t for t in texts if abs(t[1] - y) < 3), key=lambda t: t[0])
    xs = []
    for x in sorted({round(v[0]) for v in vlines if v[1] < y < v[2] or v[2] - v[1] > 100}):
        if xs and x - xs[-1] < 4:
            continue
        xs.append(x)
    if len(xs) < 3:      # no rules: borders midway between the header words
        xs = [0] + [(a[0] + b[0]) / 2 for a, b in zip(words, words[1:])] + [10000]
    cols = []
    for x0, x1 in zip(xs, xs[1:]):
        text = " ".join(w[2] for w in words if x0 - 2 <= w[0] < x1 - 2)
        cols.append((x0, x1, _role(text)))
    return cols, y


def _col(cols, x):
    for x0, x1, role in cols:
        if x0 - 3 <= x < x1 - 3:
            return role
    return ""


def _band(hlines, x0, x1, y):
    """(top, bottom) of the cell around y: the nearest rules above and below that cross the middle of column [x0, x1]."""
    cx = (x0 + x1) / 2
    ys = [ly for a, b, ly in hlines if a - 1 <= cx <= b + 1]
    above = [ly for ly in ys if ly > y + 1]
    below = [ly for ly in ys if ly < y - 1]
    return (min(above) if above else 10000.0), (max(below) if below else -10000.0)


def _labels(pieces):
    """District pieces of one band -> [(text, y)]: pieces less than 20 points apart are one label ("PASHCHIM" / "CHAMPARAN")."""
    out = []
    for a in sorted(pieces, key=lambda a: -a[1]):
        if out and out[-1][2] - a[1] < 20:
            out[-1] = (out[-1][0] + " " + _esw.clean(a[2]), (out[-1][1] * out[-1][3] + a[1]) / (out[-1][3] + 1), a[1], out[-1][3] + 1)
        else:
            out.append((_esw.clean(a[2]), a[1], a[1], 1))
    return [(t, y) for t, y, _, _ in out]


def _split(band, labels, rows, first=False):
    """[(district text, rows)] of one district band, top to bottom. A band can hold more than one district cell, because the PDF
    leaves out some rules: two labels in one band (Katihar / Khagaria on page 5), or a label below rows of the district before it
    that ran over the page break (page 13: the last Siwan rows above Supaul). Each label sits in the middle of its cell, so from a
    known edge the cell ends at 2 * label - edge. With a rule below the band the cells are measured from the bottom up, and rows
    above the first cell go into a group without a label (filled later from the page before) when the band is the first one
    of its page, else they join the first cell (labels are not always in the exact middle); without a rule below (the band runs
    to the page end) cells are measured from the top down."""
    if not labels:
        return [("", rows)]
    out = []
    if band[1] > -1000:
        bottom = band[1]
        for text, y in reversed(labels):
            top = 2 * y - bottom
            out.insert(0, (text, [r for r in rows if bottom < r["y"] <= top + 8]))
            bottom = top + 8
        rest = [r for r in rows if r["y"] > bottom]
        if rest and not first:
            out[0] = (out[0][0], rest + out[0][1])
            rest = []
        return ([("", rest)] if rest else []) + out
    top = band[0]
    for i, (text, y) in enumerate(labels):
        bottom = 2 * y - top if i + 1 < len(labels) else band[1]
        out.append((text, [r for r in rows if bottom < r["y"] <= top]))
        top = bottom
    return out


def pdf_rows(content):
    """[{district, area, post, mobile, page}] of a gridded list PDF (the BDO list), districts filled across merged cells and pages."""
    from pypdf import PdfReader
    from dforms._util2_pdfgrid import page_parts
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception:  # noqa: BLE001 - not a readable PDF
        return []
    groups, cols = [], None         # groups: [page, band, district text, [rows]]
    for pno, page in enumerate(reader.pages, 1):
        texts, hlines, vlines = page_parts(reader, page)
        found = _columns(texts, vlines)
        if found:
            cols, head_y = found
        elif cols is None:
            continue
        else:
            head_y = 10000.0
        byrole = {role: (x0, x1) for x0, x1, role in cols if role}
        if "mobile" not in byrole or "area" not in byrole:
            continue
        dcol = byrole.get("district")
        body = [t for t in texts if t[1] < head_y - 3 and _esw.clean(t[2])]
        body.sort(key=lambda a: -a[1])
        mobiles = [t for t in body if _col(cols, t[0]) == "mobile" and MOBILE.search(t[2])]
        rows = [{"y": t[1], "pieces": [], "post": "", "mobile": MOBILE.search(t[2]).group(0), "page": pno, "district": ""}
                for t in mobiles]
        # Rows have one text line each: a piece on a row's line (within 3 points) belongs to it. A piece on no row's line is text
        # that ran out of its cell (Excel overflow: "SONBHADRA BANSI" / "SURYAPUR" printed over the next row): it goes to the
        # nearest row above it (within 20 points), else to the nearest row below. The rules between rows are not used: the
        # PDF leaves many of them out.
        for a in body:
            role = _col(cols, a[0])
            if role not in ("area", "post") or not rows:
                continue
            on = [r for r in rows if abs(r["y"] - a[1]) < 3]
            # a piece a point off a row's line while another piece sits exactly on it ran over from the cell above ("SURYAPUR")
            if on and abs(on[0]["y"] - a[1]) >= 0.5 and any(abs(b[1] - on[0]["y"]) < 0.5 and _col(cols, b[0]) == role
                                                          for b in body):
                on = []
            if on:
                target = on[0]
            else:
                above = [r for r in rows if 0.5 < r["y"] - a[1] < 20]
                target = min(above, key=lambda r: r["y"] - a[1]) if above else min(rows, key=lambda r: abs(r["y"] - a[1]))
            if role == "area":
                target["pieces"].append(a)
            else:
                target["post"] = _esw.clean(target["post"] + " " + a[2])
        for r in rows:
            r["area"] = " ".join(_esw.clean(a[2]) for a in sorted(r.pop("pieces"), key=lambda a: -a[1]))
        page_groups = {}
        for r in rows:
            band = _band(hlines, *dcol, r["y"]) if dcol else (10000.0, -10000.0)
            page_groups.setdefault(band, []).append(r)
        for n, band in enumerate(sorted(page_groups, key=lambda b: -b[0])):
            labels = _labels([a for a in body if dcol and _col(cols, a[0]) == "district" and band[1] < a[1] < band[0]])
            for text, part in _split(band, labels, page_groups[band], first=n == 0):
                groups.append([pno, band, text, part])
    for i, g in enumerate(groups):
        if g[2]:
            continue
        prev = groups[i - 1] if i else None
        nxt = groups[i + 1] if i + 1 < len(groups) else None
        first = prev is None or prev[0] != g[0]
        last = nxt is None or nxt[0] != g[0]
        if first and prev and prev[2]:
            g[2] = prev[2]
        elif last and nxt and nxt[2]:
            g[2] = nxt[2]
    out = []
    for g in groups:
        for r in g[3]:
            r["district"] = g[2]
            r["y_pt"] = round(r.pop("y", 0) or 0, 1)        # source trail: the mobile's baseline on its page
            out.append(r)
    return out


# ---------------------------------------------------------------- the CO / DCLR HTML tables

def html_rows(html):
    """[{district, area, post, mobile}] of the first table whose header has a district and a mobile column."""
    for t in _esw.soup(html).find_all("table"):
        tp = []
        g = _esw.grid(t, pos=tp)
        if not g:
            continue
        roles = [_role(c) for c in g[0]]
        if "mobile" not in roles or "district" not in roles:
            continue
        ix = {r: roles.index(r) for r in set(roles) if r}
        out = []
        for r, rp in zip(g[1:], tp[1:]):
            if len(r) < len(roles):
                provenance.skip_row(r, 'skip: len(r) < len(roles)')
                continue
            post_area = r[ix["area"]] if "area" in ix else ""
            out.append({"district": r[ix["district"]], "area": post_area, "post": r[ix["post"]] if "post" in ix else "",
                        "mobile": r[ix["mobile"]], "pos": rp})
        return out
    return []


def split_post(text, post):
    """'Circle Officer, Araria Sadar' -> 'Araria Sadar'; 'DCLR,Sadar Araria' -> 'Sadar Araria'; a bare place stays."""
    t = _esw.clean(text)
    m = re.match(r"(?i)^\s*(circle\s*officer|c\.?\s*o\.?|anchal\s*adhikari|d\.?\s*c\.?\s*l\.?\s*r\.?|deputy\s*collector[^,]*|"
                 r"block\s*development\s*officer|b\.?\s*d\.?\s*o\.?)\s*[,:\-]?\s*(.*)$", t)
    return _esw.clean(m.group(2)) if m and m.group(2) else (t if not re.fullmatch(r"(?i)[a-z. ]*officer|bdo|co|dclr", t) else "")


def file_link(html):
    """The first list file the page links (table#GridView1 rows: data-id / a href)."""
    s = _esw.soup(html)
    t = s.find("table", id="GridView1") or s
    for tr in t.find_all("tr"):
        for href in [tr.get("data-id")] + [a.get("href") for a in tr.find_all("a")]:
            if href and re.search(r"(?i)\.(pdf|xlsx?)(\?|$)", href):
                return href
    return None


def build(kind, rows, source, src=None):
    """src: provenance.at(answer) the rows came from (the bdo item reads the page and then the PDF)."""
    _, dept, level, post, _ = SOURCES[kind]
    recs, seen = [], set()
    for r in rows:
        area = title(re.sub(r"(?i)\s+(block|prakhand)$", "", split_post(r["area"], post) if kind != "bdo" else r["area"]))
        phone = _esw.phones(r["mobile"])
        if not area or not phone:
            provenance.skip_row(r, 'skip: not area or not phone')
            continue
        dist, dc = district(r["district"])
        base = f"{kind}:{_esw.slug(dist)}:{_esw.slug(area)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept=dept, level=level, area=area, post=post, phone=phone, district=dist,
                                district_code=dc, state="BR", source=source,
                                **({"page": r["page"]} if r.get("page") else {}),
                                src_pos=r.get("pos") or ({"page": r["page"], "y": r.get("y_pt"), "line_text": r["mobile"]}
                                                         if r.get("page") else None),
                                method=METHOD_PDF if r.get("page") else METHOD, **(src or {})))
    return recs


def fetch(p, get):
    kind = p.get("kind", "bdo")
    url = p.get("url") or SOURCES[kind][0]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, kind, r.content)]
    rows = [] if kind == "bdo" else html_rows(r.text)
    source, src = url, provenance.at(r, url)
    if not rows:
        link = file_link(r.text)
        if not link:
            return [], files, "no table and no list file on the page"
        source = link if link.startswith("http") else BASE + "/" + link.lstrip("/")
        f = get(source)
        if f is None:
            return [], files, "no answer for the list file"
        if f.content[:5] != b"%PDF-":
            return [], files, "the list file is not a PDF"
        files.append((f"depts/{MODULE}/{kind}.pdf", f.content, "application/pdf"))
        rows = pdf_rows(f.content)
        src = provenance.at(f, source)
    recs = build(kind, rows, source, src)
    return recs, files, "" if recs else "no rows"
