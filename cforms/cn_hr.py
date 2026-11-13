"""Haryana: members and presidents of the 18 municipal councils and 28 municipal committees elected on 19.06.2022.

Source: State Election Commission Haryana notification No. SEC/1ME/2022/6120 dated 04.07.2022 (Haryana Municipal Act 1973,
section 24(2)), a 59-page Canon scan without a text layer, published by the Directorate of Urban Local Bodies:
ulbharyana.gov.in/Website/DynamicUploadContent/CONTENTFILES/b7a90171-1b60-4c3d-8617-5137e031b016.pdf (answers outside India).
Pages 1-24 are English, pages 25-59 the same list in Hindi (not queued). Ruled table, ten columns:
Sr No | District | Name of the Council | Name of the Committee | Ward No. | Name of Elected President/Member | Father's/Husband's
Name | Name of Office | Category | Affiliated with which Political Party. The district and body cells span all rows of a body and
carry their text in the first row (the President row); "--" marks the unused body column.
Pages are read with the grid reader of cforms/hr.py (lines found and erased, Tesseract per column). One queue item = 6 pages;
an item that starts inside a body gets that body from the payload ("carry": district, body, body_type, last ward).
The first item saves the PDF in the bucket; the others read the saved copy (payload "stored", see cforms/tn.py stored()).
Record id councillor:HR:<body slug>:<ward no or "chair"> (the scheme of cforms/hr.py; Tohana ward 17 was filled again in the
2026 bye-election, which holds the plain id: payload "replaced").
"""
import hashlib
import os
import re
import tempfile

import provenance
from cforms import hr
from cforms.tn import stored

METHOD = "ocr tesseract eng (ruled grid, one image per column)"     # source trail (provenance.py): how this reader reads its sources

URL = "https://ulbharyana.gov.in/Website/DynamicUploadContent/CONTENTFILES/b7a90171-1b60-4c3d-8617-5137e031b016.pdf"
ELECTION = "Haryana 2022 (poll 19.06.2022; SEC notification SEC/1ME/2022/6120 of 04.07.2022)"
COLS = ["sr", "district", "council", "committee", "ward", "name", "father", "office", "category", "party"]
EMPTY = re.compile(r"^[-–—_.~=:'\"\s]*$")
# district spellings of the notice -> civic.ulb district names (the notice predates Hansi district)
DISTRICTS = {"Charkhi Dadri": "Charkhi Dadri", "Gurugram": "Gurugram", "Nuh": "Nuh", "Mahendragarh": "Mahendragarh"}


def party(s):
    s = hr.clean(s)
    if re.search(r"Aam\s*A\w*dmi|Adami|A\.?A\.?P", s, re.I):
        return "Aam Aadmi Party"
    if re.search(r"Jan+\w*\s*Jan\w*\s*Party|JJP", s, re.I):
        return "Jannayak Janta Party"
    if re.search(r"Lok\s*dal|INLD", s, re.I):
        return "Indian National Lok Dal"
    return hr.fix_party(s)


def body_text(s):
    s = hr.clean(s)
    return "" if EMPTY.match(s) else s


def page_rows(trows, state):
    """Grid rows of one page -> member dicts (hr.record's input). state carries district/body/type/last ward across pages."""
    out = []
    for r in trows:
        if len(r["cells"]) != len(COLS):
            continue
        c = dict(zip(COLS, r["cells"]))
        if hr.HEAD_WORDS.search(" ".join(r["cells"])) and not re.search(r"\d", c["ward"]):
            continue
        name = hr.clean(c["name"])
        office = hr.clean(c["office"])
        is_chair = bool(hr.OFFICE_CHAIR.search(office))
        is_member = bool(re.search(r"m[ec]m|mbe|emb|ember", office, re.I))
        if not name or not (is_chair or is_member or re.search(r"\d", c["ward"])):
            continue
        council, committee = body_text(c["council"]), body_text(c["committee"])
        if hr.clean(c["district"]) and not EMPTY.match(hr.clean(c["district"])):
            d = re.sub(r"^\d+\W*", "", hr.clean(c["district"])).strip()
            if d:
                state["district"] = DISTRICTS.get(d, d)
        if is_chair or council or committee:
            if council or committee:
                state["body"] = council or committee
                state["body_type"] = "Municipal Council" if council else "Municipal Committee"
            state["last"] = 0
        if is_chair and not is_member:
            ward = ""
        else:
            ward = str(int(state.get("last") or 0) + 1)     # a general election lists every ward in order (OCR slips fixed)
            state["last"] = int(ward)
        out.append({"district": state.get("district", ""), "body": state.get("body", ""), "body_type": state.get("body_type"),
                    "ward": ward, "name": (c["name"] or "").replace("]", "j"), "father": c["father"], "office": office if is_chair else "Member",
                    "category": c["category"], "party": c["party"], "_pos": hr.row_pos(r)})
    return out


def records(p, rows, page):
    out = []
    for x in rows:
        if not x["body"]:
            provenance.skip_row(x, 'skip: not x["body"]')
            continue
        rid, d = hr.record(p, None, x, page, "ocr")
        d["party"] = party(x["party"])
        d["body_en"] = re.sub(r"\s*Municipal\s+(Council|Committee)$", "", x["body"])
        d["source"] = "SEC Haryana notification SEC/1ME/2022/6120, 04.07.2022"
        out.append((rid, d))
    return out


def parse(pdf, p):
    state = dict(p.get("carry") or {})
    recs, seen = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for pg in range(int(p.get("first", 1)), int(p.get("last", 1)) + 1):
            recs += records(p, page_rows(hr.table(pdf, pg, tmp, "eng"), state), pg)
    out = []
    for rid, d in recs:
        n = seen[rid] = seen.get(rid, 0) + 1
        out.append((rid + (f"-{n}" if n > 1 else ""), d))
    return out


def fetch(p, get):
    if not hr.tools():
        return [], [], "tesseract not available"
    url = p.get("url", URL)
    content = stored(p, get)
    src = provenance.file_src(content, url, p["stored"]) if content is not None else None
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    key = hashlib.sha1(url.encode()).hexdigest()[:12]
    files = [(f"councillors/HR/{key}.pdf", content, "application/pdf")] if int(p.get("first", 1)) == 1 and not p.get("stored") \
        else []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, {**p, "election": p.get("election", ELECTION), "url": url})
    for _, d in recs:
        if src:
            d["src"] = dict(src)
    return recs, files, "" if recs else "no members read"


if __name__ == "__main__":      # offline run over a local copy: python -m cforms.cn_hr FILE.pdf FIRST LAST
    import json
    import sys
    for rid, d in parse(sys.argv[1], {"url": URL, "election": ELECTION, "first": sys.argv[2], "last": sys.argv[3],
                                      "replaced": ["tohana-municipal-council:17"]}):
        print(json.dumps({"id": rid, **d}, ensure_ascii=False))
