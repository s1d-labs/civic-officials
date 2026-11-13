"""Assam: the Executive Officer of every urban body, from the Directorate of Municipal Administration (dma.assam.gov.in), page
"Contact list of ULBs" (/information-and-services/contact-list-ulbs), file /sites/default/files/swf1/dms84_contact_details.pdf.
The file is a phone scan ("New Doc 12-21-2023", OKEN Scanner; 5 pages, about 3.1 MB) of a printed Google Sheet "MASTER CONTACT
DETAILS": S.no, District Name, Name of ULB, Executive Officer, DESIGNATION (the officer's own rank: AC, ADC, CO, BDO, SDO S, IAS
...), Mobile; 104 rows. Pages 4 and 5 are scanned upside down. No text layer. Answered dev-vps-3 (Mumbai) on 2026-11-13; not
tried from abroad (route: proxy or direct).

The rows were read by eye from the rendered pages (2026-11-13) into dforms/th_as_rows.tsv (page, row on the page, district, ULB,
Executive Officer, designation, mobile), exactly as printed: names with their service tags ("Pallavi Gogoi,ACS"), "Rd." etc. Two
cells are not names ("z" for Howly, "nilutpal" for Sootea): kept as printed, marked name_doubtful. A hand-written number beside
Gohpur on page 1 (9954967127) is not read. No OCR. The reader fetches the file (the source trail copies it), checks that it is
the file the rows were read from (sha256) and gives one record per row; a changed file gives no record and the reason
"file changed": read the rows again.
The list is of December 2023 (scan name): officers may have moved since. Records say as_of "2023-12-21 (scan date)".
Records: post "Executive Officer" (role head), name, phone = the mobile, rank = the DESIGNATION column, lgd_code from
dforms/th_as_lgd.json (by page:row; Fakiragram has no LGD code).
Earlier lists on the same site: dms40 "Contact list of ULBs_0.pdf" (text, 2017) and dms19 "Contact details of EOs, Chairperson"
(scan, 2017): older, not read.
"""
import json
from pathlib import Path

import provenance
from dforms import _esw, _ulb

METHOD = "scanned DMA list: rows read by eye from the rendered pages (page + row), file checked by sha256"

MODULE = "th_as"
STATE = "AS"
URL = "https://dma.assam.gov.in/sites/default/files/swf1/dms84_contact_details.pdf"
PAGE = "https://dma.assam.gov.in/information-and-services/contact-list-ulbs"
SHA256 = "0fa4da9c365b14426be128ec76fb951ac6b4fcb9087ffc0cd7ad0606797f7a59"
AS_OF = "2023-12-21 (scan date)"
HERE = Path(__file__).parent
LGD = json.loads((HERE / "th_as_lgd.json").read_text())["rows"]
DOUBTFUL = {"z", "nilutpal"}


def rows():
    out = []
    for line in (HERE / "th_as_rows.tsv").read_text().splitlines():
        if not line.strip():
            provenance.skipped("empty")
            continue
        page, row, district, body, name, rank, mobile = line.split("\t")
        out.append({"page": int(page), "row": int(row), "district": district, "body": body, "name": name, "rank": rank,
                    "mobile": mobile})
    return out


def items(get=None):
    return [{"key": f"{MODULE}-dma", "payload": {"reader": MODULE, "url": URL, "state": STATE, "sha256": SHA256,
                                                   "india_only": True}}]


def parse(src=None):
    """Records of the transcribed rows; src = provenance.at(response) of the fetched file (or {})."""
    recs, seen = [], set()
    for r in rows():
        code = LGD.get(f"{r['page']}:{r['row']}")
        extra = {"name_doubtful": True} if r["name"].strip().lower() in DOUBTFUL else {}
        recs.append(_ulb.record(MODULE, STATE, r["body"], "Executive Officer", seen, name=r["name"], phone=r["mobile"],
                                district=r["district"], source=URL, lgd_code=code, rank=r["rank"] or None, as_of=AS_OF,
                                post_from="list", page=PAGE, method=METHOD, **(src or {}), **extra,
                                src_pos={"page": r["page"], "row": r["row"], "read": "by eye from the rendered scan"}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    body = r.content or b""
    if not body.startswith(b"%PDF"):
        return [], [], "not a pdf"
    files = [_esw.keep(MODULE, "dms84_contact_details", body, "pdf")]
    src = provenance.at(r, p["url"])
    want = p.get("sha256") or SHA256
    if src.get("src_sha256") != want:
        return [], files, f"file changed (sha256 {src.get('src_sha256', '')[:12]}, rows read from {want[:12]}): read the rows again"
    return parse(src), files, ""
