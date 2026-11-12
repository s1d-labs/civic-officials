"""Brihanmumbai Municipal Corporation (BMC / MCGM, LGD 251488): the water department staff of each administrative ward (Assistant
Engineer, Sub Engineers and Junior Engineers of Water Works) with mobiles, ward emails and their beats (the electoral wards /
prabhags and localities each engineer covers), from the "Water Dept" PDF in each ward's documents folder on the MCGM portal.

Source: https://portal.mcgm.gov.in/irj/go/km/docs/documents/D%20Ward/Water%20Dept.pdf (D ward, 2 pages, Word 2016 file created
2022-12-14; the file shows no "last updated" date). Table: Sr. No. | Designation ("A.E. (W)", "S.E. (W)", "J.E. (W)") | Name
("Shri. Prashant V. Bagwe.") | Contact No. ("9930260470 / 9819292591") | Beat ("215, 216, Part 217", "D Ward" for the AE) | Beat
Area ("Mumbai Central, Khetwadi, Part Tardeo ...") | Email ID ("aeww.d@mcgm.gov.in"). Cells are merged across rows: some Junior
Engineers have a second beat row "214,215,216,217,218 & 219 | Water Maintenance", and a row can continue on the next page.
The other wards' files: each ward's documents page (/irj/portal/anonymous/qlwrd<x>, list "प्रभागांची यादी" qlallward) shows its KM
folder in an iframe (/irj/servlet/prt/portal/prtroot/pcd!3aportal_content!2fMCGM!2f...!2fcom.mcgm.Ward<x>); the reader reads that
frame and takes every PDF whose name names water. When the frame gives no PDF it tries "<X> Ward/Water Dept.pdf" (the D ward
pattern). Only the D ward file and the D ward page were sampled (2026-11-11, request limit): the frame listing and the other
wards' file names are not checked yet. K/North and P/East have no documents page on the ward list.
The portal needs a normal desktop browser User-Agent (owner's permission for portal.mcgm.gov.in and dm.mcgm.gov.in only,
2026-11-11): ward2n_mumbai.UA. It answers from Germany.

Reading the PDF: pypdf only (the hub's runners have no pdfplumber). The table borders are thin filled rectangles in the page
content ("re"); vertical ones give the columns, horizontal ones that cover a column give that column's cell bands. Each text piece
(visitor_text position) goes to the cell (column, band) it starts in. A row = one numbered band of the Sr. No. column; officer cells
(designation, name, contact, email) go to the row whose Sr. No. band holds their centre; beat / beat-area cells are sub-rows of that
row (paired by band); cells above the first numbered row of a page continue the last row of the page before. Columns are named
from the heading row (Sr / Designation / Name / Contact / Beat / Beat Area / Email); a page without a heading uses the page before.
Records (level "ward", dept town_body, wing water; _ward.record): post in full ("Assistant Engineer (Water Works)", post_abbr as
written), name without title, phone, email, wards = prabhag numbers of all beats (the AE's beat "D Ward" = every prabhag in the
file), part_wards = prabhags written "Part 217", beats = [{"beat", "area", "wards", "part_wards"}], maintenance True for a "Water
Maintenance" beat, role "head" for the Assistant Engineer. Ids: dept:ward2n_mumbai_water:<ward>:<sr>. Expected rows: 7 for D
ward; about 5-12 per ward, ~200 for 24 wards (if every ward publishes the file).
"""
import html as _html
import io
import re
from urllib.parse import quote, unquote, urljoin

from dforms import _esw, _ward
from dforms.ward2n_mumbai import BASE, BODY, DISTRICT, LGD, STATE, UA, WARDS

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + pdf tables (pdfplumber)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_mumbai_water"
KM = f"{BASE}/irj/go/km/docs/documents"
WATER = re.compile(r"(?i)water|hydraul|\bw\.?\s?w\b|जल|पाणी")
POSTS = ((r"^a\.?\s*e\.?\s*\(\s*w", "Assistant Engineer (Water Works)"), (r"^s\.?\s*e\.?\s*\(\s*w", "Sub Engineer (Water Works)"),
         (r"^j\.?\s*e\.?\s*\(\s*w", "Junior Engineer (Water Works)"), (r"^e\.?\s*e\.?\s*\(\s*w", "Executive Engineer (Water Works)"),
         (r"^a\.?\s*e\.?(?![a-z])", "Assistant Engineer"), (r"^s\.?\s*e\.?(?![a-z])", "Sub Engineer"),
         (r"^j\.?\s*e\.?(?![a-z])", "Junior Engineer"), (r"^e\.?\s*e\.?(?![a-z])", "Executive Engineer"))
HONORIFIC = re.compile(r"(?i)^(?:shri|smt|kum|km|dr|mr|mrs|ms|miss)(?:\.\s*|\s+)")
ROLES = (("email", r"e-?\s*mail"), ("phone", r"contact|mobile|phone|tel"), ("area", r"area|localit|location"),
         ("beat", r"beat|ward|prabhag|section"), ("sr", r"^sr|sr\.?\s*no|s\.?\s*no"), ("post", r"designation|post"),
         ("name", r"name"))
DEFAULT = ["sr", "post", "name", "phone", "beat", "area", "email"]


def slug(code):
    return code.lower().replace("/", "")


def items(get=None):
    return [{"key": f"{MODULE}-{slug(c)}", "payload": {"reader": MODULE, "url": f"{BASE}/irj/portal/anonymous/{v[2]}", "ward": c,
                                                       "state": STATE}}
            for c, v in WARDS.items() if v[2]]


def km_frame(html):
    """The portal URL path of the ward page's content iframe (the KM folder view), or None."""
    for m in re.finditer(r"<iframe[^>]*\ssrc=\"([^\"]+)\"", html or ""):
        src = _html.unescape(_esw.clean(m.group(1)))
        if "/irj/servlet/prt/portal/prtroot/" in src and "EmptyDocument" not in src:
            return src
    return None


def km_url(path):
    """A KM document path or URL as a clean, percent-encoded URL."""
    path = unquote(path.replace("&amp;", "&"))
    if path.startswith("http"):
        path = re.sub(r"^https?://[^/]+", "", path)
    return BASE + quote(path, safe="/()',-._~!")


def water_links(html):
    """URLs of the PDFs in a page or KM folder view whose file name names water."""
    t = _html.unescape(html or "")
    out = []
    for m in re.finditer(r"(?i)(?:https?://[a-z0-9.]*mcgm\.gov\.in)?/irj/go/km/docs/[^\"'<>\n]+?\.pdf", t):
        u = km_url(m.group(0))
        if WATER.search(unquote(u).rsplit("/", 1)[-1]) and u not in out:
            out.append(u)
    return out


def guesses(code):
    en, compact = WARDS[code][0], WARDS[code][1]
    folders = list(dict.fromkeys([f"{compact} Ward", f"{en} Ward"]))
    return [f"{KM}/{quote(f)}/Water%20Dept.pdf" for f in folders]


# ---- the PDF table -----------------------------------------------------------------------------------------------------------

def page_parts(reader, pg):
    """(vertical rule xs, horizontal rules [(y, x0, x1)], text pieces [(x, y, text)]) of one page."""
    from pypdf.generic import ContentStream
    hr, vx = [], []
    try:
        cs = ContentStream(pg.get_contents(), reader)
        ops = cs.operations
    except Exception:
        ops = []
    for args, op in ops:
        if op != b"re" or len(args) != 4:
            continue
        x, y, w, h = (float(v) for v in args)
        if w < 0:
            x, w = x + w, -w
        if h < 0:
            y, h = y + h, -h
        if h < 1.5 and w > 10:
            hr.append((y + h / 2, x, x + w))
        elif w < 1.5 and h > 5:
            vx.append(x + w / 2)
    xs = []
    for x in sorted(vx):
        if not xs or x - xs[-1] > 3:
            xs.append(x)
    texts = []

    def vis(t, cm, tm, font, size):
        if t and t.strip():
            texts.append((tm[4] * cm[0] + tm[5] * cm[2] + cm[4], tm[4] * cm[1] + tm[5] * cm[3] + cm[5], t))
    try:
        pg.extract_text(visitor_text=vis)
    except Exception:
        pass
    return xs, hr, texts


def bands(rules, c0, c1):
    """y of the horizontal rules that cover most of the column (c0, c1), high to low (link underlines are shorter)."""
    w = c1 - c0
    ys = sorted({round(y, 1) for y, x0, x1 in rules if x0 <= c0 + 0.15 * w and x1 >= c1 - 0.15 * w}, reverse=True)
    out = []
    for y in ys:
        if not out or out[-1] - y > 2:
            out.append(y)
    return out


def band_of(y, ys):
    """(upper, lower) of the band that holds y; open ends are +/- 1e9."""
    up = 1e9
    for r in ys:
        if y > r:
            return up, r
        up = r
    return up, -1e9


def cell_text(pieces):
    lines = {}
    for x, y, t in pieces:
        k = next((k for k in lines if abs(k - y) < 3), y)
        lines.setdefault(k, []).append((x, t))
    return " ".join(_esw.clean(" ".join(t for _, t in sorted(v))) for _, v in sorted(lines.items(), key=lambda kv: -kv[0])).strip()


def roles_of(head):
    out = []
    for h in head:
        h = _esw.clean(h).lower()
        out.append(next((r for r, rx in ROLES if re.search(rx, h)), None))
    return out


def table_rows(content):
    """[{"sr", "post", "name", "phone", "email", "beats": [(beat, area)]}] of a ruled PDF table, or [] when the PDF has no rules."""
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception:
        return []
    rows, roles = [], None
    for pno, pg in enumerate(reader.pages):
        xs, hr, texts = page_parts(reader, pg)
        if len(xs) < 4 or not texts:
            continue
        cols = list(zip(xs, xs[1:]))
        cell = {}
        for x, y, t in texts:
            ci = next((i for i, (a, b) in enumerate(cols) if a - 2 <= x < b), None)
            if ci is None:
                continue
            ys = bands(hr, *cols[ci])
            cell.setdefault((ci, band_of(y, ys)), []).append((x, y, t))
        cells = [(ci, bd, cell_text(p), sum(y for _, y, _ in p) / len(p)) for (ci, bd), p in cell.items()]
        # heading row: the band of column 0 whose text starts with "Sr"
        head_y = next((yc for ci, bd, txt, yc in cells if ci == 0 and re.match(r"(?i)s\.?\s*r|s\.?\s*no", txt)), None)
        if head_y is not None:
            hb = band_of(head_y, bands(hr, *cols[0]))
            head = {ci: txt for ci, bd, txt, yc in cells if hb[1] <= yc <= hb[0]}
            roles = roles_of([head.get(i, "") for i in range(len(cols))])
            cells = [c for c in cells if not (hb[1] <= c[3] <= hb[0])]
        r = roles if roles and len(roles) == len(cols) else (DEFAULT if len(cols) == len(DEFAULT) else None)
        if not r or "sr" not in r:
            continue
        sr_i = r.index("sr")
        nums = sorted([(bd, txt) for ci, bd, txt, yc in cells if ci == sr_i and re.fullmatch(r"\d{1,3}\.?", txt)], key=lambda b: -b[0][0])
        page_rows = [{"sr": txt.strip("."), "band": bd, "post": "", "name": "", "phone": "", "email": "", "subs": {}} for bd, txt in nums]
        top = page_rows[0]["band"][0] if page_rows else -1e9
        for ci, bd, txt, yc in cells:
            role = r[ci] if ci < len(r) else None
            if role in (None, "sr") or not txt:
                continue
            row = next((x for x in page_rows if x["band"][1] <= yc <= x["band"][0]), None)
            if row is None and yc > top and rows:
                row = rows[-1]                 # continues the last row of the page before
            if row is None and page_rows:
                row = min(page_rows, key=lambda x: abs((x["band"][0] + x["band"][1]) / 2 - yc) if x["band"][0] < 1e8 else 1e9)
            if row is None:
                continue
            if role in ("beat", "area"):
                key = (pno, round(bd[0]), round(bd[1]))
                sub = row["subs"].setdefault(key, {"beat": "", "area": "", "page": pno, "y": yc})
                sub[role] = (sub[role] + " " + txt).strip()
            else:
                row[role] = (row[role] + " " + txt).strip()
        rows += page_rows
    for row in rows:
        row["beats"] = [(s["beat"], s["area"]) for s in sorted(row.pop("subs").values(), key=lambda s: (s["page"], -s["y"]))]
    return rows


def text_rows(content):
    """Fallback for a PDF without drawn rules: numbered lines of the layout text with their phones and emails."""
    out = []
    for page in _ward.layout_pages(content):
        for line in page.splitlines():
            m = re.match(r"^\s{0,6}(\d{1,3})\.?\s{2,}(\S.*?)\s{2,}(.*)$", line)
            if m and (re.search(r"[6-9]\d{9}", line) or "@" in line):
                out.append({"sr": m.group(1), "post": m.group(2), "name": "", "phone": _esw.phones(line), "email": _esw.emails(line),
                            "beats": []})
    return out


def post_of(abbr):
    a = _esw.clean(abbr)
    return next((en for rx, en in POSTS if re.search(rx, a, re.I)), a)


def nums(text):
    return [w for w in _ward.wards_of(text) if re.fullmatch(r"\d{1,3}", w)]


def parse(content, url, code, seen=None, created=None):
    seen = set() if seen is None else seen
    rows = table_rows(content) or text_rows(content)
    every = sorted({w for row in rows for b, _ in row["beats"] for w in nums(b)}, key=int)
    en = WARDS[code][0]
    area = f"{en.replace(' ', '/', 1) if '/' in code else en} Ward"      # "F/North Ward", as ward2n_mumbai writes it
    recs = []
    for row in rows:
        beats, wards, parts, maint = [], [], [], None
        for b, a in row["beats"]:
            whole = not nums(b) and bool(re.search(r"(?i)^[A-Z/\s]{1,12}\bward$", _esw.clean(b or a)))  # "D Ward"
            if whole and not b:
                b, a = a, ""
            w = every if whole else nums(b)
            pw = [x for x in re.findall(r"(?i)part\s*(\d{1,3})", b)]
            if re.search(r"(?i)maintenance", a):
                maint = True
            beats.append({"beat": b or None, "area": a or None, "wards": w or None, "part_wards": pw or None, "whole_ward": whole or None})
            wards += [x for x in w if x not in wards]
            parts += [x for x in pw if x not in parts]
        name = HONORIFIC.sub("", _esw.clean(row["name"])).strip(" .,")
        post = post_of(row["post"]) or "Water Works staff"
        recs.append(_ward.record(MODULE, f"{slug(code)}:{row['sr']}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="ward", area=area, admin_ward=code, post=post, post_abbr=row["post"] or None, name=name,
                                 phone=row["phone"], email=row["email"], wards=sorted(wards, key=int) or None,
                                 part_wards=parts or None, beats=[b for b in beats if b["beat"] or b["area"]] or None,
                                 beat_area="; ".join(b["area"] for b in beats if b["area"] and not re.search(r"(?i)maintenance", b["area"]))
                                 or None, maintenance=maint, wing="water", role="head" if post.startswith("Assistant Engineer") else
                                 "staff", sr=row["sr"], source=url, file_created=created))
    return recs


def created_of(content):
    from pypdf import PdfReader
    try:
        d = (PdfReader(io.BytesIO(content)).metadata or {}).get("/CreationDate") or ""
    except Exception:
        return None
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", str(d))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def fetch(p, get):
    code = p["ward"]
    files, pdfs = [], list(p.get("pdfs") or [])
    if not pdfs:
        r = get(p["url"], headers=UA)
        if r is not None:
            pdfs += water_links(r.text)
            frame = km_frame(r.text)
            if frame:
                f = get(urljoin(BASE, frame), headers=UA)
                if f is not None:
                    files.append(_esw.keep(MODULE, f"{slug(code)}-folder", f.content))
                    pdfs += water_links(f.text)
    found = bool(pdfs)
    pdfs = list(dict.fromkeys(pdfs)) or guesses(code)
    recs, seen, tried = [], set(), []
    for i, u in enumerate(pdfs[:4]):
        a = get(u, headers=UA)
        if a is None or not a.content.startswith(b"%PDF"):
            tried.append(u)
            continue
        files.append(_esw.keep(MODULE, f"{slug(code)}-{i}", a.content, "pdf"))
        recs += parse(a.content, u, code, seen, created_of(a.content))
        if recs and not found:
            break
    why = "" if recs else (f"no rows in {len(pdfs) - len(tried)} PDF(s)" if len(tried) < len(pdfs[:4]) else
                           "no water PDF found: " + ", ".join(tried))
    return recs, files, why
