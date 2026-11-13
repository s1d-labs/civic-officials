"""North India: village revenue officials (patwari / halqa patwari, lekhpal) with the girdawar / kanungo circles, niabats and
tehsils above them, from district portal "revenue directory" pages and PDF lists (J&K, Haryana, Uttar Pradesh, Punjab,
Himachal, Uttarakhand). Measured 2026-11-13 on the archive.s1d.me copies:
- Kathua "Revenue Contacts (CUG)" (HTML, 209 rows: DC .. patwari, name + designation + territorial jurisdiction + CUG mobile).
- Kulgam "Revenue Directory" (HTML, 7 tables, 105 rows: designation, jurisdiction, incumbent, existing + CUG number; most
  patwari rows give the halqa and the CUG number, no name).
- Ramban "Revenue Official Directory" (HTML, 92 rows: "Name (Designation)" in one cell, place of posting, mobile).
- Ambala "Revenue" (HTML: per tehsil / sub tehsil one table "Patwar Circle | Patwari | Village | H.B. No. | Area"; one row
  per village; plus a patwari seniority roster with dates of birth, joining and retirement).
- Samba "CUG Number of District Samba Revenue Officers/Officials" (PDF text, 93 rows) and Srinagar "Contact Nos of Revenue
  Officers / Officials" (PDF text, 3 pages); J&K revenue department patwar halqa pages (jkrevenue.nic.in, phone only).
- Scanned PDFs (Kushinagar lekhpal posting list 2025): kept in the bucket, why = "scanned PDF, needs OCR".

Reading: HTML tables -> header words give each column a role (serial, name, designation, name+designation, jurisdiction /
patwar circle / halqa / place of posting, villages, hadbast no., phone columns, tehsil, district); a row whose cells are all
the same is a title ("Tehsil : Ambala City" gives the tehsil). PDF text (pdftotext -layout): a line that starts with a serial
number is split at runs of 2+ spaces; payload "columns" (list of roles) says what the pieces are; the last phone-like piece
is the phone. A cell "Name (Patwari)" or "NAME Patwari" or "Sh. X, JKAS, Deputy Commissioner" is split into name and post.

Records (dept revenue): level "village" for patwari / lekhpal / halqa rows (area = patwar circle or halqa as written; the
villages of the circle in "villages" with their hadbast numbers when the page gives them: one record per circle + patwari),
"circle" for girdawar / kanungo / naib tehsildar (niabat), "subdistrict" for tehsildar, "subdivision" for SDM, "district" for
DC / ADC / ACR. Roster tables (seniority lists: dates of birth and service) are kept as type "staff_roster" records (not
offices), because the same patwaris are in the circle tables. Every row keeps its cells (header -> text) in table_row.
Ids: dept:vil_rev_north:<host>:<tag>:<row key>.
"""
import re
from urllib.parse import urlparse

from dforms import _esw, _field

METHOD = "html table (header words -> columns), or pdf text (pdftotext -layout) split at 2+ spaces with columns from the payload"

MODULE = "vil_rev_north"

POSTS = [  # (regex, canonical post, level); first match wins, so longer posts first
    (r"addl\.?\s*deputy commissioner|additional deputy commissioner|\badc\b", "Additional Deputy Commissioner", "district"),
    (r"addl\.?\s*district development commissioner", "Additional District Development Commissioner", "district"),
    (r"assistant commissioner\s*\(?\s*rev|asstt?\.?\s*commissioner\s*\(?\s*rev|\bacr\b", "Assistant Commissioner (Revenue)", "district"),
    (r"deputy commissioner|\bd\.?c\.?\b(?!\s*office)", "Deputy Commissioner", "district"),
    (r"district revenue officer|\bdro\b", "District Revenue Officer", "district"),
    (r"sub[\s-]*divisional magistrate|\bsdm\b", "Sub Divisional Magistrate", "subdivision"),
    (r"naib[\s-]*t[ae]h?s[ih]*l?i?dar|\bn\.?\s?t\.?\b", "Naib Tehsildar", "circle"),
    (r"t[ae]h?s[ih]*l?i?dar", "Tehsildar", "subdistrict"),
    (r"office qanungo|\boq\b|o\.q\.", "Office Qanungo", "subdistrict"),
    (r"gird[aw]*w?ar|\bgq\b|g\.q\.", "Girdawar Qanungo", "circle"),
    (r"kanungo|qanungo|kanoongo", "Kanungo", "circle"),
    (r"lekhpal|लेखपाल", "Lekhpal", "village"),
    (r"patwari|patwar[iy]|pathwari|पटवारी|\bp/?h\b|patwar\s*hal|parwar\s*halqa", "Patwari", "village"),
]
ROLES = [  # (role, header regex); first match wins
    ("sno", r"^(file\s*\|\s*)?(s\.?\s*no|sr\.?\s*no|sl\.?\s*no|serial|s\.\s*no|file)\b"),
    ("skip", r"image|photo"),
    ("name_post", r"name\s*(&|and)\s*designation|name\s*/\s*designation"),
    ("post_place", r"present post with place|post with place"),
    ("villages", r"villages?\b"),
    ("hb", r"\bh\.?\s?b\.?\s*no|hadbast"),
    ("acre", r"area in|acre|hect"),
    ("phone", r"mobile|contact|cug|phone|\bno\.?\s*$"),
    ("post", r"designation|^post\b|^rank"),
    ("area", r"patwar\s*(circle|halqa|halka)|halqa|halka|circle|jurisdiction|place of posting|posting|niabat|station"),
    ("district", r"district|zila"),
    ("tehsil", r"tehsil|tahsil"),
    ("name", r"name|incumbent|officer|official"),
    ("address", r"address|office"),
]
TITLE_TEHSIL = re.compile(r"(?i)^\s*(sub[\s-]*)?tehsil\s*[:\-]\s*(.+)$")
VACANT = re.compile(r"(?i)^\s*(vacant|not available|n\.?a\.?|-+|nil)\b")
SERVICE = re.compile(r"(?i)\(?\b(ias|jkas|kas|hcs|pcs|ras)\b\)?")


def post_of(text):
    for rx, post, lv in POSTS:
        if re.search(rx, text or "", re.I):
            return post, lv
    return None, None


def split_name_post(s):
    """"Melap Singh (Patwari)" / "AYAZ HUSSAIN MALIK Patwari" / "Sh. X, JKAS, Deputy Commissioner, Ramban" -> (name, post text)."""
    s = _esw.clean(s)
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", s)
    if m and post_of(m.group(2))[0]:
        return m.group(1).strip(" ,"), m.group(2).strip()
    best = None
    for rx, _, _ in POSTS:
        mm = re.search(rx, s, re.I)
        if mm and (best is None or mm.start() < best):
            best = mm.start()
    if best is None:
        return s, ""
    name, post = s[:best], s[best:]
    if re.match(r"(?i)^\s*(addl|additional|assistant|asstt|sub|naib|office)\b", post) is None:
        mm = re.search(r"(?i)\b(addl\.?|additional|assistant|asstt\.?|sub|naib)\s*$", name)
        if mm:
            name, post = name[:mm.start()], name[mm.start():] + post
    name = SERVICE.sub("", name).strip(" ,.-")
    return name, post.strip(" ,")


def roles(header):
    out = {}
    for i, h in enumerate(header):
        h = _esw.clean(h)
        for role, rx in ROLES:
            if h and re.search(rx, h, re.I):
                out[i] = role
                break
    return out


def is_header(row):
    rl = set(roles(row).values())
    return len(rl - {"skip"}) >= 2 and bool(rl & {"name", "name_post", "phone", "post", "post_place"}) and \
        bool(rl & {"name", "name_post", "area", "post_place", "post"})


def clean_name(n):
    n = SERVICE.sub("", _esw.clean(n)).strip(" ,.-")
    return n


def row_fields(cells, rl):
    """(fields dict) from one row and the column roles."""
    f = {"phones": []}
    for i, c in enumerate(cells):
        role = rl.get(i)
        c = _esw.clean(c)
        if not role or not c or role == "skip":
            continue
        if role == "phone":
            if not VACANT.match(c):
                f["phones"].append(c)
        elif role not in f:
            f[role] = c
    return f


def build(f, p, cap_tehsil, hpost):
    """(record fields) for one row: name, post, level, area ..., or None when the row names nobody and gives no phone."""
    name, post_txt = f.get("name", ""), f.get("post", "")
    if f.get("name_post"):
        name, post_txt = split_name_post(f["name_post"])
    area = f.get("area", "")
    if f.get("post_place"):
        pp = f["post_place"]
        post_txt = post_txt or pp
        m = re.search(r"(?i)(?:halqa|halka|circle|p/?h\.?)\s+(.+)$", pp)
        area = area or (m.group(1) if m else pp)
    vacant = False
    if VACANT.match(name or "") or re.match(r"(?i)^vacant", f.get("name_post", "")):
        vacant, name = True, ""
    if name and post_of(name)[0] and not post_txt:
        name, post_txt = split_name_post(name)
    name = clean_name(name)
    extra = None
    m = re.search(r"(?i)\s*\((addl\.?|additional)\s*charge\)\s*", name)
    if m:
        extra, name = True, (name[:m.start()] + " " + name[m.end():]).strip()
    phone = _esw.phones(*f["phones"]) if f["phones"] else ""
    if not (name or phone):
        return None
    post, lv = post_of(post_txt)
    if not post:
        post, lv = post_of(area)
    if not post and hpost:
        post, lv = post_of(hpost)
    if not post and p.get("post"):
        post, lv = post_of(p["post"])
    if not lv:
        lv = p.get("level") or ("subdistrict" if re.search(r"(?i)tehsil|tahsil", area or "") else "district")
    tehsil = f.get("tehsil") or cap_tehsil
    m = re.search(r"(?i)[,\s]\s*tehsil\s+([A-Za-z .()-]+)$", area or "")
    if not tehsil and m:
        tehsil = m.group(1).strip()
    return {"name": name, "post": post or (post_txt or None), "post_as_written": post_txt or None, "level": lv or p.get("level"),
            "area": area or None, "phone": phone or None, "vacant": True if vacant else None, "extra_charge": extra,
            "district": f.get("district") or p.get("district"), "tehsil": tehsil or p.get("tehsil"),
            "address": f.get("address"), "village": f.get("villages"), "hb_no": f.get("hb"), "area_acre": f.get("acre")}


def _rec(key, b, p, url, cells, pos, method, **more):
    return _esw.record(MODULE, key, dept="revenue", level=b["level"], area=b["area"], post=b["post"],
                       post_as_written=b["post_as_written"] if b["post_as_written"] != b["post"] else None, name=b["name"],
                       phone=b["phone"], vacant=b["vacant"], extra_charge=b["extra_charge"], address=b["address"], state=p.get("state"), district=b["district"],
                       tehsil=b["tehsil"], office_id=key, source=p.get("page") or url, src_url=url, src_pos=pos, method=method,
                       table_row=cells or None, last_updated=p.get("last_updated"), **more)


def html_records(html, url, p):
    host = urlparse(url).netloc
    tag = p.get("tag") or _esw.slug(urlparse(url).path)[-50:] or "page"
    lu = _field.last_updated(html)
    soup = _esw.soup(html)
    out, groups, seen = [], {}, set()
    for t_no, table in enumerate(soup.find_all("table"), 1):
        gpos = []
        g = _esw.grid(table, pos=gpos)
        hi = next((i for i, r in enumerate(g[:5]) if is_header(r)), None)
        if hi is None:
            continue
        header = [_esw.clean(c) for c in g[hi]]
        rl = roles(header)
        hpost = next((h for h in header if re.search(r"(?i)name of (patwari|lekhpal)", h)), None)
        cap_tehsil = None
        for r in g[:hi]:
            if len(set(r)) == 1:
                m = TITLE_TEHSIL.match(_esw.clean(r[0]))
                if m:
                    cap_tehsil = m.group(2).strip()
        roster = any(re.search(r"(?i)date of (birth|retire|joining)", h) for h in header)
        for r, pos in zip(g[hi + 1:], gpos[hi + 1:]):
            cells = [_esw.clean(c) for c in r]
            if len(set(cells)) == 1:            # a title row inside the table
                m = TITLE_TEHSIL.match(cells[0] if cells else "")
                if m:
                    cap_tehsil = m.group(2).strip()
                continue
            if is_header(cells):
                continue
            f = row_fields(cells, rl)
            b = build(f, p, cap_tehsil, hpost)
            if not b:
                continue
            raw = {header[i] or f"col{i + 1}": c for i, c in enumerate(cells) if c and i < len(header)}
            sno = f.get("sno", "")
            if roster:
                rk = (b["name"], b["area"], b["post_as_written"])
                if rk in seen:
                    continue
                seen.add(rk)
                key = f"{host}:{tag}:roster:{t_no}-{pos.get('row') if isinstance(pos, dict) else len(out)}"
                rid, d = _rec(key, b, p, url, raw, pos, METHOD + "; roster table", roster=True)
                d["type"] = "staff_roster"
                if rid not in seen:
                    seen.add(rid)
                    out.append((rid, d))
                continue
            if b["village"] and b["area"]:          # one row per village: group by circle + patwari
                gk = (b["tehsil"], b["area"], b["name"])
                if gk in groups:
                    groups[gk][1]["villages"].append({"village": b["village"], "hb_no": b["hb_no"], "area_acre": b["area_acre"], "src_pos": pos})
                    continue
                key = f"{host}:{tag}:{_esw.slug(b['tehsil'] or '')}:{_esw.slug(b['area'])}"
                rid, d = _rec(key, b, p, url, raw, pos, METHOD)
                d["villages"] = [{"village": b["village"], "hb_no": b["hb_no"], "area_acre": b["area_acre"], "src_pos": pos}]
                groups[gk] = (rid, d)
                out.append((rid, d))
                continue
            key = f"{host}:{tag}:{t_no}-{_esw.slug(sno) if re.fullmatch(r'[0-9A-Za-z.-]{1,8}', sno or '') else pos.get('row') if isinstance(pos, dict) else len(out)}"
            rid, d = _rec(key, b, p, url, raw, pos, METHOD)
            while rid in seen:
                rid += "-b"
            seen.add(rid)
            if lu and not d.get("last_updated"):
                d["last_updated"] = lu
            out.append((rid, d))
    # unique ids for grouped rows too
    ids, res = set(), []
    for rid, d in out:
        while rid in ids:
            rid += "-b"
        ids.add(rid)
        if lu and "last_updated" not in d:
            d["last_updated"] = lu
        res.append((rid, d))
    return res


PHONE_TOKEN = re.compile(r"^(?:\+?91[\s-]*)?\d[\d\s-]{8,}\d$|^-+$|^not available$", re.I)


def text_records(text, url, p, engine="pdftotext -layout"):
    """PDF layout text -> records. p["columns"]: roles of the pieces between the serial number and the phone (e.g.
    ["post", "area", "name"]); without it the pieces are read as name+post, area."""
    host = urlparse(url).netloc
    tag = p.get("tag") or _esw.slug(urlparse(url).path)[-50:] or "page"
    cols = p.get("columns") or ["name_post", "area"]
    out, ids = [], set()
    for pg, page in enumerate(text.split("\f"), 1):
        for ln_no, line in enumerate(page.splitlines(), 1):
            m = re.match(r"^\s*(\d{1,4})[.)]?\s{1,}(\S.*)$", line)
            if not m:
                continue
            pieces = [x.strip() for x in re.split(r"\s{2,}", m.group(2).strip()) if x.strip()]
            phone = ""
            if pieces and PHONE_TOKEN.match(pieces[-1]):
                phone = pieces.pop()
            elif pieces:                              # "Tarsem Lal 9484221500"
                mm = re.search(r"\s((?:\+?91[\s-]*)?\d{10})$", pieces[-1])
                if mm:
                    phone, pieces[-1] = mm.group(1), pieces[-1][:mm.start()].strip()
            if len(pieces) > len(cols):              # extra pieces join the last text column
                pieces = pieces[:len(cols) - 1] + [" ".join(pieces[len(cols) - 1:])]
            if len(pieces) < len(cols):
                # "Srinagar Patwari" (two columns closer than 2 spaces): split the first piece at a known post
                for i, c in enumerate(cols):
                    if c == "post" and i < len(pieces) and not post_of(pieces[i])[0] and i > 0 and post_of(pieces[i - 1])[0]:
                        nm, pt = split_name_post(pieces[i - 1])
                        pieces[i - 1:i] = [nm, pt]
                        break
            f = {"phones": [phone] if phone and not VACANT.match(phone) else [], "sno": m.group(1)}
            for c, v in zip(cols, pieces):
                f[c] = v
            b = build(f, p, None, None)
            if not b:
                continue
            key = f"{host}:{tag}:p{pg}-{ln_no}"
            rid, d = _rec(key, b, p, url, {"line": line.strip()}, {"page": pg, "line": ln_no, "line_text": line.rstrip()},
                          f"pdf text ({engine}), line split at 2+ spaces, columns from the payload")
            d["sno"] = m.group(1)
            if rid in ids:
                continue
            ids.add(rid)
            out.append((rid, d))
    return out


def items(get=None):
    return _field.seed(MODULE)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    tag = p.get("tag") or _esw.slug(urlparse(p["url"]).path)[-50:] or "page"
    content = r.content
    if content[:5] == b"%PDF-":
        files = [_esw.keep(MODULE, f"{host}-{tag}", content, "pdf")]
        text, engine = _field.pdf_text_engine(content)
        if not re.search(r"[A-Za-z]{3}", text or ""):
            return [], files, "scanned PDF, needs OCR (kept in the bucket)"
        recs = text_records(text, p["url"], p, engine)
        return recs, files, "" if recs else "no rows in the PDF text"
    html = r.text
    files = [_esw.keep(MODULE, f"{host}-{tag}", content, "html")]
    recs = html_records(html, p["url"], p)
    if p.get("follow_pdfs"):
        for i, u in enumerate(_field.pdf_links(html, p["url"], p["follow_pdfs"] if isinstance(p["follow_pdfs"], str) else None)[:10], 1):
            f = get(u)
            if f is None or f.content[:5] != b"%PDF-":
                continue
            files.append(_esw.keep(MODULE, f"{host}-{tag}-pdf{i}", f.content, "pdf"))
            text, engine = _field.pdf_text_engine(f.content)
            if re.search(r"[A-Za-z]{3}", text or ""):
                recs += text_records(text, u, dict(p, tag=f"{tag}-pdf{i}", page=p["url"]), engine)
    return recs, files, "" if recs else "no table with names or phones"
