"""Uttarakhand: UPCL (Uttarakhand Power Corporation) distribution offices down to the sub-division and the JE.
upcl.uk.gov.in is an S3WaaS site. Two kinds of queue item (payload "part"):

- "se": upcl.uk.gov.in/contact-list-of-se-and-above/, one page of small tables (S.No., Name, Designation, Telephone, Email,
  Address): the head office, then one table per distribution zone ("Chief Engineer (Distribution), <Zone> Zone" = zone, the
  "Superintending Engineer, EDC, <town>" rows below it = circles), then the project zones and the secondary works circles.
  About 45 rows. Head office, project and works rows are kept with level "state".
- "zone": one of the four PDFs "Distribution Offices <Zone> Zone upto S/s Level" linked from
  upcl.uk.gov.in/contact-details-of-other-upcl-officials/ (files on cdnbbsr.s3waas.gov.in, printed from Excel). One grid
  row = one 11 kV feeder. Two layouts:
    A (Haridwar, Kumaon, Rudrapur): Division name | Name of Sub Division | Name of Sub Station | sub station number |
      Name of Feeder | JE NO | SDO NO | EE NO, merged cells for the division, sub-division, sub-station and phones;
    B (Garhwal): Division | EE | SDO | 33/11 KV SUBSTATION | S/S NUMBER | 33/11 OUT GOING FEEDER NAME | JE, one row per
      feeder (sub-station repeated); the sub-divisions have no name, only the SDO phone.
  No officer names. Records: division (EE phone), sub-division (SDO phone; layout B: area = its sub-stations), section (one
  per JE phone in a sub-division: the sub-stations and feeders that JE looks after, with the sub-station phones).
  The grid is read from pypdf text positions and the ruling lines (dforms/_util2_pdfgrid.page_parts): a merged cell covers
  every feeder row between the lines above and below it. A merged cell that runs on to the next page is printed empty
  there: the value of the page before is carried. Row counts: one row = one feeder row; a row without a JE phone is
  counted as skipped.
Record ids dept:power3_upcl:se:<designation>, dept:power3_upcl:<zone>:div:<division>, ...:sd:<division>:<sub-division>,
...:je:<division>:<sub-division>:<phone>.
"""
import io
import re

from bs4 import BeautifulSoup

import provenance
from dforms._power import Out, cells, clean, email, phone, raw, tr_pos

METHOD = "html table + pdf table grid (pypdf text positions and ruling lines)"     # source trail (provenance.py)

MOD = "power3_upcl"
SE_URL = "https://upcl.uk.gov.in/contact-list-of-se-and-above/"
CDN = "https://cdnbbsr.s3waas.gov.in/s303412aef4dcdee4f934f7bf599f89783/uploads/2025/07/"
ZONES = {"Haridwar": CDN + "202507041315929139.pdf", "Kumaon": CDN + "202507041607222727.pdf",
         "Garhwal": CDN + "20250704215953182.pdf", "Rudrapur": CDN + "202507041047701695.pdf"}
LAYOUTS = {"A": ["division", "subdivision", "substation", "ss_phone", "feeder", "je", "sdo", "ee"],
           "B": ["division", "ee", "sdo", "substation", "ss_phone", "feeder", "je"]}
PHONES = {"ss_phone", "je", "sdo", "ee"}
HEAD = re.compile(r"(?i)division|name of|station|number|feeder|^\s*je\b|sdo|ee no|substation|substaion|33/11|s/s|zone\s*$|"
                  r"contact details")


# ---- the SE-and-above page

def parse_se(html, url=SE_URL):
    out = Out(MOD, "UK", url, discom="UPCL")
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        zone = None
        for tr in t.find_all("tr"):
            c = cells(tr)
            if len(c) < 3 or not c[0].strip().isdigit():
                provenance.skip_row(tr, "no serial number")
                continue
            name, post = clean(c[1]), clean(c[2])
            if not post:
                provenance.skip_row(tr, "no designation")
                continue
            tel = phone(*re.split(r",", c[3])) if len(c) > 3 else None
            mail = email(c[4]) if len(c) > 4 else None
            addr = c[5] if len(c) > 5 else None
            m = re.match(r"(?i)chief engineer\s*\(\s*distribution\s*\)\s*,?\s*(.+?)\s*zone\b", post)
            s = re.match(r"(?i)superintending engineer\s*,?\s*(EDC.*)$", post)
            if m:
                zone = m.group(1).strip().title() + " Zone"
                lvl, area, par = "zone", zone, None
            elif s and zone:
                lvl, area, par = "circle", re.sub(r"\s*,\s*", " ", s.group(1)).strip(), {"zone": zone}
            else:
                lvl, area, par = "state", post, None
            provenance.used()
            out.add(f"se:{post}", lvl, area, post=post, name=name, phone_=tel, email_=mail, address=addr, parents=par,
                    src_pos=tr_pos(tr), method="html table")
    return out.recs


# ---- the zone PDFs

def _join(pieces, is_phone):
    """Text of one cell from its pieces (top to bottom, left to right); phone digits broken over two lines are joined."""
    s = ""
    for p in pieces:
        p = " ".join(p.split())
        if not p:
            continue
        if is_phone and s and s[-1].isdigit() and p[0].isdigit():
            s += p
        else:
            s = f"{s} {p}" if s else p
    return clean(s)


def _layout(head_text):
    t = " ".join(head_text.split()).lower()
    if "name of sub division" in t and "je no" in t:
        return "A"
    if re.search(r"division\s+ee\s+sdo", t):
        return "B"
    return None


def page_grid(reader, page):
    """(layout, [row dicts]) of one page; a row dict = {role: (text, cell id)} for every column, plus "_y"."""
    from dforms._util2_pdfgrid import page_parts
    texts, hl, vl = page_parts(reader, page)
    div = [t for t in texts if re.match(r"\s*division", t[2], re.I)]
    if not div or not vl:
        for t in texts:
            provenance.skip_line(t[2], "page without the table header")
        return None, [], []
    ydiv = max(t[1] for t in div)
    head = [t for t in texts if abs(t[1] - ydiv) <= 14 and HEAD.search(t[2])] + [t for t in texts if t[1] > ydiv + 14]
    lay = _layout(" ".join(t[2] for t in sorted(head, key=lambda t: (-t[1], t[0]))))
    xs = []
    for x in sorted(round(v[0], 1) for v in vl):
        if not xs or x - xs[-1] > 3:
            xs.append(x)
    roles = LAYOUTS.get(lay)
    if not roles or len(xs) - 1 != len(roles):
        for t in texts:
            provenance.skip_line(t[2], "unknown table layout")
        return None, [], []
    hmin = min(t[1] for t in head if abs(t[1] - ydiv) <= 14)
    below = [y for x0, x1, y in hl if y < hmin - 0.5]
    top = max(below) if below else hmin - 2
    bottom = min(v[1] for v in vl) - 1
    provenance.skipped("header")
    cols = []
    for k, (a, b) in enumerate(zip(xs, xs[1:])):
        cx = (a + b) / 2
        ys = sorted({round(y, 1) for x0, x1, y in hl if x0 - 2 <= cx <= x1 + 2 and bottom < y < top - 0.5} | {top, bottom},
                    reverse=True)
        cells_ = [[hi, lo, []] for hi, lo in zip(ys, ys[1:]) if hi - lo > 1.5]
        cols.append((a, b, cells_))
    left, split = [], []
    for x, y, s in texts:
        m = re.match(r"\s*(\d{10})\s*([A-Za-z][A-Za-z ()/.-]+?)\s*$", s)
        if lay == "B" and m and xs[1] - 1 <= x + 1 < xs[2]:
            # layout B: pypdf reads "<EE phone><division name>" as one piece in the EE column; the name is the division's
            split += [(x, y, m.group(1)), (xs[0] + 1, y, m.group(2))]
        else:
            split.append((x, y, s))
    for x, y, s in sorted(split, key=lambda t: (-t[1], t[0])):
        if y >= top or not s.strip():
            continue
        k = next((k for k, (a, b, _) in enumerate(cols) if a - 1 <= x + 1 < b), None)
        c = None if k is None else next((c for c in cols[k][2] if c[1] < y < c[0]), None)
        if c is None:
            left.append((x, y, s))
            continue
        c[2].append(s)
    fi = roles.index("feeder")
    rows = []
    for hi, lo, pieces in cols[fi][2]:
        mid = (hi + lo) / 2
        row = {"_y": round(mid, 1)}
        for k, role in enumerate(roles):
            best = None
            for j, (h2, l2, p2) in enumerate(cols[k][2]):
                ov = min(hi, h2) - max(lo, l2)
                if l2 <= mid <= h2:
                    best = (j, p2)
                    break
                if ov > 0 and (best is None or ov > best[2]):
                    best = (j, p2, ov)
            row[role] = (_join(best[1], role in PHONES), f"{k}:{best[0]}") if best else (None, None)
        rows.append(row)
    return lay, rows, left


def parse_zone(content, zone, url=None):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    out = Out(MOD, "UK", url or ZONES.get(zone), discom="UPCL")
    zname = f"{zone} Zone"
    carry, prev_cell = {}, {}
    feeders = []          # (page, row number on the page, row dict with carried values)
    lay_seen = None
    for pno, page in enumerate(reader.pages, 1):
        lay, rows, left = page_grid(reader, page)
        for x, y, s in left:
            provenance.skip_line(s, "text outside the table")
        if not lay:
            continue
        lay_seen = lay_seen or lay
        for rn, row in enumerate(rows, 1):
            r = {}
            for role, cell in row.items():
                if role == "_y":
                    continue
                val, cid = cell
                key = (pno, cid)
                if val is None and role not in ("feeder", "je") and cid is not None and rn <= _first_rows(rows, role, cid):
                    val = carry.get(role)          # a merged cell that began on the page before
                    key = prev_cell.get(role, key)
                elif val is not None:
                    carry[role] = val
                    prev_cell[role] = key
                r[role] = val
                r[role + "#"] = key
            m = re.match(r"^(.*?\D)\s+(\d[\d /,-]{8,}\d)$", r.get("division") or "")
            if m:                                  # layout B: pypdf reads the division and its EE phone as one piece
                r["division"] = m.group(1).strip()
                r["ee"] = m.group(2)
            feeders.append((pno, rn, row["_y"], r))
    if not lay_seen:
        return out.recs
    # sub-division identity: layout A its name cell, layout B the SDO phone cell
    sd_key = "subdivision#" if lay_seen == "A" else "sdo#"
    divs, sds, jes = {}, {}, {}
    for pno, rn, y, r in feeders:
        dv = r.get("division")
        if dv:
            d = divs.setdefault(dv, {"ee": [], "at": (pno, rn, y)})
            if r.get("ee") and r["ee"] not in d["ee"]:
                d["ee"].append(r["ee"])
        sk = (dv, r.get(sd_key))
        s = sds.setdefault(sk, {"name": r.get("subdivision"), "sdo": [], "ss": [], "at": (pno, rn, y), "div": dv})
        if r.get("sdo") and r["sdo"] not in s["sdo"]:
            s["sdo"].append(r["sdo"])
        if r.get("substation") and r["substation"] not in s["ss"]:
            s["ss"].append(r["substation"])
        tel = phone(r.get("je")) if r.get("je") else None
        if not tel:
            provenance.skipped("feeder row without a JE phone")
            continue
        provenance.used()
        j = jes.setdefault((sk, tel), {"ss": [], "feeders": [], "at": (pno, rn, y)})
        ssn = r.get("substation")
        if ssn and ssn not in [x["name"] for x in j["ss"]]:
            j["ss"].append({"name": ssn, **({"phone": phone(r.get("ss_phone"))} if phone(r.get("ss_phone")) else {})})
        if r.get("feeder") and r["feeder"] not in j["feeders"]:
            j["feeders"].append(r["feeder"])

    def pos(at):
        return {"page": at[0], "row": at[1], "y": at[2]}

    for dv, d in divs.items():
        out.add(f"{zone}:div:{dv}", "division", dv, post="Executive Engineer", phone_=phone(*d["ee"]) if d["ee"] else None,
                parents={"zone": zname}, src_pos=pos(d["at"]), method="pdf table grid")
    sd_area, sd_id = {}, {}
    for sk, s in sds.items():
        area = s["name"] if lay_seen == "A" else ("SDO: " + ", ".join(s["ss"]) if s["ss"] else None)
        sd_area[sk] = area
        if not area:
            continue
        sd_id[sk] = s["name"] if lay_seen == "A" else "sdo-" + (s["sdo"][0] if s["sdo"] else ",".join(s["ss"][:1]))
        out.add(f"{zone}:sd:{s['div']}:{sd_id[sk]}", "subdivision", area, post="SDO", phone_=phone(*s["sdo"]) if s["sdo"] else None,
                parents={"zone": zname, "division": s["div"]}, substations=s["ss"] or None, src_pos=pos(s["at"]),
                method="pdf table grid")
    for (sk, tel), j in jes.items():
        area = ", ".join(x["name"] for x in j["ss"]) or sd_area.get(sk) or sk[0]
        out.add(f"{zone}:je:{sk[0]}:{sd_id.get(sk)}:{tel}", "section", area, post="JE", phone_=tel,
                parents={"zone": zname, "division": sk[0], "subdivision": sd_area.get(sk)}, substations=j["ss"] or None,
                feeders=j["feeders"] or None, src_pos=pos(j["at"]), method="pdf table grid")
    return out.recs


def _first_rows(rows, role, cid):
    """How many rows from the top of the page share the first cell of this column (the carried cell)."""
    first = rows[0].get(role, (None, None))[1] if rows else None
    if cid != first:
        return 0
    return sum(1 for r in rows if r.get(role, (None, None))[1] == first)


def fetch(p, get):
    if p.get("part") == "se":
        url = p.get("url") or SE_URL
        r = get(url)
        if r is None:
            return [], [], "no answer"
        files = [raw(MOD, "contact-list-of-se-and-above", r.content, "html")]
        recs = parse_se(r.text, url)
        return recs, files, "" if recs else "no rows"
    zone = p.get("zone")
    url = p.get("url") or ZONES.get(zone)
    if not url:
        return [], [], "no zone"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, f"distribution-offices-{zone}", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    recs = parse_zone(r.content, zone, url)
    return recs, files, "" if recs else "no rows (unknown table layout?)"
