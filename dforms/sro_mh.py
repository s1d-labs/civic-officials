"""Maharashtra: registration offices (DIG, JDR = district registrar, Joint / Sub Registrar offices) from the IGR's division lists,
igrmaharashtra.gov.in/pdf/documents/offices/<Division> Div.pdf (linked on /Home/organisation?tab=offices; the site spells two
file names "Nigpur Div.pdf" and "Nishik Div.pdf"). India only. One queue item = one PDF (8 divisions + "Other COS" = stamp
offices). Columns: Sr. No, DIG, JDR (district), Name of Office, Address, Pincode, e-mail, landline, latitude, longitude, office
time. The column order differs from file to file, so the reader does not use positions: it cuts each page's layout text
(pypdf layout mode) into columns at the blank gutters, gives each record the lines between its row number and the next, and
names the columns by their content (e-mail, PIN, landline, coordinates, office time; then of the text columns the longest is the
address, the next the office, the first two the DIG and the district). Landlines that the sheet turned into "2.17E+09" are dropped.
Record ids: dept:sro_mh:MH-SRO-<slug of district>-<slug of office>.
"""
import re

from dforms import _esw

MODULE = "sro_mh"
BASE = "https://igrmaharashtra.gov.in/pdf/documents/offices/"
FILES = {"pune": "Pune Div.pdf", "mumbai": "Mumbai Div.pdf", "thane": "Thane Div.pdf", "nashik": "Nishik Div.pdf",
         "nagpur": "Nigpur Div.pdf", "amravati": "Amravati Div.pdf", "aurangabad": "Aurangabad Div.pdf", "latur": "Latur Div.pdf",
         "other-cos": "Other COS.pdf"}
ANCHOR = re.compile(r"^\s{0,4}(\d{1,3})(?=\s{2,}\S|\s*$)")
HEADER = re.compile(r"Pincode|Lattitude|Latitude|Longitude|Mail ID|Holidays|Name of", re.I)
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
    m = re.match(r"^(\d{1,2})[°\"'.:](\d{1,2})['.:](\d{1,2}(?:\.\d+)?)?", s)
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
            m = re.match(r"^(\d{6})(?=[A-Za-z])", squeezed)
            if m:                                        # PIN and e-mail one blank apart: one column
                f.setdefault("pincode", m.group(1))
                squeezed = squeezed[6:]
            f["email"] = squeezed
        elif TIME.search(joined):
            f["time"] = joined
        elif re.fullmatch(r"\d{3}\s?\d{3}( \d{3}\s?\d{3})*", joined):
            f.setdefault("pincode", joined.split(" ")[0])
        elif re.fullmatch(r"[\d°\"'.:,\s]+[NE]?(\s*[NE°])*", joined) and coord(parts[0]) is not None and coord(parts[0]) > 5:
            f.setdefault("coords", []).append(coord(parts[0]))
        elif re.fullmatch(r"(NA|[\d\s/,+()-]+|\d\.\d+E\+\d+)(\s+(NA|[\d\s/,+()-]+))*", joined):
            if "E+" not in joined and "NA" != joined.strip():
                f["landline"] = squeezed if re.fullmatch(r"0\d{2,4}-", parts[0]) else joined
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
            while head + 1 < first and lines[head + 1].strip() in ("No", "No.", "Office", "No Office", "Office No"):
                head += 1
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
            sr = ANCHOR.match(body[a]).group(1)
            t = f["text"]
            named = f.get("named", {})
            if len(t) < 2 and not named.get("office"):
                continue
            if named.get("office") and named.get("address"):
                addr, office, dig, dist = named["address"], named["office"], named.get("dig", ""), named.get("district", "")
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
            rows.append({"office": office, "dist": dist, "dig": dig, "addr": addr, "f": f, "sr": int(sr)})
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
                                dig=row["dig"], phone=_esw.phones(f.get("landline", "")), email=_esw.emails(f.get("email", "")),
                                address=addr if pin in addr else f"{addr} {pin}", pincode=pin, state="MH", district=dist,
                                office_id=key, source=url, lat=lat, lon=lon, sr_no=row["sr"], division=division,
                                office_time=f.get("time")))
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
