"""Village officials on district portals (S3WaaS) of Maharashtra, Madhya Pradesh, Chhattisgarh, Gujarat and Goa: find and read
the pages that list Talathis / Gram Mahsul Adhikaris, Patwaris (per halka), Gram Sevaks / Panchayat Secretaries / Talatis.

Why a finder: the archive (2026-11-13) holds such lists for 2 of 139 portals only (Ahilyanagar: 14 tahsil PDFs, Jalna: Partur
taluka page; both read by dforms/vil_mh_talathi.py with fixed seeds). Most portals put them under a menu item ("Circle Officer
and Talathi", "मंडळ अधिकारी व तलाठी", "पटवारी सूची", "Know your Patwari") or on the tahsil / taluka pages.

One queue item = one portal: GET the home page; take the links on the same host (and cdn.s3waas.gov.in files) whose text or
address names a village official (LINK), then the tahsil / taluka pages (TEHSIL), at most MAX_FOLLOW pages in all, never a
recruitment, exam, seniority, transfer or tender page (NOT_LINK). Each page read: its tables go through
vil_mh_talathi.parse_html (header words in Marathi, Hindi, Gujarati or English: official, saja / halka / gram panchayat,
mobile, villages, circle officer / RI); the PDFs it links whose text or address names a village official are fetched (at most
MAX_PDFS per portal): a PDF of the Ahilyanagar template is read (vil_mh_talathi.parse_pdf_text), any other PDF is kept in the
bucket and noted as a "source_file" record (needs_ocr when it has no text layer) so a later reader can read the stored copy on
the runners. Every answer is kept as a bucket file.

Records: as vil_mh_talathi (dept revenue level village, or dept rural_development level gram_panchayat for Gram Sevak /
Panchayat Secretary / Talati columns; circle officer / RI rows at level circle), ids dept:vil_portal:<host>:<page tag>:s<n>|c<n>;
files dept:vil_portal:<host>:file:<sha1 of url, 12>. src_url = the page or PDF the row came from.
"""
import hashlib
import re
from urllib.parse import unquote, urljoin, urlparse

from dforms import _esw, _field, vil_mh_talathi as V

METHOD = "html table (header words -> columns) on pages found from the portal menu; pdf layout text (Ahilyanagar template)"

MODULE = "vil_portal"
MAX_FOLLOW = 15
MAX_PDFS = 12
LINK = re.compile(r"(?i)talathi|तलाठी|ग्राम\s*महसूल|gram-?mahsul|patwar|पटवार|know-?your-?patwari|\bhalka\b|हल्का|\bsajj?a\b|सजा|"
                  r"gram-?sevak|ग्रामसेवक|ग्राम\s*सेवक|panchayat-?secretar|पंचायत\s*सचिव|gram-?panchayat-?adhikari|"
                  r"ग्रामपंचायत\s*अधिकारी|ग्राम\s*पंचायत\s*अधिकारी|talati|તલાટી|village-?accountant|circle-?officer|मंडळ\s*अधिकारी|"
                  r"revenue-?inspector|राजस्व\s*निरीक्षक|revenue-?(department|directory|contact)|राजस्व\s*विभाग")
TEHSIL = re.compile(r"(?i)tah?e?h?sil|taluk|तहसील|तालुका|तालूका|तहसिल|તાલુક")
NOT_LINK = re.compile(r"(?i)recruit|bharti|भरती|परीक्षा|exam|seniority|ज्येष्ठता|जेष्ठता|gradation|counsel|merit|result|निकाल|"
                      r"tender|निविदा|transfer|स्थानांतरण|बदली|selection|waiting|प्रतीक्षा|answer-?key|syllabus|admit|"
                      r"land-?acquisition|भूसंपादन|gazette|notification-of|reorgani")
PDF_LINK = re.compile(r"(?i)talathi|तलाठी|महसूल|patwar|पटवार|halka|हल्का|saja|सजा|sevak|सेवक|सचिव|secretar|talati|તલાટી|"
                      r"circle|मंडळ|contact|directory|संपर्क|list|सूची|यादी|\.pdf")


def links(html, base):
    """(official pages, tehsil pages): absolute urls on the portal's host, in page order, without duplicates."""
    host = urlparse(base).netloc
    off, teh = [], []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html or ""):
        u = urljoin(base, m.group(1).replace("&amp;", "&"))
        pu = urlparse(u)
        if pu.scheme not in ("http", "https") or (pu.netloc != host and pu.netloc != "cdn.s3waas.gov.in"):
            continue
        t = _esw.clean(re.sub(r"<[^>]+>", " ", m.group(2)))
        words = f"{t} {unquote(pu.path)}"
        if NOT_LINK.search(words) or re.search(r"(?i)\.(jpe?g|png|gif|zip|docx?|xlsx?)$", pu.path):
            continue
        if LINK.search(words):
            if u not in off:
                off.append(u)
        elif TEHSIL.search(words) and pu.netloc == host and u not in teh and u.rstrip("/") != base.rstrip("/"):
            teh.append(u)
    return off, teh


def read_pdf(content, url, p, host):
    recs, has_text = V.parse(content, url, dict(p, tag=p.get("tag")))
    out = []
    for rid, d in recs:
        out.append((rid.replace(f"dept:{V.MODULE}:", f"dept:{MODULE}:", 1), d))
    if out:
        return out
    fid = hashlib.sha1(url.encode()).hexdigest()[:12]
    return [(f"dept:{MODULE}:{host}:file:{fid}", {
        "type": "source_file", "url": url, "page": p.get("page"), "state": p.get("state"), "district": p.get("district"),
        "stored": f"depts/{MODULE}/{host}-file-{fid}.pdf.gz", "needs_ocr": not has_text,
        "note": "village official list? text layer but no known table" if has_text else "scanned PDF: needs OCR",
        "src_url": url})]


def fetch(p, get):
    home = p["url"]
    host = urlparse(home).netloc
    r = get(home)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{host}-home", r.content, "html")]
    off, teh = links(r.text, home)
    queue = (off + teh)[:MAX_FOLLOW]
    recs, pdfs, seen_pdf = [], [], set()
    for u in queue:
        a = get(u)
        if a is None:
            continue
        tag = _esw.slug(unquote(urlparse(u).path))[-40:] or "page"
        if a.content[:5] == b"%PDF-":
            pdfs.append((u, a.content, home))
            continue
        files.append(_esw.keep(MODULE, f"{host}-{tag}", a.content, "html"))
        html = a.text
        q = dict(p, tag=tag, page=u)
        recs += V.parse_html(html, q, u, module=MODULE)
        for f in _field.pdf_links(html, u):
            fu = urlparse(f)
            words = unquote(fu.path) + " " + html[max(0, html.find(f) - 300):html.find(f)]
            if f in seen_pdf or NOT_LINK.search(unquote(fu.path)) or not (LINK.search(words) or u in off):
                continue
            seen_pdf.add(f)
            if len(seen_pdf) > MAX_PDFS:
                break
            b = get(f)
            if b is not None and b.content[:5] == b"%PDF-":
                pdfs.append((f, b.content, u))
    for n, (u, content, page) in enumerate(pdfs, 1):
        fid = hashlib.sha1(u.encode()).hexdigest()[:12]
        files.append(_esw.keep(MODULE, f"{host}-file-{fid}", content, "pdf"))
        recs += read_pdf(content, u, dict(p, tag=f"pdf{fid}", page=page), host)
    if not recs:
        return [], files, f"no village official list found ({len(off)} official links, {len(teh)} tehsil pages read)"
    return recs, files, ""


def items(get=None):
    return _field.seed(MODULE)
