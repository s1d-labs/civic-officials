"""Generic reader for officer tables in PDFs that were printed from a spreadsheet (MPCZ, MPEZ, PSPCL ... contact lists).

rows(content) -> one dict per person row: {"name", "post", "phone", "email", "offices": [labels left to right], "heading": text of
the last full-width heading above the row, "page"}. How:
- pypdf gives every text piece with its position (visitor_text) and the grid lines (thin filled rectangles or stroked lines).
- The header row is the first line that holds a designation word and a name or mobile word; header words give each column a
  role (name, post, phone, email, office, sn, skip). Column borders are the vertical grid lines that cross the header, else the
  midpoints between the header words.
- A cell's extent is the space between the nearest horizontal lines above and below it that cross its x. A merged cell
  (division / sub-division / DC that spans several rows) thus covers all rows in that extent, wherever its text sits.
- A PDF without lines falls back to one row per text line.
Pages without their own header reuse the columns of the page before (long lists).
"""
import io
import re

ROLE_RULES = (  # (role, regex on the header text of one column), first match wins
    ("sn", r"^\s*(s\.?\s*n|sr|sl|s\.?\s*no|so\s*no)\b[.\s0o]*$"),
    ("email", r"e-?\s*mail|email"),
    ("skip", r"emp(loyee)?\.?\s*(no|code|id)|ext\b|ext\.|extension|landline|remark|e-?office|std|fax|ip\s*phone"),
    ("phone", r"mobile|cug|contact|phone|mob\b|airtel|tel"),
    ("post", r"desig|post\b|^\s*present\s*$|rank"),
    ("name", r"name\s*of\s*(the\s*)?(officer|employee|se/)|officers?\s*name|employee\s*name|shri|s/shri|smt|^\s*name\s*$|^\s*name\s*of\s*$"),
    ("office", r"office(?!r)|posting|location|section|division|sub-?\s*div|circle|\bdc\b|d/c|zone|department|place|region|area|unit"),
    ("name", r"name|officer|employee"),
)
HEADER_HINT = re.compile(r"desig|mobile|cug|contact\s*no|airtel|mob\.?\s*no", re.I)


def _mul(a, b):
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]


def page_parts(reader, page):
    """(texts [(x, y, text)], hlines [(x0, x1, y)], vlines [(x, y0, y1)]) of one pypdf page, in page space."""
    from pypdf.generic import ContentStream
    texts = []

    def vt(text, cm, tm, *_):
        if text and text.strip():
            m = _mul(tm, cm)
            texts.append((m[4], m[5], text))
    try:
        page.extract_text(visitor_text=vt)
    except Exception:
        pass
    h, v = [], []
    try:
        ops = ContentStream(page.get_contents(), reader).operations
    except Exception:
        ops = []
    ctm, stack, path, cur = [1, 0, 0, 1, 0, 0], [], [], None

    def pt(x, y):
        return x * ctm[0] + y * ctm[2] + ctm[4], x * ctm[1] + y * ctm[3] + ctm[5]
    for args, op in ops:
        try:
            if op == b"q":
                stack.append(ctm[:])
            elif op == b"Q":
                ctm = stack.pop() if stack else [1, 0, 0, 1, 0, 0]
            elif op == b"cm":
                ctm = _mul([float(a) for a in args], ctm)
            elif op == b"re":
                x, y, w, hh = (float(a) for a in args)
                (x0, y0), (x1, y1) = pt(x, y), pt(x + w, y + hh)
                path.append(("re", min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
            elif op == b"m":
                cur = pt(float(args[0]), float(args[1]))
            elif op == b"l" and cur:
                nxt = pt(float(args[0]), float(args[1]))
                path.append(("l", min(cur[0], nxt[0]), min(cur[1], nxt[1]), max(cur[0], nxt[0]), max(cur[1], nxt[1])))
                cur = nxt
            elif op in (b"f", b"F", b"f*", b"S", b"s", b"B", b"B*", b"b", b"b*"):
                for kind, x0, y0, x1, y1 in path:
                    w, hh = x1 - x0, y1 - y0
                    if hh <= 2.5 and w > 4:
                        h.append((x0, x1, (y0 + y1) / 2))
                    elif w <= 2.5 and hh > 4:
                        v.append(((x0 + x1) / 2, y0, y1))
                    elif kind == "re" and op in (b"S", b"s", b"B", b"B*", b"b", b"b*") and w > 4 and hh > 4:  # stroked cell box
                        h += [(x0, x1, y0), (x0, x1, y1)]
                        v += [(x0, y0, y1), (x1, y0, y1)]
                path, cur = [], None
            elif op == b"n":
                path, cur = [], None
        except Exception:
            path, cur = [], None
    return texts, h, v


def _lines(texts, tol=3.0):
    """Group text pieces into lines (top to bottom); each line = [(x, y, text)] left to right."""
    out = []
    for t in sorted(texts, key=lambda t: (-t[1], t[0])):
        if out and abs(out[-1][0][1] - t[1]) <= tol:
            out[-1].append(t)
        else:
            out.append([t])
    return [sorted(l, key=lambda t: t[0]) for l in out]


def _role(text):
    t = " ".join(text.lower().split())
    for role, rx in ROLE_RULES:
        if re.search(rx, t):
            return role
    return None


def _header(lines, vlines):
    """(header y top, header y bottom, [(x_left, x_right, role)]) or None."""
    for i, line in enumerate(lines[:60]):
        txt = " ".join(t[2] for t in line)
        if len(line) < 3 or not HEADER_HINT.search(txt) or not re.search(r"name|officer|employee|office", " ".join(
                " ".join(t[2] for t in l) for l in lines[max(0, i - 2):i + 3]), re.I):
            continue
        y = line[0][1]
        band = []
        for j in range(max(0, i - 3), min(len(lines), i + 4)):
            if j > i and any(re.search(r"\d{6,}", t[2]) for t in lines[j]):
                break                     # the first data row ends the header
            band += [t for t in lines[j] if -20 <= t[1] - y <= (10 if j < i else 20) and not re.fullmatch(r"\s*\d[\d\s]*", t[2])]
        xs = sorted({round(x) for x, y0, y1 in vlines if y0 - 3 <= y <= y1 + 3})
        if len(xs) >= 4:
            if any(t[0] + 1 >= xs[-1] for t in band):
                xs.append(10_000)
            if any(t[0] + 1 < xs[0] for t in band):
                xs.insert(0, -10_000)
        cols = []
        if len(xs) >= 4:
            for a, b in zip(xs, xs[1:]):
                if b - a < 6:
                    continue
                words = " ".join(t[2] for t in sorted(band, key=lambda t: (-t[1], t[0])) if a - 1 <= t[0] + 1 < b)
                cols.append([a, b, words])
        else:
            pieces = sorted(band, key=lambda t: t[0])
            groups = []
            for t in pieces:            # pieces of one header cell (stacked words) start near each other
                if groups and t[0] - groups[-1][-1][0] < 25:
                    groups[-1].append(t)
                else:
                    groups.append([t])
            starts = [g[0][0] for g in groups]
            for k, g in enumerate(groups):
                a = starts[k] - 6 if k == 0 else (starts[k - 1] + starts[k]) / 2 + (starts[k] - starts[k - 1]) * 0.3
                b = starts[k + 1] - (starts[k + 1] - starts[k]) * 0.2 if k + 1 < len(groups) else 10_000
                cols.append([a if k else -10_000, b, " ".join(t[2] for t in sorted(g, key=lambda t: (-t[1], t[0])))])
        out = [(a, b, _role(w) or "office") for a, b, w in cols if w.strip()]
        if not out:
            continue
        # empty header cells (between two lines) still hold data: give them the role "office"
        if len(xs) >= 4:
            named = {(a, b) for a, b, _ in out}
            out += [(a, b, "office") for a, b, w in cols if (a, b) not in named]
            out.sort()
        roles = [r for *_, r in out]
        if "post" in roles and ("name" in roles or "phone" in roles):
            if "name" not in roles:  # a name column whose header said only "officer"/"S/Shri" lost to another rule
                k = next((k for k, c in enumerate(out) if c[2] == "office"), None)
                if k is not None:
                    out[k] = (out[k][0], out[k][1], "name")
            top = max(t[1] for t in band) + 10
            bot = min(t[1] for t in band) - 2
            return top, bot, out
    return None


def _col(cols, x):
    for k, (a, b, _) in enumerate(cols):
        if a - 1 <= x + 1 < b:
            return k
    return None


def _extent(hlines, x, y, top, bottom):
    above = [hy for x0, x1, hy in hlines if x0 - 2 <= x <= x1 + 2 and hy > y + 0.5]
    below = [hy for x0, x1, hy in hlines if x0 - 2 <= x <= x1 + 2 and hy < y - 0.5]
    return (max(below) if below else bottom), (min(above) if above else top)


def rows(content):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    out, cols, heading = [], None, None
    for pno, page in enumerate(reader.pages, 1):
        texts, hl, vl = page_parts(reader, page)
        lines = _lines(texts)
        hd = _header(lines, vl)
        if hd:
            top, bot, cols = hd
        elif cols is None:
            continue
        else:
            top = max((t[1] for t in texts), default=0) + 10
        texts = [t for t in texts if t[1] < (hd[1] if hd else top)]
        if not texts:
            continue
        grid = len(hl) >= 5
        roles = [c[2] for c in cols]
        name_k = roles.index("name") if "name" in roles else None
        post_k = roles.index("post") if "post" in roles else None
        cells = {}                         # (col, lo, hi) -> [(x, y, text)]
        for x, y, t in texts:
            k = _col(cols, x)
            if k is None:
                # text left of the first column or right of the last one (full-width heading pieces)
                k = -1
            if grid:
                cx = cols[k][0] + min((cols[k][1] - cols[k][0]) / 2, 12) if k >= 0 else x + 2
                lo, hi = _extent(hl, cx if k >= 0 else x + 2, y, top, -10)
            else:
                lo, hi = y - 1.5, y + 1.5
            cells.setdefault((k, round(lo, 1), round(hi, 1)), []).append((x, y, t))
        anchors = []                       # person rows: name cells, else post cells
        ak = name_k if name_k is not None else post_k
        for (k, lo, hi), ts in cells.items():
            if k == ak or (roles[k] == "sn" and any(re.match(r"\d+\.?\s+[A-Za-z]", t) for _, _, t in ts)) or (k == post_k and name_k is not None and not any(
                    kk == name_k and l2 <= (lo + hi) / 2 <= h2 for kk, l2, h2 in cells)):
                anchors.append((k, lo, hi))
        # one anchor per row: rows found from the post column too only where the name cell is empty
        rowspans = sorted({(lo, hi) for _, lo, hi in anchors}, key=lambda r: -r[1])
        if not grid:
            merged = []
            for lo, hi in rowspans:
                if merged and abs((merged[-1][0] + merged[-1][1]) / 2 - (lo + hi) / 2) < 3:
                    continue
                merged.append((lo, hi))
            rowspans = merged
        if grid:   # a grid with missing row lines: split a span when the name and phone pieces show the same separate lines
            phone_k = [k for k, r in enumerate(roles) if r == "phone"]
            split = []
            for lo, hi in rowspans:
                def ylines(ks):
                    ys = sorted({round(y, 1) for (k, clo, chi), ts in cells.items() if k in ks
                                 for _, y, t in ts if lo < y < hi and t.strip()}, reverse=True)
                    out_ = []
                    for y in ys:
                        if not out_ or out_[-1] - y > 5:
                            out_.append(y)
                    return out_
                a, ph = ylines({ak}), ylines(set(phone_k))
                if len(a) >= 2 and len(a) == len(ph) and all(abs(x - y) < 4 for x, y in zip(a, ph)):
                    cuts = [hi] + [(a[i] + a[i + 1]) / 2 for i in range(len(a) - 1)] + [lo]
                    split += [(cuts[i + 1], cuts[i], True) for i in range(len(a))]
                else:
                    split.append((lo, hi, False))
        else:
            split = [(lo, hi, False) for lo, hi in rowspans]
        used = set()
        rowrecs = []
        for lo, hi, part in split:
            mid = (lo + hi) / 2
            rec = {"page": pno, "_y": mid, "offices": []}
            for (k, clo, chi), ts in cells.items():
                if k < 0:
                    continue
                inside = clo - 0.6 <= mid <= chi + 0.6 if grid else abs((clo + chi) / 2 - mid) < 3.2
                if not inside:
                    continue
                if part:            # a cell larger than this split row: keep only its pieces inside the row, if any
                    own = [t for t in ts if lo <= t[1] <= hi]
                    ts = own or ts
                text = " ".join(t for _, _, t in sorted(ts, key=lambda t: (-round(t[1]), t[0])))
                text = " ".join(text.split())
                role = roles[k]
                used.add((k, clo, chi))
                if role in ("name", "post", "phone", "email"):
                    rec[role] = (rec.get(role, "") + " " + text).strip()
                elif role == "office" and not re.fullmatch(r"[\d\s.]+", text):
                    rec["offices"].append((cols[k][0], text))
                elif role == "sn" and re.match(r"\d+\.?\s+[A-Za-z]", text):   # "12 Sh. Name" in one piece
                    rec["_sn_name"] = re.sub(r"^\d+\.?\s+", "", text)
            rec["offices"] = [t for _, t in sorted(rec["offices"])]
            sn_name = rec.pop("_sn_name", None)
            if sn_name and not rec.get("name"):
                rec["name"] = sn_name
            if rec.get("name") or rec.get("post"):
                rowrecs.append(rec)
        # cells that belong to no person row: headings (full-width rows like "City Division South Bhopal")
        heads = []
        for (k, lo, hi), ts in cells.items():
            if (k, lo, hi) in used:
                continue
            text = " ".join(" ".join(t for _, _, t in sorted(ts, key=lambda t: (-round(t[1]), t[0]))).split())
            if text and not re.fullmatch(r"[\d\s.]+", text) and len(text) > 2:
                heads.append(((lo + hi) / 2 if grid else ts[0][1], text))
        heads.sort(key=lambda h: -h[0])
        hi_ = 0
        for rec in sorted(rowrecs, key=lambda r: -r["_y"]):
            while hi_ < len(heads) and heads[hi_][0] > rec["_y"]:
                heading = heads[hi_][1]
                hi_ += 1
            rec["heading"] = heading
            rec.pop("_y")
            out.append(rec)
    return out
