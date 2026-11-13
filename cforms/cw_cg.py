"""Chhattisgarh urban body general election 2025: the State Election Commission's list of elected councillors (parshads), read
by OCR. cgsec.gov.in/hin_2025chunavnagarpalika.html links "निर्वाचित पार्षदों की जानकारी" = Notification2025/election/
Councillor 2025.pdf: one statewide table (55 pages, about 3,200 wards of 173 bodies, printed from Excel on 25 Feb 2025) with
seven ruled columns: serial, district, body ("नगरपालिक निगम ..." / "नगरपालिका परिषद ..." / "नगर पंचायत ..."), ward no,
ward name, elected councillor, party.
The text layer drops half letters and puts the i-sign before its consonant ("पाषद" for "पार्षद", "क यप" for "कश्यप"), so it is
used only for what survives: digits (serial, ward no), the party (a small, fixed vocabulary) and a consonant key of the
district and body. The body is named from the seed's map (consonant key -> LGD body, made offline from the same file and
checked by hand); a key that is not in the map is named from Tesseract's reading of the cell. Ward names and names are read
by Tesseract (hin) on each cell, cut from one 400 dpi page rendering; the printed u-signs touch the lower border, so a crop
reaches past it and the border pixels are whitened first.
Bodies not in this file: those elected in Dec 2021 (Bhilai, Risali, Bhilai-Charoda, Birgaon ...: next election due 2026-27)
and bodies formed after the 2025 poll.
One queue item = pages first..last of the one PDF. The site answers only from India; the first item saves the PDF in the
bucket and the others read that copy (payload "stored", see cforms/tn.py stored()) or the site when the copy is not there yet.
Record id councillor:CG:2025:<body slug>:<ward no>.
"""
import hashlib
import os
import re
import subprocess
import tempfile

from cforms import gj
from cforms.tn import mark_stored, stored
import provenance

METHOD = "ocr tesseract hin (name and ward name cells, 400 dpi) + pdf text layer by drawn cell borders (pdftotext -bbox)"     # source trail (provenance.py): how this reader reads its sources

URL = "https://cgsec.gov.in/Notification2025/election/Councillor%202025.pdf"
ELECTION = "Chhattisgarh urban body general election 2025 (SEC list of elected councillors, Feb 2025)"
CONS = re.compile("[अ-औक-हक़-य़]")
TYPES = (("नगरपलकनगम", "नगर पालिक निगम"), ("नगरपलकपरषद", "नगर पालिका परिषद"), ("नगरपचयत", "नगर पंचायत"))
# party: consonant key of the text layer cell (letters the layer keeps) -> party
PARTY = (("भरतयजनत", "BJP"), ("इडयननशनल", "INC"), ("नदलय", "Independent"), ("बहजनसमज", "BSP"), ("आमआदम", "AAP"),
         ("मकस", "CPI(M)"), ("मइडयसस", "CPI(M)"), ("कयनट", "CPI"), ("शवसन", "Shiv Sena"), ("नशनलपप", "NPP"),
         ("गडवन", "GGP"), ("जनतकगरस", "JCC(J)"), ("छततसगढ़", "JCC(J)"))


def key(s):
    """Consonant key: independent vowels and consonants only (no vowel signs, virama, nukta, anusvara, spaces)."""
    s = (s or "").replace("ड़", "ड").replace("ढ़", "ढ").replace("़", "")
    return "".join(CONS.findall(s))


def body_key(s):
    """(body type, key of the name) from a body cell ("नगरपािलका प रषद तखतप र ु" -> ("नगर पालिका परिषद", "तखतपर"))."""
    k = key(s)
    for p, t in TYPES:
        if k.startswith(p):
            return t, k[len(p):]
    return "", k


def dist_key(s):
    """District key: the sorted letters of the district cell (the text layer puts some letters out of order)."""
    return "".join(sorted(key(s)))


def map_key(r):
    """The seed map's key of a row: body key | district key."""
    return body_key(r["body_raw"])[1] + "|" + dist_key(r["district_raw"])


def party_of(s):
    k = key(s)
    if not k:
        return ""
    for p, v in PARTY:
        if p in k:
            return v
    if k in ("अय", "अनय"):
        return "Other"
    return ""


def num(t):
    m = re.search(r"\d+", (t or "").translate(str.maketrans("०१२३४५६७८९", "0123456789")))
    return str(int(m.group(0))) if m else ""


def tools():
    return gj.tools("hin")


def page_rows(reader, pdf, pg):
    """Data rows of one page: [{"serial", "ward_no", "district_raw", "body_raw", "party_raw", "cols", "y0", "y1"}]."""
    hs, vs = gj.drawn_lines(reader, pg - 1)
    rows, _ = gj.grid_rows(hs, vs, 7, 6)
    ws = gj.words(pdf, pg)
    out = []
    for cols, a, b in rows:
        t = {c: gj.box_text(ws, cols[c][0], a, cols[c][1], b) for c in range(1, 8)}
        if not t[1].isdigit() or (t[2], t[3], t[7]) == ("2", "3", "7"):      # header and column-number rows
            provenance.skipped('skip: not t[1].isdigit() or (t[2], t[3], t[7]) == ("2", "3", "7")')
            continue
        out.append({"serial": t[1], "ward_no": num(t[4]), "district_raw": t[2], "body_raw": t[3], "party_raw": t[7],
                    "name_raw": t[6],
                    "cols": cols, "y0": a, "y1": b})
    return out


def ocr_cells(pdf, pg, boxes, tmp, dpi=400):
    """Text of each box (x0, y0, x1, y1 in points). The page is rendered once; each crop reaches 2 pt below its cell (the
    u-signs touch the border) and pixel rows or columns that are mostly dark (borders) are whitened. One Tesseract run reads
    all crops (psm 7: one line each)."""
    if not boxes:
        return []
    k = dpi / 72
    base = os.path.join(tmp, f"p{pg}")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(pg), "-l", str(pg), "-singlefile", pdf, base],
                   capture_output=True)
    try:
        with open(base + ".pgm", "rb") as f:
            img = f.read()
    except OSError:
        return ["" for _ in boxes]
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", img)
    if not m:
        return ["" for _ in boxes]
    width, height, off = int(m.group(1)), int(m.group(2)), m.end()
    paths = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        a, b = max(0, int((x0 + 0.6) * k)), min(width, int((x1 - 0.6) * k))
        top, bot = max(0, int((y0 + 0.4) * k)), min(height, int((y1 + 2.0) * k))
        if b - a < 4 or bot - top < 4:
            a, b, top, bot = 0, 4, 0, 4
        w = b - a
        rows = [bytearray(img[off + y * width + a:off + y * width + b]) for y in range(top, bot)]
        for r in rows:                                    # horizontal borders: a mostly dark pixel row
            if sum(1 for v in r if v < 128) > 0.6 * w:
                r[:] = b"\xff" * w
        hgt = len(rows)
        for x in range(w):                                # vertical borders at the crop's edges
            if sum(1 for r in rows if r[x] < 128) > 0.8 * hgt:
                for r in rows:
                    r[x] = 255
        pth = os.path.join(tmp, f"c{pg}_{i}.pgm")
        with open(pth, "wb") as f:
            f.write(b"P5\n%d %d\n255\n" % (w, hgt) + b"".join(bytes(r) for r in rows))
        paths.append(pth)
    os.remove(base + ".pgm")
    lst = os.path.join(tmp, f"list{pg}.txt")
    with open(lst, "w") as f:
        f.write("\n".join(paths) + "\n")
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    r = subprocess.run(["tesseract", lst, "-", "-l", "hin", "--psm", "7", "--dpi", str(dpi), "tsv"], capture_output=True,
                       text=True, env=env)
    out = [[] for _ in boxes]
    for ln in r.stdout.splitlines()[1:]:
        p = ln.split("\t")
        if len(p) < 12 or p[0] != "5" or not p[11].strip():
            provenance.skip_line(ln, 'skip: len(p) < 12 or p[0] != "5" or not p[11].strip()')
            continue
        n = int(p[1])
        if 1 <= n <= len(boxes) and not (float(p[10]) < 20 and len(p[11]) <= 2):
            out[n - 1].append(p[11])
    for pth in paths:
        try:
            os.remove(pth)
        except OSError:
            pass
    return [clean(" ".join(x)) for x in out]


def clean(s):
    s = re.sub(r"[|\[\]{}_©®“”‘’~`॒॑]", " ", s or "")
    s = re.sub(r"\.{2,}", " ", s)
    return gj.norm(s).strip(" .,:;-—'\"")


LONE = re.compile("^[\u0915-\u0939]$")


def fix_name(s):
    """Tesseract slips with u-signs, which touch the lower border: a lone consonant (the sign read as a gap: "स रेश") joins
    the next word with ु; a word-final virama is a lost ु / ू ("साह्" -> "साहू"); "प्र" at a word end is "पुर"."""
    w = (s or "").split()
    out = []
    i = 0
    while i < len(w):
        if LONE.match(w[i]) and i + 1 < len(w) and re.match("[\u0915-\u0939]", w[i + 1]):
            out.append(w[i] + "ु" + w[i + 1])
            i += 2
            continue
        out.append(w[i])
        i += 1
    t = " ".join(out)
    t = re.sub("ह्(?=$|\\s)", "हू", t)
    t = re.sub("प्र(?=$|\\s|-)", "पुर", t)
    t = re.sub("([\u0915-\u0939])्(?=$|\\s)", "\\1ु", t)
    return t


def subseq(a, b):
    """True when every letter of a appears in b in order (the text layer only drops letters)."""
    it = iter(b)
    return all(ch in it for ch in a)


def slug_of(name):
    from cforms.cg import slug
    return slug(name) or "body"


def parse(pdf, p, use_ocr=True):
    """Records of pages p["first"]..p["last"] (pages read in parallel). p["bodies"]: {map_key: {"body", "body_en",
    "body_type", "district", "district_local", "lgd", "slug"}} (the seed's map, made offline from this file and LGD)."""
    import concurrent.futures
    from pypdf import PdfReader
    n = len(PdfReader(pdf).pages)
    pages = list(range(int(p.get("first", 1)), min(int(p.get("last", 1)), n) + 1))
    with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), os.cpu_count() or 1))) as ex:
        parts = list(ex.map(lambda pg: page_records(pdf, p, pg, use_ocr), pages))
    return [r for part in parts for r in part]


def page_records(pdf, p, pg, use_ocr=True):
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    known = p.get("bodies") or {}
    recs = []
    with tempfile.TemporaryDirectory() as tmp:
        rows = page_rows(reader, pdf, pg)
        boxes, unknown = [], {}
        for r in rows:
            for c in (5, 6):
                x0, x1 = r["cols"][c]
                boxes.append((x0, r["y0"], x1, r["y1"]))
            bt, bk = body_key(r["body_raw"])
            bk = map_key(r) if map_key(r) in known else bk
            if bk not in known and bk not in unknown:
                unknown[bk] = len(boxes)
                for c in (2, 3):
                    x0, x1 = r["cols"][c]
                    boxes.append((x0, r["y0"], x1, r["y1"]))
        texts = ocr_cells(pdf, pg, boxes, tmp) if use_ocr else [""] * len(boxes)
        i = 0
        for ri, r in enumerate(rows, 1):
            ward_name, name = fix_name(texts[i]), fix_name(texts[i + 1])
            i += 2
            bt, bk = body_key(r["body_raw"])
            bk = map_key(r) if map_key(r) in known else bk
            if bk in unknown and unknown[bk] == i:
                i += 2
            if bk in known:
                b = known[bk]
            else:
                j = unknown[bk]
                dist, full = texts[j], texts[j + 1]
                nm = re.sub(r"^\s*(नगर\s*पालिक\s*निगम|नगर\s*पालिका\s*परिषद्?|नगर\s*पंचायत|नगरपालिक\s*निगम|नगरपालिका\s*परिषद्?)\s*", "",
                            full)
                b = {"body": nm or full, "body_type": bt, "district_local": dist, "slug": f"k-{slug_of(nm or full)}"}
            if not r["ward_no"]:
                provenance.skip_row(r, 'skip: not r["ward_no"]')
                continue
            d = {"type": "councillor", "state": "CG", "body": b["body"], "body_local": b["body"],
                 "body_type": b.get("body_type") or bt, "district": b.get("district"),
                 "district_local": b.get("district_local"), "ward_no": r["ward_no"],
                 "ward_name": ward_name, "name": name, "party": party_of(r["party_raw"]) or None,
                 "party_text": r["party_raw"], "election": ELECTION, "url": p.get("url", URL), "page": pg,
                 "serial": r["serial"],
                 # source trail: data row on the page (1-based, top to bottom) and its box in PDF points (top-left origin)
                 "src_pos": {"page": pg, "row": ri, "box_pt": [round(r["cols"][1][0], 1), round(r["y0"], 1),
                                                               round(r["cols"][7][1], 1), round(r["y1"], 1)]},
                 "name_check": "ok" if subseq(key(r["name_raw"]), key(name)) else "differs from text layer"}
            if b.get("body_en"):
                d["body_en"] = b["body_en"]
            if b.get("lgd"):
                d["local_body_code"] = b["lgd"]
            if not b.get("body_en") and bk not in known:
                d["body_read_by_ocr"] = True
            d = {k2: v for k2, v in d.items() if v not in (None, "")}
            recs.append((f"councillor:CG:2025:{b['slug']}:{r['ward_no']}", d))
    return recs


def fetch(p, get):
    if not tools():
        return [], [], "tesseract not available"
    url = p.get("url", URL)
    content = stored(p, get)
    from_bucket = content is not None
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    k = hashlib.sha1(url.encode()).hexdigest()[:12]
    files = [(f"councillors/CG/{k}.pdf", content, "application/pdf")] if int(p.get("first", 1)) == 1 and not p.get("stored") \
        else []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, p)
    if from_bucket:
        mark_stored(recs, p, content, url)
    return recs, files, "" if recs else "no members read"
