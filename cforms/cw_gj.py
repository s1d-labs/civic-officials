"""Gujarat: result gazettes that seeds/ocr_councillors_gj.json (April 2026 general election, cforms/gj.py) does not list.

Missing in 2026-11 (74 bodies): the 68 municipalities and Junagadh Municipal Corporation elected on 16 Feb 2025 (term to 2030),
Gandhinagar Municipal Corporation and Thara (new nagarpalika) elected on 11 Oct 2026 (counting 13 Oct 2026; SEC press note
Portal/News/2590_1_Result Akhbari yadi 13-10-2026.pdf: Gandhinagar 44 seats, Banas Kantha nagarpalika 24 seats), and Saputara
(a notified area: no elected council).
The SEC (sec.gujarat.gov.in, India only) publishes each election's results as Gazette Extraordinary Part IV-C PDFs with the
same ruled six-column table as 2026, linked from result pages (result-muncipality-2026.htm, result-nagarpalika-2026.htm,
election-oct-2026 ...). The 2025 file names are not known (result-nagarpalika-2025.htm answers 302) and the SEC's own result
portal sec-poll.gujarat.gov.in asks for a captcha (not used). So items(get) runs through the hub: it reads the SEC's start
pages, follows the result pages they link, keeps the result PDFs that the gj seed does not have, reads each PDF's first page
for the year (2025 or 2026) and returns OCR items of 6 pages (kind form-cw_gj). The first item of a file saves the PDF; the
others read the saved copy (payload "stored", as in cforms/tn.py).
fetch() is gj.parse() (grid from drawn borders, Tesseract guj for names and body titles) with the election label of the item.
Record id councillor:GJ:<file slug>-<body hash>:<ward>-<seat>.

February 2025 (found 2026-11-12): the results are in the Gujarat Government Gazette itself, egazette.gujarat.gov.in
(GazettesSearch.aspx: an ASP.NET search by date, no captcha; files ViewPdf2.aspx?docid=...&cdbid=..., a plain GET). Searched
18-24 Feb 2025, Government Central Press, Extraordinary: 30 "Part IV-C Extra" notices, Extra No. 89-118 (No. 89, 18 pp: Junagadh
Municipal Corporation 60 seats, then the Junagadh district nagarpalikas). Same six-column table as 2026: gj.parse reads them
unchanged (text-layer check of No. 89: 236 rows, every key unique). Two seed files, made from that search:
- seeds/ocr_councillors_gj25_save.json: payload "save_only": one request through an Indian proxy, the PDF goes to the bucket, no
  OCR and no records (the proxy is not held during OCR).
- seeds/stored_councillors_gj25.json: the OCR items (whole notice, pages 1-200, clamped to the file), payload "stored" = the
  saved copy, for GitHub runners without a proxy (project -ocr-b). Queue them after the save items are done.
"""
import hashlib
import io
import json
import os
import pathlib
import re
import tempfile
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from cforms import gj, tn

METHOD = gj.METHOD     # source trail: the items read with cforms/gj.py parse() (seed step: html pages)     # source trail (provenance.py): how this reader reads its sources

BASE = "https://sec.gujarat.gov.in/"
START = ("index.htm", "election-results.htm", "election-oct-2026", "DisplayNews.htm", "result-muncipality-2026.htm",
         "result-nagarpalika-2026.htm", "sitemap.htm")
RESULT_PAGE = re.compile(r"result|પરિણામ|parinam|elected|ચૂંટાયેલ|election-oct-20\d\d|feb-2025|2025", re.I)
RESULT_PDF = re.compile(r"corpo|np-doc|result|પરિણામ|gazette|ગેઝેટ|elected|ચૂંટાયેલ|winner|vijeta|વિજેતા", re.I)
NOT_RESULT = re.compile(r"akhbari|prachar|press|symbol|voterlist|delimitation|rotation|handbook|affidavit|-DP-|-TPS-|MNP-20(15|20)|"
                        r"election-prog|bill|circular", re.I)
OCR_PROJECT = "civic-officials-councillors-ocr"
PAGES = 6


def known():
    f = pathlib.Path(__file__).resolve().parent.parent / "seeds" / "ocr_councillors_gj.json"
    try:
        return {i["payload"]["url"] for i in json.loads(f.read_text())}
    except (OSError, ValueError):
        return set()


def links(html, url):
    soup = BeautifulSoup(html, "lxml")
    return [(urljoin(url, a["href"].strip()), " ".join(a.get_text(" ", strip=True).split())) for a in soup.find_all("a", href=True)]


def result_pages(html, url):
    return list(dict.fromkeys(u for u, t in links(html, url) if u.startswith(BASE) and not u.lower().endswith(".pdf")
                              and RESULT_PAGE.search(u + " " + t) and not NOT_RESULT.search(u)))


def result_pdfs(html, url):
    return list(dict.fromkeys(u for u, t in links(html, url) if u.lower().endswith(".pdf") and "sec.gujarat.gov.in" in u
                              and RESULT_PDF.search(u + " " + t) and not NOT_RESULT.search(u + " " + t)))


def year_of(text):
    t = (text or "").translate(gj.DIGITS)
    ys = [int(y) for y in re.findall(r"20(2[4-9])", t)]
    return 2000 + max(ys) if ys else None


def items(get):
    have = known()
    pages, seen = [urljoin(BASE, s) for s in START], set()
    pdfs = []
    while pages and len(seen) < 25:
        u = pages.pop(0)
        if u in seen:
            continue
        seen.add(u)
        r = get(u)
        if r is None:
            continue
        pdfs += result_pdfs(r.text, u)
        pages += [v for v in result_pages(r.text, u) if v not in seen]
    from pypdf import PdfReader
    out = []
    for url in dict.fromkeys(pdfs):
        if url in have:
            continue
        r = get(url)
        if r is None or not r.content.startswith(b"%PDF"):
            continue
        try:
            reader = PdfReader(io.BytesIO(r.content))
            n = len(reader.pages)
            head = reader.pages[0].extract_text() or ""
        except Exception:  # noqa: BLE001
            continue
        year = year_of(head) or year_of(url)
        if year is not None and year < 2025:
            continue
        key = hashlib.sha1(url.encode()).hexdigest()[:12]
        stem = re.sub(r"[^a-z0-9]+", "-", url.rsplit("/", 1)[-1].lower().rsplit(".", 1)[0]).strip("-")
        for first in range(1, n + 1, PAGES):
            pl = {"kind": "form-cw_gj", "state": "GJ", "url": url, "first": first, "last": min(n, first + PAGES - 1),
                  "election": f"Gujarat {year}" if year else "Gujarat", "slug": f"gj{str(year or '')[2:]}-{stem}",
                  "body_type": "Municipal Corporation" if "corpo" in url.lower() else "Municipality"}
            if first > 1:
                pl["stored"] = f"{OCR_PROJECT}/councillors/GJ/{key}.pdf"
            out.append({"key": f"cwgj-{stem}-p{first}", "payload": pl})
    return out


def save_only(p, get):
    """Fetch the PDF once and keep it in the bucket (the key the OCR items read as "stored"); no OCR, no records."""
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    return [], [(f"councillors/GJ/{key}.pdf", r.content, "application/pdf")], ""


def fetch(p, get):
    if p.get("save_only"):
        return save_only(p, get)
    if not gj.tools("guj"):
        return [], [], "tesseract not available"
    content = tn.stored(p, get)
    from_bucket = content is not None
    if content is None:
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    files = [(f"councillors/GJ/{key}.pdf", content, "application/pdf")] if int(p.get("first", 1)) == 1 else []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = gj.parse(pdf, p)
    for _, rec in recs:
        rec["election"] = p.get("election") or rec["election"]
    if from_bucket:
        tn.mark_stored(recs, p, content)
    return recs, files, "" if recs else "no members read"
