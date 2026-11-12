"""Maharashtra: registration offices (DIG, JDR = district registrar, Joint / Sub Registrar offices) from the IGR's division lists,
igrmaharashtra.gov.in/pdf/documents/offices/<Division> Div.pdf (linked on /Home/organisation?tab=offices; the site spells two
file names "Nigpur Div.pdf" and "Nishik Div.pdf"). India only. One queue item = one PDF (8 divisions + "Other COS" = stamp
offices). Columns: Sr. No, DIG, JDR (district), Name of Office, Address, Pincode, e-mail, landline, latitude, longitude, office
time. The column order differs from file to file, so the reader does not use positions: it cuts each page's layout text
(pypdf layout mode) into columns at the blank gutters, gives each record the lines between its row number and the next, and
names the columns by their content (e-mail, PIN, landline, coordinates, office time; then of the text columns the longest is the
address, the next the office, the first two the DIG and the district). Landlines that the sheet turned into "2.17E+09" are dropped.
Where the gutters between the e-mail, PIN, landline, coordinate and time columns move from row to row, the page-wide columns join
them into one cell; the reader then cuts the columns again from that record's own lines, and in any case sorts the parts of an
e-mail cell by kind (mail_cell). A landline whose leading 0 the sheet dropped ("2512- 688722", "2484221511": an STD code and
number of 10 digits that does not start like a mobile number) gets the 0 back (std0).
Record ids: dept:sro_mh:MH-SRO-<slug of district>-<slug of office>.
"""
import re

import provenance
from dforms import _esw
from dforms._pdftext import block_pos

METHOD = "pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_mh"
BASE = "https://igrmaharashtra.gov.in/pdf/documents/offices/"
FILES = {"pune": "Pune Div.pdf", "mumbai": "Mumbai Div.pdf", "thane": "Thane Div.pdf", "nashik": "Nishik Div.pdf",
         "nagpur": "Nigpur Div.pdf", "amravati": "Amravati Div.pdf", "aurangabad": "Aurangabad Div.pdf", "latur": "Latur Div.pdf",
         "other-cos": "Other COS.pdf"}
ANCHOR = re.compile(r"^\s{0,4}(\d{1,3})(?=\s{2,}\S|\s*$)")
HEADER = re.compile(r"Pincode|Lattitude|Latitude|Longitude|Mail ID|Holidays|Name of", re.I)
HEAD_WORDS = {"No", "No.", "Office", "Landline", "ID", "Time", "and", "weekly", "Holidays"}
TIME = re.compile(r"\b(AM|PM|Am|Pm)\b|Sunday|Saturday|\(Every|Holiday")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": BASE + f.replace(" ", "%20"), "state": "MH", "division": k,
                                                  "india_only": True}} for k, f in FILES.items()]


def columns(lines):
    """Column ranges (start, end) of a page: x positions that are blank on every line split the columns; gaps of one blank are
    joined (words inside a cell), slivers of one or two characters join the column to their left."""
    w = max((len(l) for l in lines), default=0)
    occ = [any(len(l) > x and l[x] != " " for l in lines) for x in range(w)]
    cols, start = [], None
    for x in range(w + 1):
        o = occ[x] if x < w else False
        if o and start is None:
            start = x
        elif not o and start is not None:
            cols.append([start, x])
            start = None
    out = []
    for c in cols:
        if out and (c[0] - out[-1][1] <= 1 or c[1] - c[0] <= 2):
            out[-1][1] = c[1]
        else:
            out.append(c)
    return out


def refine(cols, block):
    """The page's columns, with the column that holds the e-mail cut again at the gutters of one record's own lines (the
    other columns stay as they are, so the headings still name them)."""
    bc = columns([l for l in block if l.strip()])
    out = []
    for a, b in cols:
        has_at = any("@" in l[a:b] for l in block)
        inner = []
        for x, y in bc:
            if x < b and y > a:
                if inner and max(a, x) - inner[-1][1] <= 2:
                    inner[-1][1] = min(b, y)             # words two blanks apart: one cell ("SINGH  SQUARE,")
                else:
                    inner.append([max(a, x), min(b, y)])
        out.extend(inner if has_at and len(inner) > 1 else [[a, b]])
    return out


def cells(block, cols):
    """Text of each column in one record's lines, top to bottom."""
    out = [[] for _ in cols]
    for line in block:
        for m in re.finditer(r"\S+(?: \S+)*", line):
            x = m.start()
            i = next((k for k, (a, b) in enumerate(cols) if a - 1 <= x < b), None)
            if i is None:
                i = min(range(len(cols)), key=lambda k: abs(cols[k][0] - x))
            t = m.group()
            if out[i] and cols[i][1] - cols[i][0] <= 12 and re.search(r"[a-z]$", out[i][-1]) and re.match(r"[a-z]", t):
                out[i][-1] += t                          # a word the narrow cell broke: "Solapu" + "r"
            else:
                out[i].append(t)
    return out


def coord(s):
    """18.52258 or 18°31'22" N -> float; None if not a coordinate."""
    s = s.replace(" ", "")
    m = re.match(r"^(\d{1,2}\.\d{3,})", s)
    if m:
        return float(m.group(1))
    m = re.match(r"^(\d{1,2})[°\"'`.:](\d{1,2})['`.:](\d{1,2}(?:\.\d+)?)?", s)
    if m:
        d, mi, se = int(m.group(1)), int(m.group(2)), float(m.group(3) or 0)
        if mi < 60 and se < 60:
            return round(d + mi / 60 + se / 3600, 6)
    return None


def classify(texts, cols=None, labels=None):
    """{field: text} from the column texts of one record; text columns are also named by the nearest heading ("named")."""
    f, text_cols, named = {}, [], {}
    for i, parts in enumerate(texts):
        if not parts:
            continue
        joined = " ".join(parts)
        squeezed = "".join(parts)
        if i == 0 and ANCHOR.match(parts[0]) and len(joined) <= 4:
            continue
        if "@" in squeezed and "email" not in f:
            m = mail_cell(parts)
            f["email"] = m["mail"]
            if m["pin"]:
                f.setdefault("pincode", m["pin"])
            if m["phone"] and "landline" not in f:
                f["landline"] = m["phone"]
            if m["coords"]:
                f.setdefault("coords", []).extend(m["coords"])
            if m["time"] and "time" not in f:
                f["time"] = m["time"]
            if m["mixed"]:
                f["mixed"] = True
        elif TIME.search(joined):                        # a coordinate can share the office time's cell: ",77.706575"
            co = [x for x in parts if COORD_PART.fullmatch(x) and coord(x.lstrip(",")) is not None and coord(x.lstrip(",")) > 5]
            if co:
                f.setdefault("coords", []).extend(coord(x.lstrip(",")) for x in co)
            f["time"] = " ".join(x for x in parts if x not in co)
        elif re.fullmatch(r"\d{3}\s?\d{3}( \d{3}\s?\d{3})*", joined):
            f.setdefault("pincode", joined.split(" ")[0])
        elif COORD_PART.fullmatch(joined) and coord(parts[0].lstrip(",")) is not None and coord(parts[0].lstrip(",")) > 5:
            f.setdefault("coords", []).append(coord(parts[0].lstrip(",")))
        elif re.fullmatch(r"(NA|[\d\s/,+()-]+|\d\.\d+E\+\d+)(\s+(NA|[\d\s/,+()-]+))*", joined):
            if "E+" not in joined and "NA" != joined.strip():
                f["landline"] = squeezed if re.fullmatch(r"0\d{2,4}-", parts[0]) else joined
        elif re.search(r"\d{5}", joined) and all(PHONE_PART.fullmatch(x) or COORD_PART.fullmatch(x) for x in joined.split()):
            m = mail_cell(joined.split())                # a landline and a coordinate in one cell: "02552-242060 20°18'19"N"
            if m["phone"] and "landline" not in f:
                f["landline"] = m["phone"]
            f.setdefault("coords", []).extend(m["coords"])
            if m["pin"]:
                f.setdefault("pincode", m["pin"])
        else:
            text_cols.append(joined)
            if cols and labels:
                a, b = cols[i]
                hit = [k for k, x in labels.items() if a - 4 <= x < b + 4]
                if hit:
                    k = min(hit, key=lambda k: abs(labels[k] - (a + b) / 2))
                    named[k] = (named[k] + " " + joined) if k in named else joined
    f["text"] = text_cols
    f["named"] = named
    return f


COORD_PART = re.compile(r"[\d°\"'`.:,\s]+[NE°`\"\s]*")
PHONE_PART = re.compile(r"(NA|na|N\.A\.?|[\d\s/,+()-]+|\d\.\d+E\+\d+)")


def mail_cell(parts):
    """The parts of a cell that holds an e-mail, sorted by kind. When the page-wide columns join the e-mail column with the
    columns beside it, the cell also holds the PIN, the landline, the coordinates and the office time ("sr.pulgaon@igr...gov.in",
    "7158282040", "20.72560903", "78.321038", "09:45 AM ..."). The e-mail is the part with "@" and the pieces of an address that
    wraps over lines ("jdr.latur@igrmaharashtra.g" + "ov.in"); other words ("mixed") are text of other columns."""
    out = {"mail": "", "pin": None, "phone": "", "coords": [], "time": "", "mixed": False}
    mail, phone, seen_at = [], [], False
    for k, p in enumerate(parts):
        q = p.strip()
        m = re.match(r"^(\d{3}\s?\d{3})\s*(?=[A-Za-z][^\s@]*@)", q)
        if m:                                            # PIN and e-mail one blank apart: "411015 dig.pune@igrmahar"
            out["pin"] = out["pin"] or m.group(1).replace(" ", "")
            q = q[m.end():]
        nxt = parts[k + 1].strip() if k + 1 < len(parts) else ""
        if "@" in q:
            mail.append(q.replace(" ", ""))
            seen_at = True
        elif not seen_at and nxt.startswith("@") and re.fullmatch(r"[\w.-]+", q):
            mail.append(q)                               # "sr.vasmat" + "@igrmaharashtra.gov.in"
        elif TIME.search(q):
            out["time"] = (out["time"] + " " + q).strip()
        elif re.fullmatch(r"\d{3}\s?\d{3}", q):
            out["pin"] = out["pin"] or q.replace(" ", "")
        elif re.fullmatch(r"\d*\s*[NE]", q):
            pass                                         # the end of a coordinate: "79.376731" + "6 E"
        elif COORD_PART.fullmatch(q) and coord(q.lstrip(",")) is not None and coord(q.lstrip(",")) > 5:
            out["coords"].append(coord(q.lstrip(",")))
        elif PHONE_PART.fullmatch(q) and re.search(r"\d", q):
            phone.append(q)
        elif seen_at and re.fullmatch(r"[\w.,/@-]+", q) and re.search(r"[a-z]", q):
            mail.append(q)                               # the rest of a wrapped address: "ov.in", "n", ".in"
        elif PHONE_PART.fullmatch(q):
            pass                                         # "NA"
        else:
            out["mixed"] = True
    out["mail"] = "".join(mail)
    if phone:
        out["phone"] = "".join(phone) if re.fullmatch(r"0\d{2,4}-", phone[0]) else " ".join(phone)
    return out


def std0(s):
    """A landline whose leading 0 the sheet dropped gets it back: "2512- 688722" -> "02512-688722", "2484221511" -> "02484221511".
    Only an STD code + number of 10 digits that does not start with 6-9 (a mobile number) is changed."""
    out = []
    for x in [x.strip() for x in s.split(",")] if s else []:
        m = re.fullmatch(r"([1-5]\d{1,4})\s*-\s*(\d{5,8})", x)
        if m and len(m.group(1) + m.group(2)) == 10:
            x = f"0{m.group(1)}-{m.group(2)}"
        elif re.fullmatch(r"[1-5]\d{9}", x):
            x = "0" + x
        out.append(x)
    return ", ".join(out)


def header_labels(lines):
    """x of the text columns' headings: DIG, JDR (or COS), Name of (office), Address."""
    out = {}
    for l in lines:
        for key, rx in (("dig", r"\bDIG\b"), ("district", r"\b(JDR|COS)\b"), ("office", r"Name of"), ("address", r"\bAddress\b")):
            m = re.search(rx, l)
            if m and key not in out:
                out[key] = m.start() + len(m.group()) / 2
    return out if {"office", "address"} <= set(out) else None


def parse_pages(pages, url, division=None):
    recs, seen, labels, rows = [], set(), None, []
    for n, page in enumerate(pages):
        lines = page.split("\n")
        anchors = [i for i, l in enumerate(lines) if ANCHOR.match(l)]
        if not anchors:
            continue
        first = anchors[0]
        head = max([i for i, l in enumerate(lines[:first]) if HEADER.search(l)] or [-1])
        if head >= 0:
            labels = header_labels(lines[:head + 1]) or labels
            while head + 1 < first and lines[head + 1].strip() and set(lines[head + 1].split()) <= HEAD_WORDS:
                head += 1                                # the heading's second line: "No ... Landline No"
        body = [l for l in lines[head + 1:]]
        anchors = [i - head - 1 for i in anchors if i > head]
        cols = columns([l for l in body if l.strip()])
        if len(cols) < 5:
            continue
        for k, a in enumerate(anchors):
            lo = 0 if k == 0 else cut(body, anchors[k - 1], a)
            hi = len(body) if k == len(anchors) - 1 else cut(body, a, anchors[k + 1])
            block = [l for l in body[lo:hi] if l.strip()]
            f = classify(cells(block, cols), cols, labels)
            if f.get("mixed"):                           # the page's columns joined the e-mail with other cells: cut that
                rc = refine(cols, block)                 # column again at the gutters of this row's own lines
                if rc != cols:
                    g = classify(cells(block, rc), rc, labels)
                    if not g.get("mixed"):
                        f = g
            sr = ANCHOR.match(body[a]).group(1)
            t = f["text"]
            named = f.get("named", {})
            if labels and len(t) == len(labels) and set(named) != set(labels):
                named = dict(zip(sorted(labels, key=labels.get), t))   # one text cell per heading: name them in heading order
            if len(t) < 2 and not named.get("office"):
                continue
            if named.get("office") and named.get("address"):
                addr, office, dig, dist = named["address"], named["office"], named.get("dig", ""), named.get("district", "")
                small = [x for x in t if x not in (addr, office)]
                if not dig and small:                    # a narrow DIG / JDR cell that its heading does not reach
                    dig = small[0]
                if not dist and small:
                    dist = small[1] if len(small) > 1 else small[0]
            else:                                        # no headings: the longest text is the address, the next the office
                addr = max(t, key=len)
                rest = [x for x in t if x is not addr]
                office = max(rest, key=len) if rest else ""
                small = [x for x in rest if x is not office]
                dig = small[0] if small else ""
                dist = small[1] if len(small) > 1 else (small[0] if small else "")
            office = re.sub(r"(\w)- (\w)", r"\1-\2", office)
            m = re.match(r"([a-z]+)\s+(.*)$", office)
            if m and rows and re.search(r"[A-Za-z]$", rows[-1]["office"]):
                rows[-1]["office"] += m.group(1)          # the end of the previous row's broken name: "Mahabal" + "eshwar"
                office = m.group(2)
            rows.append({"office": office, "dist": dist, "dig": dig, "addr": addr, "f": f, "sr": int(sr),
                         "pos": block_pos(n + 1, lines, [head + 1 + j for j in range(lo, hi) if body[j].strip()])})
    for row in rows:
        office, dist, f, addr = row["office"], row["dist"], row["f"], row["addr"]
        post = "DIG of Registration" if re.match(r"DIG\b", office) else \
            "Joint District Registrar" if re.match(r"(JDR|Join\w*\s*District)", office, re.I) else \
            "Joint Sub Registrar" if re.match(r"(Joint S|JSR|Jt)", office, re.I) or re.search(r"Haveli \d", office) else "Sub Registrar"
        level = {"DIG of Registration": "division", "Joint District Registrar": "district"}.get(post, "subdistrict")
        if division == "other-cos":                     # stamp offices (Collector of Stamps), not registration offices
            post, level = "Collector of Stamps", "office"
        area = re.sub(r"\b(Joint|Jt\.?|Join\w*|Sub|Registrar|Registar|District|S\.\s*R\.|R\.|S\.|Grade-?\s*\d|Class-?\s*\d|Office|DIG|JDR|"
                      r"SRO)(?=\W|$)[,.]?", " ", office, flags=re.I)
        area = _esw.clean(re.sub(r"^[\s,.-]+|[\s,.-]+$", "", area))
        oid = f"MH-SRO-{_esw.slug(dist)}-{_esw.slug(office)}"
        key, i = oid, 2
        while key in seen:
            key, i = f"{oid}-{i}", i + 1
        seen.add(key)
        co = f.get("coords") or []
        lat = co[0] if co and 15 < co[0] < 23 else None
        lon = co[1] if len(co) > 1 and 72 < co[1] < 81 else None
        pin = f.get("pincode") or ""
        recs.append(_esw.record(MODULE, key, dept="registration", level=level, area=area or office, post=post, office=office,
                                dig=row["dig"], phone=std0(_esw.phones(f.get("landline", ""))), email=_esw.emails(f.get("email", "")),
                                address=addr if pin in addr else f"{addr} {pin}", pincode=pin, state="MH", district=dist,
                                office_id=key, source=url, lat=lat, lon=lon, sr_no=row["sr"], division=division,
                                office_time=f.get("time"), src_pos=row.get("pos")))
    return recs


def cut(lines, a, b):
    """Where the lines of the row at line a end and the row at line b begins: the blank line nearest the middle, else the middle."""
    mid = (a + b + 1) / 2
    blanks = [i for i in range(a + 1, b) if not lines[i].strip()]
    if blanks:
        return min(blanks, key=lambda i: abs(i - mid))
    return int(mid + 0.5) if (b - a) % 2 == 0 else int(mid)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    name = _esw.slug(p.get("division") or p["url"].rsplit("/", 1)[-1])
    files = [_esw.keep(MODULE, name, r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse_pages(pages, p["url"], p.get("division"))
    return recs, files, "" if recs else "no rows"
