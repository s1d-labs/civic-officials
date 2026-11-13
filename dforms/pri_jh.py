"""Jharkhand: every elected member of the Panchayat General Election 2022 (4 phases, May 2022): Zila Parishad members,
Panchayat Samiti members, Mukhiyas and Gram Panchayat (ward) members, from the district gazettes "Prapatra-23" (form 23 of
the Jharkhand Panchayat Election Rules 2001, rule 85) that the State Election Commission lists on sec.jharkhand.gov.in
(PElection.aspx: Panchayat General Election, year 2022, category Results: 24 files "<n>_<District>_Prapatra23.pdf",
two grid pages; listed 2026-11-13). The host's TLS chain is incomplete (retry without checks: tls_unverified) and it
answers outside India (the archive has it from the GitHub runners).

The files are scans (KONICA MINOLTA bizhub 287; Koderma: 53 pages, 4.6 MB): a district gazette notice, then for each tier a
ruled table: name | post (पद) | reserved / unreserved (आरक्षित/अनारक्षित) | women / other (महिला/अन्य) | the panchayat and
constituency: "VI कोडरमा/6/08/कादोडीह-(3)" = Roman district code, district / block no / panchayat no / gram panchayat name -
ward; "VI कोडरमा-(1)" = Zila Parishad constituency 1. Posts: जिला परिषद सदस्य, पंचायत समिति सदस्य, मुखिया, ग्राम पंचायत सदस्य.
The SEC gives no block names (block numbers only): the loader matches the gram panchayat by district + Hindi name
(lgd.pri_local_bodies.local_body_name_local) and keeps the block number.

Items (task depts):
- {"kind": "file", "url", "district", "no"}: one district file. Fetches it once (the trail copies it to the bucket; the item
  also saves it as depts/pri_jh/<no>_<district>.pdf for the OCR items) and returns a record "seed:dept:pri_jh:<no>" (type
  seed_items) with the OCR items of that file, PAGES pages each, "stored" = <project>/depts/pri_jh/<no>_<district>.pdf.
- {"kind": "ocr", "url", "district", "no", "stored", "pages": [first, last]}: OCR of those pages from the bucket copy
  (Tesseract hin+eng on the ruled grid, cforms/hr.py, one image per column: the same reader as cforms/ce_jh.py, which reads
  the municipal Prapatra-23). GitHub runners, no proxy, never this server.
Records (type pri_member, dforms/_pri.py): one per person. src_pos = {"page", "row", "y", "conf", "cells"}.
Record ids: pri:pri_jh:<district slug>:<level>:<constituency key>[:<n>].
"""
import concurrent.futures
import hashlib
import os
import re
import tempfile

import provenance
from dforms import _pri

METHOD = "ocr tesseract hin+eng (ruled grid of the Prapatra-23 district gazette, one image per column)"
MODULE = "pri_jh"
STATE = "JH"
ELECTION = "Jharkhand Panchayat General Election 2022 (district gazette Prapatra-23)"
LANG = "hin+eng"
PAGES = 10
SEC = "https://sec.jharkhand.gov.in/"
# (no, district, file path on sec.jharkhand.gov.in): PElection.aspx, Panchayat General Election 2022, Results (2 grid pages)
FILES = [
    (1, "Garhwa", "UserFiles/pdf/1320232191/1_Garhwa_Prapatra23.pdf"),
    (2, "Palamu", "UserFiles/pdf/9820232190/2_Palamu_Prapatra23.pdf"),
    (3, "Latehar", "UserFiles/pdf/3620232189/3_Latehar_Prapatra23.pdf"),
    (4, "Chatra", "UserFiles/pdf/2820232188/4_Chatra_Prapatra23.pdf"),
    (5, "Hazaribagh", "UserFiles/pdf/6220232187/5_Hazaribagh_Prapatra23.pdf"),
    (6, "Koderma", "UserFiles/pdf/4920232186/6_Koderma_Prapatra23.pdf"),
    (7, "Giridih", "UserFiles/pdf/9520232185/7_Giridih_Prapatra23.pdf"),
    (8, "Deoghar", "UserFiles/pdf/3520232184/8_Deoghar_Prapatra23.pdf"),
    (9, "Godda", "UserFiles/pdf/7120232183/9_Godda_Prapatra23.pdf"),
    (10, "Sahebganj", "UserFiles/pdf/1820232182/10_Sahebgunj_Prapatra23.pdf"),
    (11, "Pakur", "UserFiles/pdf/3120232181/11_Pakur_Prapatra23.pdf"),
    (12, "Dumka", "UserFiles/pdf/8520232180/12_Dumka_Prapatra 23.pdf"),
    (13, "Jamtara", "UserFiles/pdf/1520232179/13_Jamtara_Prapatra23.pdf"),
    (14, "Dhanbad", "UserFiles/pdf/3320232178/14_Dhanbad_Prapatra23.pdf"),
    (15, "Bokaro", "UserFiles/pdf/9020232177/15_Bokaro_Prapatra23.pdf"),
    (16, "Ramgarh", "UserFiles/pdf/8920232176/16_Ramgarh_Prapatra23.pdf"),
    (17, "Lohardaga", "UserFiles/pdf/4520232175/17_Lohardaga_Prapatra23.pdf"),
    (18, "Gumla", "UserFiles/pdf/8820232174/18_Gumla_Prapatra23.pdf"),
    (19, "Khunti", "UserFiles/pdf/9820232173/19_Khunti_Prapatra23.pdf"),
    (20, "Ranchi", "UserFiles/pdf/3020232172/20_Ranchi_Prapatra23.pdf"),
    (21, "Simdega", "UserFiles/pdf/2320232171/21_Simdega_Prapatra23.pdf"),
    (22, "West Singhbhum", "UserFiles/pdf/7220232170/22_WestSinghbhum_Prapatra23.pdf"),
    (23, "Saraikela Kharsawan", "UserFiles/pdf/1820232169/23_Seraikela_Prapatra23.pdf"),
    (24, "East Singhbhum", "UserFiles/pdf/4320232168/24_EastSinghbhum_Prapatra23.pdf"),
]
# post words -> (level, role, English post)
POSTS = [(r"जिला\s*परि", ("zp", "member", "Zila Parishad Member")),
         (r"पंचायत\s*समि", ("ps", "member", "Panchayat Samiti Member")),
         (r"उप\s*मुखिया", ("gp", "deputy", "Up-Mukhiya")),
         (r"मुखिया", ("gp", "head", "Mukhiya")),
         (r"ग्राम\s*पंचायत|वार्ड\s*सदस्य", ("gp", "member", "Gram Panchayat Member (ward)"))]
DIGITS = str.maketrans("०१२३४५६७८९OoIl|", "012345678900111")


def url_of(path):
    return SEC + path.replace(" ", "%20")


def items(get=None):
    return [{"key": f"{MODULE}:file:{no}", "payload": {"reader": MODULE, "kind": "file", "url": url_of(path), "district": d,
                                                       "no": no, "state": STATE, "expected": 0, "route": "abroad"}}
            for no, d, path in FILES]


def listing(html):
    """[(district label, file url)] from a PElection.aspx results grid page (to check FILES against the site)."""
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        m = re.search(r"href='(UserFiles/[^']+\.pdf)'", row)
        if m and re.search(r"Results", row):
            cells = [_pri.clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            out.append((cells[3] if len(cells) > 3 else "", url_of(m.group(1))))
    return out


def post_of(text):
    t = _pri.clean(text)
    for rx, v in POSTS:
        if re.search(rx, t):
            return v
    return None


def constituency(text):
    """'VI कोडरमा/6/08/कादोडीह-(3)' -> {district, block_no, gp_no, gp, ward}; 'VI कोडरमा-(1)' -> {district, zp_no}."""
    t = re.sub(r"^\s*[IVXLivxl1|]+\s+", "", _pri.clean(text))      # the Roman district code
    t = t.translate(DIGITS)
    out = {"raw": _pri.clean(text)}
    m = re.search(r"[-–—]\s*\(?\s*(\d{1,3})\s*\)?\s*$", t)
    num = m.group(1) if m else None
    if m:
        t = t[:m.start()]
    parts = [_pri.clean(x) for x in t.split("/")]
    out["district"] = parts[0] if parts else None
    nums = [p for p in parts[1:] if p.isdigit()]
    names = [p for p in parts[1:] if p and not p.isdigit()]
    if len(nums) >= 1:
        out["block_no"] = nums[0]
    if len(nums) >= 2:
        out["gp_no"] = nums[1]
    if names:
        out["gp"] = names[-1]
    if num:
        out["no"] = str(int(num))
    return {k: v for k, v in out.items() if v}


def page_records(rows, p, page):
    """Grid rows of one OCR page (cforms/hr.py table(): [{"cells", "row", "y", "conf"}]) -> pri_member records (data dicts)."""
    out = []
    for r in rows:
        cells = [_pri.clean(c) for c in r["cells"]]
        if len(cells) < 5:
            continue
        name, post, resv, women, place = cells[0], cells[1], cells[2], cells[3], " ".join(cells[4:])
        got = post_of(post)
        if not got or not name or len(name) < 3 or re.search(r"नाम|पद का|विवरण", name):
            continue
        level, role, en = got
        c = constituency(place)
        d = {"state": STATE, "level": level, "role": role, "post": en, "post_regional": post, "name": name,
             "category": resv or None, "gender": "female" if "महिला" in women else None,
             "women_seat": women or None, "district": p["district"], "district_regional": c.get("district"),
             "block_no": c.get("block_no"), "gp_no": c.get("gp_no"), "election": ELECTION, "election_year": 2022,
             "source": p["url"], "constituency": c.get("raw"), "read": "ocr",
             "src_pos": {"page": page, "row": r.get("row"), "y": r.get("y"),
                         "conf": min([x for x in (r.get("conf") or []) if x is not None] or [None]) if r.get("conf") else None,
                         "cells": cells}}
        if level == "gp":
            d["body_name_regional"] = c.get("gp")
            if role == "member":
                d["ward_no"] = c.get("no")
        elif level == "ps":
            d["body_name_regional"] = c.get("gp")       # the panchayat named in the constituency, when given
            d["ward_no"] = c.get("no")
        else:
            d["body_name"] = p["district"]
            d["ward_no"] = c.get("no")
        out.append(d)
    return out


def record_id(d):
    dist = _pri.slug(d["district"])
    if d["level"] == "zp":
        return f"{dist}:zp:{d.get('ward_no') or 'row'}"
    key = "-".join(x for x in (d.get("block_no"), d.get("gp_no")) if x) or hashlib.sha1((d.get("constituency") or "").encode()).hexdigest()[:8]
    if d["level"] == "ps":
        return f"{dist}:ps:{key}:{d.get('ward_no') or 'row'}"
    if d["role"] in ("head", "deputy"):
        return f"{dist}:gp:{key}:{d['role']}"
    return f"{dist}:gp:{key}:w{d.get('ward_no') or 'row'}"


def build(found):
    out, seen = [], {}
    for d in found:
        rid = record_id(d)
        k = seen[rid] = seen.get(rid, 0) + 1
        out.append(_pri.record(MODULE, rid + (f":{k}" if k > 1 else ""), **d))
    return out


def stored(p, get):
    from cforms.tn import stored as tn_stored
    return tn_stored(p, get)


def file_item(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    m = re.search(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", r.content)
    n = int(m.group(1)) if m else None
    if n is None:
        n = len(re.findall(rb"/Type\s*/Page\b(?!s)", r.content)) or None
    path = f"depts/{MODULE}/{p['no']}_{_pri.slug(p['district'])}.pdf"
    project = os.environ.get("SCRAPE_POOL_PROJECT", "civic-officials-depts")
    ocr = [{"key": f"{MODULE}:ocr:{p['no']}:{a}", "payload": {
        "reader": MODULE, "kind": "ocr", "url": p["url"], "district": p["district"], "no": p["no"], "state": STATE,
        "stored": f"{project}/{path}", "pages": [a, min(a + PAGES - 1, n)], "route": "abroad", "expected": 0}}
        for a in range(1, (n or 0) + 1, PAGES)]
    recs = [(f"seed:dept:{MODULE}:{p['no']}", {"type": "seed_items", "module": MODULE, "items": ocr, "url": p["url"],
                                                "district": p["district"], "pages": n, "file": path,
                                                "src_url": p["url"], "src_pos": {"file": p["url"]}})]
    return recs, [(path, r.content, "application/pdf")], "" if ocr else "page count not found"


def fetch(p, get):
    if p.get("kind") == "file":
        return file_item(p, get)
    from cforms import hr
    if not hr.tools():
        return [], [], "tesseract not available"
    content = stored(p, get)
    from_bucket = content is not None
    if content is None:
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        content = r.content
    if not content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    a, b = p["pages"]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        pages = list(range(a, b + 1))
        with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), (os.cpu_count() or 2) // 2))) as ex:
            tabs = dict(zip(pages, ex.map(lambda pg: hr.table(pdf, pg, tmp, LANG), pages)))
    found = [d for pg in pages for d in page_records(tabs[pg], p, pg)]
    recs = build(found)
    if from_bucket:
        src = provenance.file_src(content, p["url"], p.get("stored"))
        for _, d in recs:
            d["src"] = dict(src)
    return recs, [], "" if recs else "no member rows on these pages"
