"""Uttarakhand: every elected mayor/chairperson and ward member of the urban bodies (general election 2024-25, poll 23.01.2025),
from the Urban Development Department's list "Information related to the newly elected public representatives in the
Uttarakhand Municipal Corporation General Election 2024-25" (udd.uk.gov.in/newly-elected-public-representatives/, file of
02.09.2026: cdnbbsr.s3waas.gov.in/s38208974663db80265e9bfe7b222dcb18/uploads/2026/06/202609031174499502.pdf, 32 pages printed
from Chrome). It answers outside India.
Columns: क्र.सं. | जनपद | निकाय का नाम | कक्ष संख्या | कक्ष का नाम | मा0 मेयर / अध्यक्ष / सदस्य का नाम | महिला/पुरूष | मोबाइल न0 |
शपथ ग्रहण करने की तिथि | प्रथम बोर्ड की तिथि | अभियुक्ति. Each body starts with its head row ("मा0 मेयर" or "अध्यक्ष" in the ward
name column); the serial, district and body cells are merged over the body's rows, so their text stands once, in the middle of
the block (sometimes on the next page).
The text layer is good, but Chrome splits some Devanagari clusters with a false space ("कु मार", "रे नू"). Words are read with
their boxes (pdftotext -bbox): a true space is 0.209 x the word height wide; any other small gap is a split and is closed.
The body's English name and district come from the payload map "bodies" (Hindi body text -> civic.ulb name, made offline from
this file and checked by hand); a body not in the map keeps its Hindi name only.
One queue item = the whole file. Record id councillor:UK:<body slug>:<ward no or "chair">.
"""
import hashlib
import os
import re
import subprocess
import tempfile
from html import unescape

URL = "https://cdnbbsr.s3waas.gov.in/s38208974663db80265e9bfe7b222dcb18/uploads/2026/06/202609031174499502.pdf"
ELECTION = "Uttarakhand urban local bodies general election 2024-25 (poll 23.01.2025)"
COLS = ["sr", "district", "body", "ward_no", "ward_name", "name", "gender", "phone", "oath", "board", "remark"]
HEAD = {"sr": "क्र.सं.", "district": "जनपद", "body": "निकाय", "ward_no": "कक्ष", "name": "मा0", "gender": "महिला/", "phone": "मोबाइल",
        "oath": "शपथ", "board": "प्रथम", "remark": "("}
TYPES = (("नगर निगम", "Municipal Corporation", "Mayor"), ("नगर पालिका परिषद", "Municipal Council", "Chairperson"),
         ("नगर पालिका", "Municipal Council", "Chairperson"), ("नगर पंचायत", "Nagar Panchayat", "Chairperson"))
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')
PAGE = re.compile(r"<page [^>]*>(.*?)</page>", re.S)


def words(bbox_html):
    """pdftotext -bbox output -> pages of words (x0, y0, x1, y1, text)."""
    return [[(float(a), float(b), float(c), float(d), unescape(w)) for a, b, c, d, w in WORD.findall(pg)]
            for pg in PAGE.findall(bbox_html)]


def join(ws):
    """Words of one cell line, left to right, with Chrome's false spaces closed."""
    out = ""
    prev = None
    for w in sorted(ws):
        if prev is not None:
            gap, h = w[0] - prev[2], prev[3] - prev[1]
            space = 0.209 * h
            out += " " if abs(gap - space) <= 0.35 or gap >= 0.36 * h else ""
        out += w[4]
        prev = w
    return out.strip()


def bounds(ws, last):
    """Column left edges from the header words of a page (or the previous page's when it has no header)."""
    top = [w for w in ws if w[1] < 75]
    x = {}
    for key, word in HEAD.items():
        hits = sorted(w[0] for w in top if w[4] == word)
        if key == "ward_no" and hits:
            x["ward_no"], x["ward_name"] = hits[0] - 3, (hits[1] - 70 if len(hits) > 1 else None)
        elif hits:
            x[key] = hits[0]
    if not {"district", "body", "ward_no", "name", "gender", "phone"} <= set(x):
        return last
    b = {"sr": 0, "district": x["district"] - 15, "body": x["body"] - 5, "ward_no": x["ward_no"],
         "ward_name": next(w[2] for w in top if w[4] == "संख्या") + 4, "name": x["name"] - 6, "gender": x["gender"] - 5,
         "phone": x["phone"] - 10, "oath": x.get("oath", x["phone"] + 80) - 10, "board": x.get("board", x["phone"] + 180) - 8,
         "remark": x.get("remark", 1015) - 5}
    return [b[c] for c in COLS]


def column(x, b):
    return max(i for i, a in enumerate(b) if a <= x) if x >= b[0] else 0


def lines(ws):
    """Words -> lines (by vertical centre, 4 pt tolerance), top to bottom."""
    out = []
    for w in sorted(ws, key=lambda w: (w[1] + w[3]) / 2):
        c = (w[1] + w[3]) / 2
        if out and abs(out[-1][0] - c) <= 4:
            out[-1][1].append(w)
        else:
            out.append([c, [w]])
    return out


def rows(pages):
    """Pages of words -> (member rows, body label fragments); positions are (page, y)."""
    b, members, frags = None, [], []
    for pi, ws in enumerate(pages):
        b = bounds(ws, b)
        if b is None:
            continue
        for y, lw in lines([w for w in ws if w[1] >= 72 or not any(t[1] < 72 for t in ws)]):
            cells = [[] for _ in COLS]
            for w in lw:
                cells[column((w[0] + w[2]) / 2 if w[0] < b[COLS.index("ward_name")] else w[0], b)].append(w)
            c = {k: join(v) for k, v in zip(COLS, cells)}
            if c["sr"] == "क्र.सं." or c["name"].startswith("मा0 मेयर /"):
                continue
            for k in ("sr", "district", "body"):
                if c[k]:
                    frags.append((k, (pi, y), c[k]))
            head = re.search(r"मेयर|अध्यक्ष", c["ward_name"])
            has = c["name"] or c["phone"] or re.fullmatch(r"\d+", c["ward_no"] or "")
            if head or (has and (re.fullmatch(r"\d+", c["ward_no"] or "") or c["phone"])):
                members.append({**c, "head": bool(head), "pos": (pi, y)})
            elif has and members:                  # a wrapped name or ward name
                for k in ("ward_name", "name", "remark"):
                    if c[k]:
                        members[-1][k] = (members[-1][k] + " " + c[k]).strip()
    return members, frags


def bodies(members, frags):
    """Group members into bodies (a head row starts one) and give each its sr/district/body text (fragments inside its span)."""
    out = []
    for m in members:
        if m["head"] or not out:
            out.append({"start": m["pos"], "members": [], "sr": [], "district": [], "body": []})
        out[-1]["members"].append(m)
    for i, bo in enumerate(out):
        end = out[i + 1]["start"] if i + 1 < len(out) else (10 ** 6, 0)
        for k, pos, t in frags:
            if bo["start"][:1] <= pos[:1] and (bo["start"] <= (pos[0], pos[1] + 6)) and pos < (end[0], end[1] - 6):
                bo[k].append(t)
    for bo in out:
        bo["body_text"] = " ".join(bo["body"]).replace(" ,", ",").strip()
        bo["district_text"] = " ".join(bo["district"]).strip()
    return out


def body_key(t):
    return re.sub(r"[\s,.‌‍]", "", t or "")


def body_type(t):
    for hi, en, head in TYPES:
        if body_key(t).startswith(body_key(hi)):
            return en, head, t[len(hi):].strip(" ,") if t.startswith(hi) else re.sub(r"^नगर\s*\S+\s*(परिषद)?\s*,?\s*", "", t)
    return None, None, t


def phone(s):
    d = re.sub(r"\D", "", s or "")
    return d if len(d) == 10 and d[0] in "6789" else None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def records(bos, p):
    known = p.get("bodies") or {}
    recs = []
    for bo in bos:
        info = known.get(body_key(bo["body_text"])) or {}
        btype, head, name_hi = body_type(bo["body_text"])
        btype = info.get("body_type") or btype
        en = info.get("body_en")
        key = slug(en) if en else hashlib.sha1(body_key(bo["body_text"]).encode()).hexdigest()[:10]
        for m in bo["members"]:
            ward = "chair" if m["head"] else str(int(m["ward_no"])) if re.fullmatch(r"\d+", m["ward_no"] or "") else ""
            if not ward or not m["name"]:
                continue
            d = {"type": "councillor", "state": "UK", "body": bo["body_text"], "body_local": info.get("body_local") or name_hi,
                 "body_en": en,
                 "body_type": btype, "district": info.get("district"), "district_local": bo["district_text"] or None,
                 "ward_no": ward, "ward_name": None if m["head"] else m["ward_name"] or None, "name": m["name"],
                 "position": (head or "Chairperson") if m["head"] else "Member",
                 "position_local": m["ward_name"] if m["head"] else None, "gender": m["gender"] or None,
                 "phone": phone(m["phone"]), "oath_date": m["oath"] if re.search(r"\d", m["oath"]) else None,
                 "first_board_date": m["board"] if re.search(r"\d", m["board"]) else None, "remark": m["remark"] or None,
                 "election": p.get("election", ELECTION), "url": p.get("url", URL), "page": m["pos"][0] + 1, "read": "text layer"}
            recs.append((f"councillor:UK:{key}:{ward}", {k: v for k, v in d.items() if v not in (None, "")}))
    seen, out = {}, []
    for rid, d in recs:
        n = seen[rid] = seen.get(rid, 0) + 1
        out.append((rid + (f"-{n}" if n > 1 else ""), d))
    return out


def parse_bbox(bbox, p):
    members, frags = rows(words(bbox))
    return records(bodies(members, frags), p)


def parse(pdf, p):
    return parse_bbox(subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True).stdout, p)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [(f"councillors/UK/{hashlib.sha1(url.encode()).hexdigest()[:12]}.pdf", r.content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(r.content)
        recs = parse(pdf, p)
    return recs, files, "" if recs else "no members read"
