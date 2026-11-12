"""Maharashtra: the Assistant Electoral Registration Officers (AEROs) of all 288 assembly constituencies, from the Election
Commission notification No. 429/MH/2025(2) of 18 March 2026 (Maharashtra Government Gazette, extraordinary part IV-C, 25 March
2026), "AERO for all AC in Maharashtra.pdf" on ceoelection.maharashtra.gov.in/Downloads/PDF/ (answers from Germany too).

The file is a 70-page scan (KONICA MINOLTA bizhub 361i, no text layer, 5.9 MB). One table: "No. & Name of Assembly Constituency"
| serial | "Assistant Electoral Registration Officer" (the post and its place: "Tahsildar, Akkalkuwa", "Block Development Officer,
Dhadgaon (Akrani)", "Naib Tahsildar (Election), Tahsildar Office, Shahada"). It names no persons and gives no phones: it is the
list of which taluka offices serve each assembly constituency (tahsildar, additional / naib tahsildar, BDO, taluka agriculture
officer, block education officer, municipal chief officer ...). In Mumbai the AEROs are special-purpose tahsildars and
municipal officers.

OCR (task "depts", project civic-officials-depts-open: GitHub runners, never this box and never the India servers): each item reads
10 pages. The PDF is read from the bucket when an earlier item saved it ("stored", via get.hub.read_urls), else fetched once from
the site and saved (depts/sub3_mh_aero/aero.pdf in the item's project). Each page: pdftoppm 300 dpi grey, Tesseract eng --psm 4
(column-aware; --psm 6 loses the table rows). Tesseract and poppler are installed by forms/blo2_ocr.tools() on a runner. The OCR
text of the item is saved next to the PDF (ocr-p<first>-<last>.txt.gz), so the rows can be read again without OCR.

parse(pages) reads the OCR text: a line "<AC no> – <AC name> [|] <serial> | <post, place>" starts a constituency; "<serial> |
<post, place>" adds an AERO; other lines continue the last AERO (wrapped cells). AC numbers must rise (1-288); OCR slips in the
post words are mended (Tabsildar -> Tahsildar). Records (posts of interest only, POSTS): dept, level, post (normal form), area
(the place: last part of the cell; the AC name when the cell names no place), designation (the whole cell), ac_no, ac_name,
serial, page, ocr true. No district in the source (join on ac_no). Record ids: dept:sub3_mh_aero:AC-<no>:<serial>.
"""
import concurrent.futures
import gzip
import os
import re
import subprocess
import tempfile

import provenance
from dforms import _esw

METHOD = "ocr tesseract eng (pdftoppm 300 dpi, psm 4, text lines)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub3_mh_aero"
URL = "https://ceoelection.maharashtra.gov.in/Downloads/PDF/AERO%20for%20all%20AC%20in%20Maharashtra.pdf"
PAGES, STEP = 70, 10
PDF_PATH = f"depts/{MODULE}/aero.pdf"
PROJECT = "civic-officials-depts-open"
TAH = r"t[ae][hb]?[a]?s[il1|]+[il1|]?d[ae]r"
# (post, dept, level, pattern on the cell); first match wins
POSTS = (("Naib Tahsildar", "revenue", "subdistrict", rf"\bnaib\s*{TAH}"),
         ("Additional Tahsildar", "revenue", "subdistrict", rf"\b(addl\.?|additional|add\.)\s*{TAH}"),
         ("Tahsildar", "revenue", "subdistrict", rf"\b{TAH}"),
         ("Block Development Officer", "rural_development", "block", r"\bblock\s*develop\w*\s*off\w*|\bb\.?\s*d\.?\s*o\b|group\s*develop\w*"),
         ("Taluka Agriculture Officer", "agriculture", "subdistrict", r"\btaluka\s*agri\w*\s*off\w*"),
         ("Block Education Officer", "education", "block", r"\bblock\s*educ\w*\s*off\w*"),
         ("Deputy Superintendent of Land Records", "revenue", "subdistrict", r"\bdeputy\s*super\w*\s*(of\s*)?land\s*rec\w*"),
         ("Sub-Divisional Officer", "administration", "subdivision", r"\bsub[\s-]*divisional\s*off\w*|\bs\.?\s*d\.?\s*o\b"))
AC = re.compile(r"^[\s|_“\"'.]*(\d{1,3})\s*[—–\-~=_]+\s*([A-Za-z][A-Za-z .()&'\-]*?)\s*(?:\(\s*(?:SC|ST)\s*\))?\s*"
                r"[|\]]?\s*(?:(\d{1,2})\s*[.,]?\s*[|\]!]?\s*(.*))?$")
ITEM = re.compile(r"^[\s|_“\"'.]*(\d{1,2})\s*[.,]?\s*[|\]!]\s*(.*)$|^[\s|_“\"'.]*(\d{1,2})\s{1,3}([A-Z][a-z].*)$")
SKIP = re.compile(r"(?i)no\.?\s*&\s*name|assembly\s*constitu|assistant\s*electoral\s*registration|^\s*1\s+2\s*$|^\s*[(\[]?\s*\d+\s*[)\]]?\s*$")


# pages whose 10-page items gave up three times (2026-11-12: p011, p021; no OCR text saved): three pages per item, each item
# starting on the last page of the one before it, so a constituency that runs over a page break is read whole in one of
# them (the same rows from two items have the same record ids)
RETRY = [(f, f + 2) for f in range(10, 30, 2)]


def items(get=None):
    out = []
    for first in range(1, PAGES + 1, STEP):
        last = min(PAGES, first + STEP - 1)
        out.append({"key": f"sub3_mh_aero-p{first:03d}", "payload": {
            "reader": MODULE, "url": URL, "state": "MH", "first": first, "last": last, "open": True, "ocr": True,
            "stored": f"{PROJECT}/{PDF_PATH}", "expected": 0}})
    for first, last in RETRY:
        out.append({"key": f"sub3_mh_aero-r{first:03d}-{last:03d}", "payload": {
            "reader": MODULE, "url": URL, "state": "MH", "first": first, "last": last, "open": True, "ocr": True,
            "stored": f"{PROJECT}/{PDF_PATH}", "expected": 0}})
    return out


# ---------------------------------------------------------------- the OCR text -> rows

def _clean_cell(s):
    s = _esw.clean(s)
    s = re.sub(r"^[|_\]!\s]+|[|_\s]+$", "", s)
    return re.sub(r"\s*\|\s*", " ", s).strip(" .:;")


def parse(pages):
    """pages: [(page number, OCR text)] -> [{ac_no, ac_name, serial, cell, page}] in list order."""
    rows, ac, last_ac = [], None, 0
    for page, text in pages:
        cont = False        # a page starts with the gazette's running head (Marathi read as Latin): no continuation before a row
        for n, ln in enumerate((text or "").splitlines(), 1):
            if not ln.strip() or SKIP.search(ln) or re.search(r"[^\x00-\x7f]{3}", ln) and not re.search(r"[A-Za-z]{4}", ln):
                continue
            m = AC.match(ln)
            if m and last_ac < int(m.group(1)) <= 288 and re.search(r"[A-Za-z]{3}", m.group(2) or ""):
                ac = {"ac_no": int(m.group(1)), "ac_name": _esw.clean(m.group(2)).strip(" -|")}
                last_ac = ac["ac_no"]
                if m.group(3):
                    rows.append({**ac, "serial": int(m.group(3)), "cell": _clean_cell(m.group(4) or ""), "page": page,
                                 "pos": provenance.line_pos(page, n, ln)})
                    cont = True
                continue
            if ac is None:
                continue
            m = ITEM.match(ln)
            if m:
                serial, cell = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
                prev = [r["serial"] for r in rows if r["ac_no"] == ac["ac_no"]]
                if not prev or int(serial) == prev[-1] + 1 or int(serial) not in prev and int(serial) <= 30:
                    rows.append({**ac, "serial": int(serial), "cell": _clean_cell(cell), "page": page,
                                 "pos": provenance.line_pos(page, n, ln)})
                    cont = True
                    continue
            if cont and rows and rows[-1]["ac_no"] == ac["ac_no"]:
                rows[-1]["cell"] = _clean_cell(rows[-1]["cell"] + " " + ln)
                if rows[-1].get("pos") and rows[-1]["pos"]["page"] == page:
                    rows[-1]["pos"]["line_end"] = n           # the cell wraps down to this line
    return rows


def post_of(cell):
    for post, dept, level, rx in POSTS:
        if re.search(rx, cell, re.I):
            return post, dept, level, rx
    return None


def place_of(cell, rx, ac_name):
    """The place the cell names: the last comma part after the post ("Tahsildar, Akkalkuwa" -> Akkalkuwa; "Naib Tahsildar
    (Election), Tahsildar Office, Shahada" -> Shahada; "Block Development Officer, Panchayat Samiti, Dhule" -> Dhule); the AC
    name when the last part is not a place (an office, a branch, an authority, an address)."""
    m = re.search(rx, cell, re.I)
    rest = cell[m.end():] if m else cell
    parts = [p.strip(" .-()") for p in re.split(r",", rest) if p.strip(" .-()")]
    for p in reversed(parts):
        p = re.sub(r"(?i)^(panchayat\s*samiti|tahsil\s*office|tahsildar\s*office|municipal\s*council|zilla\s*parishad|z\.?\s*p\.?)\s*", "", p)
        p = re.sub(r"\s*[-–]?\s*\d{3}\s?\d{3}\s*$", "", p).strip(" .-")
        if p and len(p) < 40 and not re.search(r"(?i)\b(office|branch|authority|road|ward|dept|department|election|"
                                                 r"m\.?\s*m\.?\s*r\.?\s*d\.?\s*a|slum|competent|land|estate|sector|bmc|mcgm|"
                                                 r"corporation|division|n\.?\s*a\.?)\b|\d", p):
            return p.title() if p.isupper() else p
    return ac_name.title() if ac_name.isupper() else ac_name


def fix_ocr(cell):
    """Common OCR slips in the post words: Tabsildar / Tahsi1dar -> Tahsildar."""
    cell = re.sub(rf"(?i)\b{TAH}\b", "Tahsildar", cell)
    return re.sub(r"(?i)\bAgricultural\b", "Agriculture", cell)


def build(rows, source):
    recs, seen = [], set()
    for r in rows:
        cell = fix_ocr(r["cell"])
        found = post_of(cell)
        if not found:
            continue
        post, dept, level, rx = found
        rid = f"AC-{r['ac_no']}:{r['serial']}"
        if rid in seen:
            continue
        seen.add(rid)
        recs.append(_esw.record(MODULE, rid, dept=dept, level=level, area=place_of(cell, rx, r["ac_name"]), post=post,
                                designation=cell, state="MH", ac_no=r["ac_no"], ac_name=r["ac_name"], serial=r["serial"],
                                page=r["page"], ocr=True, office_id=f"MH-AERO-AC-{r['ac_no']}-{r['serial']}",
                                last_updated="2026-03-18", source=source, src_pos=r.get("pos")))
    return recs


# ---------------------------------------------------------------- the PDF and the OCR (GitHub runners only)

def stored(p, get):
    """(bytes, key) of the saved PDF, or None. The hub's signed url is read directly (the copy is in the bucket already);
    the records name it in src (provenance.file_src)."""
    hub, k = getattr(get, "hub", None), p.get("stored")
    own = os.environ.get("SCRAPE_POOL_PROJECT")
    keys = [k] if k else []
    if own:
        keys.append(f"{own}/{PDF_PATH}")
    if not hub:
        return None
    import requests
    for key in keys:
        try:
            url = hub.read_urls(key.split("/", 1)[0], [key]).get(key)
            if not url:
                continue
            r = requests.get(url, timeout=(20, 180))
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content, key
        except Exception:  # noqa: BLE001 - try the next copy, then the site
            continue
    return None


def ocr_page(pdf, page, tmp):
    """OCR text of one page. Tesseract runs single-threaded (OMP_THREAD_LIMIT=1: the pages already run in parallel; nested
    OpenMP threads made pages 11-30 run past the time limit on 2026-11-12). A page that takes longer than 300 s is read again
    at 200 dpi with --psm 6; when that fails too the page gives "" (its rows are missing, the rest of the item is kept)."""
    env = {**os.environ, "OMP_THREAD_LIMIT": "1"}
    for dpi, psm, limit in (("300", "4", 300), ("200", "6", 240)):
        base = os.path.join(tmp, f"p{page}-{dpi}")
        try:
            subprocess.run(["pdftoppm", "-r", dpi, "-gray", "-png", "-singlefile", "-f", str(page), "-l", str(page), pdf, base],
                           capture_output=True, timeout=300)
            r = subprocess.run(["tesseract", base + ".png", "-", "-l", "eng", "--psm", psm], capture_output=True, text=True,
                               timeout=limit, env=env)
            return r.stdout
        except subprocess.TimeoutExpired:
            continue
    return ""


def fetch(p, get):
    from forms.blo2_ocr import tools
    if not tools("eng"):
        return [], [], "tesseract eng not available"
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
    files.append((f"depts/{MODULE}/ocr-p{first:03d}-{last:03d}.txt.gz", gzip.compress(raw.encode("utf-8")), "application/gzip"))
    # a constituency that starts on the page before this item's first page: its rows here are read from the next AC line on
    recs = build(parse(texts), (p.get("url") or URL))
    for _, d in recs:          # src_pos = page + line of the OCR text (saved too: pages_of() reads it back)
        d["src_url"] = p.get("url") or URL
        if key:
            d["src"] = provenance.file_src(content, d["src_url"], key)
    return recs, files, "" if recs else f"no rows (ocr {sum(len(t) for _, t in texts)} chars)"


def pages_of(raw):
    """The saved OCR text (ocr-p<first>-<last>.txt.gz, unzipped) -> [(page, text)], to read it again without OCR."""
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"### page (\d+)\n(.*?)(?=\f### page |\Z)", raw, re.S)]
