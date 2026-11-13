"""Punjab: members of the Zila Parishads and Panchayat Samitis elected on 14.12.2025, from the State Election Commission page
"Result Notification of Zila Parishads and Panchayat Samiti Elections 2025"
https://sec.punjab.gov.in/en/panchayat-samitis-zila-parishads-2025/result-notification-of-zila-parishads-and-panchayat-samiti-elections-2025/
It links one gazette PDF per district and level: Final_Gazette_Report-ZP_<district>.pdf (22) and Final_Gazette_Report-PS_<district>.pdf
(21; SAS Nagar has PS only, Final_Gazette_Report.pdf is a further file). Punjab Govt. Gazette (extra) of 31 December 2025,
notification No. SEC/SAP/ZP-PS/2025/755. The pages are "Microsoft: Print To PDF" images (the tables have no text layer):
English table rows "S.No | Panchayat Samiti | Zone (no) | NAME (PARTY) | category", e.g. "21 | Doraha | Dhamot Kalan (1) |
KIRANPREET KAUR (AAP) | SC (W)". The archive copies (2026-11-05) are cut short (15-32 KB): fetch the files again.
sec.punjab.gov.in: only Indian captures in the archive (abroad not checked): the save step runs direct (India).

Two steps (fetch once, process anywhere):
  {"step": "save"}: GET the PDF and keep it in the bucket (pri/PB/<file name>), one source_file record. Route direct.
  {"step": "ocr", "stored": "<project>/pri/PB/<file>"}: read the bucket copy (hub.read_urls; else the site), pdftoppm 300 dpi
      grey + Tesseract eng --psm 6 per page (GitHub runners only, never this server), keep the OCR text
      (pri/PB/ocr-<file>.txt.gz), parse rows. Route abroad (runners, no proxy).
Rows: a line "<serial> <samiti> <zone> (<zone no>) <NAME> (<PARTY>) <category>". The samiti is the longest samiti name of the
district (payload "samitis", LGD names, plus the names seen in earlier rows) that starts the text; else the first word. ZP files:
the zone is everything between the serial and "(<no>)". Records (dforms/_pri.py): level zp / ps, role member, post "Member, Zila
Parishad" / "Member, Panchayat Samiti", name, party, category, zone (ward), ward_no, body_name (district for ZP, samiti for PS).
Ids: pri:pri_pb:<district slug>:zp:<zone no>-<zone slug> | ...:ps-<samiti slug>:<zone no>-<zone slug>.
"""
import concurrent.futures
import gzip
import os
import re
import subprocess
import tempfile

import provenance
from dforms import _pri

METHOD = "ocr tesseract eng (pdftoppm 300 dpi grey, psm 6, text lines; table rows by pattern)"

MODULE = "pri_pb"
PAGE = ("https://sec.punjab.gov.in/en/panchayat-samitis-zila-parishads-2025/"
        "result-notification-of-zila-parishads-and-panchayat-samiti-elections-2025/")
ELECTION = "Punjab Zila Parishad and Panchayat Samiti General Elections 2025"
SAVE_PROJECT = "civic-officials-depts-direct"
ROW = re.compile(r"^\s*[|(\[]?\s*(\d{1,4})\s*[|.,)\]]?\s+(.+?)\s*[(\[{]\s*(\d{1,3})\s*[)\]}]\s*[|]?\s*(.+?)\s*[(\[{]\s*([A-Za-z.\- ]{2,12})\s*[)\]}]"
                 r"\s*[|]?\s*(.*?)\s*$")
CATEGORY = re.compile(r"^(SC|ST|BC|Gen\.?|General|W|SC\s*\(W\)|BC\s*\(W\)|ST\s*\(W\)|Gen\.?\s*\(W\))", re.I)


def file_name(url):
    return re.sub(r"[^A-Za-z0-9_.-]", "", url.rsplit("/", 1)[-1])


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def split_samiti(text, samitis):
    """(samiti, zone) from "Doraha Dhamot Kalan": the longest known samiti name that starts the text, else the first word."""
    t = _pri.clean(text.strip("| "))
    best = None
    for s in samitis or []:
        n = len(s)
        if norm(t[:n + 2]).startswith(norm(s)) and (best is None or len(s) > len(best)):
            best = s
    if best:
        k, out = 0, 0
        target = norm(best)      # cut after as many characters of t as the samiti name has letters/digits
        for i, ch in enumerate(t):
            if norm(ch):
                k += 1
            if k == len(target):
                out = i + 1
                break
        return t[:out].strip(), t[out:].strip(" -|")
    parts = t.split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def parse(pages, p):
    """[(row dict)] from the OCR text of each page: {"serial", "samiti", "zone", "zone_no", "name", "party", "category", pos}."""
    level = p.get("level", "ps")
    known = list(p.get("samitis") or [])
    rows = []
    for pg, text in pages:
        for ln, line in enumerate(text.split("\n"), 1):
            m = ROW.match(line.replace("—", "-"))
            if not m:
                continue
            serial, head, zno, name, party, cat = m.groups()
            if level == "ps":
                samiti, zone = split_samiti(head, known)
                if samiti and samiti not in known:
                    known.append(samiti)
            else:
                samiti, zone = "", _pri.clean(head.strip("| "))
            rows.append({"serial": serial, "samiti": samiti, "zone": zone, "zone_no": zno, "name": _pri.clean(name.strip("| ")),
                         "party": party.strip().upper(), "category": _pri.clean(cat.strip("| ")),
                         "pos": provenance.line_pos(pg, ln, line)})
    return rows


def build(rows, p, src_url):
    level = p.get("level", "ps")
    dsl = _pri.slug(p["district"])
    recs, seen = [], {}
    for r in rows:
        if not r["name"]:
            continue
        body = p["district"] if level == "zp" else r["samiti"]
        key = f"{dsl}:{'zp' if level == 'zp' else 'ps-' + _pri.slug(r['samiti'])}:{r['zone_no']}-{_pri.slug(r['zone'])}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key += f"-{seen[key]}"
        recs.append(_pri.record(
            MODULE, key, state="PB", level=level, role="member",
            post="Member, Zila Parishad" if level == "zp" else "Member, Panchayat Samiti",
            post_regional="ਮੈਂਬਰ, ਜ਼ਿਲ੍ਹਾ ਪ੍ਰੀਸ਼ਦ" if level == "zp" else "ਮੈਂਬਰ, ਪੰਚਾਇਤ ਸੰਮਤੀ",
            name=r["name"], party=r["party"], seat_category=r["category"], ward=r["zone"], ward_no=r["zone_no"],
            constituency=f"{r['zone']} ({r['zone_no']})", body_name=body, district=p["district"],
            block=r["samiti"] if level == "ps" else None, serial=r["serial"], status="won", ocr=True,
            election=ELECTION, election_year=2025, result_date="2025-12-30", source=p["url"], src_url=src_url,
            src_pos=r["pos"]))
    return recs


# ---------------------------------------------------------------- the PDF and the OCR (GitHub runners only)

def stored(p, get):
    """(bytes, key) of the bucket copy, or None."""
    hub, key = getattr(get, "hub", None), p.get("stored")
    if not hub or not key:
        return None
    import requests
    try:
        url = hub.read_urls(key.split("/", 1)[0], [key]).get(key)
        if url:
            r = requests.get(url, timeout=(20, 180))
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content, key
    except Exception:  # noqa: BLE001 - then the site
        return None
    return None


def ocr_page(pdf, page, tmp):
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
    base = os.path.join(tmp, f"p{page}")
    try:
        subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", "-singlefile", "-f", str(page), "-l", str(page), pdf, base],
                       capture_output=True, timeout=300)
        return subprocess.run(["tesseract", base + ".png", "-", "-l", "eng", "--psm", "6"], capture_output=True, text=True,
                              timeout=300, env=env).stdout
    except subprocess.TimeoutExpired:
        return ""


def fetch(p, get):
    name = file_name(p["url"])
    if p.get("step") == "save":
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        if r.content[:5] != b"%PDF-":
            return [], [], "not a PDF"
        path = f"pri/PB/{name}"
        rec = (f"pri:{MODULE}:{_pri.slug(p['district'])}:{p['level']}:file", {
            "type": "source_file", "state": "PB", "level": p["level"], "district": p["district"], "url": p["url"],
            "stored": path, "size": len(r.content), "ocr_needed": True, **provenance.at(r, p["url"])})
        return [rec], [(path, r.content, "application/pdf")], ""
    from forms.blo2_ocr import tools
    if not tools("eng"):
        return [], [], "tesseract eng not available"
    files = []
    got = stored(p, get)
    content, key = got if got else (None, None)
    if content is None:
        r = get(p["url"])
        if r is None or r.content[:5] != b"%PDF-":
            return [], [], "no copy in the bucket and the site gave no PDF"
        content = r.content
        files.append((f"pri/PB/{name}", content, "application/pdf"))
    from pypdf import PdfReader
    import io
    n = len(PdfReader(io.BytesIO(content)).pages)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "a.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        with concurrent.futures.ThreadPoolExecutor(max(1, os.cpu_count() or 1)) as ex:
            texts = list(zip(range(1, n + 1), ex.map(lambda pg: ocr_page(pdf, pg, tmp), range(1, n + 1))))
    raw = "".join(f"\f### page {pg}\n{t}" for pg, t in texts)
    files.append((f"pri/PB/ocr-{name}.txt.gz", gzip.compress(raw.encode("utf-8")), "application/gzip"))
    recs = build(parse(texts, p), p, p["url"])
    for _, d in recs:
        if key:
            d["src"] = provenance.file_src(content, p["url"], key)
    return recs, files, "" if recs else f"no rows (ocr {sum(len(t) for _, t in texts)} chars)"
