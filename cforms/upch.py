"""Uttar Pradesh and Uttarakhand: elected heads of urban local bodies (chairpersons and mayors), from the states' own lists.

- UP (Directorate of Local Bodies, localbodies.up.nic.in/pdf/): elected-npp.pdf (नगर पालिका परिषद: अध्यक्ष, 6 pages) and
  elected-np.pdf (नगर पंचायत: अध्यक्ष, 16 pages). Columns: क्रमांक | जनपद | निकाय का नाम | पद का आरक्षण | उम्मीदवार |
  पिता/पति | मोबाइल नं०. (elected-nn.pdf, the mayors, is the 2017 list and is not queued.)
- Uttarakhand (Urban Development Department, udd.uk.gov.in/newly-elected-public-representatives/): "Mayor and Chairman list"
  (11 pages). Columns: क्र.सं. | जनपद | निकाय का नाम | पद/Designation | नाम | मोबाइल नं.
The files are printed from a browser, Excel or Google Sheets: their text layer drops parts of Devanagari conjuncts, so the
pages are read by OCR (Tesseract hin) with the grid reader of cforms/hr.py (ruled table, one column at a time).
Records are type "councillor" with ward_no "chair" and position "Chairperson" or "Mayor".
Record id councillor:<UP|UK>:<district>-<body>:chair. One queue item = one PDF and a page range (payload first, last).
"""
import hashlib
import os
import re
import tempfile

from cforms import hr

METHOD = "ocr tesseract"     # source trail (provenance.py): how this reader reads its sources

COLS = {"UP": ["sr", "district", "body", "reservation", "name", "father", "phone"],
        "UK": ["sr", "district", "body", "designation", "name", "phone"]}
TYPES = [("नगर निगम", "Municipal Corporation"), ("नगर पालिका परिषद", "Municipal Council"), ("नगर पंचायत", "Nagar Panchayat")]
HEAD = re.compile(r"जनपद|निकाय|नकाय|उम्मीदवार|मोबाइल|Designation|आरक्षण")


def norm(s):
    s = hr.clean(s).replace("।", "")
    s = s.replace("‌", "").replace("‍", "")
    return re.sub(r"\s+([ािीुूृेैोौंँः्])", r"\1", s)      # OCR splits vowel signs off their letter


def reservation(s):
    s = norm(s)
    if re.search(r"जनजाति", s):
        base = "Scheduled Tribe"
    elif re.search(r"अनुसूचित|जाति", s):
        base = "Scheduled Caste"
    elif re.search(r"पिछड़ा|पिछडा|पिछ", s):
        base = "Backward Class"
    elif re.search(r"अनार", s):
        base = "Unreserved"
    else:
        base = ""
    women = bool(re.search(r"महिला", s))
    if not base:
        return "Women" if women else s
    return base + (" (Women)" if women else "")


def phone(s):
    d = re.sub(r"\D", "", s or "")
    return d if len(d) == 10 and d[0] in "6789" else None


def split_body(text, default):
    """UK prints the type with the name: "नगर पालिका परिषद, विकासनगर"."""
    t = norm(text)
    for hi, en in TYPES:
        loose = r"\s*".join(re.escape(ch) for ch in hi.replace(" ", ""))
        m = re.match(rf"\s*{loose}\s*,?\s*(.*)$", t)
        if m and m.group(1):
            return m.group(1).strip(" ,"), en, hi
    return t, default[0], default[1]


def fetch(p, get):
    st = p["state"]
    if not hr.tools():
        return [], [], "tesseract not available"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    first, last = int(p.get("first", 1)), int(p.get("last", 1))
    files = [(f"councillors/{st}/{key}.pdf", r.content, "application/pdf")] if first == 1 else []
    cols = p.get("cols") or COLS[st]
    recs, seen = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(r.content)
        for pg in range(first, last + 1):
            for row in hr.table(pdf, pg, tmp, p.get("lang", "hin")):
                if len(row["cells"]) != len(cols):
                    continue
                c = dict(zip(cols, row["cells"]))
                if (HEAD.search(" ".join(row["cells"][:4])) or not norm(c.get("name")) or not norm(c.get("body"))
                        or re.search(r"स्थित|के नाम", " ".join(row["cells"]))):     # title row inside the frame
                    continue
                body, btype, btype_hi = split_body(c["body"], (p.get("body_type"), p.get("body_type_hi")))
                desig = norm(c.get("designation", ""))
                position = "Mayor" if re.search(r"मेयर|महापौर", desig) or btype == "Municipal Corporation" else "Chairperson"
                district = norm(c["district"])
                d = {"type": "councillor", "state": st, "body": body, "body_type": btype, "body_type_local": btype_hi,
                     "district": district, "ward_no": "chair", "name": norm(c["name"]),
                     "father_or_husband": norm(c.get("father")) or None, "phone": phone(c.get("phone")),
                     "reservation": reservation(c["reservation"]) if c.get("reservation") else None,
                     "reservation_local": norm(c.get("reservation")) or None, "designation_local": desig or None,
                     "position": position, "election": p.get("election"), "url": p["url"], "page": pg, "read": "ocr"}
                place = re.sub(r"[\s,]+", "-", f"{district} {body}")[:60]
                rid = f"councillor:{st}:{place}:chair"
                n = seen[rid] = seen.get(rid, 0) + 1
                recs.append((rid + (f"-{n}" if n > 1 else ""), {k: v for k, v in d.items() if v not in (None, "")}))
    return recs, files, "" if recs else "no heads read"
