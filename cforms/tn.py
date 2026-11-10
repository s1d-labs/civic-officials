"""Tamil Nadu urban local body results 2022 (tnsec.tn.gov.in, ulbe2022/{corp|mun|tp}_{district}.pdf), read by OCR.

The PDFs use a legacy font: their text layer keeps the table (ward number, candidates, votes, result) but drops some Tamil letters
in names. So each page is read twice: pdftotext gives the structure, Tesseract (tam+eng, 300 dpi, grey) gives the names, the
party and the body name; the two are paired by the winner's vote count, which both readings give the same.
One queue item = one PDF and a page range (payload first, last). Runs on GitHub runners through an Indian proxy (the site answers
only from India); Tesseract and poppler are installed with sudo when missing.
"""
import concurrent.futures
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

WIN_TEXT = ("ெவற்ற", "வெற்றி")           # "won" in the text layer (legacy glyph order) and in OCR
GENDER = re.compile(r"^(பெண்|பெ[ணன]்?|ஆ[ணனஸ]்?|ஆனன்|ஆன்|திருநங்கை)$")   # with common OCR slips (ஆன், ஆஸ், ஆனன்)
PARTY = {"தி.மு.க": "DMK", "அ.இ.அ.தி.மு.க": "AIADMK", "பா.ஜ.க": "BJP", "இ.தே.கா": "INC", "சுயேட்சை": "Independent",
         "ம.தி.மு.க": "MDMK", "வி.சி.க": "VCK", "பா.ம.க": "PMK", "தே.மு.தி.க": "DMDK", "நா.த.க": "NTK", "அ.ம.மு.க": "AMMK",
         "இ.கம்யூ": "CPI", "மா.கம்யூ": "CPI(M)", "இ.யூ.மு.லீ": "IUML", "ம.நீ.ம": "MNM", "வேட்பாளர்": "Independent"}
BODY_TYPE = {"corp": "மாநகராட்சி", "mun": "நகராட்சி", "tp": "பேரூராட்சி"}


def tools():
    """Tesseract with Tamil and poppler; installs them on a GitHub runner (sudo without password)."""
    if shutil.which("tesseract") and shutil.which("pdftoppm"):
        return True
    cmd = "sudo -n apt-get update -q && sudo -n apt-get install -y -q tesseract-ocr tesseract-ocr-tam poppler-utils"
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0 and bool(shutil.which("tesseract"))


def text_layer(pdf, page):
    return subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), pdf, "-"], capture_output=True,
                          text=True).stdout


def ocr(pdf, page, tmp):
    base = os.path.join(tmp, f"p{page}")
    subprocess.run(["pdftoppm", "-r", "300", "-gray", "-f", str(page), "-l", str(page), "-singlefile", "-png", pdf, base],
                   capture_output=True)
    # Tamil model only: with eng added, some Tamil names come out as Latin letters
    r = subprocess.run(["tesseract", base + ".png", "-", "-l", "tam", "--psm", "4"], capture_output=True, text=True)
    return r.stdout


def norm(s):
    return " ".join((s or "").replace("‌", "").replace("‍", "").split())


def layer_wards(text):
    """Text layer: [(ward no, winner votes, all votes)] in page order."""
    out, cur = [], None
    for ln in text.splitlines():
        m = re.search(r"எண்\s*:\s*(\d+)", ln)
        if m and ":" in ln.split("எண்")[0]:
            cur = {"ward": m.group(1), "rows": []}
            out.append(cur)
            continue
        m = re.match(r"^\s*(\d+)\s+.+?\s(\d+)\s+(\d+\.\d+)\s*(\S*)\s*$", ln)
        if m and cur is not None:
            cur["rows"].append((int(m.group(2)), any(w in ln for w in WIN_TEXT)))
    res = []
    for w in out:
        if not w["rows"]:
            continue
        won = [v for v, flag in w["rows"] if flag] or [max(v for v, _ in w["rows"])]
        res.append((w["ward"], won[0], [v for v, _ in w["rows"]]))
    return res


def ocr_parts(text):
    """OCR: headers [(position, body, ward, reservation)] and winner lines [(position, name, father, party, votes)]."""
    heads, wins = [], []
    for i, ln in enumerate(norm(x) for x in text.splitlines()):
        m = re.search(r"ராட்சி\s*:\s*(.+?)\s+வா\S*\s+\S+\s*:?\s*(\d+)\s*(?:\[(.*?)\]?)?$", ln)
        if m:
            heads.append((i, m.group(1).strip(" :"), m.group(2), (m.group(3) or "").strip()))
            continue
        if "வெற்றி" in ln:
            toks = ln.split()
            vi = next((j for j in range(len(toks) - 1, -1, -1) if re.fullmatch(r"\d+", toks[j]) and j + 1 < len(toks)
                       and re.fullmatch(r"\d+\.\d+", toks[j + 1])), None)
            if vi is None:
                continue
            gi = next((j for j, t in enumerate(toks) if GENDER.match(t)), None)
            start = 1 if toks and re.fullmatch(r"\d+", toks[0]) else 0
            name = " ".join(toks[start:gi]) if gi else " ".join(toks[start:vi - 1])
            party = toks[vi - 1]
            father = " ".join(toks[gi + 1:vi - 1]) if gi is not None else ""
            wins.append((i, name, father, party, int(toks[vi])))
    return heads, wins


def page_records(p, page, layer, text):
    wards = layer_wards(layer)
    heads, wins = ocr_parts(text)
    recs, used = [], set()
    for k, (ward, votes, _) in enumerate(wards):
        cand = [w for w in wins if w[4] == votes and w[0] not in used]
        if not cand:
            continue
        w = cand[0]
        used.add(w[0])
        head = next((h for h in reversed(heads) if h[0] < w[0]), None)
        body = head[1] if head else ""
        rec = {"type": "councillor", "state": "TN", "body_local": body, "body": body, "body_type": BODY_TYPE.get(p.get("type"), ""),
               "district": p.get("district"), "ward_no": ward, "reservation": head[3] if head else "",
               "name": w[1], "father_or_husband": w[2], "party_local": w[3], "party": PARTY.get(w[3].rstrip("."), w[3]),
               "votes": votes, "election": "Tamil Nadu 2022", "url": p["url"], "page": page, "read": "ocr+text layer"}
        recs.append(rec)
    return recs


def fetch(p, get):
    if not tools():
        return [], [], "tesseract not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    files = [(f"councillors/TN/{key}.pdf", r.content, "application/pdf")] if int(p.get("first", 1)) == 1 else []
    recs = []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(r.content)
        pages = list(range(int(p.get("first", 1)), int(p.get("last", 1)) + 1))
        with concurrent.futures.ThreadPoolExecutor(max(1, os.cpu_count() or 1)) as ex:
            texts = dict(zip(pages, ex.map(lambda pg: (text_layer(pdf, pg), ocr(pdf, pg, tmp)), pages)))
        for pg in pages:
            layer, text = texts[pg]
            for rec in page_records(p, pg, layer, text):
                slug = re.sub(r"\s+", "-", rec["body"])[:40] or f"{p.get('type')}-{p.get('district_code')}-p{pg}"
                recs.append((f"councillor:TN:{p.get('type')}-{p.get('district_code')}:{slug}:{rec['ward_no']}", rec))
    return recs, files, "" if recs else "no winners read"
