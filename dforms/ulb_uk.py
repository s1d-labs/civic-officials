"""Uttarakhand: Urban Development Directorate (udd.uk.gov.in), the statewide list of the officers in charge of every town body.
Answers from outside India too (checked 2026-11-11).

One seed item: the document page udd.uk.gov.in/document-category/list-of-ulb-eo/ ("List Of ULB EO"). fetch() reads the page, takes
the PDF of the row "ULBs EO Contact List" (now cdnbbsr.s3waas.gov.in/.../2026/08/202609211745084968.pdf, dated 21/09/2026 on the
page, "07-09-2026" in the PDF title; each new upload gets a new URL) and the PDF of the row "ULBs Email ID List" (05/08/2026), and
reads both. If the page gives no link, the URLs in the payload are used.

EO list: LibreOffice Calc, 4 ruled pages, set in Kruti Dev 010 (dforms/ulb_uk_krutidev.py turns it into Devanagari). Columns:
serial, district (one cell over all bodies of the district), body ("नगर निगम, देहरादून"), "name, post" (one line per officer: a
nagar nigam lists its nagar ayukt and assistant / deputy commissioners), mobile (one per officer line). About 105 bodies and 125
officers. The rows are read from the ruling: a line across the serial column closes a body row, a line across the district column
closes a district. One record per officer: area = the body name without the type words, body_type = the type words
(नगर निगम / नगर पालिका परिषद / नगर पंचायत), post as written ("अधिशासी अधिकारी श्रेणी-3", "सफाई निरीक्षक/प्रभारी अधिशासी अधिकारी"), role from
the post (_ulb.role_of: "प्रभारी अधिशासी अधिकारी" = head). The email list (serial, district, body, email; Kruti Dev) gives the
office email of each body: it goes on the body's records (matched by body name and type, as both lists write them).
Extra keys: lgd_code (civic.ulb local_body_code from dforms/ulb_uk_lgd.json, 102 of 103 bodies), area_latin / district_latin,
serial, last_updated (the date of the row on the document page). Vacant posts ("रिक्त", no phone) give no record (Laksar, Munsyari,
Bajpur, Nagla on 21/09/2026).
Record and office ids use a Latin form of district + body (ulb_up.latin), because _esw.slug drops Devanagari.
"""
import json
import re
from pathlib import Path

from dforms import _esw, _ulb, ulb_up
from dforms._water import unique
import provenance
from dforms.ulb_uk_krutidev import convert

METHOD = "pdf ruled table (pypdf text runs + rules) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_uk"
PAGE = "https://udd.uk.gov.in/document-category/list-of-ulb-eo/"
EO_PDF = "https://cdnbbsr.s3waas.gov.in/s38208974663db80265e9bfe7b222dcb18/uploads/2026/08/202609211745084968.pdf"
EMAIL_PDF = "https://cdnbbsr.s3waas.gov.in/s38208974663db80265e9bfe7b222dcb18/uploads/2026/08/202608051632633803.pdf"
TYPE = re.compile(r"^(नगर\s*(?:निगम|पालिका\s*परिषद|पा0\s*परिषद|पंचायत))\s*[,]?\s*")
KIND = {"नगर निगम": "nn", "नगर पालिका परिषद": "npp", "नगर पंचायत": "np"}
HONORIFIC = re.compile(r"^(?:श्रीमती|श्रीमति|सुश्री|श्री|कु0|कुमारी)\s*")
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
_LGD = None


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": PAGE, "eo_pdf": EO_PDF, "email_pdf": EMAIL_PDF, "state": "UK",
                                        "india_only": False}}]


def hindi(s):
    """Kruti Dev text -> Devanagari; "]" is the comma, "¼ ½" the brackets, "&" the hyphen, "@" the slash."""
    s = ulb_up.nfc(convert((s or "").replace("]", "\ue001").replace("¼", "\ue002").replace("½", "\ue003")))
    s = s.replace("\ue001", ",").replace("\ue002", "(").replace("\ue003", ")")
    s = s.replace("चैधरी", "चौधरी").replace("चैहान", "चौहान")            # the usual Kruti Dev typing slip for au
    return _esw.clean(s).strip(" ,।")


def links(html):
    """{"eo": (url, date), "email": (url, date)} from the document table of the page."""
    out = {}
    for tr in _esw.soup(html).find_all("tr"):
        tds = tr.find_all("td")
        a = tr.find("a", href=re.compile(r"\.pdf$", re.I))
        if len(tds) < 2 or a is None:
            continue
        title, date = _esw.clean(tds[0].get_text(" ")), _esw.clean(tds[1].get_text(" "))
        m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", date)
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
        for k, rx in (("eo", r"(?i)\bEO\b.*contact"), ("email", r"(?i)e-?mail")):
            if k not in out and re.search(rx, title):
                out[k] = (a["href"], date)
    return out


# ---------------------------------------------------------------- ruled PDF pages -> rows
def page_parts(page, reader):
    """(runs, horizontal lines, vertical x) of one page: runs = [(x, y, text)], lines = [(x0, x1, y)]."""
    from pypdf.generic import ContentStream
    runs = []

    def visit(text, cm, tm, fd, fs):
        if text.strip():
            runs.append((cm[4] + tm[4] * cm[0], cm[5] + tm[5] * cm[3], text))
    page.extract_text(visitor_text=visit)
    hor, ver, cur, ctm = [], set(), None, [(1, 0, 0, 1, 0, 0)]
    for ops, op in ContentStream(page.get_contents(), reader).operations:
        if op == b"q":
            ctm.append(ctm[-1])
        elif op == b"Q" and len(ctm) > 1:
            ctm.pop()
        elif op == b"cm":
            a, b, c, d, e, f = (float(x) for x in ops)
            A, B, C, D, E, F = ctm[-1]
            ctm[-1] = (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)
        elif op == b"m":
            A, B, C, D, E, F = ctm[-1]
            x, y = float(ops[0]), float(ops[1])
            cur = (A * x + C * y + E, B * x + D * y + F)
        elif op == b"l" and cur:
            A, B, C, D, E, F = ctm[-1]
            x, y = float(ops[0]), float(ops[1])
            end = (A * x + C * y + E, B * x + D * y + F)
            if abs(cur[1] - end[1]) < 0.5:
                hor.append((min(cur[0], end[0]), max(cur[0], end[0]), cur[1]))
            elif abs(cur[0] - end[0]) < 0.5:
                ver.add(round(cur[0], 1))
            cur = end
    return runs, hor, sorted(ver)


def bands(hor, x):
    """y values (top down) of the lines that cross x."""
    return sorted({round(y, 1) for x0, x1, y in hor if x0 - 1 <= x <= x1 + 1}, reverse=True)


def band_of(y, ys):
    for i in range(len(ys) - 1):
        if ys[i] + 1 >= y >= ys[i + 1] - 1:
            return i
    return None


def table_rows(content, ncols):
    """Rows of a ruled table: [{"cells": [[(y, text), ...] per column], "district": [...]}] over all pages."""
    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    rows = []
    for pno, page in enumerate(reader.pages, 1):
        runs, hor, ver = page_parts(page, reader)
        if len(ver) < ncols + 1:
            continue
        cols = ver[:ncols + 1]
        mid = [(cols[i] + cols[i + 1]) / 2 for i in range(ncols)]
        body_ys, dist_ys = bands(hor, mid[2]), bands(hor, mid[1])     # the body cell spans the whole row (serial lines do not)
        edge = [y for x0, x1, y in hor if x1 - x0 > 20]                  # the lowest rule closes the last cells of the page
        if edge:
            body_ys = sorted(set(body_ys) | {round(min(edge), 1)}, reverse=True)
            dist_ys = sorted(set(dist_ys) | {round(min(edge), 1)}, reverse=True)
        page_rows = {}
        dist_text = {}
        for x, y, t in runs:
            c = next((i for i in range(ncols) if cols[i] - 2 <= x + 1 < cols[i + 1]), None)
            if c is None:
                continue
            if c == 1:
                k = band_of(y + 3, dist_ys)            # baseline + 3 pt: the middle of the letters
                if k is not None:
                    dist_text.setdefault(k, []).append((y, t))
                continue
            k = band_of(y + 3, body_ys)
            if k is None:
                continue
            page_rows.setdefault(k, [[] for _ in range(ncols)])[c].append((y, t))
        for k in sorted(page_rows):
            top, bottom = body_ys[k], body_ys[k + 1]
            dk = band_of((top + bottom) / 2, dist_ys)
            d = " ".join(t for _, t in sorted(dist_text.get(dk, []), key=lambda r: -r[0]))
            rows.append({"cells": page_rows[k], "district": d, "page": pno, "band": k + 1})
    # a row cut by a page break: the part on the next page has no serial and no body; it joins the row before
    out = []
    for r in rows:
        if out and not r["cells"][0] and not r["cells"][2] and any(r["cells"][3:]):
            for c in range(ncols):
                out[-1]["cells"][c] += [(y - 10000, t) for y, t in r["cells"][c]]
        else:
            out.append(r)
    return out


def body_parts(raw):
    """"uxj fuxe] nsgjknwu" -> ("देहरादून", "नगर निगम")."""
    b = hindi(raw)
    m = TYPE.match(b)
    return (b[m.end():].strip(" ,"), re.sub(r"\s+", " ", m.group(1)).replace("पा0", "पालिका")) if m else (b, None)


POST = re.compile(r"\s(?=(?:प्रभारी|अधिशासी|अधि0|नगर आयुक्त|उप नगर|सहायक|कर |सफाई|मुख्य|प्रधान|वरिष्ठ|कनिष्ठ|लिपिक|प्रशासनिक|"
                  r"अवर अभियन्ता|सहायक अभियन्ता|लेखाकार|राजस्व|स्वच्छता|पर्यावरण)\S*)")


def officer(raw):
    """"Jh vkyksd dqekj ik.Ms;] uxj vk;qDrA" -> ("आलोक कुमार पाण्डेय", "नगर आयुक्त"); without the comma the first post word
    ends the name ("श्री सुनील पुरोहित प्रभारी अधिशासी अधिकारी")."""
    t = hindi(raw)
    if "," not in t:
        t = POST.sub(",", t, count=1)
    name, _, post = t.partition(",")
    name = HONORIFIC.sub("", HONORIFIC.sub("", name.strip())).strip()
    return name, _esw.clean(post).strip(" ,।")


def lgd_code(district, body, body_type):
    """civic.ulb local_body_code of a body as the list writes it (dforms/ulb_uk_lgd.json, matched once)."""
    global _LGD
    if _LGD is None:
        _LGD = json.loads((Path(__file__).parent / "ulb_uk_lgd.json").read_text(encoding="utf-8"))["codes"]
    return _LGD.get(f"{district}|{body}|{body_type}")


def rec(body, post, seen, district=None, **f):
    code = lgd_code(district or "", body, f.get("body_type"))
    if code:
        f["lgd_code"] = code
    _, d = _ulb.record(MODULE, "UK", body, post, set(), district=district, **f)
    lb, ld = ulb_up.latin(body), ulb_up.latin(district or "")
    kind = KIND.get(f.get("body_type") or "", "ulb")
    d["area_latin"] = lb
    if district:
        d["district_latin"] = ld
    d["office_id"] = f"UK-{kind.upper()}-{_esw.slug(ld)}-{_esw.slug(lb)}"
    key = unique(f"UK-{kind}-{_esw.slug(ld)}-{_esw.slug(lb)}-{_esw.slug(ulb_up.latin(post))[:60] or 'office'}", seen)
    return f"dept:{MODULE}:{key}", d


def parse_email(content):
    """{(body, type): email} from the email list (serial, district, body, email)."""
    out = {}
    for r in table_rows(content, 4):
        body = " ".join(t for _, t in sorted(r["cells"][2], key=lambda x: -x[0]))
        mail = _esw.emails(" ".join(t for _, t in r["cells"][3]).replace("/", " "))
        if body and mail:
            out[body_parts(body)] = mail
    return out


def parse_eo(content, url=EO_PDF, emails=None, last_updated=None, email_url=None, src=None):
    """src: provenance.at(answer) of the EO list (the item reads three answers); src_pos = page, ruled row band on the page
    (1-based from the top), y of the officer's line and its raw (Kruti Dev) text; email_from = the email list the email came from."""
    recs, seen, district = [], set(), None
    for r in table_rows(content, 5):
        serial = "".join(t for _, t in r["cells"][0]).strip()
        if not re.fullmatch(r"\d+", serial):
            continue                                     # the heading row
        if r["district"].strip():
            district = hindi(r["district"])
        body, btype = body_parts(" ".join(t for _, t in sorted(r["cells"][2], key=lambda x: -x[0])))
        offs = sorted(r["cells"][3], key=lambda x: -x[0])
        mobs = [(y, m) for y, t in r["cells"][4] for m in MOBILE.findall(t)]
        lines = []                                       # an officer's text can wrap: a line starting with Jh / lqJh starts one
        for y, t in offs:
            if lines and not re.match(r"\s*(?:Jh|lqJh|Jherh|Jhefr|dq0)\b", t) and "]" not in t:
                lines[-1] = (lines[-1][0], lines[-1][1] + " " + t)
            else:
                lines.append((y, t))
        mail = (emails or {}).get((body, btype))
        for y, t in lines:
            name, post = officer(t)
            if not post or name in ("", "रिक्त"):
                continue
            phone = ", ".join(m for my, m in mobs if abs(my - y) < 4)
            pos = {"page": r.get("page"), "row": r.get("band"), "line_text": t}
            if y > -5000:                                # a line from a continuation row on the next page has no y here
                pos["y"] = round(y, 1)
            if mail and email_url:
                pos["email_from"] = email_url
            recs.append(rec(body, post, seen, district=district, name=name, phone=phone, email=mail, body_type=btype, source=url,
                            serial=int(serial), last_updated=last_updated, src_pos=pos, **(src or {})))
    return recs


def fetch(p, get):
    files, eo, email, date = [], (p.get("eo_pdf") or EO_PDF), p.get("email_pdf") or EMAIL_PDF, None
    r = get(p.get("url", PAGE))
    if r is not None:
        files.append(_esw.keep(MODULE, "list-of-ulb-eo", r.content, "html"))
        found = links(r.text)
        if "eo" in found:
            eo, date = found["eo"]
        if "email" in found:
            email = found["email"][0]
    emails = {}
    m = get(email)
    if m is not None and m.content[:5] == b"%PDF-":
        files.append(_esw.keep(MODULE, "ulb-email-list", m.content, "pdf"))
        emails = parse_email(m.content)
    r = get(eo)
    if r is None or r.content[:5] != b"%PDF-":
        return [], files, "no EO list"
    files.insert(0, _esw.keep(MODULE, "ulb-eo-contact-list", r.content, "pdf"))
    recs = parse_eo(r.content, eo, emails, date, email if emails else None, provenance.at(r, eo))
    return recs, files, "" if recs else "no rows"
