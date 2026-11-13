"""Chhattisgarh: elected members of the district panchayats (जिला पंचायत सदस्य) and janpad panchayats (जनपद पंचायत सदस्य) of the
three-tier panchayat general election 2025 (polls February 2025), from the State Election Commission page
cgsec.gov.in/hin_2025chunavpanchayat.html ("निर्वाचित ... की जानकारी"):
- Notification2025/election/त्रिस्तरीय पंचायत आम निर्वाचन 2025- निर्वाचित जिला पंचायत सदस्यों की जानकारी.pdf (28 pages, 433 rows)
- Notification2025/election/त्रिस्तरीय पंचायत आम निर्वाचन 2025- निर्वाचित जनपद पंचायत सदस्यों की जानकारी.pdf (86 pages)
Both are Google Sheets prints (Skia/PDF) WITH a text layer. Columns: division | district no | district | [serial (ZP file)] |
janpad panchayat | constituency no | elected candidate | husband/father | address. The sarpanch and panch files on the same page
give only counts per district (no names): not read. The page does not list the ZP / JP chairpersons (adhyaksh).
Measured 2026-11-13 from Mumbai; the site answered dev-vps-3 (the archive copies of cgsec.gov.in were all fetched through
Indian proxies: abroad not checked).

Text: poppler's pdftotext -bbox (word boxes). pypdf loses glyphs of this font (U+0000 for conjuncts), so the reader needs
pdftotext (route direct: the civic workers on dev-vps-3 have poppler). Columns come from the header words of each page
(संभाग, क्रमां(क), जिला, क्र., जनपद, क्षेत्र, अभ्यर्थी, पिता, पता); a row is anchored on the running serial number (one line); every other word
goes to the row whose anchor is nearest in height (multi-line cells are centred on their row). pdftotext splits a syllable
with a lower or upper vowel sign from the rest of its word ("कु मार", "रे वाशंकर"): a lone one-syllable fragment is joined to
the next word (name); the raw cell text is kept in cells.
One queue item = one file (two items). Record ids pri:pri_cg:2025:zp:<serial> and pri:pri_cg:2025:ps:<serial> (the
files' running serial numbers: ZP 1-433, JP 1-2973).
"""
import json
import re
import subprocess
from html import unescape
from pathlib import Path

from dforms import _pri
import provenance

METHOD = "pdf text (pdftotext -bbox word boxes; columns from the header words, rows anchored on the running serial number)"
MODULE = "pri_cg"
BASE = "https://cgsec.gov.in/Notification2025/election/"
PAGE = "https://cgsec.gov.in/hin_2025chunavpanchayat.html"
FILES = {
    "zp": "त्रिस्तरीय पंचायत आम निर्वाचन 2025- निर्वाचित जिला पंचायत सदस्यों की जानकारी.pdf",
    "ps": "त्रिस्तरीय पंचायत आम निर्वाचन 2025- निर्वाचित जनपद पंचायत सदस्यों की जानकारी.pdf",
}
ELECTION = "Chhattisgarh Three-tier Panchayat General Election 2025"
POST = {"zp": ("Member, Zila Panchayat", "सदस्य, जिला पंचायत"), "ps": ("Member, Janpad Panchayat", "सदस्य, जनपद पंचायत")}
HEAD = [("div", r"^संभाग$"), ("dno", r"^क्रमां"), ("dist", r"^जिला$"), ("serial", r"^क्र\.$"), ("jp", r"^जनपद"),
        ("const", r"^क्षेत्र$"), ("name", r"^अभ्यर्थी$"), ("father", r"पिता$"), ("addr", r"^पता$")]
FRAG = re.compile(r"^[क-हक़-य़][ुूृेै]$")     # one consonant + ु ू ृ े ै
# district / janpad as the SEC writes them -> LGD local_body_code (made offline from the two files: sound match of the Hindi name
# to the LGD English name within the district, two districts set by hand (Korea, Raipur); 170 of 199 district|janpad pairs)
LGD = json.loads((Path(__file__).with_name("pri_cg_lgd.json")).read_text())
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')


def items(get=None):
    from urllib.parse import quote
    return [{"key": f"{MODULE}:2025:{lvl}", "payload": {"reader": MODULE, "url": BASE + quote(f), "level": lvl, "state": "CG",
             "page": PAGE, "india_only": True, "route": "direct"}} for lvl, f in FILES.items()]


def words(content):
    """[[(x0, y0, x1, y1, text), ...] per page] from pdftotext -bbox; None when pdftotext is missing."""
    try:
        out = subprocess.run(["pdftotext", "-bbox", "-", "-"], input=content, capture_output=True, timeout=300).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    pages = []
    for pg in out.decode("utf-8", "replace").split("<page ")[1:]:
        pages.append([(float(a), float(b), float(c), float(d), unescape(t)) for a, b, c, d, t in WORD.findall(pg)])
    return pages


def join(ws):
    """Words of one cell (sorted by line, then x) -> (text with split syllables joined, raw text)."""
    lines = []
    for w in sorted(ws, key=lambda w: (w[1], w[0])):
        if lines and abs(lines[-1][0] - w[1]) < 4:
            lines[-1][1].append(w)
        else:
            lines.append([w[1], [w]])
    toks = [w[4] for _, ln in lines for w in sorted(ln, key=lambda w: w[0])]
    raw = " ".join(toks)
    out = []
    for t in toks:
        if out and FRAG.match(out[-1]) and re.match(r"[ऀ-ॿ]", t):
            out[-1] += t
        else:
            out.append(t)
    return _pri.clean(" ".join(out)), _pri.clean(raw)


def phrases(ws, gap=6.0):
    """Words of one line closer than gap points -> one phrase (a cell line); a phrase goes to a column as a whole, so a long
    district name that runs over the column border stays in its cell."""
    out = []
    for w in sorted(ws, key=lambda w: (round((w[1] + w[3]) / 2), w[0])):
        last = out[-1][-1] if out else None
        if last and abs((last[1] + last[3]) / 2 - (w[1] + w[3]) / 2) < 2 and 0 <= w[0] - last[2] <= gap:
            out[-1].append(w)
        else:
            out.append([w])
    return out


def page_rows(ws, level):
    """[(cells dict role -> (text, raw), anchor y)] for one page, or [] when the page has no header."""
    top = [w for w in ws if w[4] == "अभ्यर्थी"]
    if not top:
        return []
    a = min(top, key=lambda w: w[1])
    band = [w for w in ws if a[1] - 10 <= w[1] <= a[3] + 2]       # the header row (words of 1-2 lines around "अभ्यर्थी")
    cols = {}
    for role, rx in HEAD:
        hit = sorted((w for w in band if re.search(rx, w[4])), key=lambda w: w[0])
        if hit:
            cols[role] = (hit[0][0] + hit[0][2]) / 2
    if not {"const", "name", "dist"} <= set(cols):
        return []
    order = sorted(cols.items(), key=lambda kv: kv[1])
    head_y = max(w[3] for w in band)
    data = [w for w in ws if w[1] > head_y + 1 and not w[4].startswith("टीप")]
    # column borders: the x gap free of any data word between two header centres, nearest the midpoint; else the midpoint
    edges = sorted((w[0], w[2]) for w in data)
    free, reach = [], -1.0
    for x0, x1 in edges:
        if reach >= 0 and x0 > reach + 0.5:
            free.append((reach, x0))
        reach = max(reach, x1)
    cuts = []
    for (r1, c1), (r2, c2) in zip(order, order[1:]):
        mid = (c1 + c2) / 2
        gaps = [(a + b) / 2 for a, b in free if c1 < (a + b) / 2 < c2]
        cuts.append(min(gaps, key=lambda g: abs(g - mid)) if gaps else mid)
    bounds = [(r, cuts[i - 1] if i else -1, cuts[i] if i < len(cuts) else 10 ** 6) for i, (r, _) in enumerate(order)]

    def col(w):
        xc = (w[0] + w[2]) / 2
        return next(r for r, lo, hi in bounds if lo <= xc < hi)
    foot = min([w[1] for w in ws if w[4].startswith("टीप")] or [10 ** 6])
    body = [w for w in ws if head_y - 1 < w[1] < foot - 1]
    # the column number row of the JP file (1 2 3 ... 8) sits right under the header: digits in every column
    key = "serial" if "serial" in cols else "dno"       # the running serial: one line, centred on its row
    anchors = sorted({round((w[1] + w[3]) / 2, 1) for w in body if col(w) == key and re.fullmatch(r"\d+", _pri.digits(w[4]))})
    first = [y for y in anchors if sum(1 for w in body if abs((w[1] + w[3]) / 2 - y) < 2 and w[4].isdigit()) >= 6]
    anchors = [y for y in anchors if y not in first]
    if not anchors:
        return []
    rows = {y: {} for y in anchors}
    for ph in phrases(body):
        yc = (ph[0][1] + ph[0][3]) / 2
        if any(abs(yc - y) < 2 for y in first):
            provenance.skipped('skip: any(abs(yc - y) < 2 for y in first)')
            continue
        y = min(anchors, key=lambda a: abs(a - yc))
        span = (ph[0][0], 0, ph[-1][2], 0, "")
        rows[y].setdefault(col(span), []).extend(ph)
    return [({r: join(v) for r, v in cells.items()}, y) for y, cells in rows.items()]


def records(content, url, level, source_page=None):
    pages = words(content)
    if pages is None:
        return None
    post, post_reg = POST[level]
    out, seen = [], set()
    for pno, ws in enumerate(pages, 1):
        for rno, (c, y) in enumerate(page_rows(ws, level), 1):
            t = {r: v[0] for r, v in c.items()}
            m = re.match(r"(\d+)", _pri.digits(t.get("const", "")))
            const = int(m.group(1)) if m else None
            dno = _pri.int_or_none(t.get("dno"))
            if const is None or not t.get("name"):
                provenance.skipped('skip: const is None or not t.get("name")')
                continue
            serial = _pri.int_or_none(t.get("serial")) if level == "zp" else dno      # the JP file's क्रमांक is the running serial
            key = f"2025:{level}:{serial}"
            if key in seen:
                key += f":p{pno}r{rno}"
            seen.add(key)
            dist_l = LGD["districts"].get(t.get("dist", ""), {})
            blk_l = LGD["blocks"].get(f"{t.get('dist', '')}|{t.get('jp', '')}", {})
            lgd = dist_l.get("lgd") if level == "zp" else blk_l.get("lgd")
            name = re.sub(r"^(श्रीमती|श्रीमति|श्री|सुश्री|कु\.)\s*", "", t["name"])
            out.append(_pri.record(
                MODULE, key, state="CG", level=level, role="member", post=post, post_regional=post_reg,
                name=t["name"], name_plain=name if name != t["name"] else "", father_name=t.get("father"), address=t.get("addr"),
                division=t.get("div"), district=t.get("dist"), district_no=dno if level == "zp" else None, block=t.get("jp"),
                body_name=t.get("dist") if level == "zp" else t.get("jp"), constituency_no=const, ward_no=str(const) if const is not None else "",
                constituency=t.get("const") if t.get("const") != str(const) else "",
                serial=serial, lgd_code=lgd, lgd_match="name" if lgd else "", district_lgd=dist_l.get("lgd"),
                block_lgd=blk_l.get("lgd"), election=ELECTION, election_year=2025, status="elected",
                source=url, src_url=url, list_page=source_page,
                src_pos={"page": pno, "row": rno, "y": y}, cells={r: v[1] for r, v in c.items()}))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    recs = records(r.content, p["url"], p["level"], p.get("page"))
    if recs is None:
        return [], [], "needs pdftotext (poppler): run on the direct route"
    return recs, [], "" if recs else "no rows"
