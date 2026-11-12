"""Nagpur Municipal Corporation, Fire & Emergency Service: "Fire_Station_Officer_details.pdf" (nmcnagpur.gov.in, Feb 2025
upload, saved on archive.s1d.me 2026-11-11). One page printed from Excel: Sr. No. | Name of Fire Station | Location |
Contact No. landline (STD) | Name of Fire Officer | Designation | Mobile Number | Email ID. Cells wrap over 2-3 lines; the
headquarters row holds two officers (D.F.O and A.D.F.O for Civil Fire Station). 12 stations / officers, all named.
Read with dforms/_pdftext.layout_pages() (imported, not changed) and cut at the header's column starts.
Record ids: dept:emerg_fire_nagpur:<slug of the station>. No date in the PDF; the URL path says 2025/02.
"""
import re

from dforms import _emerg, _pdftext
from provenance import line_pos

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_nagpur"
URL = "https://nmcnagpur.gov.in/assets/300/2025/02/mediafiles/Fire_Station_Officer_details.pdf"
HEADS = ("Name Of Fire Station", "Location", "Contact No.", "Name of Fire", "Mobile", "Email ID")
POSTS = {"D.F.O": "Divisional Fire Officer", "A.D.F.O": "Assistant Divisional Fire Officer", "Sub-Officer": "Sub Officer"}


def items(get=None):
    return _emerg.seed(MODULE)


def starts(lines):
    """Column starts from the header lines: [sn, station, location, landline, name, designation, mobile, email]."""
    for i, ln in enumerate(lines):
        if all(h in ln for h in HEADS):
            xs = [0] + [ln.index(h) - 2 for h in HEADS]
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            d = nxt.find("Designation")
            xs.insert(5, d - 4 if d > 0 else (xs[4] + xs[5]) // 2)
            body = lines[i + 2:]
            # header words are centred: move the location, landline, name, mobile and email starts left to where the cells start
            moved = _pdftext.settle(xs, body, left=12, right=1)
            xs = [xs[0], min(xs[1], 4)] + moved[2:5] + [xs[5]] + moved[6:]
            return xs, i + 2
    return None, 0


def blocks(text):
    """[(sn, [cells per line])]: a row starts at a line whose first cell is a number or whose name cell starts with Shri/Smt."""
    lines = text.splitlines()
    xs, k = starts(lines)
    if not xs:
        return []
    out = []
    for li, ln in enumerate(lines[k:], k):
        if not ln.strip() or re.search(r"Chief Fire Officer|Fire & Emergency Service\s*$|NMC Nagpur\s*$", ln) and len(ln.strip()) < 40:
            continue
        cells = _pdftext.cut(ln, xs)
        new = re.fullmatch(r"\d{1,3}", cells[0]) or re.match(r"(?i)^(shri|smt)\b", cells[4])
        if new or not out:
            out.append([cells[0] if re.fullmatch(r"\d{1,3}", cells[0]) else (out[-1][0] if out else ""), [], li])
        out[-1][1].append(cells)
    return out


def records(text, url, at=None, engine=None):
    recs, seen = [], set()
    lines = text.splitlines()
    for sn, rows, li in blocks(text):
        pos = line_pos(*at[li], lines[li]) if at and li < len(at) else {"line": li + 1, "line_text": lines[li]}
        pos["lines"] = len(rows)
        col = [" ".join(r[i] for r in rows if i < len(r) and r[i]).strip() for i in range(8)]
        allt = " ".join(" ".join(r) for r in rows)
        station = _emerg.clean(col[1])
        name = _emerg.clean(re.sub(r"(?i)\b(D\.F\.O|A\.D\.F\.O|Sub-Officer)\b", " ", col[4]))
        post = next((v for k, v in POSTS.items() if re.search(r"(?<![\w.])" + re.escape(k) + r"(?![\w])", allt)), None)
        mobiles = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", col[6] + " " + col[5] + " " + col[7])
        land_rx = r"0?712\s*-\s*\d{6,7}/?(?:\s*\d{7})?"
        land = [x.strip("/ ") for x in re.findall(land_rx, col[2] + " " + col[3])]
        land += [x for x in re.findall(r"(?<![\d-])\d{7}(?!\d)", re.sub(land_rx, " ", col[3])) if land]   # "0712-2567777/ 2567029"
        land = ", ".join(land)
        address = _emerg.clean(re.sub(land_rx, " ", col[2]))
        typo = "&gmail" in col[7]
        email = _emerg.emails(col[7].replace("&gmail", "@gmail"))
        if not station or not name:
            continue
        key = _emerg.unique(_emerg.slug(re.sub(r"(?i)\(head quarter\)", "hq", station))[:60], seen)
        recs.append(_emerg.record(
            MODULE, key, "fire", dept="fire", level="facility", area=station, post=post, name=name,
            phone=", ".join(x for x in (land, ", ".join(mobiles)) if x), landline=land, mobile=", ".join(mobiles), email=email,
            email_as_written=_emerg.clean(col[7]) if typo else None, address=address, district="Nagpur", body="Nagpur Municipal Corporation", state="MH",
            office_id=key, source=url, src_pos=pos, **({"method": f"pdf text ({engine}), columns cut at the header"} if engine else {})))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    pages, engine = _pdftext.layout_pages(r.content)
    at = [(pn, k) for pn, pg in enumerate(pages, 1) for k, _ in enumerate(pg.split("\n"), 1)]
    recs = records("\n".join(pages), url, at, _emerg.ENGINE.get(engine))
    return recs, [_emerg.keep(MODULE, "fire-station-officers", r.content, "pdf")], "" if recs else "no rows"
