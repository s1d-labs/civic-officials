"""Goa: "Government Official Telephone Directory 2023" (Department of Information and Publicity), linked on
https://www.goa.gov.in/citizen/official-government-directory/ :
https://www.goa.gov.in/wp-content/uploads/2023/06/GovtOfficialTelephonedirectory2023.pdf
99,041,129 bytes, 278 pages, made in CorelDRAW X7 (text as curves: no text layer, pdffonts lists no fonts), so it needs OCR.
Checked 2026-11-13 from dev-vps-3 (200, 63 s). A HEAD request gets 403; GET works.
This reader only saves the file ONCE to the bucket (depts/st_ga_teldir/teldir2023.pdf) and writes one "source_file" record,
so an OCR task can read the bucket copy on the GitHub runners (no OCR or parsing here). Route: direct (answers from Mumbai).
"""
METHOD = "file saved to the bucket (pdf, scanned: OCR later)"

M = "st_ga_teldir"
URL = "https://www.goa.gov.in/wp-content/uploads/2023/06/GovtOfficialTelephonedirectory2023.pdf"


def items(get=None):
    return [{"key": f"{M}:2023", "payload": {"reader": M, "url": URL, "state": "GA", "india_only": True, "route": "direct",
                                             "ocr": True, "pages": 278}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    ok = r.content[:5] == b"%PDF-"
    if not ok:
        return [], [], "not a pdf"
    path = f"depts/{M}/teldir2023.pdf"
    rec = (f"dept:{M}:file:2023", {"type": "source_file", "url": url, "stored": path, "bytes": len(r.content), "fetched": True,
                                   "state": "GA", "label": "Government Official Telephone Directory 2023", "pages": p.get("pages"),
                                   "ocr_needed": True, "source": url, "src_url": url, "method": METHOD})
    return [rec], [(path, r.content, "application/pdf")], ""
