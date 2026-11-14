"""Haryana: the ICDS project officer of every project (WCDPO, Women & Child Development Project Officer: the CDPO of Haryana) and
the District Programme Officer (DPO) of every district, from the Who's Who page of the Women & Child Development Department
(https://wcdhry.gov.in/whos-who/, S3WaaS; the archive saved it from the GitHub pool on 2026-11-06: the site answers abroad).

1. The page: table "District Programme Officers": District name | Address | Name of DPO | Phone no. | Mobile no. | E-mail ID
   (written pofbd.wcd[at]gmail[dot]com) | Contacts No. of WCDPOs (a link "View Document (PDF 21.3 KB)" per district; 21 links for
   22 districts on 2026-11-06: Charkhi Dadri has none). The state officers above it are not read.
2. One PDF per district on cdnbbsr.s3waas.gov.in ("WCDPO CONTACT LIST", Word 2013, one page, created June 2020; Ambala, Hisar
   and Karnal fetched from Mumbai on 2026-11-14): Sr. No. | Name of district | Name of Block | Name of WCDPO | Contact No. of
   WCDPO | Address of WCDPO office. "Name of Block" is the ICDS project ("Ambala R-1", "Hisar-U", "Hansi-1st"). Names and
   addresses wrap onto the next lines; a row ends at the next serial number. "Vacant" = vacant post, "--" = no phone,
   "(Additional)" after a name = additional charge of the project.
Reading the PDF (pdftotext -layout, else pypdf layout): the header line gives the column starts (the three "Name of", "Contact",
"Address"), each line is cut there (dforms/_pdftext.cut), a line whose first cell is a number starts a row, other lines add
their cells to the open row.

Records (depts.py contract): dept women_child, layer field, field_layer icds.
- DPO: level district, post "District Programme Officer", area = district, name, phone (phone + mobile), email, address.
  Id dept:field_icds_hr_wcd:dpo:<district slug>.
- WCDPO: level block, post "Women & Child Development Project Officer (CDPO)", post_kind cdpo, area and icds_project = the
  project as written, name (vacant=true for "Vacant"), additional_charge, phone, address, district, last_updated = the PDF's
  creation month. Id dept:field_icds_hr_wcd:cdpo:<district slug>:<project slug>. src_pos = page + line of the serial number
  (+ the row's other lines).
One queue item = the page + every PDF it links (about 22 GETs).
"""
import re

from dforms import _esw, _pdftext
import provenance

METHOD = "html table (DPOs); pdf text with columns from the header positions (WCDPO lists)"

MODULE = "field_icds_hr_wcd"
URL = "https://wcdhry.gov.in/whos-who/"
POST_CDPO = "Women & Child Development Project Officer (CDPO)"
POST_DPO = "District Programme Officer"


def _col(head, rx):
    for i, h in enumerate(head):
        if re.search(rx, h, re.I):
            return i
    return None


def parse_page(html, url=URL):
    """(DPO records, [(district, pdf url)]) from the Who's Who page."""
    s = _esw.soup(html)
    recs, pdfs = [], []
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or not re.search(r"(?i)name of dpo", " ".join(rows[0])):
            continue
        head = rows[0]
        c = {k: _col(head, rx) for k, rx in (("district", r"district"), ("address", r"address"), ("name", r"name of dpo"),
                                              ("phone", r"phone"), ("mobile", r"mobile"), ("email", r"e-?mail"))}
        trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        for row, sp in zip(rows[1:], pos[1:]):
            get = lambda k: row[c[k]] if c[k] is not None and c[k] < len(row) else ""
            district = get("district")
            if not district or re.search(r"(?i)district name", district):
                provenance.skip_row(row, "no district")
                continue
            a = trs[sp["row"] - 1].find("a", href=re.compile(r"(?i)\.pdf($|\?)"))
            if a:
                pdfs.append((district, a["href"]))
            name = get("name")
            vacant = bool(re.fullmatch(r"(?i)vacant|-+|—", name or ""))
            phone, email = _esw.phones(get("phone"), get("mobile")), _esw.emails(get("email"))
            if not (name or phone or email):
                provenance.skip_row(row, "no name, phone or e-mail")
                continue
            provenance.used()
            recs.append(_esw.record(MODULE, f"dpo:{_esw.slug(district)}", dept="women_child", level="district", layer="field",
                                    field_layer="icds", area=district, post=POST_DPO, name=None if vacant else name,
                                    vacant=vacant or None, phone=phone, email=email, address=get("address"), district=district,
                                    state="HR", source=url, page=url, src_url=url, src_pos=sp))
    return recs, pdfs


def _starts(lines):
    """Column starts [serial, district, project, name, contact, address] from the header line ("Sr. Name of Name of Name of
    Contact No. ... Address ..."), or None."""
    for ln in lines:
        names = [m.start() for m in re.finditer(r"Name of", ln)]
        c, a = ln.find("Contact"), ln.find("Address")
        if len(names) == 3 and c > names[2] and a > c:
            return [0] + names + [c, a]
    return None


def parse_pdf(content, district, url, created=""):
    pages, _engine = _pdftext.layout_pages(content)
    recs, seen = [], set()
    for pn, text in enumerate(pages, 1):
        lines = text.splitlines()
        starts = _starts(lines)
        if not starts:
            continue
        data = [ln for ln in lines if re.match(r"\s*\d{1,3}\s{2,}\S", ln)]
        # the "Address" header word sits right of its cells ("Address" over "BDPO campus"): move that start left to the cells,
        # never left of the phone numbers (the other headers sit over their cells)
        phone_end = max((m.end() for ln in data for m in re.finditer(r"\d{10}|--", ln[starts[4]:starts[5] + 2])), default=0)
        starts[5] = max(_pdftext.settle(starts[5:], data, left=14)[0], starts[4] + phone_end + 1)
        rows, cur = [], None
        for i, ln in enumerate(lines):
            if not ln.strip() or re.search(r"WCDPO CONTACT LIST|^\s*(Sr\.|No\.)\s", ln):
                continue
            cells = _pdftext.cut(ln, starts)
            if re.fullmatch(r"\d{1,3}", cells[0]):
                cur = {"cells": [[x] if x else [] for x in cells], "idx": [i]}
                rows.append(cur)
            elif cur is not None:
                for k, x in enumerate(cells):
                    if x:
                        cur["cells"][k].append(x)
                cur["idx"].append(i)
        for r in rows:
            serial, dist, proj, name, contact, address = (" ".join(x) for x in r["cells"])
            sp = _pdftext.block_pos(pn, lines, r["idx"], row=int(serial))
            extra = bool(re.search(r"(?i)\(\s*addl?\.?(itional)?\s*\)", name))
            name = re.sub(r"(?i)\s*\(\s*addl?\.?(itional)?\s*\)", "", name).strip()
            vacant = bool(re.fullmatch(r"(?i)vacant", name))
            phone = _esw.phones(contact)
            if not proj or not (name or phone):
                provenance.skipped("row without project, name or phone")
                continue
            dist = dist or district
            key = f"cdpo:{_esw.slug(dist)}:{_esw.slug(proj)}"
            k, n = key, 2
            while k in seen:
                k, n = f"{key}:{n}", n + 1
            seen.add(k)
            provenance.used()
            recs.append(_esw.record(MODULE, k, dept="women_child", level="block", layer="field", field_layer="icds", area=proj,
                                    icds_project=proj, post=POST_CDPO, post_kind="cdpo", name=None if vacant else name,
                                    vacant=vacant or None, additional_charge=extra or None, phone=phone, address=address,
                                    district=dist, district_page=district if district != dist else None, state="HR",
                                    last_updated=created or None, source=url, page=URL, src_url=url, src_pos=sp))
    return recs


def _created(content):
    """'YYYY-MM' from the PDF's CreationDate (D:20200622113102...), else ''."""
    m = re.search(rb"/CreationDate\s*\(D:(\d{4})(\d{2})", content or b"")
    return f"{m.group(1).decode()}-{m.group(2).decode()}" if m else ""


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "HR", "expected": 170}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs, pdfs = parse_page(r.text, url)
    files = [_esw.keep(MODULE, "whos-who", r.content)]
    missing = []
    for district, pdf in pdfs:
        f = get(pdf)
        if f is None or f.content[:4] != b"%PDF":
            missing.append(district)
            continue
        recs += parse_pdf(f.content, district, pdf, _created(f.content))
    why = "" if recs else "no rows"
    if missing and recs:
        why = f"no WCDPO list for {len(missing)} districts: {', '.join(missing)}"[:300]
    return recs, files, why
