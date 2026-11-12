"""Chhattisgarh urban body general election 2025: the directly elected heads, mayors (महापौर, 10 municipal corporations) and
chairpersons (अध्यक्ष, municipal councils and nagar panchayats). Source: cgsec.gov.in/hin_2025chunavnagarpalika.html,
"निर्वाचित महापौर / अध्यक्ष की जानकारी" = Notification2025/election/Mayor-president 2025.pdf (5 pages, Microsoft Print To PDF,
one ruled table per body type: serial | district | body | elected mayor/chairperson | party). The SEC's vote file
("Elected Mayor-President.pdf", 31 pages, every candidate's votes) is a second item, kind "votes" below.
The text layer has the same faults as the councillor list (cforms/cw_cg.py): half letters dropped, i-sign misplaced. So the
text layer gives the serial, the party and the consonant keys of district and body; the name is read by Tesseract (hin) on its
cell (cw_cg.ocr_cells). The body comes from the councillor list's seed map (body key | district key -> body, LGD code, slug,
made offline and checked by hand), so the head and the ward members share one body slug.
One queue item = the whole file (OCR on GitHub runners; the site answers only from India, so a proxy, or the stored copy).
Record id councillor:CG:2025:<body slug>:chair.
"""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from cforms import cw_cg, gj
from cforms.tn import mark_stored, stored

METHOD = ("ocr tesseract hin (name cell, 400 dpi) + pdf text layer by drawn cell borders (serial, district, body, party; "
          "pdftotext -bbox)")

URL = "https://cgsec.gov.in/Notification2025/election/Mayor-president%202025.pdf"
ELECTION = "Chhattisgarh urban body general election 2025 (direct election of mayors and chairpersons; SEC list, Feb 2025)"
HERE = Path(__file__).resolve().parent.parent


def body_map():
    """The councillor list's map {body key | district key: body} from every seeds/ocr_councillors_cw_cg.json item."""
    out = {}
    f = HERE / "seeds" / "ocr_councillors_cw_cg.json"
    if f.exists():
        for it in json.loads(f.read_text()):
            out.update(it["payload"].get("bodies") or {})
    return out


def page_rows(reader, pdf, pg):
    hs, vs = gj.drawn_lines(reader, pg - 1)
    rows, _ = gj.grid_rows(hs, vs, 5, 4)
    ws = gj.words(pdf, pg)
    out = []
    for cols, a, b in rows:
        t = {c: gj.box_text(ws, cols[c][0], a, cols[c][1], b) for c in range(1, 6)}
        if not t[1].isdigit() or (t[2], t[3]) == ("2", "3"):
            continue
        out.append({"serial": t[1], "district_raw": t[2], "body_raw": t[3], "name_raw": t[4], "party_raw": t[5],
                    "cols": cols, "y0": a, "y1": b})
    return out


def position(body_type):
    return ("Mayor", "महापौर") if "निगम" in (body_type or "") else ("Chairperson", "अध्यक्ष")


def parse(pdf, p, use_ocr=True):
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    known = p.get("bodies") or body_map()
    recs = []
    for pg in range(1, len(reader.pages) + 1):
        with tempfile.TemporaryDirectory() as tmp:
            rows = page_rows(reader, pdf, pg)
            boxes = []
            for r in rows:
                boxes.append((r["cols"][4][0], r["y0"], r["cols"][4][1], r["y1"]))
                if cw_cg.map_key(r) not in known:            # body not in the map: read district and body too
                    boxes += [(r["cols"][c][0], r["y0"], r["cols"][c][1], r["y1"]) for c in (2, 3)]
            texts = cw_cg.ocr_cells(pdf, pg, boxes, tmp) if use_ocr else [""] * len(boxes)
        i = 0
        for ri, r in enumerate(rows, 1):
            name = cw_cg.fix_name(texts[i])
            i += 1
            bt, bk = cw_cg.body_key(r["body_raw"])
            mk = cw_cg.map_key(r)
            if mk in known:
                b = known[mk]
            else:
                dist, full = texts[i], texts[i + 1]
                i += 2
                nm = re.sub(r"^\s*(नगर\s*पालिक\s*निगम|नगर\s*पालिका\s*परिषद्?|नगर\s*पंचायत|नगरपालिक\s*निगम|नगरपालिका\s*परिषद्?)\s*", "",
                            full)
                b = {"body": nm or full or bk, "body_type": bt, "district_local": dist,
                     "slug": f"k-{cw_cg.slug_of(nm or full or bk)}"}
            pos, pos_local = position(b.get("body_type") or bt)
            d = {"type": "councillor", "state": "CG", "body": b["body"], "body_local": b["body"],
                 "body_type": b.get("body_type") or bt, "district": b.get("district"), "district_local": b.get("district_local"),
                 "ward_no": "chair", "name": name, "position": pos, "position_local": pos_local,
                 "party": cw_cg.party_of(r["party_raw"]) or None, "party_text": r["party_raw"], "name_text": r["name_raw"], "elected_by": "voters (direct election)",
                 "election": p.get("election", ELECTION), "url": p.get("url", URL), "page": pg, "serial": r["serial"],
                 "src_pos": {"page": pg, "row": ri, "serial": r["serial"],
                             "box_pt": [round(r["cols"][1][0], 1), round(r["y0"], 1), round(r["cols"][5][1], 1), round(r["y1"], 1)]},
                 "name_check": "ok" if cw_cg.subseq(cw_cg.key(r["name_raw"]), cw_cg.key(name)) else "differs from text layer"}
            if b.get("body_en"):
                d["body_en"] = b["body_en"]
            if b.get("lgd"):
                d["lgd_code"] = d["local_body_code"] = b["lgd"]
            if mk not in known:
                d["body_read_by_ocr"] = True
            recs.append((f"councillor:CG:2025:{b['slug']}:chair", {k: v for k, v in d.items() if v not in (None, "")}))
    seen, out = {}, []
    for rid, d in recs:
        n = seen[rid] = seen.get(rid, 0) + 1
        out.append((rid + (f"-{n}" if n > 1 else ""), d))
    return out


def fetch(p, get):
    if not cw_cg.tools():
        return [], [], "tesseract not available"
    url = p.get("url", URL)
    content = stored(p, get)
    from_bucket = content is not None
    if content is None:
        r = get(url)
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    k = hashlib.sha1(url.encode()).hexdigest()[:12]
    files = [] if p.get("stored") else [(f"councillors/CG/{k}.pdf", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, p)
    if from_bucket:
        mark_stored(recs, p, content, url)
    return recs, files, "" if recs else "no heads read"
