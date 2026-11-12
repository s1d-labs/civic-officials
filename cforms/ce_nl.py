"""Nagaland: ward members of the 3 municipal councils and 22 town councils elected on 26.06.2024 (results 29.06.2024).

Source: State Election Commission Nagaland notification No. SEC/ELE-RESULT/2024/279 of 01.07.2024 (Nagaland Municipal Act
2023, section 44), printed as Nagaland Gazette Extraordinary No. 179 of 01.07.2024. The press posts extraordinary issues
only inside its fortnightly "mastercopy" PDFs: No. 179 is pages 50-75 of the issue of 31.08.2024,
govtpress.nagaland.gov.in/wp-content/uploads/2017/09/mastercopy-31-Aug.pdf (17.3 MB, 110 pages, a scan: the text layer
has only the page headers). Page 50 is the notification ("278 Wards across 25 Municipalities"), pages 51-75 are one body
each: a heading "<NAME> MUNICIPAL/TOWN COUNCIL", then a ruled table Ward No. | Ward Name | Reservation status | Name of
Candidate | Gender | Party that Won | Remarks (Dimapur has no Ward Name column), then two small summary tables (totals and
seats per party).
The page is rendered and cut below the member table (the summary tables would add vertical lines), then read with the grid
reader of cforms/hr.py (lines found and erased, Tesseract eng per column). Columns are found from the header row. The body
of each page comes from the payload ("bodies": {page: [name, LGD code]}), checked by eye on the page headings.
One queue item = a few pages. The first item saves the PDF in the bucket; the others read the saved copy (payload "stored",
see cforms/tn.py stored()). The site answers outside India (the archive's pool copies of the 2024 issues failed, unchecked why).
Record id councillor:NL:<body slug>:<ward no>.
"""
import concurrent.futures
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

from cforms import hr
from cforms.tn import stored

METHOD = 'ocr tesseract eng (gazette scan)'     # source trail (provenance.py): how this reader reads its sources

URL = "https://govtpress.nagaland.gov.in/wp-content/uploads/2017/09/mastercopy-31-Aug.pdf"
ELECTION = ("Nagaland ULB general election 2024 (poll 26.06.2024, results 29.06.2024; SEC notification "
            "SEC/ELE-RESULT/2024/279 of 01.07.2024, Nagaland Gazette Extraordinary No. 179)")
ROLES = [("ward_no", r"ward\s*n[o0]|^ward$|^no\.?$"), ("ward_name", r"ward\s*na|^name$"), ("reservation", r"reserv|status"),
         ("name", r"candid|name\s*of"), ("gender", r"gend"), ("party", r"party|won"), ("remarks", r"remark")]
PARTIES = [("NDPP", r"N\W*D\W*P\W*P|NDP"), ("NPP", r"^N\W*P\W*P$|^NPP"), ("BJP", r"B\W*J\W*P"), ("NPF", r"N\W*P\W*F"),
           ("INC", r"I\W*N\W*C|CONG"), ("JD(U)", r"J\W*D"), ("LJP(RV)", r"L\W*J\W*P"), ("RPI(A)", r"R\W*P\W*I"),
           ("NCP", r"N\W*C\W*P"), ("IND", r"^I\W*N\W*D|INDEP|^1ND")]


def tools():
    if shutil.which("tesseract") and shutil.which("pdftoppm"):
        return True
    cmd = "sudo -n apt-get update -q && sudo -n apt-get install -y -q tesseract-ocr tesseract-ocr-eng poppler-utils"
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0 and bool(shutil.which("tesseract"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def party(s):
    t = hr.clean(s).upper().replace("0", "O")
    for code, rx in PARTIES:
        if re.search(rx, t):
            return code
    return hr.clean(s)


def gender(s):
    t = hr.clean(s).upper()
    return "F" if t.startswith(("F", "E")) else "M" if t.startswith(("M", "N", "H")) else t or None


def reservation(s):
    t = re.sub(r"[^a-z]", "", (s or "").lower())
    return "Unreserved" if t.startswith("un") or "unres" in t else "Reserved" if "reser" in t or "serv" in t else hr.clean(s)


def main_bottom(w, h, data, minrun=250):
    """Bottom (y) of the longest vertical rule on the page: the member table's border. The summary tables below it are
    shorter, so cutting there leaves only the member table."""
    bits = data.translate(hr.LINE)
    best = (0, 0)
    for x in range(1, w - 1, 2):
        col = hr._pool([bytes(bits[x + k::w]) for k in (-1, 0, 1)])
        for m in re.finditer(rb"\x01{%d,}" % minrun, col):
            if m.end() - m.start() > best[1] - best[0]:
                best = (m.start(), m.end())
    return best[1]


def page_table(pdf, page, tmp):
    pgm = hr.render(pdf, page, tmp)
    w, h, data = hr.read_pgm(pgm)
    y = main_bottom(w, h, data)
    if y and y + 12 < h:
        cut = pgm[:-4] + "-main.pgm"
        hr.write_pgm(cut, w, y + 12, data[:w * (y + 12)])
        pgm = cut
    return hr.table_pgm(pgm, "eng")


def columns(head):
    """Header cells -> {role: column index}."""
    out = {}
    for i, c in enumerate(head):
        t = hr.clean(c).lower()
        for role, rx in ROLES:
            if role not in out and re.search(rx, t):
                out[role] = i
                break
    return out


def page_records(rows, p, page):
    body, lgd = (p.get("bodies") or {}).get(str(page), [None, None])
    if not body:
        return []
    cols, recs, n = None, [], 0
    for r in rows:
        cells = r["cells"]
        if cols is None:
            c = columns(cells)
            if "name" in c and ("party" in c or "gender" in c):
                cols = c
            continue
        at = lambda k: cells[cols[k]] if k in cols and cols[k] < len(cells) else ""
        name = hr.clean(at("name"))
        if not name or re.search(r"(?i)^total|no\. of", name):
            continue
        n += 1
        ocr_ward = re.sub(r"\D", "", at("ward_no").replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1"))
        ward = str(n)       # the lists give every ward in order: row order fixes OCR slips in the ward number
        rem = hr.clean(at("remarks"))
        d = {"type": "councillor", "state": "NL", "body": body, "lgd_code": lgd, "ward_no": ward,
             "ward_name": hr.clean(at("ward_name")) or None, "reservation": reservation(at("reservation")) or None,
             "name": name, "gender": gender(at("gender")), "party": party(at("party")) or None, "remarks": rem or None,
             "unopposed": True if re.search(r"(?i)unop", rem) else None, "position": "Member",
             "ward_no_read": ocr_ward if ocr_ward and ocr_ward != ward else None,
             "election": ELECTION, "url": p["url"], "page": page, "read": "ocr"}
        recs.append((f"councillor:NL:{slug(body)}:{ward}", {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def fetch(p, get):
    if not tools():
        return [], [], "tesseract not available"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    content = stored(p, get)
    if content is None:
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [(f"councillors/NL/{key}.pdf", content, "application/pdf")] if p.get("save") and not p.get("stored") else []
    pages = list(range(int(p["first"]), int(p["last"]) + 1))
    recs = []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), (os.cpu_count() or 2) // 2))) as ex:
            tabs = dict(zip(pages, ex.map(lambda pg: page_table(pdf, pg, tmp), pages)))
    for pg in pages:
        recs += page_records(tabs[pg], p, pg)
    return recs, files, "" if recs else "no members read"
