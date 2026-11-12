"""Tamil Nadu urban local body results 2022 (tnsec.tn.gov.in, ulbe2022/{corp|mun|tp}_{district}.pdf), read from the text layer.

The files were made by mPDF with its Tamil font: the text layer is complete once the font's Private Use glyphs are mapped back
and the vowel signs put in logical order (cforms/cn_mpdf_ta.py). So no OCR is needed (the older reader cforms/tn.py OCRs each
page and pairs it with the text layer by vote count; it found about half of the wards).
Each ward block: "<body type> : <body>   வார்டு எண்: <n> [<reservation>]", a totals line (electors, polled, valid, invalid),
then one row per candidate: serial, name, gender, father's/husband's name, party, votes, %, result ("வெற்றி" = won,
"போட்டியின்றி தேர்வு" = elected unopposed). Cells that wrap are printed on the lines above and below the row (centred):
the reader puts them back by column position.
One queue item = one PDF, read from the bucket copy (payload "stored"), so no Indian proxy is needed; the site is asked only
when there is no stored copy. Payload: {"kind": "form-tn_text", "state": "TN", "url", "type" (corp|mun|tp), "district_code",
"district", "stored"}. One record per ward winner, with every candidate of the ward in "candidates".
Record id: councillor:TN:tx:<type>-<district code>:<body>:<ward>.
"""
import os
import re
import shutil
import subprocess
import tempfile

import provenance
from cforms.cn_mpdf_ta import convert

METHOD = "pdf text (pdftotext -layout) + Tamil font map (mPDF glyphs)"     # source trail (provenance.py): how this reader reads its sources

BODY_TYPE = {"corp": "மாநகராட்சி", "mun": "நகராட்சி", "tp": "பேரூராட்சி"}
HEAD = re.compile(r"^\s*(மாநகராட்சி|நகராட்சி|பேரூராட்சி)\s*:\s*(.+?)\s{2,}வார்டு\s*எண்\s*:\s*(\S+)\s*(?:\[(.*?)\]?)?\s*$")
GENDER = re.compile(r"^(பெண்|ஆண்|திருநங்கை|மூன்றாம் பாலினம்|இதர)$")
PARTY = {"தி.மு.க": "DMK", "அ.இ.அ.தி.மு.க": "AIADMK", "பி.ஜே.பி": "BJP", "பா.ஜ.க": "BJP", "இ.தே.கா": "INC", "காங்கிரஸ்": "INC",
         "சுயேட்சை வேட்பாளர்": "Independent", "சுயேட்சை": "Independent", "ம.தி.மு.க": "MDMK", "வி.சி.க": "VCK",
         "பா.ம.க": "PMK", "தே.மு.தி.க": "DMDK", "நா.த.க": "NTK", "அ.ம.மு.க": "AMMK", "இ.கம்யூ": "CPI", "சி.பி.ஐ": "CPI",
         "மா.கம்யூ": "CPI(M)", "சி.பி.ஐ (எம்)": "CPI(M)", "சி.பி.ஐ(எம்)": "CPI(M)", "இ.யூ.மு.லீ": "IUML",
         "ம.நீ.ம": "MNM", "Makkal Needhi Maiam": "MNM", "எஸ்.டி.பி.ஐ": "SDPI", "பகுஜன் சமாஜ் கட்சி": "BSP", "பி.எஸ்.பி": "BSP"}
NUM = re.compile(r"^\d+$")
PCT = re.compile(r"^\d+\.\d+$")
DONE = {"வெற்றி", "தோல்வி"}
CHUNK = re.compile(r"\S+(?: \S+)*")


def chunks(raw):
    """[(x, text)] of a raw pdftotext -layout line: runs of text split at two or more spaces, x in raw characters."""
    return [(m.start(), convert(m.group())) for m in CHUNK.finditer(raw)]


def party_en(s):
    k = (s or "").strip().rstrip(".").strip()
    return PARTY.get(k) or PARTY.get(k.replace(" ", "")) or s


def num(s):
    s = (s or "").replace(",", "").strip()
    return int(s) if NUM.match(s) else None


def totals(line):
    d = {}
    for key, pat in (("electors", r"மொத்த\s*வாக்காளர்கள்\s*:\s*(\d+)"), ("polled", r"பதிவான\s*வாக்குகள்\s*:\s*(\d+)"),
                     ("valid", r"செல்லத்தக்க\s*வாக்குகள்\s*:\s*(\d+)"), ("invalid", r"செல்லாத\s*வாக்குகள்\s*:\s*(\d+)")):
        m = re.search(pat, line)
        if m:
            d[key] = int(m.group(1))
    m = re.search(r"பதிவான\s*வாக்குகள்\s*:\s*\d+\s*\(([\d.]+)%\)", line)
    if m:
        d["poll_pct"] = m.group(1)
    return d


class Block:
    def __init__(self, head, page):
        self.body_type, self.body, self.ward, self.reservation = (head.group(1), head.group(2).strip(), head.group(3).strip(),
                                                                   (head.group(4) or "").strip())
        self.page, self.totals, self.cols, self.rows, self.extra = page, {}, {}, [], []

    def col_of(self, x):
        """Column of a chunk that starts at x (raw characters), from the block's header positions."""
        c = self.cols
        g, f, p, v, r = c.get("gender"), c.get("father"), c.get("party"), c.get("votes"), c.get("result")
        if g is not None and x < g - 2:
            return "name"
        if f is not None and p is not None and x < (f + p) / 2:
            return "father"
        if v is not None and x < v - 4:
            return "party"
        if r is not None and x >= r - 12:
            return "result"
        return "numbers"


def row_of(ch):
    """A candidate row (list of chunks starting with the serial number) -> dict, or None."""
    if len(ch) < 4 or not NUM.match(ch[0][1]) or ch[0][0] > 8:
        return None
    rest = ch[1:]
    vi = next((i for i in range(len(rest) - 1) if NUM.match(rest[i][1]) and PCT.match(rest[i + 1][1])), None)
    if vi is None:
        return None
    gi = next((i for i in range(vi) if GENDER.match(rest[i][1])), None)
    name = rest[0][1]
    if gi is None:                                 # name and gender joined by one space
        m = re.match(r"^(.*\S)\s+(பெண்|ஆண்|திருநங்கை)$", name)
        if m:
            name, gender, mid = m.group(1), m.group(2), rest[1:vi]
        else:
            gender, mid = "", rest[1:vi]
    else:
        gender, mid = rest[gi][1], rest[gi + 1:vi]
        if gi == 0:                                # the name wraps: it is on the lines above and below
            name = ""
        elif gi > 1:                                 # a name in two chunks
            name = " ".join(t for _, t in rest[:gi])
    return {"serial": ch[0][1], "name": name, "gender": gender, "mid": mid, "votes": rest[vi][1], "pct": rest[vi + 1][1],
            "result": " ".join(t for _, t in rest[vi + 2:])}


def parse_text(raw, p=None):
    """pdftotext -layout output of one file (pages split by form feed) -> [ward dict] in file order."""
    blocks, cur = [], None
    for page_no, page in enumerate(raw.split("\f"), 1):
        lines = page.splitlines()
        for i, rl in enumerate(lines):
            line = convert(rl)
            h = HEAD.match(line)
            if h:
                cur = Block(h, page_no)
                blocks.append(cur)
                continue
            if cur is None:
                continue
            if "வாக்காளர்கள்" in line and "வாக்குகள்" in line:
                cur.totals = totals(line)
                continue
            ch = chunks(rl)
            if any("பாலினம்" in t or t.startswith(("தந்தை", "பெற்ற", "சதவீதம்", "முடிவு")) for _, t in ch):
                for x, t in ch:
                    if "பாலினம்" in t:
                        cur.cols["gender"] = x
                    elif t.startswith("தந்தை"):
                        cur.cols["father"] = x
                    elif t.startswith("கட்சி"):
                        cur.cols["party"] = x
                    elif t.startswith("பெற்ற"):
                        cur.cols["votes"] = x
                    elif t.startswith("முடிவு"):
                        cur.cols["result"] = x
                continue
            if not ch or any(t.startswith(("வ.", "எண்.")) for _, t in ch[:1]):
                continue
            r = row_of(ch)
            if r:
                r["line"], r["page"], r["raw"] = (page_no, i), page_no, rl
                r["cells"] = {"name": [], "father": [], "party": [], "result": []}
                for x, t in r.pop("mid"):
                    col = cur.col_of(x)
                    if col == "name":
                        col = "father"              # anything between gender and votes is father or party
                    r["cells"]["party" if col in ("party", "numbers", "result") else "father"].append(t)
                if r["result"]:
                    r["cells"]["result"].append(r["result"])
                cur.rows.append(r)
            else:
                cur.extra.append(((page_no, i), ch))
    return [ward_of(b, p or {}) for b in blocks]


def ward_of(b, p):
    """Put the wrapped cell lines back on their rows, pick the winner."""
    rows = b.rows
    for (pg, i), ch in b.extra:
        above = next((r for r in reversed(rows) if r["line"][0] == pg and r["line"][1] < i), None)
        below = next((r for r in rows if r["line"][0] == pg and r["line"][1] > i), None)
        for x, t in ch:
            col = b.col_of(x)
            if col == "numbers":
                continue
            # a wrapped cell is centred on its row: a line next to a row whose cell is empty on the row line belongs to it; else
            # a three-line cell (text on the row line too) takes it. Cells of different heights are not on the same text lines,
            # so a row two lines away can own a line ("வெற்றி / (குலுக்கல் / முறை)" next to a two-line party). A row whose
            # result is one word (வெற்றி, தோல்வி) has no wrapped result.
            near = []
            for dist in (1, 2):
                if below is not None and below["line"][1] - i == dist:
                    near.append(("_pre_", below, dist))
                if above is not None and i - above["line"][1] == dist:
                    near.append(("_post_", above, dist))
            own = lambda r: bool(r["name"]) if col == "name" else bool(r["cells"][col])
            near = [n for n in near if not (col == "result" and " ".join(n[1]["cells"]["result"]) in DONE)]
            pick = next((n for n in near if n[2] == 1 and not own(n[1])), None)
            if pick is None:       # a three-line cell above (a line above its row, text on the row line) takes its third line
                pick = next((n for n in near if n[0] == "_post_" and own(n[1]) and n[1].get("_pre_" + col)
                             and not n[1].get("_post_" + col)), None)
            if pick is None:
                pick = next((n for n in near if n[2] == 1), None)
            if pick is None and near:
                pick = next((n for n in near if not own(n[1])), near[0])
            if pick:
                pick[1].setdefault(pick[0] + col, []).append(t)
    cands = []
    for r in rows:
        cell = {c: " ".join(r.get("_pre_" + c, []) + r["cells"][c] + r.get("_post_" + c, [])) for c in ("name", "father", "party", "result")}
        name = " ".join(x for x in (r["name"], cell["name"]) if x)
        cands.append({"serial": r["serial"], "name": name, "gender": r["gender"], "father_or_husband": cell["father"],
                      "party_local": cell["party"], "party": party_en(cell["party"]), "votes": num(r["votes"]),
                      "vote_pct": r["pct"], "result": cell["result"], "page": r["page"]})
    won = [c for c in cands if "வெற்றி" in c["result"] or "போட்டியின்றி" in c["result"]]
    if not won and len(cands) == 1:
        won = cands
    # source trail: the winner's row line (page 1-based, line 1-based in that page's pdftotext -layout text, raw line)
    row = {id(c): r for c, r in zip(cands, rows)}
    pos = [provenance.line_pos(row[id(c)]["line"][0], row[id(c)]["line"][1] + 1, row[id(c)]["raw"], serial=c["serial"]) for c in won]
    return {"body_type": b.body_type, "body": b.body, "ward_no": b.ward, "reservation": b.reservation, "page": b.page,
            **b.totals, "candidates": cands, "winners": won, "winner_pos": pos}


def records(wards, p):
    recs, seen = [], {}
    for w in wards:
        for k, c in enumerate(w["winners"]):
            rec = {"type": "councillor", "state": "TN", "body": w["body"], "body_local": w["body"], "body_type": w["body_type"],
                   "district": p.get("district"), "ward_no": w["ward_no"], "reservation": w["reservation"], "name": c["name"],
                   "gender": c["gender"], "father_or_husband": c["father_or_husband"], "party_local": c["party_local"],
                   "party": c["party"], "votes": c["votes"], "vote_pct": c["vote_pct"], "result": c["result"],
                   "unopposed": "போட்டியின்றி" in c["result"], "position": "Ward Member",
                   **{x: w[x] for x in ("electors", "polled", "valid", "invalid", "poll_pct") if x in w},
                   "candidates": w["candidates"], "election": "Tamil Nadu 2022", "url": p.get("url"), "page": w["page"],
                   "read": "text layer (mPDF Tamil glyphs mapped)"}
            if k < len(w.get("winner_pos") or []):
                rec["src_pos"] = w["winner_pos"][k]
            if p.get("_src"):
                rec["src"] = dict(p["_src"])
            slug = re.sub(r"\s+", "-", w["body"])[:60]
            rid = f"councillor:TN:tx:{p.get('type')}-{p.get('district_code')}:{slug}:{w['ward_no']}"
            n = seen.get(rid, 0)
            seen[rid] = n + 1
            recs.append((rid if n == 0 else f"{rid}:{n + 1}", rec))
    return recs


def pdftotext():
    if shutil.which("pdftotext"):
        return True
    subprocess.run("sudo -n apt-get -o DPkg::Lock::Timeout=600 install -y -q poppler-utils", shell=True, capture_output=True)
    return bool(shutil.which("pdftotext"))


def fetch(p, get):
    from cforms.tn import stored
    if not pdftotext():
        return [], [], "pdftotext not available"
    content = stored(p, get)
    files = []
    src = provenance.file_src(content, p.get("url"), p.get("stored")) if content is not None else None
    if content is None:
        r = get(p["url"])
        if r is None or r.content[:5] != b"%PDF-":
            return [], [], "no answer"
        content = r.content
        import hashlib
        if not p.get("stored"):        # an item that names a stored copy does not store the file a second time
            files = [(f"councillors/TN/{hashlib.sha1(p['url'].encode()).hexdigest()[:12]}.pdf", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        raw = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    wards = parse_text(raw, p)
    recs = records(wards, dict(p, _src=src) if src else p)
    nowin = [f"{w['body']}:{w['ward_no']}" for w in wards if not w["winners"]]
    if recs:
        return recs, files, ""
    return [], files, f"no winners read ({len(wards)} ward blocks; {len(nowin)} without a winner)"
