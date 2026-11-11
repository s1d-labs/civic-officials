"""Tata Power-DDL (north and north-west Delhi): its 13 district customer care centres. India only (www.tatapower-ddl.com answers
406 to this box in Germany; live samples 2026-11-11 from the India server; not in archive.s1d.me). Two PDFs, one queue item each:
- "charter": Customer_Charter_2025.pdf (13 pages, made 2025-08-11), page "Annexure-A, LIST OF CUSTOMER CARE CENTERS": District |
  Address | Customer Service Manager (name). Names and addresses wrap over 2-3 lines; each line goes to the nearest district
  label. Shalimar Bagh has no manager of its own on the page (the one name between Shalimar Bagh and Dheerpur goes to Dheerpur).
- "ccc": "Updated Customer Care Centres List.pdf" (1 page, made 2021-04-15): the same districts with "Contact No." of each office
  (and 2021 names of CRE / CSM / district manager / circle head, which wrap across districts and are not read).
The website's district manager page ("To know contact details of CRE/CSM/District Manager, Click Here") has no link in the PDF.
Levels: district (Tata Power-DDL's own unit, below its circles). About 13 + 13 records.
Record ids dept:power2_tpddl:<district>:csm and dept:power2_tpddl:<district>:office.
"""
import re

from dforms._power import Out, clean, pdf_pages, phone, raw

MOD = "power2_tpddl"
CHARTER = "https://www.tatapower-ddl.com/Editor_UploadedDocuments/Content/Customer_Charter_2025.pdf"
CCC = "https://www.tatapower-ddl.com/UploadedDocuments/Updated%20Customer%20Care%20Centres%20List.pdf"
RUN = re.compile(r"\S+(?: \S+)*")


def _runs(line):
    return [(m.start(), m.group(0)) for m in RUN.finditer(line)]


def parse_charter(text, url=CHARTER):
    out = Out(MOD, "DL", url, discom="Tata Power-DDL")
    lines = text.splitlines()
    a = next((i for i, l in enumerate(lines) if "Manager" in l and "District" not in l), None)
    b = next((i for i, l in enumerate(lines) if l.strip().startswith("Note")), len(lines))
    if a is None:
        a = next((i for i, l in enumerate(lines) if "LIST OF CUSTOMER CARE" in l), 0) + 3
    anchors, items = [], []                    # anchors: [line no, district, last line]; items: (line no, kind, text)
    for i in range(a + 1, b):
        for col, t in _runs(lines[i]):
            if col < 20:
                if anchors and anchors[-1][2] == i - 1:
                    anchors[-1][1] += " " + t          # "Shalimar" / "Bagh": the label keeps its first line
                    anchors[-1][2] = i
                else:
                    anchors.append([i, t, i])
            elif col >= 95:
                items.append((i, "right", t))
            else:
                items.append((i, "mid", t))
    if not anchors:
        return out.recs
    by = {k: {"mid": [], "right": []} for k in range(len(anchors))}
    for i, kind, t in items:
        pool = range(len(anchors))
        if kind == "mid" and re.match(r"(?i)(district office|tata power)", t):   # an address starts: it belongs to the next label
            pool = [j for j in pool if anchors[j][0] >= i] or list(pool)
        k = min(pool, key=lambda j: (abs(anchors[j][0] - i), anchors[j][0]))
        by[k][kind].append(t)
    for k, (_, district, _) in enumerate(anchors):
        names, cur = [], []
        for t in by[k]["right"]:
            if re.match(r"(?i)(mr|ms|mrs|dr|shri|smt)\.?\s", t) and cur:
                names.append(" ".join(cur))
                cur = []
            cur.append(t)
        if cur:
            names.append(" ".join(cur))
        out.add(f"{district}:csm", "district", f"{clean(district)} District", post="Customer Service Manager",
                name=", ".join(names) or None, address=" ".join(by[k]["mid"]), district=None, document="Customer Charter 2025")
    return out.recs


def parse_ccc(text, url=CCC):
    out = Out(MOD, "DL", url, discom="Tata Power-DDL")
    district = None
    for line in text.splitlines():
        runs = _runs(line)
        if runs and runs[0][0] < 15 and not re.match(r"(?i)district|customer|please", runs[0][1]):
            district = runs[0][1]
        m = re.search(r"Contact\s*No\.?\s*([\d\s-]{8,})", line)
        if m and district:
            out.add(f"{district}:office", "district", f"{clean(district)} District", post="District Customer Care Centre",
                    phone_=phone(m.group(1).strip()), document="Customer Care Centres list (April 2021)")
    return out.recs


def fetch(p, get):
    part = p.get("part", "charter")
    url = p.get("url") or (CHARTER if part == "charter" else CCC)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    pages = pdf_pages(r.content)
    if part == "charter":
        page = next((t for t in pages if "Annexure-A" in t and "CUSTOMER CARE" in t.upper()), "")
        recs = parse_charter(page, url)
    else:
        recs = parse_ccc("\n".join(pages), url)
    return recs, [raw(MOD, part, r.content, "pdf")], "" if recs else "no rows"
