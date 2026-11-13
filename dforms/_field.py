"""Shared engine of the field-official readers (dforms/field_<layer>_<xx>.py): the officials of health, education, child
development, revenue and food / drug control who serve a town, ward, village or block.

A source is one page or one file: an HTML page with tables (S3WaaS district portals, state department sites) or a PDF list.
The engine maps each column by the words in its header, so one reader reads many differently ordered lists:
  name   "Name", "Name of Patwari", "Name of the Officer", "VAO Name", "Medical Officer" ...
  post   "Designation", "Post", "Rank"
  area   the smallest area in the row: "Village", "Halqa", "Patwar Circle", "Saja", "Name of PHC", "Sector", "Project" ...
  parent areas, kept as their own fields: tehsil, block, circle, district
  phone  "Mobile", "Contact", "Phone", "CUG", "Tel"; email "E-mail"
A header cell that names a post ("Name of Patwari", "VAO Name") also gives the post when the row has no post column.
PDF lists: pypdf / pdftotext layout text; the header line gives the column positions; a line that starts with a serial
number opens a row, the next lines without one continue the cells above them.

Records (depts.py contract): "dept:<module>:<key>" = {"type": "dept_office", "dept", "level", "layer": "field", "area",
"post", "name", "phone", "email", "address", "state", "district", "tehsil", "block", "circle", "office_id", "source",
"last_updated", "table_row"}. Nothing is masked: the lists are published as they are.
"""
import gzip
import io
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dforms import _esw
import provenance

HEAD_WORDS = re.compile(r"(?i)name|designation|post\b|rank|mobile|phone|contact|cug|e-?mail|village|halq|halk|patwar|circle|"
                        r"saja|sajja|tehsil|taluk|block|district|phc|chc|sector|project|ward|mandal|firka|office|officer|s\.?\s?no|"
                        r"sl\.?\s?no|sr\.?\s?no|address|area|jurisdiction|beat|cluster|centre|center|institution|hospital|"
                        r"lekhpal|talathi|vao|vro|karamchari|kanungo|inspector")
PERSON_POST = [  # header word -> post it names
    (r"patwari|patwar[iy]?s?\b(?! ?(circle|halqa|halka|mandal))", "Patwari"), (r"lekhpal", "Lekhpal"), (r"talathi", "Talathi"),
    (r"village accountant|\bv\.?a\.?\b(?! ?office)", "Village Accountant"),
    (r"village administrative officer|\bvao\b", "Village Administrative Officer"), (r"\bvro\b", "Village Revenue Officer"),
    (r"revenue inspector|\br\.?i\.?\b", "Revenue Inspector"), (r"kanungo|qanungo|girdawar", "Kanungo"),
    (r"karamchari|karmchari", "Rajasv Karmchari"), (r"\bgq\b|girdawar", "Girdawar Qanungo"), (r"\boq\b", "Office Qanungo"), (r"cdpo|child development project officer", "CDPO"),
    (r"supervisor|mukhya sevika", "Supervisor"), (r"\bbeo\b|block education officer", "Block Education Officer"),
    (r"\bbrc\b|block resource", "BRC Coordinator"), (r"\bcrc\b|cluster resource", "CRC Coordinator"),
    (r"medical officer|\bm\.?o\.?\b|moic|\bsmo\b", "Medical Officer"), (r"in-?charge", "In-charge"),
    (r"food safety officer|\bfso\b", "Food Safety Officer"), (r"drugs? (control )?inspector|\bd\.?i\.?\b", "Drugs Inspector"),
    (r"designated officer", "Designated Officer"),
]
PARENT = [("district", r"district|zila|jila"), ("tehsil", r"tehsil|taluk|taluka|mandal|sub-?division|anchal"),
          ("block", r"block|project|cd block"), ("circle", r"circle|firka|ri circle|kanungo circle|revenue circle|division")]
FINE_AREA = re.compile(r"(?i)village|gram\b|mauza|mouza|halq|halk|patwar|saja|sajja|beat|sector|cluster|phc|chc|uphc|centre|"
                       r"center|institution|hospital|dispensar|ward|locality|area|jurisdiction|place|station|panchayat|"
                       r"health facility|facility|unit|school|office name|name of (the )?office|post(ing)? place|place of posting")
SNO = re.compile(r"(?i)^(s\.?\s*no|sl\.?\s*no|sr\.?\s*no|serial|#|no\.?|क्र|क्रम)")
ROW_NO = re.compile(r"^\s*(\d{1,4})[.)]?(?:\s{1,}|$)")
NOT_NAME = re.compile(r"(?i)^(vacant|nil|na|n/a|-+|—|do|post vacant|vacancy)$")


PERSON_HEAD = re.compile(r"(?i)officer|official|incumbent|employee|staff|in-?charge|patwari|lekhpal|talathi|\bvao\b|\bvro\b|"
                         r"karamchari|karmchari|kanungo|cdpo|supervisor|\bbeo\b|inspector|\bm\.?o\.?\b|doctor|accountant|"
                         r"\bmlhp\b|provider|coordinator|co-ordinator|person|holder|sevika|worker|teacher|principal|head ?master")
COUNT_HEAD = re.compile(r"(?i)^(no\.?|number|total|count)\s+of\b|\bno\.? of (awc|centres?|villages?|posts?)|sanctioned|operational|"
                        r"hadbast|^code$|\bcode\b|census|population|pin ?code|^date|year|remarks?$|status$|std ?code|website|"
                        r"view|download|gps|latitude|longitude|^type")


def header_kind(h):
    """('name'|'post'|'area'|'phone'|'email'|'address'|'sno'|parent field|None, post named by the header or None)."""
    t = _esw.clean(h).lower().strip(" :.")
    if not t:
        return None, None
    if re.search(r"e-?\s?mail", t):
        return "email", None
    if re.search(r"mobile|phone|contact|cug|\btel\b|telephone|\bcell\b|whatsapp|landline|\bmob\b", t) and not re.search(r"name", t):
        return "phone", None
    if re.fullmatch(r"(?:patwari|kanungo|vao|lekhpal|talathi)\s+(?:no|number)\.?", t):     # Gurdaspur "patwari no" = his mobile
        return "phone", None
    if SNO.match(t) and len(t) < 12:
        return "sno", None
    if COUNT_HEAD.search(t):
        return None, None
    if re.search(r"designation|\bpost\b|\brank\b|cadre|allotted|charge of", t) and not re.search(r"place of post|posting|post office", t):
        return "post", None
    if re.search(r"address", t):
        return "address", None
    named = next((pp for rx, pp in PERSON_POST if re.search(rx, t)), None)
    person = bool(PERSON_HEAD.search(t)) and not re.search(r"\b(circles?|halqa|halka|sectors?|beat|jurisdiction|office)\s*$", t)
    if not person and (FINE_AREA.search(t) or re.search(r"(?i)\bawc\b|anganwadi|aanganwadi|aam\b|arogya|wellness|health centre|"
                                                       r"niabat|mohalla|town|city|zone|location", t)):
        return "area", None
    if not person:
        for f, rx in PARENT:
            if re.search(rx, t):
                return f, None
    if person or re.search(r"\bname\b", t):
        return "name", named
    return None, None


def header_map(cells):
    """{field: column index} and the post the headers imply. Needs a name or a phone column and one other known column.
    Of several name columns the one that names a person ("Name of the Incharge Medical Officer") wins; a plain "Name of X"
    column then serves as the area when the row has no other area. Of several phone columns the first one after the name
    column wins ("Name Of Kanungo | Mobile | Name Of Patwari | Mobile": the patwari's). Later area columns go in "areas2"."""
    cols, post, names, phones, areas = {}, None, [], [], []
    for i, c in enumerate(cells):
        k, p = header_kind(c)
        if k == "name":
            names.append((bool(PERSON_HEAD.search(_esw.clean(c))), i, p))
        elif k == "phone":
            phones.append(i)
        elif k == "area":
            areas.append(i)
        elif k and k not in cols:
            cols[k] = i
    if names:
        names.sort(key=lambda x: (not x[0], -x[1] if x[0] else x[1]))
        cols["name"], post = names[0][1], names[0][2]
        areas += [i for _, i, _ in names[1:] if not _[0]] if False else [i for ok, i, _ in names[1:] if not ok]
        areas.sort()
    if areas:
        cols["area"] = areas[0]
        cols["areas2"] = areas[1:]
    if phones:
        after = [i for i in phones if i > cols.get("name", -1)]
        cols["phone"] = after[0] if after and "name" in cols else phones[0]
    if not post:
        post = next((pp for c in cells for rx, pp in PERSON_POST if re.search(rx, _esw.clean(c), re.I)), None)
    known = set(cols) - {"sno", "areas2"}
    if not ({"name", "phone"} & known) or len(known) < 2:
        return None, None
    return cols, post


TITLE = re.compile(r"(?i)^(dr|sh|shri|smt|sri|mr|mrs|ms|miss|kumari|km|thiru|tmt|selvi|janab|er|prof)\b\.?")
POSTY = re.compile(r"(?i)\b(officer|commissioner|collector|magistrate|superintendent|director|secretary|inspector|supervisor|"
                   r"in-?charge|incharge|cdpo|bmo|cmo|cmho|dmho|beo|deo|tehsildar|patwari|lekhpal|talathi|vao|kanungo|"
                   r"coordinator|surgeon|programme|program|manager|assistant|addl|additional|deputy|district|block|chief)\b")


def is_post_text(s):
    """'District Medical & Health Officer (87 PHC's incharge)' is a post, 'Dr. K Rajender' is a person."""
    return bool(s) and not TITLE.match(s) and bool(POSTY.search(s))


def split_name(s):
    """'Sh. Ravi Kumar, Patwari' -> ('Sh. Ravi Kumar', 'Patwari') when a post word follows a comma or a dash; else (s, '')."""
    s = _esw.clean(s)
    m = re.match(r"^(.*?)[,(/-]\s*((?:" + "|".join(rx for rx, _ in PERSON_POST) + r")[^,)]*)\)?$", s, re.I)
    if m and len(m.group(1)) > 3:
        return m.group(1).strip(" ,-"), m.group(2).strip()
    return s, ""


def last_updated(html):
    m = re.search(r"(?i)(?:Last Updated|Updated on|Last Reviewed)\s*:?\s*(?:<[^>]+>\s*)*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", html or "")
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.search(r"(?i)(?:Last Updated|Updated on)\s*:?\s*(?:<[^>]+>\s*)*(\w+ \d{1,2},? \d{4})", html or "")
    if m:
        from datetime import datetime
        for f in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(m.group(1), f).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def html_rows(html):
    """[(header cells, row cells, caption, src_pos)] for every data row of every table that has a usable header (the first of its
    first 4 rows that header_map accepts). caption = the nearest heading before the table (a block or tehsil name)."""
    soup = _esw.soup(html)
    out = []
    for table in soup.find_all("table"):
        gpos = []                         # source trail: {"table", "row"} of each grid row
        g = _esw.grid(table, pos=gpos)
        if len(g) < 2:
            continue
        hi = next((i for i, r in enumerate(g[:4]) if header_map(r)[0]), None)
        if hi is None:
            continue
        cap = table.find("caption")
        cap = _esw.clean(cap.get_text(" ")) if cap else ""
        if not cap:
            h = table.find_previous(["h2", "h3", "h4", "h5", "strong"])
            cap = _esw.clean(h.get_text(" ")) if h else ""
        head = g[hi]
        for r, rp in zip(g[hi + 1:], gpos[hi + 1:]):
            if [c.lower() for c in r] == [c.lower() for c in head]:
                provenance.skip_row(r, 'skip: [c.lower() for c in r] == [c.lower() for c in head]')
                continue
            out.append((head, r, cap[:120], rp))
    return out


CHUNK = re.compile(r"\S+(?: \S+)*")


# Layers: department key, the words that mark a row as this layer's, and the level of a row (from post + area + caption).
LAYERS = {
    "health": {"dept": "health", "words": r"medical|\bm\.?o\.?\b|moic|\bbmo\b|\bsmo\b|\bphc\b|\bchc\b|uphc|hospital|dispensar|"
               r"health|surgeon|\bcmo|cmho|dmho|cmoh|doctor|\bdr\.|clinic|\bhwc\b|\baam\b|arogya|\bmlhp\b|\banm\b|sub ?cent",
               "levels": [("facility", r"\bphc\b|\bchc\b|uphc|uchc|\bhwc\b|\baam\b|sub ?cent|\bs\.?c\.?\b|hospital|dispensar|clinic|"
                                       r"\bdgd\b|puhc|health (centre|center|post|unit)|polyclinic|cottage|arogya|ayushman|\bmlhp\b|"
                                       r"moic|in-?charge|\bm\.?o\.?\b|medical officer|\bsdh\b|\bdh\b|\bch\b"),
                          ("block", r"\bblock\b|\bbphc\b|\bbmo\b|\bbpm\b|\bbhm\b"),
                          ("district", r".")]},
    "education": {"dept": "education", "words": r"\bbeo\b|\bbeeo\b|block education|\bbrc|\bcrc|cluster|sankul|education officer|"
                  r"\bdeo\b|\bsdeo\b|\bdpo\b|\bbsa\b|khand shiksha|shiksha|\bdiet\b|\bbrp\b|\bcrp\b|\bmeo\b|mandal education|"
                  r"school|\bdse\b|\bdee\b|samagra|\bssa\b",
                  "levels": [("section", r"\bcrc|cluster|sankul|\bcrp\b"),
                             ("block", r"\bbeo\b|\bbeeo\b|block|\bbrc|\bbrp\b|khand|\bmeo\b|mandal|\bsdeo\b|sub-?division|taluk|tehsil"),
                             ("district", r".")]},
    "icds": {"dept": "women_child", "words": r"cdpo|child development|\bicds\b|supervisor|mukhya sevika|anganwadi|aanganwadi|"
             r"\baww\b|\bawc\b|\bdpo\b|programme officer|program officer|project officer|poshan|women (and|&) child|\bwcd\b",
             "levels": [("facility", r"\baww\b|anganwadi worker|sevika|\bawc\b|centre"),
                        ("section", r"supervisor|mukhya sevika|sector"),
                        ("block", r"cdpo|project|block"),
                        ("district", r".")]},
    "revenue": {"dept": "revenue", "words": r"patwar|lekhpal|talathi|tlathi|village accountant|village administrative|\bvao\b|\bvro\b|"
                r"\bv\.?a\.?\b|revenue|kanungo|qanungo|girdawar|karamchari|karmchari|halq|halk|\bsaja|\bgq\b|\boq\b|naib|tehsildar|"
                r"\bri\b|firka|mamlatdar|circle officer|anchal",
                "levels": [("section", r"patwar|lekhpal|talathi|village accountant|village administrative|\bvao\b|\bvro\b|\bv\.?a\.?\b|"
                                       r"karamchari|karmchari|halq|halk|\bsaja|\bgq\b|\boq\b|village"),
                           ("circle", r"revenue inspector|\bri\b|kanungo|qanungo|girdawar|firka|naib|circle"),
                           ("subdistrict", r"tehsil|taluk|mamlatdar|\bsdm\b|sub-?divisional|anchal|\bc\.?o\.?\b|mandal"),
                           ("district", r".")]},
    "food": {"dept": "health", "words": r"food safety|\bfso\b|drugs? (control )?inspector|drugs? control|designated officer|"
             r"\bfda\b|licens|\bdi\b|\bado\b|assistant drugs",
             "levels": [("circle", r"food safety officer|\bfso\b|drugs? inspector|\bdi\b|circle|area|ward|zone"),
                        ("district", r".")]},
}


STATE_POST = re.compile(r"(?i)minister|\bsecretary\b|director of|mission director|\bstate\b|directorate")
DISTRICT_WORD = re.compile(r"(?i)district|zila|jila|deputy director|dy\.? director|joint director|regional")


def level_of(layer, text):
    if STATE_POST.search(text or "") and not DISTRICT_WORD.search(text or ""):
        return "state"
    for lv, rx in LAYERS[layer]["levels"]:
        if re.search(rx, text or "", re.I):
            return lv
    return "district"


def in_layer(layer, d):
    """True when a record's post / area / caption / name carries one of the layer's words."""
    t = " ".join(str(d.get(k) or "") for k in ("post", "area", "caption", "name"))
    t += " " + " ".join(str(k) for k in (d.get("table_row") or {}))
    return bool(re.search(LAYERS[layer]["words"], t, re.I))


def pdf_text(content):
    """Layout text of a PDF: pdftotext -layout when the binary is there (keeps columns best), else pypdf layout mode."""
    return pdf_text_engine(content)[0]


def pdf_text_engine(content):
    """(layout text, engine): engine "pdftotext -layout" or "pypdf layout" (source trail: the record's method)."""
    import shutil
    import subprocess
    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=content, capture_output=True, timeout=180)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", "replace"), "pdftotext -layout"
        except Exception:
            pass
    return "\f".join(_esw.pdf_pages(content)), "pypdf layout"


def _is_head(ch):
    cells = [c for _, c in ch]
    return len(ch) >= 3 and header_map(cells)[0] is not None and sum(1 for c in cells if HEAD_WORDS.search(c)) >= 3


def _chunks(ln):
    return [(m.start(), m.group()) for m in CHUNK.finditer(ln)]


def _head_part(ln):
    """A header continuation line: 2+ chunks, no long number, no serial number."""
    return len(_chunks(ln)) >= 2 and not re.search(r"\d{5,}", ln) and not ROW_NO.match(ln) and len(ln.strip()) < 200


HEAD_SPLIT = re.compile(r"(?i)(?<=\S) (?=name\s+of\b)|(?<=\)) (?=(?:mobile|contact|phone)\b)")


def _split_head(ch):
    """Header chunks that hold two headers with one space between ("kanungoMobile Name Of Patwar") are cut before the second."""
    out = []
    for x, c in ch:
        start = 0
        for m in HEAD_SPLIT.finditer(c):
            out.append((x + start, c[start:m.start()]))
            start = m.end()
        out.append((x + start, c[start:]))
    return out


def _merge_head(main, extra):
    """Add the chunks of a header line above or below to the main header: a chunk over a main column joins its text, a
    chunk in a gap becomes a new column."""
    cols = [[x, x + len(c), c] for x, c in main]
    for x, c in extra:
        hit = next((col for col in cols if x < col[1] + 1 and x + len(c) > col[0] - 1), None)
        if hit:
            hit[2] = f"{hit[2]} {c}" if extra is not None else hit[2]
            hit[0], hit[1] = min(hit[0], x), max(hit[1], x + len(c))
        else:
            cols.append([x, x + len(c), c])
    cols.sort()
    return [(a, c) for a, _, c in cols]


def text_rows(text):
    """Rows of layout-text tables. A header line (3+ header words that header_map accepts), joined with the header word
    lines right above and below it, sets the columns; a later header line replaces them (a PDF can hold several tables).
    A row starts at a line with a serial number, or (when the table has no serial column) at any line with chunks in at
    least half of the columns; the next lines add their chunks to the open row. A chunk goes to the column whose span it
    overlaps most (a column reaches halfway to the centres of its neighbours' headers, so centred headers work)."""
    text = re.sub(r"(?i)\bpage\s+\d+\s+of\s+\d+\b", " ", text)
    where = [(pg, k) for pg, pt in enumerate(text.split("\f"), 1) for k, ln in enumerate(pt.split("\n"), 1) if ln.strip()]
    lines = [ln for ln in text.replace("\f", "\n").split("\n") if ln.strip()]
    rows, cur, head, xs, cs, title, cap, has_sno, skip = [], None, None, None, None, "", "", True, 0
    for n, ln in enumerate(lines):
        if skip:
            skip -= 1
            continue
        ch = _chunks(ln)
        if _is_head(ch):
            cap = title
            hd = _split_head(ch)
            if n and _head_part(lines[n - 1]) and _esw.clean(lines[n - 1]) != title:
                hd = _merge_head(hd, _split_head(_chunks(lines[n - 1])))
            if n + 1 < len(lines) and _head_part(lines[n + 1]) and len(_chunks(lines[n + 1])) <= len(hd):
                hd = _merge_head(hd, _split_head(_chunks(lines[n + 1])))
                skip = 1
            head, xs, cur = [c for _, c in hd], [x for x, _ in hd], None
            cs = [x + len(c) / 2 for x, c in hd]
            has_sno = any(header_kind(c)[0] == "sno" for c in head)
            continue
        if not ROW_NO.match(ln) and len(ch) <= 2 and re.search(r"[A-Za-zऀ-෿]{4}", ln):
            title = _esw.clean(ln)[:120]    # a title line: the caption of the next table
        if head is None:
            continue
        if ROW_NO.match(ln) or (not has_sno and len(ch) >= max(3, (len(xs) + 1) // 2)):
            cur = [""] * len(xs)
            # source trail: page + line (1-based, blank lines counted; "Page x of y" blanked) where the row starts
            rows.append((head, cur, cap, {"page": where[n][0], "line": where[n][1], "line_text": ln}))
        elif cur is not None and ch:
            rows[-1][3]["line_end"] = where[n][1]
        if cur is None:
            provenance.skip_line(ln, 'skip: cur is None')
            continue
        for x, c in ch:
            span = (x, x + len(c))
            best, bj = -1, 0
            for j in range(len(xs)):
                lo = (cs[j - 1] + cs[j]) / 2 if j else -10 ** 6
                hi = (cs[j] + cs[j + 1]) / 2 if j + 1 < len(xs) else 10 ** 6
                ov = min(span[1], hi) - max(span[0], lo)
                if ov > best:
                    best, bj = ov, j
            cur[bj] = (cur[bj] + " " + c).strip()
    # a blank parent cell (tehsil, block, circle, district) means "as above" in these lists
    prev = {}
    for hd, row, *_ in rows:
        for j, h in enumerate(hd):
            if header_kind(h)[0] in ("tehsil", "block", "circle", "district"):
                if row[j]:
                    prev[(id(hd), j)] = row[j]
                else:
                    row[j] = prev.get((id(hd), j), "")
    return rows


def records(module, rows, p, url, lu=None, method=None):
    """One record per row that names a person or gives a phone. rows: (head, row, caption[, src_pos])."""
    recs, seen = [], set()
    host = urlparse(url).netloc
    tag = p.get("tag") or _esw.slug(urlparse(url).path)[-50:] or "page"
    for n, t in enumerate(rows, 1):
        head, row, cap = t[:3]
        cols, hpost = header_map(head)
        if not cols:
            provenance.skipped('skip: not cols')
            continue

        def cell(k):
            i = cols.get(k)
            return _esw.clean(row[i]) if i is not None and i < len(row) else ""
        sub = " / ".join(x for x in (_esw.clean(row[i]) for i in cols.get("areas2", []) if i < len(row)) if x)
        name, npost = split_name(cell("name"))
        name = re.sub(r"^\d+[.)]\s*", "", name)
        if is_post_text(name) and not npost:
            npost, name = name, ""
        if NOT_NAME.match(name) or re.fullmatch(r"[\d\s.,/-]*", name):
            vac = bool(NOT_NAME.match(name)) and name.lower() not in ("do", "-", "—", "")
            name = ""
        else:
            vac = False
        phone = _esw.phones(cell("phone"))
        email = _esw.emails(cell("email"))
        if not (name or phone or email):
            provenance.skipped('skip: not (name or phone or email)')
            continue
        area = cell("area")
        if not area:
            area = next((cell(f) for f, _ in reversed(PARENT) if cell(f)), "") or p.get("area") or cap
        cpost = next((pp for rx, pp in PERSON_POST if re.search(rx, cap or "", re.I)), None)
        apost = next((pp for rx, pp in PERSON_POST[:11] if re.search(rx, area or "", re.I)), None)   # "Patwari Halqa X", "GQ X"
        post = cell("post") or npost or hpost or apost or cpost or p.get("post")
        sno = cell("sno")
        key = f"{host}:{tag}:{_esw.slug(sno) if sno and re.fullmatch(r'[0-9A-Za-z.-]{1,8}', sno) else n}"
        while key in seen:
            key += "-b"
        seen.add(key)
        lay = p.get("layer_key")
        lv = p.get("level")
        if not lv and lay:
            lv = level_of(lay, " ".join(x or "" for x in (post, area, cap, name)))
            if lv == "district" and not re.search(r"(?i)district|zila|jila|\bcmo|civil surgeon|\bdeo\b|\bdpo\b", post or ""):
                lv = level_of(lay, " ".join(head))
        recs.append(_esw.record(
            module, key, dept=p.get("dept") or LAYERS[lay]["dept"], level=lv, layer="field", field_layer=lay, area=area, post=post, name=name, phone=phone,
            email=email, address=cell("address"), state=p.get("state"), district=cell("district") or p.get("district"),
            tehsil=cell("tehsil") or p.get("tehsil"), block=cell("block") or p.get("block"), circle=cell("circle"),
            sub_area=sub or None, vacant=True if vac else None, caption=cap or None, office_id=key, source=url, last_updated=lu or p.get("last_updated"),
            table_row={h: c for h, c in zip(head, row) if h and c} or None,
            src_url=url, src_pos=t[3] if len(t) > 3 else None, method=method))
    if p.get("layer_key") and not p.get("all_rows"):
        recs = [(r, d) for r, d in recs if in_layer(p["layer_key"], d)]
    return recs


def parse(content, url, p, module):
    """Records from one saved answer (HTML or PDF bytes)."""
    if content[:5] == b"%PDF-":
        text, engine = pdf_text_engine(content)
        return records(module, text_rows(text), p, url, method=f"pdf text ({engine}), columns from the header positions")
    html = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
    if p.get("text_layout"):
        return records(module, text_rows(html), p, url, method="text layout, columns from the header positions")
    return records(module, html_rows(html), p, url, last_updated(html), method="html table")


def pdf_links(html, url, rx=None):
    """PDF links on a page (absolute, de-duplicated, in page order); rx narrows them by link text or href."""
    out = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', html or ""):
        u = urljoin(url, m.group(1).replace("&amp;", "&"))
        t = _esw.clean(re.sub(r"<[^>]+>", " ", m.group(2)))
        if (not rx or re.search(rx, u + " " + t, re.I)) and u not in out:
            out.append(u)
    return out


def fetch(p, get, module):
    """One queue item: p["url"] (HTML page or PDF). p["follow_pdfs"] (a regex, or true) also reads the PDFs the page links
    (at most p["max_pdfs"], default 25), for pages that only list files. Keeps every answer as a bucket file."""
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    tag = p.get("tag") or _esw.slug(urlparse(p["url"]).path)[-50:] or "page"
    pdf = r.content[:5] == b"%PDF-"
    files = [_esw.keep(module, f"{host}-{tag}", r.content, "pdf" if pdf else "html")]
    recs = parse(r.content, p["url"], p, module)
    if not pdf and p.get("follow_pdfs"):
        rx = p["follow_pdfs"] if isinstance(p["follow_pdfs"], str) else None
        for i, u in enumerate(pdf_links(r.text, p["url"], rx)[:p.get("max_pdfs", 25)], 1):
            f = get(u)
            if f is None or f.content[:5] != b"%PDF-":
                continue
            q = dict(p, tag=f"{tag}-pdf{i}")
            files.append(_esw.keep(module, f"{host}-{tag}-pdf{i}", f.content, "pdf"))
            recs += parse(f.content, u, q, module)
    why = "" if recs else ("no table with names or phones" + (" (scanned PDF? needs OCR)" if pdf and not pdf_text(r.content).strip() else ""))
    return recs, files, why


def seed(module):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{module}.json").read_text())


def reader(module, layer, **defaults):
    """(items, fetch) for a thin field_<layer>_<xx> module. The layer gives the department key, the level of each row and
    the row filter (rows of other departments on a shared page are left out; payload "all_rows": true keeps every row).
    defaults (dept, level, post, state) apply when the payload does not set them."""
    def items(get=None):
        return seed(module)

    def _fetch(p, get):
        q = dict(defaults, layer_key=layer)
        q.update({k: v for k, v in p.items() if v is not None})
        return fetch(q, get, module)
    return items, _fetch
