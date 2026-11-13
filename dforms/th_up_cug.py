"""Uttar Pradesh: the CUG mobiles of the heads of all town bodies, from the Directorate of Local Bodies' list
http://localbodies.up.nic.in/pdf/ulb-cug2005.pdf ("सी0यू0जी0 नं0"; 16 scanned pages, 4.6 MB, no text layer; PDF made 2021-03-19;
linked from the directorate's download pages; the archive holds a copy of 2026-11-05, vantage pool: it answers from abroad).

Page 1 starts with the 17 posts "नगर आयुक्त, <city>" (municipal commissioners: serial | post | CUG). Then "नगर निकाय": serial |
मण्डल (division, only on the first row of each division) | जनपद (district) | निकाय का नाम (body) | निकाय के प्रकार (न0पं0 = नगर
पंचायत, न0पा0प0 = नगर पालिका परिषद) | सी0यू0जी0 नं0. The CUG numbers run in one series (8189077813 ...). The list names no
persons: the CUG phone belongs to the post (Executive Officer of the body, नगर आयुक्त of a corporation) and reaches whoever holds
it. Records: post "Executive Officer" (अधिशासी अधिकारी; "Municipal Commissioner" for the corporations), name empty, phone = the
CUG, post_from "directory", cug true, list_date 2021-03-19 (the PDF's creation date).

OCR (task "depts", GitHub runners only: never this box): pdftoppm 300 dpi grey, Tesseract hin+eng --psm 6, pages in parallel
(OMP_THREAD_LIMIT=1). The PDF is read from the bucket when an earlier item saved it ("stored"), else fetched once and saved
(depts/th_up_cug/cug.pdf); the OCR text of each item is saved too (ocr-p<first>-<last>.txt.gz).

parse(): a line whose last number is a 10-digit mobile and that starts with a serial is a row. Its middle words are split into
district and body by the best match against dforms/ulb_up_lgd.json (district|body|type, Hindi, as the Directorate's 2023 lists
write them; difflib similarity, OCR slips tolerated; a leading division word is skipped). lgd_code only when the body matches
with similarity >= 0.75 inside a district that matches >= 0.75; the row is kept without a code otherwise. src_pos = page + line
of the OCR text + the OCR line.
The test fixture tests/data/th_up_cug_p02.txt is page 2 TYPED BY HAND from the page image (2026-11-13), in the shape of Tesseract
psm 6 output: it tests the row reader, not the OCR.
"""
import concurrent.futures
import difflib
import gzip
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import provenance
from dforms import _esw, _ulb

METHOD = "ocr tesseract hin+eng (pdftoppm 300 dpi, psm 6, text lines) + name match to ulb_up_lgd.json"

MODULE = "th_up_cug"
STATE = "UP"
URL = "http://localbodies.up.nic.in/pdf/ulb-cug2005.pdf"
PAGES, STEP = 16, 4
PDF_PATH = f"depts/{MODULE}/cug.pdf"
PROJECT = "civic-officials-depts-open"
LIST_DATE = "2021-03-19"
CODES = json.loads((Path(__file__).with_name("ulb_up_lgd.json")).read_text(encoding="utf-8"))["codes"]
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
MOBILE = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")
SERIAL = re.compile(r"^[\s|_.'\"“]*(\d{1,3})[\s|.,)\]]+(.*)$")
COMMR = re.compile(r"नगर\s*आयुक्त\s*[,،.]?\s*(.+)$")


def items(get=None):
    out = []
    for first in range(1, PAGES + 1, STEP):
        out.append({"key": f"{MODULE}-p{first:02d}", "payload": {
            "reader": MODULE, "url": URL, "state": STATE, "first": first, "last": min(PAGES, first + STEP - 1), "open": True,
            "ocr": True, "stored": f"{PROJECT}/{PDF_PATH}", "india_only": False, "expected": 0}})
    return out


# ---------------------------------------------------------------- names -> LGD

def _n(s):
    return re.sub(r"[\s.\-‐–—0०]+", "", s or "")


DISTS = sorted({k.split("|")[0] for k in CODES})


def btype(word):
    w = (word or "").replace("०", "0")
    if re.search(r"पा", w):
        return "नगर पालिका परिषद"
    if re.search(r"पं|प[ंं]?0?$", w):
        return "नगर पंचायत"
    return None


def best_split(words, kind):
    """(district, body, code, district score, body score) for the middle words of a row."""
    best = (None, " ".join(words), None, 0.0, 0.0)
    for skip in (0, 1):
        ws = words[skip:]
        for i in range(1, len(ws)):
            d, b = " ".join(ws[:i]), " ".join(ws[i:])
            ds, dist = max((difflib.SequenceMatcher(None, _n(d), _n(x)).ratio(), x) for x in DISTS)
            if ds < 0.75:
                continue
            cands = [(k, v) for k, v in CODES.items() if k.startswith(dist + "|") and (not kind or k.endswith("|" + kind))]
            if not cands:
                continue
            bs, (k, code) = max((difflib.SequenceMatcher(None, _n(b), _n(k.split("|")[1])).ratio(), (k, v)) for k, v in cands)
            if ds + bs > best[3] + best[4]:
                best = (d, b, code if bs >= 0.75 else None, ds, bs)
    return best


# ---------------------------------------------------------------- OCR text -> rows

def parse(pages):
    """pages: [(page number, OCR text)] -> [dict(serial, kind, district, body, body_type, cug, code, pos)]."""
    out = []
    for pg, text in pages:
        for ln, raw in enumerate(text.splitlines(), 1):
            line = raw.translate(DIGITS)
            mobs = MOBILE.findall(line)
            m = SERIAL.match(line)
            if not mobs or not m:
                provenance.skip_line(raw, 'skip: not mobs or not m')
                continue
            mid = MOBILE.sub(" ", m.group(2))
            mid = re.sub(r"[|_\[\]{}“”\"']", " ", mid).strip()
            pos = provenance.line_pos(pg, ln, raw)
            c = COMMR.search(mid)
            if c:
                city = _esw.clean(c.group(1))
                nn = [(difflib.SequenceMatcher(None, _n(city), _n(k.split("|")[1])).ratio(), k, v) for k, v in CODES.items()
                      if k.endswith("|नगर निगम")]
                bs, k, code = max(nn) if nn else (0, None, None)
                out.append({"serial": m.group(1), "kind": "commissioner", "district": k.split("|")[0] if bs >= 0.75 else None,
                            "body": city, "body_type": "नगर निगम", "cug": mobs[-1], "code": code if bs >= 0.75 else None,
                            "match": round(bs, 2), "pos": pos})
                continue
            words = mid.split()
            kind = btype(words[-1]) if words else None
            if kind:
                words = words[:-1]
            if not words:
                provenance.skip_line(raw, 'skip: not words')
                continue
            dist, body, code, ds, bs = best_split(words, kind)
            out.append({"serial": m.group(1), "kind": "body", "district": dist, "body": _esw.clean(body), "body_type": kind,
                        "cug": mobs[-1], "code": code, "match": round(bs, 2) if bs else None, "pos": pos})
    return out


def build(rows, url=URL):
    recs, seen = [], set()
    for r in rows:
        post = "Municipal Commissioner" if r["kind"] == "commissioner" else "Executive Officer"
        recs.append(_ulb.record(MODULE, STATE, r["body"], post, seen, phone=r["cug"], district=r["district"],
                                body_type=r["body_type"], source=url, latin=r["code"] or f"{r['kind']}-{r['serial']}",
                                lgd_code=r["code"], name_match=r.get("match"), serial=r["serial"], cug=True,
                                post_from="directory", list_date=LIST_DATE, page=url, ocr=True, src_pos=r["pos"]))
    return recs


# ---------------------------------------------------------------- fetch (runners)

def stored(p, get):
    hub, k = getattr(get, "hub", None), p.get("stored")
    if not hub or not k:
        return None
    import requests
    try:
        url = hub.read_urls(k.split("/", 1)[0], [k]).get(k)
        if url:
            r = requests.get(url, timeout=(20, 180))
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content, k
    except Exception:  # noqa: BLE001 - fall back to the site
        pass
    return None


def ocr_page(pdf, page, tmp):
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
    base = os.path.join(tmp, f"p{page}")
    try:
        subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", "-singlefile", "-f", str(page), "-l", str(page), pdf, base],
                       capture_output=True, timeout=300)
        r = subprocess.run(["tesseract", base + ".png", "-", "-l", "hin+eng", "--psm", "6"], capture_output=True, text=True,
                           timeout=400, env=env)
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""


def fetch(p, get):
    from forms.blo2_ocr import tools
    if not tools("hin+eng"):
        return [], [], "tesseract hin+eng not available"
    files = []
    got = stored(p, get)
    content, key = got if got else (None, None)
    if content is None:
        r = get(p.get("url") or URL)
        if r is None:
            return [], [], "no answer"
        if r.content[:5] != b"%PDF-":
            return [], [], "not a PDF"
        content = r.content
        files.append((PDF_PATH, content, "application/pdf"))
    first, last = int(p.get("first", 1)), int(p.get("last", PAGES))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "a.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        pages = list(range(first, last + 1))
        with concurrent.futures.ThreadPoolExecutor(max(1, os.cpu_count() or 1)) as ex:
            texts = list(zip(pages, ex.map(lambda pg: ocr_page(pdf, pg, tmp), pages)))
    raw = "".join(f"\f### page {pg}\n{t}" for pg, t in texts)
    files.append((f"depts/{MODULE}/ocr-p{first:02d}-{last:02d}.txt.gz", gzip.compress(raw.encode("utf-8")), "application/gzip"))
    recs = build(parse(texts), p.get("url") or URL)
    for _, d in recs:
        d["src_url"] = p.get("url") or URL
        if key:
            d["src"] = provenance.file_src(content, d["src_url"], key)
    return recs, files, "" if recs else f"no rows (ocr {sum(len(t) for _, t in texts)} chars)"
