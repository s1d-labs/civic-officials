"""Maharashtra municipal corporation results, January 2026, from the divisional e-Gazette notices that have a text layer and
no drawn table (Government e-Gazette, egazzete.mahaonline.gov.in, "Part -1 A" extraordinary, 19 Jan 2026).

The Nagpur and Amravati divisional supplements are set in Adobe InDesign with a Unicode text layer: no OCR is needed. The
layer repeats some vowel signs and the reph consonant ("महाारााष्ट्र", "साार्ववत्रि�क"); fix() sets them back
("महाराष्ट्र", "सार्वत्रिक"). The tables have no ruled cells, so the columns come from the column-number line under the
table head ("(१) (२) (३) (४) (५)", repeated on every page): each word goes to the column whose number is nearest. A member
row starts on the line that has a seat letter (अ ब क ड इ, alone or as "१-अ"); the lines below it (address and name wraps)
belong to it until the next seat line. Each notice gives its column order in the payload ("cols"), e.g. Nagpur
["ward", "seat", "name", "address", "party"], Chandrapur ["serial", "name", "ward", "seat", "reservation"].
Checked 2026-11-12 on the saved notices: Nagpur A-2530 (9 pages, 151 members), Chandrapur A-2529 (6 pages), Akola A-2531
(5 pages). The search and the "View" postback are the ones of cforms/mh.py (India only).
One queue item = one notice (payload as cforms/mh.py plus "cols", "lgd_code"). Record id councillor:MH:<slug>:<ward>-<seat>.
"""
import hashlib
import os
import re
import subprocess
import tempfile

from cforms import gj, mh

METHOD = 'pdf text layer (gazette, Unicode Marathi)'     # source trail (provenance.py): how this reader reads its sources

DIGITS = mh.DIGITS
MARK = re.compile(r"([ँ-ःा-ौॢॣ])\1+")
REPH = re.compile(r"र्([क-ह])\1")
COLNO = re.compile(r"^\(([0-9०-९]+)\)$")
SEAT = re.compile(r"(?:^|[-\s])([अबकडइ])$")
STOP = re.compile(r"आयुक्त|ON BEHALF|एक-अ-[0-9०-९]|दिनांक|नागपूर\s*:|अमरावती\s*:|अकोला\s*:|चंद्रपूर\s*:")


def fix(t):
    """The InDesign text layer's doubled vowel signs and reph consonants, and its stray U+FFFD, set right."""
    t = gj.norm((t or "").replace("�", ""))
    t = MARK.sub(r"\1", t)
    return REPH.sub(r"र्\1", t)


def lines_of(ws, tol=5):
    """Words [(x0, y0, x1, y1, text)] -> lines [(y, [(x0, x1, text)])], top to bottom."""
    out = []
    for w in sorted(ws, key=lambda w: (w[1], w[0])):
        if out and abs(w[1] - out[-1][0]) <= tol:
            out[-1][1].append((w[0], w[2], fix(w[4])))
        else:
            out.append([w[1], [(w[0], w[2], fix(w[4]))]])
    return [(y, sorted(ws)) for y, ws in out]


def column_marks(lines, ncols):
    """(y, [x centre of column 1..n]) of the "(१) (२) ..." line, or None."""
    for y, ws in lines:
        marks = [((a + b) / 2, int(COLNO.match(t).group(1).translate(DIGITS))) for a, b, t in ws if COLNO.match(t)]
        if len(marks) >= ncols and [n for _, n in marks[:ncols]] == list(range(1, ncols + 1)):
            return y, [x for x, _ in marks[:ncols]]
    return None


def borders(lines, xs):
    """Column borders: between two column numbers, the middle of the widest x range that the fewest words cover (the
    white gap between the columns). Column numbers sit over the middle of their column, but the columns differ in width
    and their text is left aligned, so the plain midpoint would cut names."""
    width = int(max([b for _, ws in lines for _, b, _ in ws] + [xs[-1]])) + 2
    cover = [0] * width
    for _, ws in lines:
        for a, b, _ in ws:
            for x in range(max(0, int(a)), min(width, int(b) + 1)):
                cover[x] += 1
    out = []
    for i in range(len(xs) - 1):
        lo, hi = int(xs[i]) + 1, int(xs[i + 1])
        if hi <= lo:
            out.append((xs[i] + xs[i + 1]) / 2)
            continue
        m = min(cover[lo:hi])
        best, run, start = (0, (lo + hi) / 2), 0, lo
        for x in range(lo, hi + 1):
            if x < hi and cover[x] == m:
                if run == 0:
                    start = x
                run += 1
            else:
                if run > best[0]:
                    best = (run, start + run / 2)
                run = 0
        out.append(best[1])
    return out


def split(ws, bs):
    """Words of one line -> text per column (by the borders)."""
    cells = [[] for _ in range(len(bs) + 1)]
    for a, b, t in ws:
        x = (a + b) / 2
        cells[sum(1 for v in bs if x > v)].append(t)
    return [" ".join(c) for c in cells]


def seat_of(t):
    m = SEAT.search(gj.norm(t))
    return m.group(1) if m else ""


def rows_of(pages, cols):
    """pages: [(page no, words)] -> member rows {"page", role: text}; columns carry from page to page."""
    xs, rows, cur = None, [], None
    si = cols.index("seat")
    for pg, ws in pages:
        lines = lines_of(ws)
        mk = column_marks(lines, len(cols))
        if mk:
            xs, top = mk[1], mk[0]
        elif xs is None:
            continue
        else:
            top = -1
        body = [(y, lw) for y, lw in lines if y > top + 2]
        stop = next((y for y, lw in body if STOP.search(" ".join(t for _, _, t in lw))), None)
        body = [(y, lw) for y, lw in body if stop is None or y < stop]
        bs = borders(body, xs)
        last_y = None
        for y, lw in body:
            cells = split(lw, bs)
            if seat_of(cells[si]):
                cur = {"page": pg, "_seat": seat_of(cells[si]), **{c: v for c, v in zip(cols, cells)}}
                rows.append(cur)
                last_y = y
            elif cur is not None and cur["page"] == pg and last_y is not None and y - last_y < 45:
                for c, v in zip(cols, cells):
                    if v:
                        cur[c] = (cur[c] + " " + v).strip()
                last_y = y
    return rows


def records(rows, p):
    out, ward = [], ""
    for r in rows:
        seat = r.get("_seat") or seat_of(r["seat"])
        w = mh.num(r.get("ward", "")) or mh.num(r["seat"])
        ward = w or ward
        name = gj.norm(r.get("name", ""))
        if not name or not ward:
            continue
        ward_name = re.sub(r"^[\s0-9०-९.\-–]+", "", gj.norm(r.get("ward", ""))).strip() if "ward" in r else ""
        party_local = gj.norm(r.get("party", ""))
        resv = gj.norm(r.get("reservation", ""))
        d = {"type": "councillor", "state": "MH", "body": p.get("body_local") or p.get("body", ""),
             "body_local": p.get("body_local", ""), "body_en": p.get("body", ""), "body_type": "Municipal Corporation",
             "district": p.get("district", ""), "lgd_code": p.get("lgd_code", ""), "ward_no": ward, "ward_name": ward_name,
             "seat": seat, "name": name, "address": gj.norm(r.get("address", "")), "party_local": party_local,
             "party": mh.party_of(party_local) or party_local, "reservation_local": resv,
             "reservation": mh.reservation(resv) if resv else "", "serial": mh.num(r.get("serial", "")),
             "election": "Maharashtra 2026", "url": p["url"], "gazette": p.get("match", ""), "page": r["page"],
             "read": "text layer"}
        out.append((f"councillor:MH:{p.get('slug', 'x')}:{ward}-{seat}", {k: v for k, v in d.items() if v not in ("", None)}))
    return out


def parse(pdf, p):
    n = int(p.get("last", 0)) or int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True,
                                                                                    text=True).stdout).group(1))
    pages = [(pg, gj.words(pdf, pg)) for pg in range(int(p.get("first", 1)), n + 1)]
    return records(rows_of(pages, p["cols"]), p)


def fetch(p, get):
    content, why = mh.get_pdf(p, get)
    if content is None:
        return [], [], why
    key = hashlib.sha1((p["gazette_date"] + p["match"]).encode()).hexdigest()[:12]
    files = [(f"councillors/MH/{key}.pdf", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, p)
    return recs, files, "" if recs else "no members read"
