"""Tamil Nadu: the Village Administrative Officer (VAO, கிராம நிர்வாக அலுவலர்) of each revenue village, with mobile numbers, from
the District Disaster Management Plans 2024 that TNSDMA publishes (tnsdma.tn.gov.in/pages/view/ddmp: one PDF per district, 38).
Many plans carry the full VAO list in the chapter "Important contact numbers" (taluk -> firka -> village, VAO name, cell / CUG
number, sometimes a personal mobile); some carry early-warning tables per vulnerable village with the Revenue Inspector, the VAO
and the village Panchayat Secretary (Ariyalur); some give only village + VAO number (Coimbatore).

Structure (measured 2026-11-13 on the archive.s1d.me copies of 2026-11-07): text PDFs (pdftotext -layout keeps the columns).
A list starts at a header block (1-4 lines with words like S.No / Village / VAO's Name / Cell No / CUG / Mobile / Designation)
that names the VAO (in the header or in a title up to 8 lines above: "VAO", "V.A.O", "Village Administrative Officer");
columns come from the x-positions of the header words (overlapping words of a multi-line header are one column). A row starts
at a line with a serial number in the S.No column; wrapped cells on other lines join the row above when the next serial line
already fills that column (or the cell above ends with "," / "&"), else the row below. Lines with "Firka" / "Taluk" set the
firka / taluk of the rows after them. The list continues over page breaks without a new header and ends at another header
that does not name the VAO, or after 4 lines without a row.

Records (dept revenue, level village): one per row: post "Village Administrative Officer", post_regional "கிராம நிர்வாக அலுவலர்",
name (honorific Thiru. / Tmt. / Selvi / Mr. / Mrs. removed; raw cells kept), phone (all numbers of the row's VAO columns,
CUG first, as written), area = village as written, firka, taluk, district (payload), in_charge (i/c), vacant. A Revenue
Inspector column gives a record with post "Revenue Inspector" (level circle) and a Panchayat Secretary column a record with
post "Village Panchayat Secretary" (dept rural_development, level gram_panchayat) for the same village.
One queue item per district PDF (archive-first: the hub reads the archive.s1d.me copy when it has one). The PDF is kept in the
bucket. Record ids: dept:vil_tn_ddmp:<district slug>:<page>-<line>[:ri|:ps].
"""
import re

import provenance
from dforms import _esw, _field

METHOD = "pdf text (pdftotext -layout), columns from the header word positions, wrapped cells joined by column"

MODULE = "vil_tn_ddmp"
POST = "Village Administrative Officer"
POST_TA = "கிராம நிர்வாக அலுவலர்"

PHONE = re.compile(r"(?<![\d])(?:\+?91[\s-]?)?(?:[6-9]\d{4}[ -]?\d{5}|[6-9]\d{9}|0\d{2,4}[ -]?\d{6,8})(?:-[A-Z])?(?![\d])")
VAO_TITLE = re.compile(r"(?i)\bvao|v\.\s?a\.\s?o\b|village\s+administrat")
HEADISH = re.compile(r"(?i)s\.?\s?no|sl\.?|^s\.?$|^no\.?$|village|name|vao|cell|mobile|cug|contact|phone|designation|secretary|"
                     r"\bri\b|landline|number|officer|thiru|tmt|selvi|personal|office|location|firka|\bno\b")
NAME_W = re.compile(r"(?i)name|vao|officer")
PHONE_W = re.compile(r"(?i)cell|mobile|cug|contact|phone|number")
AREA_W = re.compile(r"(?i)village|designation|office|location")
SERIAL = re.compile(r"^\d{1,3}[.)]?$")
NOISE = re.compile(r"(?i)disaster\s+management\s+plan|ddmp|^p\s?a\s?g\s?e\b|^page\b|^\d{1,4}$|^-\s*\d+\s*-$")
CONTEXT = re.compile(r"(?i)\bfirka\b|\btaluk\b|\btaluka\b")
HONOR = re.compile(r"(?i)^(thiru|tmt|selvi|mr|mrs|ms|miss|dr|selvan|thirumathi)\b\.?\s*")
VACANT = re.compile(r"(?i)^(vacant|nil|-+|—|_+|post vacant)$")
IC = re.compile(r"(?i)\(?\s*i\s*/\s*c\s*\)?|\bin-?charge\b|\bincharge\b")


def chunks(line):
    """[(start, end, text)] of one layout line: runs split at 2+ spaces, and phone numbers split out of their run."""
    out = []
    for m in re.finditer(r"\S+(?: \S+)*", line):
        s, t, last = m.start(), m.group(0), 0
        for pm in PHONE.finditer(t):
            pre = t[last:pm.start()].strip()
            if pre:
                out.append((s + last, s + pm.start(), pre))
            out.append((s + pm.start(), s + pm.end(), pm.group(0)))
            last = pm.end()
        rest = t[last:].strip()
        if rest:
            out.append((s + last + (len(t[last:]) - len(t[last:].lstrip())), s + len(t), rest))
    return out


def kind(text):
    t = text.lower()
    if re.search(r"(?i)^s\.?\s?no\.?$|^sl\.?\s?(no\.?)?$|^s\.?$|^no\.?$|^s\.?\s?no\.?\s", t) and len(t) < 12:
        return "sno"
    if "landline" in t:
        return "landline"
    if "secretary" in t:
        return "ps"
    if re.search(r"\bri\b|revenue inspector", t):
        return "ri"
    if re.search(r"village|designation|location|office", t) and not re.search(r"vao|officer'?s? name|name of the officer", t):
        return "area"
    if re.search(r"vao|name|officer|thiru|tmt", t):
        return "vao"
    if re.search(r"personal", t):
        return "phone2"
    if PHONE_W.search(t):
        return "phone"
    if "firka" in t:
        return "firka"
    return None


def header_cols(lines):
    """Columns [(start, end, kind, text)] from the header lines (overlapping chunks merge; text in line order). A line that is
    only a long title naming the VAO ("VILLAGE ADMINISTRATIVE OFFICER") is not a column."""
    spans = []
    for n, ln in enumerate(lines):
        cs = chunks(ln)
        if len(cs) == 1 and len(cs[0][2]) >= 20 and VAO_TITLE.search(cs[0][2]) and not PHONE_W.search(cs[0][2]):
            provenance.skip_line(ln, 'skip: len(cs) == 1 and len(cs[0][2]) >= 20 and VAO_TITLE.search(cs[0][2])...')
            continue
        for s, e, t in cs:
            spans.append([s, e, [(n, t)]])
    spans.sort(key=lambda x: (x[0], x[1]))
    cols = []
    for s, e, t in spans:
        hit = next((c for c in cols if s <= c[1] + 1 and e >= c[0] - 1), None)
        if hit:
            hit[0], hit[1] = min(hit[0], s), max(hit[1], e)
            hit[2] += t
        else:
            cols.append([s, e, list(t)])
    out = []
    for s, e, parts in cols:
        t = " ".join(x for _, x in sorted(parts, key=lambda y: y[0]))
        k = kind(t)
        if k == "phone" and any(c[2] == "phone" for c in out):
            k = "phone2"
        out.append((s, e, k, _esw.clean(t)))
    return out


def is_header(block):
    t = " ".join(block)
    return (bool(NAME_W.search(t) or AREA_W.search(t)) and bool(PHONE_W.search(t)) and bool(AREA_W.search(t) or VAO_TITLE.search(t))
            and not PHONE.search(t))


def headish(line):
    s = line.strip()
    if not s or PHONE.search(s) or re.match(r"^\d{1,3}[.)]?\s", s) or CONTEXT.search(s) or re.search(r"(?i)\blist\b|:", s):
        return False
    cs = chunks(line)
    return bool(cs) and all(len(c[2]) <= 40 for c in cs) and sum(bool(HEADISH.search(c[2])) for c in cs) >= max(1, len(cs) // 2)


def col_of(cols, s, e):
    best, bd = None, None
    for i, (cs, ce, k, _) in enumerate(cols):
        ov = min(e, ce) - max(s, cs)
        d = -ov if ov > 0 else (cs - e if e <= cs else s - ce)
        if bd is None or d < bd:
            best, bd = i, d
    return best


def name_of(s):
    s = _esw.clean(s)
    ic = bool(IC.search(s))
    s = _esw.clean(IC.sub(" ", s))
    s = HONOR.sub("", s).strip(" ,.-")
    return s, ic


def ctx_update(ctx, line):
    t = _esw.clean(re.sub(r"(?i)vao'?’?s?\b|village administrat\w*\s*officers?'?’?s?|list|name\s*:|:+", " ", line))
    if re.search(r"(?i)\bfirka\b", t):
        ctx["firka"] = _esw.clean(re.sub(r"(?i)\bfirka\b|name|:", " ", t)).strip(" -") or None
    elif re.search(r"(?i)\btaluka?\b", t):
        ctx["taluk"] = _esw.clean(re.sub(r"(?i)\btaluka?\b", " ", t)).strip(" -") or None
        ctx["firka"] = None


def rows_of(text):
    """[(row dict, src_pos)] from the layout text of a whole plan: row = {"cols": [(kind, text)...], "firka", "taluk", ...}."""
    pages = text.split("\f")
    lines = [(pn, ln_no, ln) for pn, pg in enumerate(pages, 1) for ln_no, ln in enumerate(pg.split("\n"), 1)]
    out, cols, active, ctx = [], None, False, {"firka": None, "taluk": None}
    seg, gap, recent = [], 0, []      # seg: lines of the current segment; recent: non-blank lines (titles before a header)
    i = 0

    def flush():
        if cols and seg:
            out.extend(group(seg, cols, dict(ctx)))
        seg.clear()

    while i < len(lines):
        pn, ln_no, ln = lines[i]
        s = ln.strip()
        if not s or NOISE.search(s):
            i += 1
            continue
        if headish(ln):
            j = i
            block = []
            while j < len(lines) and len(block) < 5 and headish(lines[j][2]):
                block.append(lines[j][2])
                j += 1
            if len(block) <= 4 and is_header(block):
                flush()
                title = " ".join(r for r in recent[-8:])
                hc = header_cols(block)
                vao = VAO_TITLE.search(" ".join(block)) or VAO_TITLE.search(title)
                if vao and any(k in ("vao", "phone", "area") for _, _, k, _ in hc) and any(k == "area" for _, _, k, _ in hc):
                    cols, active, gap = hc, True, 0
                else:
                    cols, active = None, False
                recent = []
                i = j
                continue
        if active and CONTEXT.search(s) and not PHONE.search(s) and not re.match(r"^\d{1,3}[.)]?\s", s) and len(s) < 80:
            flush()
            ctx_update(ctx, s)
            i += 1
            continue
        if active:
            cs = chunks(ln)
            serial = bool(cs) and SERIAL.match(cs[0][2]) and (cols[col_of(cols, cs[0][0], cs[0][1])][2] == "sno"
                                                              or cs[0][1] <= min(c[0] for c in cols if c[2] != "sno") + 1)
            if serial or PHONE.search(s) or VACANT.match(cs[-1][2]):
                gap = 0
            else:
                gap += 1
            if gap > 4 or any(len(c[2]) > 45 for c in cs):
                flush()
                active, cols, gap = False, None, 0
                ctx = {"firka": None, "taluk": None}
            else:
                seg.append((pn, ln_no, ln, cs, bool(serial)))
        else:
            if CONTEXT.search(s) and not PHONE.search(s) and len(s) < 80:
                ctx_update(ctx, s)
        recent.append(s)
        i += 1
    flush()
    return out


def group(seg, cols, ctx):
    """Rows of one segment (lines between titles / headers)."""
    cells = []
    for pn, ln_no, ln, cs, serial in seg:
        d = {}
        if serial and len(cs) == len(cols):
            for c, (s, e, t) in enumerate(cs):      # a full row: by order (pages after the header may sit at other x)
                d.setdefault(c, []).append(t)
        else:
            for s, e, t in cs:
                d.setdefault(col_of(cols, s, e), []).append(t)
        cells.append(d)
    idx = [n for n, x in enumerate(seg) if x[4]]
    if not idx:
        return []
    rows = {n: {k: list(v) for k, v in cells[n].items()} for n in idx}
    for n, x in enumerate(seg):
        if x[4]:
            continue
        prev = max((m for m in idx if m < n), default=None)
        nxt = min((m for m in idx if m > n), default=None)
        for c, ts in cells[n].items():
            if prev is None:
                tgt = nxt
            elif nxt is None:
                tgt = prev
            else:
                above = rows[prev].get(c)
                if above and re.search(r"[,&/-]$", above[-1]):
                    tgt = prev
                elif cells[nxt].get(c):
                    tgt = prev
                else:
                    tgt = nxt
            rows[tgt].setdefault(c, []).extend(ts)
    out = []
    for n in idx:
        pn, ln_no, ln, cs, _ = seg[n]
        r = {"cols": [(cols[c][2], cols[c][3], " ".join(ts)) for c, ts in sorted(rows[n].items())], **ctx}
        out.append((r, provenance.line_pos(pn, ln_no, ln.rstrip())))
    return out


def records(text, p, url, method=METHOD):
    recs, seen = [], set()
    dist = p.get("district") or ""
    ds = _esw.slug(dist) or "tn"
    for r, pos in rows_of(text):
        by = {}
        for k, h, t in r["cols"]:
            by.setdefault(k, []).append(t)
        area = _esw.clean(" ".join(by.get("area", [])))
        area = re.sub(r"\s*,\s*$", "", area)
        sno = _esw.clean(" ".join(by.get("sno", [])))
        raw = {h: t for k, h, t in r["cols"] if t}
        key = f"{ds}:{pos['page']}-{pos['line']}"
        while key in seen:
            key += "b"
        seen.add(key)

        def person(text_k, phone_ks):
            txt = " ".join(by.get(text_k, []))
            ph = [m.group(0) for m in PHONE.finditer(txt)]
            for k in phone_ks:
                ph += [m.group(0) for m in PHONE.finditer(" ".join(by.get(k, [])))]
            nm = _esw.clean(re.sub(r"(?i)\brevenue inspector\b|\bpanchayat secretary\b|\bv\.?a\.?o\b", " ", PHONE.sub(" ", txt)))
            if nm and nm.lower() == area.lower():
                nm = ""         # the village name in the officer column (a cell that slid left)
            vac = bool(VACANT.match(nm)) or bool(re.fullmatch(r"(?i)vacant.*", nm))
            if vac or re.fullmatch(r"[\W_\d]*", nm):
                nm = ""
            nm, ic = name_of(nm)
            return nm, list(dict.fromkeys(ph)), vac, ic
        common = dict(state="TN", district=dist, taluk=r.get("taluk"), firka=r.get("firka"), area=area, source=url, src_url=url,
                      src_pos=pos, table_row=raw, serial=sno or None, method=method, last_updated=p.get("last_updated"),
                      tls_unverified=p.get("tls_unverified"))
        if not area:
            provenance.skip_line(r, 'skip: not area')
            continue
        nm, ph, vac, ic = person("vao", ["phone", "phone2"]) if "vao" in by or "phone" in by else ("", [], False, False)
        if nm or ph or vac:
            recs.append(_esw.record(MODULE, key, dept="revenue", level="village", post=POST, post_regional=POST_TA, name=nm,
                                    phone=", ".join(ph), phone_cug=ph[0] if ph and "cug" in " ".join(h.lower() for _, h, _ in r["cols"]) else None,
                                    vacant=True if vac and not nm else None, in_charge=True if ic else None,
                                    office_id=f"{ds}:vao:{_esw.slug(area)}", **common))
        if "ri" in by:
            nm, ph, vac, ic = person("ri", [])
            if nm or ph:
                recs.append(_esw.record(MODULE, key + ":ri", dept="revenue", level="circle", post="Revenue Inspector",
                                        post_regional="வருவாய் ஆய்வாளர்", name=nm, phone=", ".join(ph),
                                        in_charge=True if ic else None, **common))
        if "ps" in by:
            nm, ph, vac, ic = person("ps", [])
            if nm or ph:
                recs.append(_esw.record(MODULE, key + ":ps", dept="rural_development", level="gram_panchayat",
                                        post="Village Panchayat Secretary", post_regional="ஊராட்சி செயலர்", name=nm,
                                        phone=", ".join(ph), in_charge=True if ic else None, **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    ds = _esw.slug(p.get("district") or "tn")
    files = [_esw.keep(MODULE, f"ddmp-{ds}", r.content, "pdf")]
    text, engine = _field.pdf_text_engine(r.content)
    recs = records(text, p, p["url"], method=METHOD.replace("pdftotext -layout", engine))
    return recs, files, "" if recs else "no VAO list found in the plan"


def items(get=None):
    return _field.seed(MODULE)
