"""Haryana: members of the panchayats elected in the PRI General Elections 2022 (polls November 2022), from the State Election
Commission notifications in the Haryana Government Gazette (extraordinary) of 30 November 2022. The SEC index PDF of 02.12.2022
("Result sheet for Elected Members of Zila Parishads and Members Panchayat Samitis and Elected Sarpanches and Panches",
https://cdnbbsr.s3waas.gov.in/s31c6a0198177bfcc9bd93f6aab94aad3c/uploads/2022/12/2022121338.pdf, linked from
https://secharyana.gov.in/orders-notifications-related-to-panchayat-elections-2021/) links 187 PDFs: per district "Members ZP"
(22) and "Members PS" (22), per block "Sarpanch and Panches" (143). seeds/build_pri_hr.py reads the links (seeds/dept_pri_hr.json).
The files are on the S3WaaS CDN (answers abroad: route abroad, GitHub runners). No captcha.

The PDFs are Word prints with a text layer, mostly in the legacy font Kruti Dev 010 (Latin letters: "ljiap" = "सरपंच"); a few
blocks are in English. One queue item = one PDF (block files 10-50 pages). Steps:
  1. text per page with pypdf layout mode (the same on any machine; columns stay apart);
  2. columns per page, learned from the row lines: block files: a row line holds the post ("ljiap"/"iap", "Sarpanch"/"Panch");
     the chunks (runs split by 2+ spaces) before it are [serial, GP,] ward ("&" = - for the Sarpanch), name, father/husband,
     after it the reservation. ZP / PS files: a row line starts with the ward number; [serial, samiti,] ward, name,
     father/husband, reservation, party. The start column of each part is the median over the page's well-formed rows;
  3. every chunk of every line goes to the nearest column start (a chunk that runs over the next column start is cut at the
     last space before it), so wrapped names and reservations (next lines) join their row;
  4. Kruti Dev cells are mapped to Unicode (dforms/_ward_kd.convert); the raw cell is kept in cells_raw.
"*" before a name = elected unopposed. Records (dforms/_pri.py, type pri_member): block files: level gp, Sarpanch (head) and Panch
(member, ward_no); ZP files: level zp, member (ward_no = ZP ward, party); PS files: level ps, member (samiti, ward_no, party).
Some PS files have a broken text layer (every glyph doubled: "Harryanaa Goovernnmentt"): no rows; the item ends "garbled text
layer: OCR needed" and the PDF is kept in the bucket.
Ids: pri:pri_hr:<district slug>:<block slug or zp / ps-<samiti slug>>:<GP slug>:sarpanch | ...:<GP slug>:w<ward> | zp:w<ward>.
"""
import gzip
import io
import re
import statistics

import provenance
from dforms import _pri, _ward_kd as kd

METHOD = "pdf text (pypdf layout) + Kruti Dev map; columns learned per page from the row lines"

MODULE = "pri_hr"
ELECTION = "Haryana PRI General Elections 2022"
POST_GP = {"ljiap": "head", "iap": "member", "sarpanch": "head", "panch": "member"}
CHUNK = re.compile(r"\S+(?: \S+)*")
GARBLED = re.compile(r"Harryanaa|Goovern|EEXTRA")
PROSE = re.compile(r"(?i)notif|hereby|following persons|election commission|vf/klwpuk|fuokZpu|Panchayati Raj Act|"
                   r"^\s*(Sr\.|dz0|la0|Ø0|okMZ ua)")
WARD = re.compile(r"^\d{1,3}\.?$")


HONORIFIC = re.compile(r"^(Sh\.?|Shri|Smt\.?|Jh|Jherh|Dr\.?)$")


def chunks(line):
    """[(start column, text)] of the runs split by 2+ spaces; a lone honorific ("Sh.       Narender") joins the next run."""
    out = []
    for m in CHUNK.finditer(line):
        if out and HONORIFIC.match(out[-1][1]):
            out[-1] = (out[-1][0], out[-1][1] + " " + m.group(0))
        else:
            out.append((m.start(), m.group(0)))
    return out


def pages_text(content):
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception:
        return []
    out = []
    for pg in reader.pages:
        try:
            out.append(pg.extract_text(extraction_mode="layout") or "")
        except Exception:
            out.append(pg.extract_text() or "")
    return out


def _post_index(ch):
    """Index of the post chunk in a block-file line (the chunk equal to a post word), else None. A post glued to the father's
    name by one space ("Jh lq[knso jkt iap") is split off first (the list is changed in place)."""
    for i, (s, t) in enumerate(ch):
        if t.lower() in POST_GP:
            return i
        m = re.match(r"^(.*\S) (ljiap|iap|Sarpanch|Panch)$", t)
        if m and i >= 2:
            ch[i:i + 1] = [(s, m.group(1)), (s + len(m.group(1)) + 1, m.group(2))]
            return i + 1
    return None


def _learn(rows, names):
    """{column name: start} from well-formed rows: rows = [[(start, text) ...] in column order]."""
    cols = {}
    for k, name in enumerate(names):
        xs = [r[k][0] for r in rows if len(r) > k]
        if xs:
            cols[name] = statistics.median(xs)
    return cols


def _assign(ch, cols):
    """{column: [texts]}: each chunk to the column whose start is nearest; a chunk running past the next column start + 1 is cut."""
    order = sorted(cols.items(), key=lambda kv: kv[1])
    out = {}
    for s, t in ch:
        pieces = [(s, t)]
        while pieces:
            ps, pt = pieces.pop(0)
            i = min(range(len(order)), key=lambda j: abs(order[j][1] - ps))
            nxt = order[i + 1][1] if i + 1 < len(order) else None
            if nxt is not None and ps + len(pt) > nxt + 1 and ps < nxt:
                cut = pt.rfind(" ", 0, int(nxt - ps) + 1)
                if cut > 0:
                    pieces.insert(0, (ps + cut + 1, pt[cut + 1:]))
                    pt = pt[:cut]
            out.setdefault(order[i][0], []).append(pt)
    return out


def _body_lines(text):
    """(line no, line) of the table part of one page: skips the gazette header, the notice text and the signature."""
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip() or re.search(r"GAZ\.|Gazette|EXTRAORDINARY|Published by|Govt\. of|^\s*\(\d+\)\s*$|^\s*\d{4,5}\s*$", line):
            continue
        out.append((n, line))
    return out


def parse(pages, p):
    """[row] from the page texts of one file; row = {"cells": {column: text}, "gp": GP name (block files), "page", "line",
    "line_text"}."""
    kind = p.get("kind", "gp")
    names = ["ward", "name", "father", "post", "reservation"] if kind == "gp" else ["ward", "name", "father", "reservation", "party"]
    rows, cur, gp = [], None, None
    for pi, text in enumerate(pages, 1):
        lines = _body_lines(text)
        parsed, good, gp_x = [], [], []
        for n, line in lines:
            ch = chunks(line)
            if kind == "gp":
                k = _post_index(ch)
                if k is not None and k >= 3 and len(ch) == k + 2 and k in (3, 5):     # clean rows: ward name father post res
                    pre = ch[:k]
                    good.append(pre[-3:] + ch[k:k + 2])
                    if len(pre) == 5:
                        gp_x.append(pre[1][0])
                parsed.append((n, line, ch, k))
            else:
                k = 0 if ch and WARD.match(ch[0][1]) else None
                if k == 0 and len(ch) == 5:
                    good.append(ch)
                parsed.append((n, line, ch, k))
        cols = _learn(good, names)
        if kind == "gp" and gp_x:
            cols["gp"] = statistics.median(gp_x)
        if len(cols) < 4:
            continue
        cont_cols = {c: x for c, x in cols.items() if c not in ("ward", "post")}
        for n, line, ch, k in parsed:
            if not ch:
                continue
            if max(len(x) for _, x in ch) > 45 or PROSE.search(line):    # notice text between the lists: no row continues
                cur = None
                continue
            if k is not None:
                if kind == "gp":
                    pre, post = ch[:k], ch[k:]
                    wi = next((i for i in range(len(pre) - 1, -1, -1) if re.match(r"^(\d{1,3}|&|-+|–)$", pre[i][1])
                               and abs(pre[i][0] - cols.get("ward", pre[i][0])) <= 6), None)
                    if wi is None:                      # a header line ("Name of Post"): not a row
                        cur = None
                        continue
                    lead = pre[:wi]
                    if lead:                            # [serial] GP before the ward: a new GP starts
                        sno = lead[0][1].rstrip(".") if len(lead) >= 2 else ""
                        gname = " ".join(x for _, x in (lead[1:] if sno.isdigit() else lead))
                        gp = {"text": gname, "serial": sno if sno.isdigit() else ""}
                    cells = {c: " ".join(v) for c, v in _assign(pre[wi + 1:], {c: cols[c] for c in ("name", "father") if c in cols}).items()}
                    cells["ward"] = pre[wi][1] if pre else ""
                    cells["post"] = post[0][1]
                    cells["reservation"] = " ".join(x for _, x in post[1:])
                else:
                    wi = next((i for i, (s, x) in enumerate(ch) if WARD.match(x) and abs(s - cols.get("ward", s)) <= 6), 0)
                    cells = {c: " ".join(v) for c, v in _assign(ch[wi + 1:], {c: cols[c] for c in names[1:] if c in cols}).items()}
                    cells["ward"] = ch[wi][1]
                    if wi:                              # [serial, samiti,] before the ward (PS files)
                        cells["samiti"] = " ".join(x for _, x in ch[:wi] if not WARD.match(x))
                cur = {"cells": cells, "gp": gp, "page": pi, "line": n, "line_text": line}
                rows.append(cur)
                continue
            if cur is None or re.search(r"(?i)unopposed|fufoZjks/k|^\s*\*\s*-|Commissioner|vk;qDr|DHANPAT|H\.G\.P|C\.S\.—|^\s*/k", line):
                continue
            for c, v in _assign(ch, cont_cols).items():
                if c == "gp":
                    if cur.get("gp") is not None:
                        cur["gp"]["text"] += " " + " ".join(v)
                else:
                    cur["cells"][c] = (cur["cells"].get(c, "") + " " + " ".join(v)).strip()
    return rows


def uni(s, is_kd):
    s = _pri.clean(s)
    if is_kd and s:       # the Word prints use curly quotes for the Kruti Dev keys ' (श) and " (ष)
        s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201d", '"').replace("\u201c", '"')
        return _pri.clean(kd.convert(s))
    return s


def build(rows, p, pages, src_url):
    kind = p.get("kind", "gp")
    dsl = _pri.slug(p["district"])
    kdp = {i: kd.is_krutidev(t) for i, t in enumerate(pages, 1)}
    recs, seen = [], {}
    for r in rows:
        c, is_kd = r["cells"], kdp.get(r["page"], False)
        name_raw = c.get("name", "")
        unopposed = name_raw.startswith("*")
        name = uni(name_raw.lstrip("* "), is_kd)
        if not name:
            continue
        ward_raw = (c.get("ward") or "").strip().rstrip(".")
        ward = ward_raw if ward_raw.isdigit() else ""
        common = dict(state="HR", district=p["district"], name=name, father_name=uni(c.get("father", ""), is_kd),
                      seat_category=uni(c.get("reservation", ""), is_kd), unopposed=unopposed or None, status="won",
                      election=ELECTION, election_year=2022, result_date="2022-11-30", source=src_url, src_url=src_url,
                      cells={k: uni(v.lstrip("* ") if k == "name" else v, is_kd) for k, v in c.items()}, cells_raw=c, kruti_dev=is_kd or None,
                      src_pos=provenance.line_pos(r["page"], r["line"], r["line_text"]))
        if kind == "gp":
            post = (c.get("post") or "").strip().lower()
            role = POST_GP.get(post) or ("head" if not ward else "member")
            gp = uni((r.get("gp") or {}).get("text", ""), is_kd)
            if not gp:
                continue
            g = r.get("gp") or {}
            base = f"{dsl}:{_pri.slug(p['block'])}:g{g.get('serial') or _pri.slug(gp) or 'x'}"     # GP serial of the list
            key = f"{base}:sarpanch" if role == "head" else f"{base}:w{ward or 'x'}"
            rec = dict(level="gp", role=role, block=p["block"], body_name=gp, gp_serial=g.get("serial"),
                       post="Sarpanch" if role == "head" else "Panch", post_regional="सरपंच" if role == "head" else "पंच",
                       ward_no=ward if role == "member" else None)
        else:
            if not ward:
                continue
            body = p["district"] if kind == "zp" else uni(c.get("samiti", ""), is_kd) or p["district"]
            key = f"{dsl}:{kind}:w{ward}"
            rec = dict(level=kind, role="member", body_name=body, ward_no=ward, party=uni(c.get("party", ""), is_kd),
                       post="Member, Zila Parishad" if kind == "zp" else "Member, Panchayat Samiti",
                       post_regional="सदस्य, जिला परिषद" if kind == "zp" else "सदस्य, पंचायत समिति")
        if not is_kd:            # the gazette prints each list in Hindi and again in English: both kept, the English rows marked
            key += ":en"
            rec["lang"] = "en"
        else:
            rec["lang"] = "hi"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key += f"-{seen[key]}"
        recs.append(_pri.record(MODULE, key, **common, **rec))
    return recs


def garbled(pages):
    """True when the text layer doubles glyphs ("Harryanaa Goovernnmentt Gazzette"): the rows cannot be read from it."""
    return bool(pages) and bool(GARBLED.search(pages[0][:600]))


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    name = re.sub(r"[^A-Za-z0-9_.-]", "", p["url"].rsplit("/", 1)[-1])
    files = [(f"pri/HR/{_pri.slug(p['district'])}-{p['kind']}-{_pri.slug(p.get('block', ''))}-{name}.gz",
              gzip.compress(r.content), "application/gzip")]
    pages = pages_text(r.content)
    if not pages:
        return [], files, "not a readable PDF"
    if garbled(pages):
        return [], files, "garbled text layer (glyphs doubled): OCR needed"
    recs = build(parse(pages, p), p, pages, p["url"])
    return recs, files, "" if recs else "no rows"
