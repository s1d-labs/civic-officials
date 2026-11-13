"""Uttarakhand, Dehradun district: the village worker lists that the district disaster management page links
(https://dehradun.nic.in/disaster-management/, "DDMP Action Plan", all dated 09/06/2021; files on cdn.s3waas.gov.in, not in
archive.s1d.me, fetched once on 2026-11-13 from Mumbai):
- "List of Aanganwadi Workers" (2021060969.pdf, 45 pages, Excel export, text layer): "S.NO | STATE CODE | STATE NAME | DISTRICT
  CODE | DISTRICT NAME | PROJECT NAME | SECTOR NAME | AWC NAME | AWW NAME | AWW MOBILE NO | AWC TYPE | AWW HELPER NAME | AWW
  HELPER MOBILE NO": 1,555 numbered rows (format "aww").
- "List of Asha Workers" (2021060975.pdf, 10 pages): "ASHA List Urban Dehradun", "S.No. | Ward No | Ward NO (name) | ASHA Name
  | Mobile": 503 rows; the ward name is written only on the first row of each ward (format "asha").
- "List of Gram Prahari" (2021060974.pdf, 5 pages, Word, Kruti Dev font): the gram prahari (village watchman, appointed per gram
  sabha by the tehsil) of the tehsils Tyuni, Chakrata, Kalsi ...: serial, name, age, gram panchayat / address, mobile
  (format "prahari"; text converted to Unicode Hindi with cforms/cn_krutidev.convert).
The other lists on the page (Village Pradhan, Patwari) are other readers' posts.
Lines are read from the layout text (pdftotext -layout, else pypdf layout). AWW rows are anchored on "Main AWC" / "Mini AWC"
and the mobile numbers; the text before them splits at runs of 2+ spaces into district, project, sector, AWC and worker name. A
row that does not split into these five gets "split_unsure": true (the raw line stays in src_pos).
Records: layer village_worker, level village: AWW + helper (dept women_child); level ward: urban ASHA (dept health, area
"Ward <n> <name>", body Dehradun Municipal Corporation); level village:
Gram Prahari (dept police, post "Gram Prahari", age, address, tehsil). "_" / blank names give no record.
Ids dept:vil_uk_ddmp:aww:<project slug>-<serial>[:awh], asha:<serial>, prahari:s<tehsil section>:<serial>.
"""
import re

import provenance
from cforms import cn_krutidev
from dforms import _esw, _field

METHOD = "pdf text (layout), rows by serial number, columns split at runs of 2+ spaces and anchored on mobile numbers"

MODULE = "vil_uk_ddmp"
MOB = r"(?:\d{9,11}|_+|-+)"     # a few mobiles in the file have 9 or 11 digits: kept as written
AWW = re.compile(r"^\s*(\d{1,4})\s+05\s+UTTARAKHAND\s+(\d{5})\s+(.*?)\s+(" + MOB + r")?\s*(Main\s*AWC|Mini\s*AWC)\s*(.*?)\s*("
                 + MOB + r")?\s*$", re.I)
ASHA = re.compile(r"^\s*(\d{1,4})\s+(\d{1,3})\s+(?:(.*?)\s{2,})?(\S.*?)\s+(\d{10}|_+|-+)?\s*$")
PRAHARI = re.compile(r"^\s*[A-Z]?(\d{1,4})\s+(.*?)\s+(\d{10}(?:\s*[,/]\s*\d{10})?)?\s*$")
NONAME = re.compile(r"(?i)^[_\-\s.]*$|^vacant$")


def phone(s):
    return _esw.phones(s) if s and re.search(r"\d{6}", s) else ""


def gaps(s):
    return [x for x in re.split(r"\s{2,}", (s or "").strip()) if x]


def aww_records(pages, url, p, engine):
    recs, seen = [], set()
    for pg, page in enumerate(pages, 1):
        for ln, line in enumerate(page.splitlines(), 1):
            m = AWW.match(line)
            if not m:
                continue
            sno, dcode, pre, mob, typ, helper, hmob = m.groups()
            parts = gaps(pre)
            sure = len(parts) == 5
            if len(parts) >= 5:
                dist, proj, sector, awc, worker = parts[0], parts[1], parts[2], " ".join(parts[3:-1]), parts[-1]
            else:   # a merged cell: keep the last part as the worker, the rest as the AWC text
                dist = parts[0] if parts else ""
                proj = parts[1] if len(parts) > 3 else ""
                sector = ""
                awc = " ".join(parts[2:-1] if len(parts) > 3 else parts[1:-1])
                worker = parts[-1] if len(parts) > 1 else ""
            pos = provenance.line_pos(pg, ln, line)
            row = f"{_esw.slug(proj) or 'x'}-{sno}"     # serials restart in some projects
            while row in seen:
                row += "-b"
            seen.add(row)
            base = dict(dept="women_child", level="village", layer="village_worker", area=awc, awc_type=_esw.clean(typ),
                        sector=sector, project=proj, district=dist or "Dehradun", district_code=dcode, state="UK", serial=sno,
                        split_unsure=None if sure else True, source=url, src_url=url, src_pos=pos,
                        method=f"pdf text ({engine}), rows anchored on the AWC type and mobiles", last_updated="2021-06-09")
            if worker and not NONAME.match(worker):
                k = f"aww:{row}"
                recs.append(_esw.record(MODULE, k, post="Anganwadi Worker", name=worker, phone=phone(mob), office_id=k, **base))
            helper = _esw.clean(helper)
            if helper and not NONAME.match(helper):
                k = f"aww:{row}:awh"
                recs.append(_esw.record(MODULE, k, post="Anganwadi Helper", name=helper, phone=phone(hmob), office_id=k, **base))
    return recs


def asha_records(pages, url, p, engine):
    recs, ward_name, last_ward, seen = [], "", None, set()
    for pg, page in enumerate(pages, 1):
        for ln, line in enumerate(page.splitlines(), 1):
            m = ASHA.match(line)
            if not m:
                continue
            sno, ward, wname, name, mob = m.groups()
            if ward != last_ward:
                ward_name, last_ward = "", ward
            if wname:
                ward_name = _esw.clean(wname)
            name = _esw.clean(name)
            if NONAME.match(name):
                continue
            k = f"asha:{sno}"
            while k in seen:
                k += "-b"
            seen.add(k)
            recs.append(_esw.record(
                MODULE, k, dept="health", level="ward", layer="village_worker", post="ASHA", name=name, phone=phone(mob),
                area=f"Ward {ward}" + (f" {ward_name}" if ward_name else ""), ward_no=ward, ward_name=ward_name or None,
                body="Dehradun Municipal Corporation", district="Dehradun", state="UK", serial=sno, office_id=k, source=url,
                src_url=url, src_pos=provenance.line_pos(pg, ln, line), method=f"pdf text ({engine}), rows by serial number",
                last_updated="2021-06-09"))
    return recs


def prahari_records(pages, url, p, engine):
    recs, tehsil, seen, section = [], "", set(), 0
    for pg, page in enumerate(pages, 1):
        for ln, line in enumerate(page.splitlines(), 1):
            uni = cn_krutidev.convert(line)
            t = re.search(r"तहसील\s*[-–]?\s*([^\s।,]+)", uni)
            if t and not re.match(r"^\s*[A-Z]?\d", line):
                if t.group(1) != tehsil:
                    section += 1
                tehsil = t.group(1)
                continue
            m = PRAHARI.match(line)
            if not m or not m.group(3):
                continue
            sno, mid, mob = m.groups()
            cells = [cn_krutidev.convert(x).replace("Œ", ".") for x in gaps(mid)]
            age = next((c for c in cells if re.fullmatch(r"\d{2}", c)), "")
            name = cells[0] if cells else ""
            if NONAME.match(name) or re.fullmatch(r"\d+", name):
                continue
            rest = [c for c in cells[1:] if c != age]
            k = f"prahari:s{section}:{sno}"
            while k in seen:
                k += "-b"
            seen.add(k)
            recs.append(_esw.record(
                MODULE, k, dept="police", level="village", layer="village_worker", post="Gram Prahari", post_regional="ग्राम प्रहरी",
                name=name, name_regional=name, phone=phone(mob), age=age, area=rest[0] if rest else None,
                address=" / ".join(rest) or None, tehsil=tehsil or None, district="Dehradun", state="UK", serial=sno, office_id=k,
                source=url, src_url=url, src_pos=provenance.line_pos(pg, ln, line, text_unicode=uni),
                method=f"pdf text ({engine}), Kruti Dev -> Unicode, rows by serial number", last_updated="2021-06-09"))
    return recs


READERS = {"aww": aww_records, "asha": asha_records, "prahari": prahari_records}


def parse(content, url, p):
    text, engine = _field.pdf_text_engine(content)
    return READERS[p["format"]](text.split("\f"), url, p, engine)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    files = [_esw.keep(MODULE, f"dehradun-{p['format']}", r.content, "pdf")]
    recs = parse(r.content, p["url"], p)
    return recs, files, "" if recs else "no rows"
