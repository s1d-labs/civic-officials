"""Maharashtra nagar panchayats, general election 2021-22 (polls 21 Dec 2021 and 18 Jan 2022, counting 19 Jan 2022): the
collectors' notices of the elected councillors, section 19(1) of the Maharashtra Municipal Councils, Nagar Panchayats and
Industrial Townships Act, 1965, in the divisional "Part -1 A" supplements of the Government e-Gazette
(egazzete.mahaonline.gov.in, 21 Jan - 1 Mar 2022).

The Marathi part of most notices is set in legacy fonts (DV-TTYogesh, DVB-TTYogesh, DV-TTSurekh: the text layer is Latin-1
glyph codes, not Unicode). But the Nagpur, Amravati, Pune, Nashik and Aurangabad notices repeat the order in English
("BY COLLECTOR / ORDER ... SCHEDULE"), with a plain text layer. This reader reads that English part: no OCR.
- An English block starts at a line "ORDER" (or "NOTIFICATION"). Its body is the payload body whose English name stands
  next to "Nagar Panchayat" / "Nagarpanchayat" / "Municipal Council" in the block's text (payload "bodies":
  [{"lgd_code", "en": [names], "local"}]), else the only body named in the block.
- The schedule head (the line with "Name" and "Ward" / "Prabhag") gives the columns: each head phrase is a column, its role
  from its words (Sr / Name / Ward, Prabhag / Reservation, Remarks, Category / Address / Party). The column borders are the
  white gaps between the head phrases (cforms/mh_gztext.borders) over the block's lines.
- A row starts on a line whose serial cell is a number and whose name cell has Latin letters; the lines below it (name,
  address and reservation wraps) belong to it until the next row, a signature or a page head.
Notices without an English part (Konkan scans, Gondia) are not read here (route: OCR on the runners, cforms/mh_scan.py).
One queue item = one notice (payload as cforms/mh.py: gazette_date, division, section, gazette_type, match, "nth" when the
day lists the same text more than once, "bodies"). The first item that fetches a notice keeps the PDF in the bucket
(councillors/MH/<key>.pdf); payload "stored" names that copy, then the item makes no request to the gazette.
Payload "save_only": fetch and keep the PDF, read nothing (notices whose Marathi-only text needs OCR on the runners).
Record id councillor:MH:<LGD code>:<ward>.
"""
import hashlib
import os
import re
import tempfile

from cforms import gj, mh, mh_gztext
import provenance

METHOD = "pdf text layer (pdftotext -bbox words): the English ORDER of each notice; columns from the schedule head"
ELECTION = "Maharashtra Nagar Panchayat General Election 2021-22"
START = re.compile(r"^(ORDER|Order|NOTIFICATION|Notification)\.?$")
LEGACY = re.compile(r"[¡-ÿŒœŠšŸŽžƒˆ˜–-›™]{2}")
STOP = re.compile(r"Collector|\(\s*I\.?\s*A\.?\s*S\.?\s*\)|\bI\.A\.S\b|^[A-Z][a-z]+\s*:|GAZETTE|Gazette|^_{3,}|^-{3,}|^\(?[A-Z][A-Z .]+,\)?$|"
                  r"^[A-Z][a-z]+,\s+(dated\s+)?\d|^Place|^Date[d :]|^Dated|^\d+(st|nd|rd|th) [A-Z][a-z]+ 20\d\d")
RESULT = re.compile(r"declare|publish(es)?\s+(the\s+)?names?|elected\s+as\s+Councillor", re.I)
NOT_RESULT = re.compile(r"Draft\s+Order|extent\s+of\s+the\s+Wards|Nominated|Ward\s+Formation", re.I)
ROLE = (("serial", re.compile(r"^(Sr|S)\b\.?|^No\.$")), ("name", re.compile(r"^Names?\b")),
        ("ward", re.compile(r"^(Ward|Prabhag|Pra\.)\b")),
        ("reservation", re.compile(r"^(Reserv\w*|Remarks?|Category|Catagory|Class)\b")), ("address", re.compile(r"^Address\b")),
        ("party", re.compile(r"^(Party|Political|Affil\w*)\b")))
RESV = ((r"\bS\.?\s*T\.?\b|Tribe", "ST"), (r"\bS\.?\s*C\.?\b|Cast", "SC"),
        (r"Backward|\bB\.?\s*C\.?\s*C\b|\bO\.?\s*B\.?\s*C\b|N\.?\s*A\.?\s*M\.?\s*P\.?\s*R\.?\s*A|NAMPRA|Nagrikancha|"
         r"Nagarikancha|Mag[a]?s", "OBC"),
        (r"General|Open|\bGEN\b|Unreserved|Sarvasadharan", "General"))
PARTY = ((r"Bharatiya\s+Janata|\bB\.?\s*J\.?\s*P\b", "BJP"), (r"Nationalist|\bN\.?\s*C\.?\s*P\b|Rashtrawadi|Rashtravadi", "NCP"),
         (r"Congress|\bI\.?\s*N\.?\s*C\b", "INC"), (r"Shiv\s*-?\s*sena|Shivsena|Shiv Sena", "SHS"),
         (r"Navnirman|\bM\.?\s*N\.?\s*S\b", "MNS"), (r"Vanchit", "VBA"), (r"Communist.*Marx|Markzist|\bC\.?P\.?I\.?\s*\(?M", "CPI(M)"),
         (r"Communist", "CPI"), (r"Bahujan\s+Samaj", "BSP"), (r"Samajwadi", "SP"), (r"Prahar", "PJP"),
         (r"Independent|Apaksha|Apksha", "Independent"))


def reservation(t):
    t = t or ""
    cat = next((v for k, v in RESV if re.search(k, t, re.I)), "")
    woman = bool(re.search(r"Wom[ae]n|Female|Ladies|Mahila|\(W\.?\)|\bW\b", t, re.I))
    return (cat + " woman") if (cat and woman) else (cat or ("Woman" if woman else ""))


def party_of(t):
    return next((v for k, v in PARTY if re.search(k, t or "", re.I)), "")


def lines_of(ws, tol=3):
    """Words [(x0, y0, x1, y1, text)] -> lines [(y, [(x0, x1, text)])], top to bottom (text kept as is)."""
    out = []
    for w in sorted(ws, key=lambda w: (w[1], w[0])):
        if out and abs(w[1] - out[-1][0]) <= tol:
            out[-1][1].append((w[0], w[2], w[4]))
        else:
            out.append([w[1], [(w[0], w[2], w[4])]])
    return [(y, sorted(lw)) for y, lw in out]


def phrases(lw, gap=7):
    """Words of one line -> phrases [(x0, x1, text)]: words closer than `gap` points join."""
    out = []
    for a, b, t in lw:
        keyword = any(rx.match(t) for r, rx in ROLE if r != "serial") or re.match(r"^(Sr|S)\b\.?", t)
        if out and a - out[-1][1] < gap and not keyword:
            out[-1] = (out[-1][0], b, out[-1][2] + " " + t)
        else:
            out.append((a, b, t))
    return out


def head_roles(lw):
    """The schedule head line -> [(x centre, role)] in x order, or None. A head names a Name and a Ward / Prabhag column."""
    roles = []
    ph = [(a, b, t, next((r for r, rx in ROLE if rx.match(t.split()[0])), None)) for a, b, t in phrases(lw)]
    names = [i for i, x in enumerate(ph) if x[3] == "name"]
    if len(names) > 1:     # Solapur: "Name of the / Nagarpanchayat" before "Name of the Councillor": the first is the body
        keep = next((i for i in names if re.search(r"Councillor|Candidate|Member|Elected|Person", ph[i][2])), names[-1])
        ph = [(a, b, t, "body" if (r == "name" and i != keep) else r) for i, (a, b, t, r) in enumerate(ph)]
    for a, b, t, role in ph:
        if role and role not in [r for _, r in roles]:
            roles.append(((a + b) / 2, role))
    names = [r for _, r in roles]
    if lw and re.match(r"\d", lw[0][2]):
        return None                              # a member row ("6 Ward No. 6 ... Namewar ...") is not a head
    return roles if "name" in names and "ward" in names else None


def text(lw):
    return " ".join(t for _, _, t in lw)


def body_of(block, bodies):
    """The payload body that the block's text names (the name next to Nagar Panchayat / Municipal Council first)."""
    found = []
    for b in bodies:
        for n in b.get("en", []):
            e = re.escape(n).replace(r"\ ", r"[\s\-]*")
            near = (rf"\b{e}\b[\s,.]*(Nagar\s*-?\s*Panchayat|Nagarpanchayat|N\.\s*P\.|Municipal\s+Council)|"
                    rf"(Nagar\s*-?\s*Panchayat|Nagarpanchayat|Municipal\s+Council)[\s,.]*(of\s+)?\b{e}\b")
            m = re.search(near, block, re.I)
            if m:
                found.append((0, m.start(), b))
            else:
                m = re.search(rf"\b{e}\b", block, re.I)
                if m:
                    found.append((1, m.start(), b))
    found.sort(key=lambda f: (f[0], f[1]))
    return found[0][2] if found else None


def rows_of(pages):
    """pages: [(page no, words)] -> blocks [{"text": block text, "rows": [{"page", "line", "line_text", role: text}]}]."""
    blocks, cur, roles, bs, row, last = [], None, None, None, None, None
    for pg, ws in pages:
        lines = lines_of(ws)
        for li, (y, lw) in enumerate(lines, 1):
            t = gj.norm(text(lw))
            if LEGACY.search(t):
                provenance.skipped('skip: LEGACY.search(t)')
                continue                         # a line of the Marathi part (legacy font codes)
            if START.match(t):
                cur = {"text": "", "rows": []}
                blocks.append(cur)
                roles, bs, row = None, None, None
                continue
            if cur is None:
                provenance.skipped('skip: cur is None')
                continue
            hr = head_roles(lw)
            if hr and not row:
                roles = hr
                body = [lw2 for _, lw2 in lines[li:] if not LEGACY.search(text(lw2))]
                bs = mh_gztext.borders([(0, l) for l in body], [x for x, _ in roles]) if len(roles) > 1 else []
                continue
            if roles is None:
                cur["text"] += " " + t
                continue
            cells = dict(zip([r for _, r in roles], mh_gztext.split(lw, bs)))
            serial = cells.get("serial", "") if "serial" in cells else (lw[0][2] if lw else "")
            name = cells.get("name", "")
            if re.fullmatch(r"\d{1,3}\.?", serial.strip()) and re.search(r"[A-Za-z]{2}", name) and not STOP.search(t):
                row = {"page": pg, "line": li, "line_text": t, **cells, "serial": serial.strip(" .")}
                cur["rows"].append(row)
                last = (pg, y)
            elif row is not None and last and last[0] == pg and y - last[1] < 40 and not STOP.search(t) \
                    and not re.fullmatch(r"[\d\s()]+", t):
                for c, v in cells.items():
                    if v and c != "serial":
                        row[c] = (row.get(c, "") + " " + v).strip()
                last = (pg, y)
            elif STOP.search(t) and row is not None:
                row, last = None, None           # the signature ends the schedule; a page head only pauses it
            if row is None and cur["rows"] and START.match(t):
                pass
    return blocks


def records(blocks, p):
    out, seen = [], set()
    bodies = p.get("bodies") or []
    for bi, blk in enumerate(blocks):
        if not blk["rows"]:
            provenance.skip_row(blk, 'skip: not blk["rows"]')
            continue
        b = body_of(blk["text"], bodies) if bodies else None
        if b is None and len(bodies) == 1 and len(blocks) == 1:
            b = bodies[0]
        if b is None:
            provenance.skip_row(blk, 'skip: b is None')
            continue                             # a block for a body that the item does not ask for
        if not RESULT.search(blk["text"]) or NOT_RESULT.search(blk["text"]):
            provenance.skip_row(blk, 'skip: not RESULT.search(blk["text"]) or NOT_RESULT.search(blk["text"])')
            continue                             # a ward formation, reservation or nomination order
        for r in blk["rows"]:
            m = re.match(r"^(.*?[A-Za-z.])\s+(\d{1,3})$", gj.norm(r.get("name", "")))
            if m and not mh.num(r.get("ward", "")):
                r["name"], r["ward"] = m.group(1), m.group(2)     # the ward number set close to the name
            ward_t = re.sub(r"^[.\s…]+", "", gj.norm(r.get("ward", "")))
            m = re.fullmatch(r"(?:(?:Ward|Prabhag|Pra\.)\s*)?(?:(?:No|Kr)\.?\s*)?(\d{1,3})\s*[.,]?\s*(.*)", ward_t, re.I)
            rest = m.group(2).strip() if m else ""
            if not m or (rest and not re.fullmatch(r"[\d\s.]+", rest) and not reservation(rest)):
                provenance.skip_row(r, 'skip: not m or (rest and not re.fullmatch(r"[\\d\\s.]+", rest) and not rese...')
                continue                         # a ward cell is a short number: anything else is not a member row
            if rest and reservation(rest) and not r.get("reservation"):
                r["reservation"] = rest          # the reservation set close to the ward number (Amravati)
            ward = str(int(m.group(1)))
            name = gj.norm(r.get("name", "")).strip(" .")
            name = re.sub(r"\s*\.\.+\s*", " ", name).strip()
            if not ward or not name:
                provenance.skip_row(r, 'skip: not ward or not name')
                continue
            resv_t = re.sub(r"^\d{1,2}\s+(?=[A-Za-z])", "", gj.norm(r.get("reservation", "")))
            party_t = gj.norm(r.get("party", ""))
            d = {"type": "councillor", "state": "MH", "body": b.get("en", [""])[0] + " Nagar Panchayat",
                 "body_local": b.get("local", ""), "body_en": b.get("name") or (b.get("en", [""])[0] + " Nagar Panchayat"),
                 "body_type": "Nagar Panchayat", "district": b.get("district", ""), "lgd_code": b["lgd_code"],
                 "ward_no": ward, "name": name, "reservation": reservation(resv_t), "reservation_text": resv_t,
                 "address": gj.norm(r.get("address", "")), "party": party_of(party_t) or party_t, "party_text": party_t,
                 "serial": mh.num(r.get("serial", "")), "election": ELECTION, "url": p["url"],
                 "gazette": p.get("match", ""), "gazette_date": p.get("gazette_date", ""), "page": r["page"],
                 "read": "text layer (English order)", "method": METHOD,
                 "src_pos": {"page": r["page"], "line": r["line"], "line_text": r["line_text"], "block": bi + 1}}
            key = f"councillor:MH:{b['lgd_code']}:{ward}"
            if key in seen:
                key += f"-s{d['serial'] or len(out)}"
            seen.add(key)
            out.append((key, {k: v for k, v in d.items() if v not in ("", None)}))
    return out


def parse(pdf, p):
    import subprocess
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    first, last = int(p.get("first", 1)), min(int(p.get("last", n) or n), n)
    return records(rows_of([(pg, gj.words(pdf, pg)) for pg in range(first, last + 1)]), p)


def fetch(p, get):
    from cforms.tn import stored
    content = stored(p, get)
    if content is None:
        content, why = mh.get_pdf(p, get)
        if content is None:
            return [], [], why
    key = hashlib.sha1((p["gazette_date"] + p["match"] + str(p.get("nth", ""))).encode()).hexdigest()[:12]
    files = [] if p.get("stored") else [(f"councillors/MH/{key}.pdf", content, "application/pdf")]
    if p.get("save_only"):          # a notice without an English part: keep the copy for the OCR reader, read nothing here
        return [], files, ""
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, p)
    want = {b["lgd_code"] for b in p.get("bodies") or []}
    got = {r["lgd_code"] for _, r in recs}
    why = "" if recs else "no members read"
    if recs and want - got:
        why = "bodies not read: " + ",".join(sorted(want - got))
    return recs, files, why
