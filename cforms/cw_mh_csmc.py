"""Chhatrapati Sambhajinagar (Aurangabad) Municipal Corporation, general election 2025-26 (polls 15 Jan 2026): the corporation's
list of elected members, chhsambhajinagarmc.org/assets/300/2026/05/mediafiles/Corporator_list-2026.pdf (Municipal Secretary
department, "निर्वाचित स.पालिका सदस्यांची यादी", 8 pages, 115 members of 29 prabhags).
A ruled table printed to PDF from Word: serial, prabhag area, prabhag number, seat (अ ब क ड), name and address, phone numbers.
The rows come from the drawn cell borders (cforms/gj.py grid_rows). The text layer keeps digits and the seat letters, but its
Devanagari is broken (conjuncts and some letters lost), so the name-and-address cell is read by Tesseract (mar), each cell
cropped alone at 300 dpi; the name is the text before the first comma, the rest is the address. The prabhag number is in a
merged cell (cell_of). Party is not in this file.
One queue item = the whole file (payload first, last). The site also answers from outside India.
Record id councillor:MH:chh-sambhajinagar-mc:<prabhag>-<seat>.
"""
import os
import re
import tempfile

from cforms import gj

METHOD = "ocr tesseract + pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

URL = "https://chhsambhajinagarmc.org/assets/300/2026/05/mediafiles/Corporator_list-2026.pdf"
SEATS = "अबकडइ"
PHONE = re.compile(r"[6-9]\d{9}|0\d{2,4}[- ]?\d{6,8}")
TITLE = re.compile(r"^(श्रीमती|श्री|सौ|डॉ|अॅड|अ‍ॅड|प्रा|ॲड)\.?\s*")


def tools():
    return gj.tools("mar")


def split_name(t):
    """'श्री.अशोक रंगनाथ हिवराळे, रो-हाऊस A-2, ...' -> (title, name, address)."""
    t = gj.clean_cell(t)
    name, _, addr = t.partition(",")
    m = TITLE.match(name)
    title = m.group(1) if m else ""
    return title, gj.norm(name[m.end():] if m else name), gj.norm(addr)


def parse_page(ws, hs, vs, texts=None, last_ward=""):
    """Rows of one page: [(serial, ward, seat, name cell text, phones)]. texts: OCR of the name cells in row order (else the
    text layer)."""
    rows, _ = gj.grid_rows(hs, vs, 6, 5)
    out = []
    i = 0
    for cols, a, b in rows:
        serial = re.sub(r"\D", "", gj.box_text(ws, cols[1][0], a, cols[1][1], b))
        if not serial:
            continue
        band = gj.cell_of(3, hs, (a + b) / 2, cols)
        ward = re.sub(r"\D", "", gj.box_text(ws, cols[3][0], band[0], cols[3][1], band[1])) or last_ward
        last_ward = ward
        seat = re.sub(r"[^अबकडइ]", "", gj.box_text(ws, cols[4][0], a, cols[4][1], b))[:1]
        cell = texts[i] if texts is not None else gj.box_text(ws, cols[5][0], a, cols[5][1], b)
        i += 1
        phones = PHONE.findall(gj.box_text(ws, cols[6][0], a, cols[6][1], b).replace(" ", "  "))
        out.append((serial, ward, seat, cell, phones))
    return out, last_ward


def parse(pdf, p, use_ocr=True):
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    first, last = int(p.get("first", 1)), min(int(p.get("last", 99)), len(reader.pages))
    recs, last_ward, counts = [], "", {}
    with tempfile.TemporaryDirectory() as tmp:
        for pg in range(first, last + 1):
            ws = gj.words(pdf, pg)
            hs, vs = gj.drawn_lines(reader, pg - 1)
            texts = None
            if use_ocr:
                rows, _ = gj.grid_rows(hs, vs, 6, 5)
                keep = [(cols, a, b) for cols, a, b in rows if re.sub(r"\D", "", gj.box_text(ws, cols[1][0], a, cols[1][1], b))]
                texts = gj.ocr_boxes(pdf, pg, [(c[5][0] + 1.2, a + 1.2, c[5][1] - 1.2, b - 1.2) for c, a, b in keep], tmp, "mar")
            rows, last_ward = parse_page(ws, hs, vs, texts, last_ward)
            for serial, ward, seat, cell, phones in rows:
                counts[ward] = counts.get(ward, 0) + 1
                seat = seat or SEATS[min(counts[ward], 5) - 1]
                title, name, addr = split_name(cell)
                if not name:
                    continue
                rec = {"type": "councillor", "state": "MH", "body": "Aurangabad", "body_en": "Aurangabad",
                       "body_local": "छत्रपती संभाजीनगर महानगरपालिका", "body_type": "Municipal Corporation",
                       "district": "Chhatrapati Sambhajinagar", "position": "Member", "ward_no": ward, "seat": seat,
                       "name": name, "title": title, "address": addr, "phone": ", ".join(dict.fromkeys(phones)),
                       "serial": int(serial), "election": "Maharashtra Municipal Corporation General Election 2026",
                       "url": URL, "page": pg, "read": "ocr" if use_ocr else "text layer"}
                recs.append((f"councillor:MH:chh-sambhajinagar-mc:{ward or 'x'}-{seat}", rec))
    return recs


def items(get=None):
    return [{"key": "cw-mh-csmc-corporators", "payload": {"kind": "form-cw_mh_csmc", "state": "MH", "url": URL, "first": 1,
                                                          "last": 8}}]


def fetch(p, get):
    if not tools():
        return [], [], "tesseract not available"
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    files = [("councillors/MH/csmc-corporator-list-2026.pdf", r.content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "r.pdf")
        with open(path, "wb") as f:
            f.write(r.content)
        recs = parse(path, p)
    return recs, files, "" if recs else "no members read"
