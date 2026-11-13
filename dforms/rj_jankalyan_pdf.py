"""Rajasthan: officer lists in the PDF files of the Jankalyan portals, read from the copies that dforms/rj_jankalyan.py saved.

dforms/rj_jankalyan.py keeps every file of a portal's contact directory in the bucket once (record dept:rj_jankalyan:<code>:file:<id>,
type source_file, "stored": depts/rj_jankalyan/<portal>/<id>.pdf in project civic-officials-depts-direct). This reader reads that copy
(hub.read_urls; fetch once, process anywhere: any runner, no proxy) and only when the copy is missing asks the file host (India only).

The files are free-form: Excel / Word / Chrome prints, about 1-15 pages, English or Hindi; much of the Hindi is set in the legacy
font Kruti Dev 010 (the text layer holds Latin letters: "uke vf/kdkjh" = "नाम अधिकारी"). Steps:
  1. layout text per page (pdftotext -layout when the binary is there, else pypdf layout mode);
  2. on a page that is Kruti Dev (dforms/_ward_kd.is_krutidev), each word that has Kruti Dev letter patterns is mapped to Unicode;
     English words, abbreviations (IAS, RAS, CHC), numbers and email addresses stay. Every chunk keeps its start column;
  3. Hindi header words become their English header words (नाम -> Name, पद -> Designation, मोबाइल -> Mobile ...), on header lines only;
  4. dforms/_field.text_rows: a header line sets the columns, a line with a serial number opens a row, the next lines continue it;
  5. pages or files with no usable header: "loose" rows, one per line that carries a phone number or an email, cells = chunks of that
     line (name = the chunk with Sh. / Smt. / Dr. / श्री ..., post = the chunk with a post word).
Records (depts.py contract): one dept_office per row with a name or a post and a phone or an email. dept and level from the post and
the file's category with rj_jankalyan.classify (district portals default administration; CHC / PHC files: health, facility level;
Sarpanch / Pradhan / Zila Parishad / Panchayat Samiti member / Parshad files: elected=true, rural_development or town_body).
Fields: post, name, phone, email, area, office, district (payload; or the row's own district column), category, cells (every column
of the row, header -> text), src_pos = provenance.line_pos(page, line, raw line text) of the line that opens the row (+ line_end,
mode "table" or "loose"), src = provenance.file_src (sha256 of the bytes read, original url, bucket key), method.
Ids: dept:rj_jankalyan_pdf:<portal code>:<file id>:<row n>.
A scanned file (no text layer) gives no rows: the item ends done with a note record {"type": "note", "ocr_needed": true}.
"""
import re

import provenance
from dforms import _esw, _field, _ward_kd as kd
from dforms import rj_jankalyan as rj

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + Kruti Dev map; columns from the header positions, else one row per phone line"

MODULE = "rj_jankalyan_pdf"
PROJECT = "civic-officials-depts-direct"     # project whose bucket holds the copies of rj_jankalyan

# file categories (ContactCategoryName) that list officers or elected members; others (help lines, Aadhaar centres, bus times,
# environment plans, BLO lists) are not queued
OFFICER_CATS = re.compile(r"(?i)^(dlo|other officers|chc|phc|ero|directory|bdo|district office|directorate|head office|ceo|"
                          r"chief planning|block office|pradhan|sarpanch|zila parishad member|panchayat samiti member|parshad|"
                          r"ward panch|right to information|telephone)")
ELECTED = [(re.compile(r"(?i)sarpanch|ward panch"), "rural_development", "gram_panchayat", "Sarpanch"),
           (re.compile(r"(?i)pradhan"), "rural_development", "block", "Pradhan"),
           (re.compile(r"(?i)zila parishad member"), "rural_development", "district", "Zila Parishad Member"),
           (re.compile(r"(?i)panchayat samiti member"), "rural_development", "block", "Panchayat Samiti Member"),
           (re.compile(r"(?i)parshad"), "town_body", "ward", "Parshad (Councillor)")]

KD_SIGN = re.compile(r"[;'\"/\]\[{}<>=|`~^&*+,]|[a-z][A-Z]|^(Jh|Jherh|lqJh|Mk0|Mk-|Jhefr)$")
ENGLISH = re.compile(r"(?i)^(officer|officers|district|collector|engineer|executive|assistant|block|development|superintendent|"
                     r"police|medical|health|education|office|nagar|road|deputy|additional|addl|chief|director|joint|secretary|"
                     r"commissioner|magistrate|sub|division|divisional|tehsildar|in-?charge|incharge|charge|extra|vacant|"
                     r"name|mobile|phone|email|e-mail|no|post|designation|place|posting|department|jaipur|ajmer|kota|bikaner|"
                     r"jodhpur|udaipur|alwar|sikar|tonk|bundi|pali|dausa|churu|baran|barmer|jalore|jhalawar|jhunjhunu|karauli|"
                     r"nagaur|sirohi|dholpur|bharatpur|bhilwara|banswara|dungarpur|rajsamand|pratapgarh|hanumangarh|ganganagar|"
                     r"sriganganagar|chittorgarh|jaisalmer|beawar|balotra|phalodi|kekri|shahpura|sanchore|anupgarh|deeg|"
                     r"salumber|dudu|neem|ka|thana|city|rural|urban|north|south|east|west|and|of|the|for|to|at|cum)$")
HINDI_HEAD = [  # Hindi header words -> English header words (header lines only)
    (r"क्र\.?\s*0?\s*सं\.?0?|क्रम\s*संख्या|क्रमांक|क्र\.\s*स\.?", "S.No"),
    (r"(ई|इ)-?\s?मेल(\s*आई\s*डी|\s*आईडी)?", "Email"),
    (r"मोबाइ?ई?ल(\s*(न|नं|नम्बर|नंबर|नo|न0)\.?)?|मो\.?\s*नं\.?", "Mobile"),
    (r"(दूरभाष|फोन|सम्पर्क|संपर्क)(\s*(न|नं|नम्बर|नंबर)\.?)?", "Phone"),
    (r"कार्यालय\s*(नम्बर|नंबर|न\.|दूरभाष|फोन)", "Office Phone"),
    (r"पद\s*नाम|पदनाम|पद", "Designation"),
    (r"(अधिकारी|सरपंच|प्रधान|सदस्य|पार्षद|प्रभारी|कर्मचारी)\s*(का|के)\s*नाम|नाम\s*(अधिकारी|सरपंच|प्रधान|सदस्य)", "Name of Officer"),
    (r"नाम", "Name"),
    (r"पंचायत\s*समिति", "Panchayat Samiti"), (r"ग्राम\s*पंचायत", "Gram Panchayat"), (r"जिला|जिले", "District"),
    (r"तहसील", "Tehsil"), (r"विभाग", "Department"), (r"पता", "Address"), (r"वार्ड", "Ward"),
]
EN_HEAD = [(r"(?i)\b(official|office|off\.|residence|resi\.|res\.)\s*(no\.?|number|contact( no\.?)?|phone|tel\.?)(?=\s|$)", "Office Phone"),
           (r"(?i)\binstitute\b", "Institution")]
TITLE = re.compile(r"(?i)^(dr|sh|shri|smt|sri|mr|mrs|ms|km|kumari)\b\.?|^(श्री|श्रीमती|सुश्री|डॉ|डा\.|डा\s|कु\.|सुश्री)")
KD_TITLE = re.compile(r"^(Jh|Jhefr|Jherh|Jefr|Jheku|lqJh|Mk0|Mk-|Mk\.)(?=\s)")      # Kruti Dev श्री, श्रीमति, श्रीमती, सुश्री, डॉ0
NAME_HEAD = re.compile(r"(?i)name|नाम|पार्षद|सदस्य|सरपंच|प्रधान")
CHUNK = re.compile(r"\S+(?: \S+)*")
ROW_NO = re.compile(r"^\s*(\d{1,4})\s*[.)\-]?(?:\s+|$)")    # "1", "4-", "12." open a row
MOBILE = re.compile(r"(?<!\d)(?:0?[6-9]\d{9}|[6-9]\d{4} \d{5}|0\d{2,4}[\s-]\d{5,8})(?!\d)")   # sure phone numbers (not a PIN code or a count)
PHONE = re.compile(r"(?<!\d)(?:[6-9]\d{9}|0\d{2,4}[\s-]?\d{5,8}|\d{6,8})(?!\d)")


def kd_token(t):
    """On a Kruti Dev page: is this word Kruti Dev? Not: emails, numbers, abbreviations (IAS, R.A.S.), common English words,
    Capitalised English-looking words without Kruti Dev signs ("Ramesh"); lower-case words and words with signs are."""
    w = t.strip(".:()")
    if not w or "@" in t or "www" in t or not re.search(r"[A-Za-z]", w) or re.fullmatch(r"[A-Z][A-Z.\-&/]*", w) \
            or ENGLISH.match(w.strip(",")):
        return False
    if KD_SIGN.search(w) or re.search(r"Hk|kj|q[^u]|^[A-Z]k[a-z]", w):
        return True
    return not re.fullmatch(r"[A-Z][a-z]{2,}", w)


def kd_chunk(c):
    toks = c.split(" ")
    if not any(kd_token(t) for t in toks):
        return c
    out = []
    for t in toks:
        out.append(kd.convert(t) if kd_token(t) else t)
    return " ".join(out)


def relayout(line, fn):
    """Apply fn to each chunk of a layout line; every chunk keeps its start column (at least 2 spaces between chunks)."""
    out = ""
    for m in CHUNK.finditer(line):
        c = fn(m.group())
        if len(out) < m.start():
            out += " " * (m.start() - len(out))
        elif out:
            out += "  "
        out += c
    return out


def head_en(chunk):
    s = chunk
    for rx, en in HINDI_HEAD:
        s = re.sub(rx, en, s)
    return s


def en_head(chunk):
    for rx, en in EN_HEAD:
        chunk = re.sub(rx, en, chunk)
    return chunk


def is_head_line(ln):
    hits = sum(1 for rx, _ in HINDI_HEAD if re.search(rx, ln))
    return hits >= 2 and not PHONE.search(ln)


def page_lines(text):
    """[(page, line no, raw line, line for parsing)] of the layout text (pages split at form feeds)."""
    out = []
    for pg, pt in enumerate(text.split("\f"), 1):
        is_kd = kd.is_krutidev(pt)
        for k, raw in enumerate(pt.split("\n"), 1):
            ln = _esw.clean(raw) and re.sub("[​‌‍﻿]", "", raw.replace("\xa0", " "))
            if not ln or not ln.strip():
                provenance.skipped("empty")
                continue
            if is_kd:
                ln = relayout(ln, kd_chunk)
            if is_head_line(ln):
                ln = relayout(ln, head_en)
            if _field._is_head(_field._chunks(ln)) or _field._head_part(ln):
                ln = relayout(ln, en_head)
            out.append((pg, k, raw, ln))
    return out


def text_of(lines):
    """Layout text for _field.text_rows (pages joined with form feeds; empty lines kept so line numbers stay right)."""
    pages = {}
    for pg, k, _, ln in lines:
        pages.setdefault(pg, {})[k] = ln
    out = []
    for pg in range(1, max(pages or {0: 0}) + 1):
        d = pages.get(pg, {})
        out.append("\n".join(d.get(k, "") for k in range(1, max(d or {0: 0}) + 1)))
    return "\f".join(out)


def _header_at(lines, i):
    """(header chunks, lines used) when line i is a header line (with the header word lines right above / below it), else None."""
    ch = _field._chunks(lines[i][3])
    if not _field._is_head(ch):
        return None
    hd, used = _field._split_head(ch), 1
    if i and _field._head_part(lines[i - 1][3]) and lines[i - 1][0] == lines[i][0] and lines[i][1] - lines[i - 1][1] <= 2:
        hd = _field._merge_head(hd, _field._split_head(_field._chunks(lines[i - 1][3])))
    if i + 1 < len(lines) and _field._head_part(lines[i + 1][3]) and len(_field._chunks(lines[i + 1][3])) <= len(hd) \
            and lines[i + 1][0] == lines[i][0] and lines[i + 1][1] - lines[i][1] <= 2:
        hd = _field._merge_head(hd, _field._split_head(_field._chunks(lines[i + 1][3])))
        used = 2
    return hd, used


def _gap(a, b):
    """Line distance between two lines (page, line); across pages: far."""
    return abs(b[1] - a[1]) if a[0] == b[0] else 99


def _assign(seg, anchors):
    """Each body line -> index of the anchor (row) it belongs to. A line between two anchors goes to the nearer one; a blank line
    between it and one of them sends it to the other (cells printed centred in tall rows sit above and below their row line)."""
    out = {}
    for j, L in enumerate(seg):
        if j in anchors:
            out[j] = j
            continue
        up = max((a for a in anchors if a < j), default=None)
        dn = min((a for a in anchors if a > j), default=None)
        du = _gap(seg[up], L) if up is not None else 99
        dd = _gap(L, seg[dn]) if dn is not None else 99
        bu = du > 1 and all(_gap(seg[x], seg[x + 1]) == 1 for x in range(up, j)) if up is not None else False
        bd = dd > 1 and all(_gap(seg[x], seg[x + 1]) == 1 for x in range(j, dn)) if dn is not None else False
        # bu / bd: the lines between are contiguous (no blank line) -> the line is "attached" on that side
        if du <= 3 and (du < dd or (du == dd and not bd) or (bu and not bd)) and not (bd and not bu and dd <= 2):
            out[j] = up
        elif dd <= 2:
            out[j] = dn
    return out


def table_rows(lines):
    """Rows of the tables in the page lines: a header line (dforms/_field rules) sets the columns until the next header; a line
    that starts with a serial number opens a row (when the table has none: a line with a phone or an email); other lines join the
    nearest row line. A chunk goes to the column whose span it overlaps most (columns reach halfway to their neighbours' centres)."""
    rows, i = [], 0
    heads = []
    while i < len(lines):
        h = _header_at(lines, i)
        if h:
            heads.append((i, h[0], h[1]))
            i += h[1]
        else:
            i += 1
    for t, (hi, hd, used) in enumerate(heads):
        end = heads[t + 1][0] - (1 if heads[t + 1][2] and heads[t + 1][0] and _field._head_part(lines[heads[t + 1][0] - 1][3]) else 0) \
            if t + 1 < len(heads) else len(lines)
        seg = lines[hi + used:end]
        head = [en_head(c) for _, c in hd]
        cols, hpost = _field.header_map(head)
        if not cols or not seg:
            continue
        cs = [x + len(c) / 2 for x, c in hd]
        anchors = [j for j, L in enumerate(seg) if ROW_NO.match(L[3])]
        if len(anchors) < 2:
            anchors = [j for j, L in enumerate(seg) if PHONE.search(L[3]) or "@" in L[3]]
        if not anchors:
            continue
        own = _assign(seg, anchors)
        cap = _esw.clean(lines[hi - 1][3])[:120] if hi and len(_field._chunks(lines[hi - 1][3])) <= 2 else ""
        for a in anchors:
            cells = [[] for _ in hd]
            mine = [j for j in range(len(seg)) if own.get(j) == a]
            for j in mine:
                for x, c in _field._chunks(seg[j][3]):
                    best, bj = -10 ** 6, 0
                    for q in range(len(hd)):
                        lo = (cs[q - 1] + cs[q]) / 2 if q else -10 ** 6
                        hi_ = (cs[q] + cs[q + 1]) / 2 if q + 1 < len(hd) else 10 ** 6
                        ov = min(x + len(c), hi_) - max(x, lo)
                        if ov > best:
                            best, bj = ov, q
                    cells[bj].append(c)
            row = [" ".join(c) for c in cells]
            if cols.get("sno") is not None and row[cols["sno"]]:
                row[cols["sno"]] = re.sub(r"[.)]$", "", row[cols["sno"]])
            pg, k, raw, _ = seg[a]
            rows.append(_row(head, row, cols, hpost, cap, provenance.line_pos(
                pg, k, raw, line_end=max(seg[j][1] for j in mine) if mine else None,
                line_start=min(seg[j][1] for j in mine) if mine else None, mode="table")))
    return rows


def _row(head, row, cols, hpost, cap, pos):
    cells = {(h or f"col{j}"): c for j, (h, c) in enumerate(zip(head, row)) if c}

    def cell(k):
        i = cols.get(k)
        return _esw.clean(row[i]) if i is not None and i < len(row) else ""
    skip = {cols.get(k) for k in ("sno", "address")}
    phone_cols = [j for j, h in enumerate(head) if _field.header_kind(h)[0] == "phone"]
    skip |= set(phone_cols)
    phone = " , ".join([row[j] for j in phone_cols if row[j]] + [   # + mobiles printed into other columns
        " , ".join(MOBILE.findall(_esw.EMAIL.sub(" ", c))) for j, c in enumerate(row)
        if j not in skip and MOBILE.search(_esw.EMAIL.sub(" ", c))])
    dep = next((c for h, c in cells.items() if re.search(r"(?i)department|विभाग", h)), "")
    return {"name": cell("name"), "post": cell("post") or hpost or "", "phone": phone, "email": cell("email") or _esw.emails(" ".join(row)), "area": cell("area") or cell("block") or cell("tehsil"), "district": cell("district"),
        "address": cell("address"), "department": dep, "caption": cap, "cells": cells, "pos": pos}


def loose_rows(lines):
    """One row per line with a phone number or an email (lists without a header the engine knows)."""
    rows = []
    for pg, k, raw, ln in lines:
        if not (MOBILE.search(ln) or "@" in ln):
            provenance.skip_line(ln, "no phone or email")
            continue
        ch = [c for c in CHUNK.findall(ln)]
        ch = [re.sub(r"^\d{1,3}[.)]?\s+", "", c) if j == 0 else c for j, c in enumerate(ch)]
        name = next((c for c in ch if TITLE.match(c)), "")
        post = next((c for c in ch if c != name and (_field.is_post_text(c) or rj.classify(c, "", None)[0] != "administration"
                                                      or re.search(r"अधिकारी|तहसीलदार|सचिव|निरीक्षक|अभियंता|प्रधानाचार्य|सरपंच|प्रधान", c))
                     and not PHONE.search(c) and "@" not in c), "")
        rows.append({"name": name, "post": post, "phone": " , ".join(c for c in ch if MOBILE.search(c) and "@" not in c),
                     "email": " ".join(c for c in ch if "@" in c), "area": "", "district": "", "address": "", "department": "",
                     "caption": "", "cells": {f"col{j}": c for j, c in enumerate(ch)},
                     "pos": provenance.line_pos(pg, k, raw, mode="loose")})
    return rows


KD_TITLES = {"Jh": "श्री", "Jheku": "श्रीमान", "Jhefr": "श्रीमति", "Jefr": "श्रीमति", "Jherh": "श्रीमती", "lqJh": "सुश्री", "Mk0": "डॉ0", "Mk-": "डॉ.",
             "Mk.": "डॉ."}


def person_of(cells, titled_only=False, post_hint=""):
    """(name, post) of a row that has a phone or an e-mail but no name (or no post) column the header map knows (2026-11-13:
    these rows were dropped, 76 of 102 in a Baran file). The name: a cell under a name-like header ("User Name", "निर्वाचित
    पार्षद"), else a cell with a title (Shri, श्री, Kruti Dev "Jhefr"); unless titled_only: else the first Hindi cell that is not
    a post, else the last text cell. The post: the next Hindi cell after the name."""
    texts = []
    for h, c in cells.items():
        c = _esw.clean(MOBILE.sub(" ", _esw.EMAIL.sub(" ", c)))
        c = re.sub(r"^\d{1,4}[.)]?\s+", "", c)
        if not re.search(r"[A-Za-zऀ-ॿ]{2}", c) or "@" in c:
            continue
        m = KD_TITLE.match(c)
        if m:
            rest = c[m.end():].strip()
            c = KD_TITLES[m.group(1)] + " " + (rest if re.search(r"[ऀ-ॿ]", rest) else kd_chunk(rest))
        texts.append((h, re.split(r"\]", c)[0].strip(" ,")))
    vals = [c for _, c in texts]
    name = next((c for h, c in texts if NAME_HEAD.search(h) and not _field.is_post_text(c) and
                 not re.fullmatch(r"(?i)(name|नाम)", c)), "") or next((c for c in vals if TITLE.match(c)), "")
    if not name and titled_only and post_hint in vals:    # the cell after the post: "Dy Dir Agriculture | Radhey Shyam Narwal"
        nxt = vals[vals.index(post_hint) + 1:vals.index(post_hint) + 2]
        if nxt and not _field.is_post_text(nxt[0]) and not re.search(r"\d", nxt[0]) and 1 <= len(nxt[0].split()) <= 5:
            name = nxt[0]
    if not name and not titled_only:
        name = next((c for c in vals if re.search(r"[ऀ-ॿ]", c) and not _field.is_post_text(c)), "") or (vals[-1] if vals else "")
    post = next((c for c in vals[vals.index(name) + 1:] if re.search(r"[ऀ-ॿ]", c)), "") if name in vals else ""
    return name, post


def build(rows, p):
    cat = p.get("category") or ""
    el = next(((d, lv, post) for rx, d, lv, post in ELECTED if rx.search(cat)), None)
    health_fac = re.search(r"(?i)^(chc|phc)$", cat.strip())
    recs, seen = [], set()
    for n, r in enumerate(rows, 1):
        name = _esw.clean(r["name"])
        name = re.sub(r"^\d+[.)]\s*", "", name)
        post = _esw.clean(r["post"])
        if _field.is_post_text(name) and not post:
            post, name = name, ""
        phone = _esw.phones(r["phone"])
        email = _esw.emails(r["email"])
        if re.fullmatch(r"[\d\s+()/,-]*", name):
            name = ""
        if not phone:                                   # a mobile printed in a column the header map does not know
            phone = _esw.phones(" , ".join(MOBILE.findall(" ".join(_esw.EMAIL.sub(" ", c) for c in r["cells"].values()))))
        name = _esw.clean(MOBILE.sub(" ", name))           # "श्रीमति मंजू धंनते वाल 9950363890" (loose rows)
        if (phone or email) and not name:
            n2, p2 = person_of(r["cells"], titled_only=bool(post), post_hint=post)
            if n2 != post:
                name, post = n2, post or p2
        if health_fac and not (name or post) and r["area"]:
            post = f"{cat.strip()} {r['area']}"
        if not (phone or email) or not (name or post):
            provenance.skipped("no phone/email or no name/post")
            continue
        vacant = bool(re.search(r"(?i)^(vacant|रिक्त)", name))
        if el:
            dept, level = el[0], el[1]
            post = post or el[2]
        else:
            dtext = r.get("department") or ""
            dept, level = rj.classify(post, dtext or cat, p.get("dept") or "administration")
            if re.search(r"(?i)public health engineering|\bphed\b|जन स्वास्थ्य अभियांत्रिकी", f"{post} {dtext}"):
                dept = "water"
            if re.search(r"(?i)^\s*(bdo|b\.d\.o)\b|vikas adhikari|विकास अधिकारी", post):   # "BDO- M. Thana" is not a police post
                dept, level = "rural_development", "block"
            if health_fac:
                dept, level = "health", "facility"
        key = f"{p['code']}:{p['entry_id']}:{n}"
        if key in seen:
            provenance.skipped("repeated key")
            continue
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept=dept, level=level, area=r["area"] or p.get("district") or "Rajasthan",
                                post=post or cat, name="" if vacant else name, vacant=True if vacant else None, phone=phone,
                                email=email, address=r["address"] or None, office=r["department"] or None,
                                elected=True if el else None, category=cat or None, caption=r["caption"] or None,
                                state="RJ", district=p.get("district"), row_district=r["district"] or None, portal=p.get("portal"),
                                office_id=f"rj-jankalyan:{p['code']}:{p['entry_id']}:{n}", source=p.get("source") or p.get("url"),
                                file_url=p.get("url"), cells=r["cells"], src_pos=r["pos"], method=METHOD))
    return recs


def parse(content, p):
    """(records, engine) of one stored PDF."""
    text, engine = _field.pdf_text_engine(content)
    lines = page_lines(text)
    rows = table_rows(lines)
    used = {(r["pos"]["page"], r["pos"]["line"]) for r in rows}
    if not rows:
        rows = loose_rows(lines)
    elif len(rows) < 3:
        rows += [r for r in loose_rows(lines) if (r["pos"]["page"], r["pos"]["line"]) not in used]
    return build(rows, p), engine, bool(text.strip())


def stored(p, get):
    """(bytes, key) of the bucket copy (payload "stored": "<project>/<path>.pdf"), None when the item has no copy."""
    hub, k = getattr(get, "hub", None), p.get("stored")
    if not hub or not k:
        return None
    try:
        import requests
        url = hub.read_urls(k.split("/", 1)[0], [k])[k]
        r = requests.get(url, timeout=(20, 180))
        if r.status_code == 200 and r.content[:5] == b"%PDF-":
            return r.content, k
    except Exception:  # noqa: BLE001 - fall back to the file host
        pass
    return None


def items_from(file_records):
    """Queue items from the source_file records of rj_jankalyan: [(record id, data)] -> [{"key", "payload"}]."""
    out = []
    for rid, d in file_records:
        cat = (d.get("category") or "").strip()
        if not d.get("fetched") or not d.get("stored") or (cat and not OFFICER_CATS.search(cat)):
            continue
        _, _, code, _, eid = rid.split(":")[:5]
        label = (d.get("portal") or "").split(".")[0]
        out.append({"key": f"{MODULE}:{label}:{eid}", "payload": {
            "reader": MODULE, "url": d["url"], "stored": f"{PROJECT}/{d['stored']}", "category": d.get("category"),
            "portal": d.get("portal"), "code": code, "entry_id": eid, "district": d.get("district"), "dept": d.get("dept"),
            "source": d.get("source"), "state": "RJ", "route": "abroad", "expected": 0}})
    return sorted(out, key=lambda i: i["key"])


def items(get=None):
    return _field.seed(MODULE)


def fetch(p, get):
    got = stored(p, get)
    content, key = got if got else (None, None)
    if content is None:
        r = get(p["url"])
        if r is None or r.content[:5] != b"%PDF-":
            return [], [], "no stored copy and the file host gave no pdf"
        content = r.content
    recs, engine, has_text = parse(content, p)
    src = {"src": provenance.file_src(content, p["url"], key)} if key else {"src_url": p["url"]}
    for _, d in recs:
        d.update(src)
        d["method"] = d["method"].replace("pdftotext -layout, else pypdf layout", engine)
    if not recs:
        note = {"type": "note", "category": p.get("category"), "portal": p.get("portal"), "file_url": p["url"], "state": "RJ",
                "district": p.get("district"), "ocr_needed": not has_text, "method": f"pdf text ({engine})",
                "note": "no text layer (scan): needs OCR" if not has_text else "no rows with a name or post and a phone or email",
                **src}
        return [(f"dept:{MODULE}:{p['code']}:{p['entry_id']}:note", note)], [], ""
    return recs, [], ""
