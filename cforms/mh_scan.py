"""Maharashtra municipal corporation results, January 2026, from e-Gazette notices that are scans of a ruled table printed
sideways (Thane Municipal Corporation: Part II, extraordinary No. 17, 19 Jan 2026, 18 pages, one 3507 x 2480 grey image per page,
the table turned 90 degrees on an upright page).

The notice is found and fetched as in cforms/mh.py (search the day, post "View" back; India only). Each page is rendered at
300 dpi, turned upright (payload "rotate": 90 = a quarter turn clockwise, 270 = counter-clockwise), and read by the grid
reader of cforms/hr.py (ruled lines found in the image and erased, Tesseract mar per column strip, words placed in the cells
between the lines). The payload "cols" names the columns in order; Thane: serial, ward, ward name, population, SC population,
ST population, seat, reservation, name, gender, party, votes. A row with a seat letter (अ ब क ड इ) is a member. The ward
number and ward name are merged cells over the ward's rows: a ward block starts where the ruled line above crosses the ward
column, and the block's number is the first number read in it.
OCR runs on the GitHub runners only (councillors-ocr project, Indian proxy for the gazette). One queue item = up to 6 pages.
Record id councillor:MH:<slug>:<ward>-<seat>.
"""
import hashlib
import os
import re
import tempfile

from cforms import gj, hr, mh

METHOD = 'ocr tesseract mar (rotated gazette scan, ruled grid)'     # source trail (provenance.py): how this reader reads its sources

SEAT = re.compile(r"(?:^|[\s\-(])([अबकडइ])\s*\)?\s*$")


def rotate(w, h, data, deg):
    """A grey image (row-major bytes) turned a quarter turn: 90 clockwise, 270 counter-clockwise. -> (w, h, data)."""
    data = bytes(data)
    if deg == 90:
        rows = (data[x::w][::-1] for x in range(w))
    elif deg == 270:
        rows = (data[x::w] for x in range(w - 1, -1, -1))
    else:
        return w, h, bytearray(data)
    return h, w, bytearray(b"".join(rows))


def upright(pgm, deg):
    if deg not in (90, 270):
        return pgm
    w, h, data = hr.read_pgm(pgm)
    w, h, data = rotate(w, h, data, deg)
    out = pgm[:-4] + f"-r{deg}.pgm"
    hr.write_pgm(out, w, h, data)
    return out


def records(rows, p, page=None):
    """rows: [{"cells": [text per column], "new": [line above crosses the column?]}] of one or more pages, in order."""
    cols = p["cols"]
    at = {c: i for i, c in enumerate(cols)}
    out, ward, ward_name, block = [], "", "", []
    seen = set()

    def cell(r, c):
        i = at.get(c)
        return gj.norm(r["cells"][i]) if i is not None and i < len(r["cells"]) else ""
    members = []
    for r in rows:
        wi = at.get("ward")
        starts = wi is not None and (not r.get("new") or wi >= len(r["new"]) or r["new"][wi])
        if starts and block:
            members.append(block)
            block = []
        block.append(r)
    if block:
        members.append(block)
    for blk in members:
        if not any(SEAT.search(cell(r, "seat")) for r in blk):
            continue                     # head rows ("(१) (२) ...") and empty bands: their numbers are not wards
        w = next((mh.num(cell(r, "ward")) for r in blk if mh.num(cell(r, "ward"))), "")
        wn = " ".join(cell(r, "ward_name") for r in blk if cell(r, "ward_name"))
        if w:
            ward, ward_name = w, wn
        for r in blk:
            m = SEAT.search(cell(r, "seat"))
            name = hr.clean(cell(r, "name"))
            if not m or not name or not ward:
                continue
            seat = m.group(1)
            party_local = hr.clean(cell(r, "party"))
            resv = hr.clean(cell(r, "reservation"))
            votes = mh.num(cell(r, "votes"))
            d = {"type": "councillor", "state": "MH", "body": p.get("body_local") or p.get("body", ""),
                 "body_local": p.get("body_local", ""), "body_en": p.get("body", ""), "body_type": "Municipal Corporation",
                 "district": p.get("district", ""), "lgd_code": p.get("lgd_code", ""), "ward_no": ward,
                 "ward_name": ward_name, "seat": seat, "name": name, "gender_local": hr.clean(cell(r, "gender")),
                 "party_local": party_local, "party": mh.party_of(party_local) or party_local, "reservation_local": resv,
                 "reservation": mh.reservation(resv), "votes": int(votes) if votes else None,
                 "serial": mh.num(cell(r, "serial")), "election": "Maharashtra 2026", "url": p["url"],
                 "gazette": p.get("match", ""), "page": r.get("page", page), "read": "ocr (scan)"}
            key = f"councillor:MH:{p.get('slug', 'x')}:{ward}-{seat}"
            if key in seen:
                key += f"-s{d['serial'] or len(out)}"
            seen.add(key)
            out.append((key, {k: v for k, v in d.items() if v not in ("", None)}))
    return out


def parse(pdf, p):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for pg in range(int(p.get("first", 1)), int(p.get("last", 1)) + 1):
            pgm = upright(hr.render(pdf, pg, tmp), int(p.get("rotate", 0)))
            for r in hr.table_pgm(pgm, "mar"):
                r["page"] = pg
                rows.append(r)
    return records(rows, p)


def fetch(p, get):
    if not mh.tools():
        return [], [], "tesseract not available"
    content, why = mh.get_pdf(p, get)
    if content is None:
        return [], [], why
    key = hashlib.sha1((p["gazette_date"] + p["match"]).encode()).hexdigest()[:12]
    files = [(f"councillors/MH/{key}.pdf", content, "application/pdf")] if int(p.get("first", 1)) <= 2 else []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, p)
    return recs, files, "" if recs else "no members read"
