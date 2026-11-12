"""Maharashtra municipal councils and nagar panchayats, general election 2025 (polls 2 and 20 Dec 2025, counting 21 Dec 2025):
the State Election Commission's statistical reports (mahasec.maharashtra.gov.in, Statistical Reports, 13 Feb 2026).

- "members": Upload/PDF/Member Winning Candidate Data.pdf, "Municipal Council and Nagar Panchayat 1st and 2nd Place Winning
  Candidates (Members) Results - 2025", 552 pages, 6,865 seats of 288 bodies (246 councils, 42 nagar panchayats).
- "presidents": Upload/PDF/President.pdf, the directly elected presidents (nagaradhyaksha) of the same bodies, 26 pages.
Both are Excel printouts in English with a text layer and drawn cell borders. Columns (members): serial, division, district,
body, ward, seat, reservation, winner, gender, votes, party, runner-up, runner-up votes, runner-up party. The presidents file
has no ward and seat columns. Each row is the band between two horizontal borders (cforms/gj.py grid_rows); each cell is the
text layer inside its borders. Words that the printout wraps inside a cell ("MANGALWEDH A", "UNOPP OSED") are joined.
One queue item = one file and a page range (payload doc, first, last). The first item of a file saves it in the bucket; the
other items read that copy (payload "stored", as cforms/tn.py). The site also answers from outside India.
Record id councillor:MH:<LGD code, or district-body when LGD has no such body>:<ward>-<seat> (presidents: ...:president).
items() lists the queue items (seeds/ocr_councillors_cw_mh.json): 12 items of 46 pages for the members file, 1 for presidents.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

from cforms import gj
from cforms.tn import mark_stored, stored

METHOD = "pdf text layer by drawn cell borders (pdftotext -bbox)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://mahasec.maharashtra.gov.in/Upload/PDF/"
DOCS = {"members": (BASE + "Member%20Winning%20Candidate%20Data.pdf", 14, 8),
        "presidents": (BASE + "President.pdf", 12, 6)}
ELECTION = "Maharashtra Municipal Council and Nagar Panchayat General Election 2025"
MEMBER_COLS = ("serial", "division", "district", "body", "ward_no", "seat", "reservation", "name", "gender", "votes", "party",
               "runner_up", "runner_up_votes", "runner_up_party")
PRESIDENT_COLS = ("serial", "division", "district", "body", "reservation", "name", "gender", "votes", "party", "runner_up",
                  "runner_up_votes", "runner_up_party")
# SEC (district, body) -> LGD (code, name, type), checked by hand 2026-11-11 (cw_mh_lgd.json): the SEC spellings (Paoni, Shegoan,
# Vasmat, Omerga, Urun- Ishwarpur) are far from LGD's (Pauni, Shegaon, Basmath, Umarga, Uran Islampur), and some names exist in
# several districts (Malkapur, Nandgaon, Malegaon). body_en carries the LGD name. Rahata is LGD's Rahta Pimplas; Ozar and
# Nashirabad (councils formed in 2025) are not in LGD.
LGD = json.load(open(os.path.join(os.path.dirname(__file__), "cw_mh_lgd.json"), encoding="utf-8"))
# Nagar panchayats in this election (SEC's due-election list /Site/141844/Nagar-Panchayat); every other body is a council.
NP = {"BARSHI-TAKALI", "DHARNI", "NAND. KHANDESHWAR", "NANDGAON KHANDESHWAR", "MALEGAON", "DHANKI", "FULAMBRI", "PHULAMBRI",
      "RENAPUR", "HIMAYATNAGAR", "WADA", "DEVRUKH", "GUHAGAR", "LANJA", "KANKAVALI", "KANKAWALI", "BHISI", "GOREGAON",
      "SALEKASA", "BAHADURA", "BESA PIPLA", "BESA-PIPLA", "BHIWAPUR", "BIDGAON-TARODI(KHURD)-PANDHURNA", "GODHANI (RAILWAY)",
      "KANDRI (KANHAN)", "KONDHALI", "MAHADULA", "MOUDA", "NILDOH", "PARSHIVNI", "YERKHEDA", "NEWASA", "SHINDKHEDA",
      "MUKTAINAGAR", "HATKANANGLE", "HATKANANGALE", "ANGAR", "MALEGAON BU.", "MALEGAON BK", "SHENDURNI", "WAGHOLI"}
# Party names as the returning officers typed them (BHARTIY JANTA PARTY, भारतीय जनता पाटी, NCP-SP ...), matched on the letters
# alone (spaces and signs dropped: the printout also breaks words, "SHARADCHAN DRA"). Order matters: UBT before SHS, SP before NCP.
PARTY = ((r"^BJP$|BHA?RA?TI?Y?A?JANA?TA?PA?RT[YI]|^भारतीयजनता", "BJP"),
         (r"UDDHAV|UDHAV|UBT|UBATHA|THAC?KE?R|उद्धव|ठाकरे", "SS(UBT)"),
         (r"^SHIVSENA$|^SHS$|^SS$|^SHIVSENAEKNATHSHINDE|EKNATH|SHINDE|^शि.?.?सेना$", "SHS"),
         (r"SHARAD|NCPSP|^NCPS$|शरद", "NCP(SP)"),
         (r"^NCP$|AJIT|NATIONALISTCONGRES+PART|राष्ट्रवादी", "NCP"),
         (r"^INC$|INDIANNATIONALCONGRES|^CONGRESS$|काँग्रेस|कॉंग्रेस|काॅंग्रेस|कााँग्रेस|^भारतीयराष्ट्रीयक|^इंड.?.?यननॅ", "INC"),
         (r"NAVNIRMAN|^MNS$|मनसे|नवनिर्माण", "MNS"), (r"VANCHIT|वंचित", "VBA"),
         (r"MAJLIS|AIMIM|ITTEHAD|मजलिस|एमआयएम", "AIMIM"), (r"BAHUJANSAMAJPART|^BSP$|बहुजनसमाजपा", "BSP"),
         (r"SAMAJWADI|^SP$|समाजवादी", "SP"), (r"FORWARDBLOC|^ऑलइ.*ब्ल", "AIFB"),
         (r"^INDEPEND[AE]NT|^IND$|^अपक्ष", "Independent"))
SKIP = re.compile(r"POS[T]?PONED|स्थगित")


def party_of(t):
    t = " ".join((t or "").split())
    c = re.sub(r"[^A-Zऀ-ॿ]", "", t.upper())
    for k, v in PARTY:
        if re.search(k, c):
            return v
    return title(t) if t and t != "-" else ""


def cell(ws, x0, y0, x1, y1):
    """Text inside a cell, line by line. A word wider than the cell is broken by the printout: when a line holds one word that
    fills the cell width and the next line holds one short fragment, the two are one word ("MANGALWEDH A", "UNOPP OSED")."""
    sel = [w for w in ws if gj.in_box(w, x0, y0, x1, y1)]
    lines = []
    for w in sorted(sel, key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        if lines and abs((w[1] + w[3]) / 2 - lines[-1][0]) < 3:
            lines[-1][1].append(w)
        else:
            lines.append([(w[1] + w[3]) / 2, [w]])
    out, prev = [], None
    for _, line in lines:
        line = sorted(line, key=lambda w: w[0])
        words = [w[4] for w in line]
        if out and prev and len(words) == 1 and len(words[0]) <= 4 and len(prev) == 1 and \
                prev[0][2] - prev[0][0] >= 0.8 * (x1 - x0):
            out[-1] += words[0]
        else:
            out.append(" ".join(words))
        prev = line
    return gj.norm(" ".join(out))


def slug(*parts):
    s = "-".join(re.sub(r"[^a-z0-9]+", "-", (p or "").lower()).strip("-") for p in parts if p)
    return s or "x"


def title(s):
    return " ".join(w.capitalize() if not re.fullmatch(r"[IVX]+|\(?[A-Z]\.?\)?", w) else w for w in (s or "").split())


def votes(t):
    t = re.sub(r"\s+", "", t or "")
    return int(t) if t.isdigit() else None


class Cells(list):
    """Cell texts of one row; .pos = its src_pos (grid row on the page, row box in PDF points, top-left origin)."""
    pos = None


def rows_of(ws, hs, vs, ncols, name_col):
    """Cell texts of every data row of one page, from its text-layer words and drawn lines."""
    rows, _ = gj.grid_rows(hs, vs, ncols, name_col)
    for gi, (cols, a, b) in enumerate(rows, 1):
        cells = Cells(cell(ws, cols[c][0] + 0.5, a, cols[c][1] - 0.5, b) for c in range(1, ncols + 1))
        cells.pos = {"row": gi, "box_pt": [round(cols[1][0], 1), round(a, 1), round(cols[ncols][1], 1), round(b, 1)]}
        if cells[0].isdigit():
            yield cells


def record(d, p, page):
    president = p["doc"] == "presidents"
    body = title(d["body"])
    district = title(d["district"])
    lgd = LGD.get(f"{district}|{body}")
    unopposed = re.sub(r"\s+", "", d.get("votes") or "").upper() == "UNOPPOSED"
    np = lgd[2] == "Nagar Panchayat" if lgd else d["body"].upper() in NP
    rec = {"type": "councillor", "state": "MH", "body": lgd[1] if lgd else body, "body_en": lgd[1] if lgd else body,
           "body_sec": body, "body_local": "", "lgd_code": lgd[0] if lgd else "",
           "body_type": "Nagar Panchayat" if np else "Municipal Council",
           "district": district, "division": title(d["division"]), "name": title(d["name"]),
           "gender": {"F": "Female", "MALE": "Male", "M": "Male"}.get((d.get("gender") or "").upper(), d.get("gender") or ""),
           "reservation": d.get("reservation", ""), "party": party_of(d.get("party")), "party_source": d.get("party", ""),
           "votes": votes(d.get("votes")), "unopposed": unopposed,
           "runner_up": title(d.get("runner_up")) if (d.get("runner_up") or "-") != "-" else "",
           "runner_up_votes": votes(d.get("runner_up_votes")), "runner_up_party": party_of(d.get("runner_up_party")),
           "election": ELECTION, "url": DOCS[p["doc"]][0], "page": page, "serial": int(d["serial"]),
           "source": "SEC Maharashtra statistical report, 13 Feb 2026"}
    if rec["votes"] is not None and rec["runner_up_votes"] is not None:
        rec["margin"] = str(rec["votes"] - rec["runner_up_votes"])
    key = (lgd[0] if lgd else "") or slug(d["district"], d["body"])
    if president:
        rec.update({"position": "President", "ward_no": ""})
        return f"councillor:MH:{key}:president", rec
    seat = re.sub(r"\s+", "", d.get("seat") or "")
    rec.update({"position": "Member", "ward_no": re.sub(r"\D", "", d.get("ward_no") or "") or d.get("ward_no", ""),
                "seat": seat})
    return f"councillor:MH:{key}:{rec['ward_no'] or 'x'}-{seat or d['serial']}", rec


def parse_page(ws, hs, vs, p, page, recs):
    """Adds the records of one page to recs (a tied second runner-up row goes to the record above it)."""
    _, ncols, name_col = DOCS[p["doc"]]
    names = MEMBER_COLS if p["doc"] == "members" else PRESIDENT_COLS
    for cells in rows_of(ws, hs, vs, ncols, name_col):
        d = dict(zip(names, cells))
        if not d.get("body") or SKIP.search(d.get("name") or ""):
            continue                    # seats whose poll was postponed: no member yet
        if not d.get("name"):           # a second runner-up with the same votes: its own row, winner cells empty
            if recs and d.get("runner_up"):
                recs[-1][1].setdefault("runner_up_tied", []).append(title(d["runner_up"]))
            continue
        recs.append(record(d, p, page))
        if getattr(cells, "pos", None):
            recs[-1][1]["src_pos"] = {"page": page, **cells.pos}
    return recs


def parse(pdf, p):
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    first, last = int(p.get("first", 1)), min(int(p.get("last", 1)), len(reader.pages))
    recs = []
    for page in range(first, last + 1):
        hs, vs = gj.drawn_lines(reader, page - 1)
        parse_page(gj.words(pdf, page), hs, vs, p, page, recs)
    return recs


PROJECT = "civic-officials-councillors-ocr"


def items(get=None):
    """Queue items: page ranges of both files; the first item of each file saves it, the others read the saved copy."""
    out = []
    for doc, pages, step in (("members", 552, 46), ("presidents", 26, 26)):
        for first in range(1, pages + 1, step):
            p = {"kind": "form-cw_mh", "state": "MH", "doc": doc, "url": DOCS[doc][0], "first": first,
                 "last": min(pages, first + step - 1)}
            if first > 1:
                p["stored"] = f"{PROJECT}/councillors/MH/sec-{doc}-2025.pdf"
            out.append({"key": f"cw-mh-sec-{doc}-p{first}", "payload": p})
    return out


def tools():
    """pdftotext (poppler); installed on a GitHub runner with sudo when missing."""
    if not shutil.which("pdftotext"):
        subprocess.run("sudo -n apt-get update -q && sudo -n apt-get install -y -q poppler-utils", shell=True, capture_output=True)
    return bool(shutil.which("pdftotext"))


def fetch(p, get):
    if not tools():
        return [], [], "pdftotext not available"
    url = DOCS[p["doc"]][0]
    content = stored(p, get)
    from_bucket = content is not None
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
    if content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    files = [(f"councillors/MH/sec-{p['doc']}-2025.pdf", content, "application/pdf")] \
        if int(p.get("first", 1)) == 1 and not p.get("stored") else []
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "r.pdf")
        with open(path, "wb") as f:
            f.write(content)
        recs = parse(path, p)
    if from_bucket:
        mark_stored(recs, p, content, url)
    return recs, files, "" if recs else "no members read"
