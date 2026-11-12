"""Ranchi Municipal Corporation (ranchimunicipal.com + its property tax portal municipalservices.jharkhand.gov.in): the tax
collectors of every ward and the corporation's telephone list. Both answer from Germany (live check 2026-11-11). Two items:
  tax-collectors  municipalservices.jharkhand.gov.in/CitizenProperty/list_tax_collector ("Know Your Tax Collector", the SUDA
                  property tax portal; this instance serves Ranchi only; saved in archive.s1d.me 2026-11-05): one card per tax
                  collector: mobile, name, employee code ("EMP-00001825") and "Ward List: 1, 1A, 2, 2A". The portal writes the
                  holding-tax wards with suffixes ("1A", "47/1"): "wards" holds the plain ward numbers (1-55), the extra key
                  "ward_codes" holds the list as written. 21 collectors cover the 55 wards.
  contacts        ranchimunicipal.com/docs/RMC_Contact.pdf ("Important Telephone Number Of Ranchi Municipal Corporation", 2 pages,
                  made 2026-07-09; linked from the home page; not in archive.s1d.me, live sample 2026-11-11): Sl. No. | Name |
                  Designation | Office | Residence | Mobile: the commissioner, the 7 assistant municipal commissioners, engineers
                  (SE, EE cum town planner, AE, JE), health officers, city managers. A row that wraps puts its extra lines ABOVE the
                  line with the serial number, so a row is read as the lines after the last serial line up to its own serial line.
                  The list names no zone or ward for any officer: level "body" (a body-wide list with field engineers).
                  Read with pypdf layout mode (_esw.pdf_pages), not pdftotext: the columns are found from the name column.
Records: tax collectors at level "ward" (area "Wards 1, 2", wards = the plain numbers); the telephone list at level "body".
Record ids: dept:ward2s_ranchi:tc:<employee code> and dept:ward2s_ranchi:body:<post slug>:<name slug>.
"""
import collections
import re

import provenance
from dforms import _esw, _ward

METHOD = "html cards (div.box) + pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_ranchi"
BODY, LGD, STATE, DISTRICT = "Ranchi Municipal Corporation", "250413", "JH", "Ranchi"
TC_URL = "https://municipalservices.jharkhand.gov.in/CitizenProperty/list_tax_collector"
PDF_URL = "https://ranchimunicipal.com/docs/RMC_Contact.pdf"
HONORIFIC = re.compile(r"^(SHRI|SMT\.?|SUSHRI|KUMARI|DR\.?|MD\.?|MR\.?|MRS\.?|MS\.?)(?=\s|[A-Z])", re.I)
MOBILE = re.compile(r"^\+?\d{5}[\s-]?\d{5}$")
LANDLINE = re.compile(r"^\d{6,8}$")
ABBR = ((r"\bASSTT?\.", "Assistant"), (r"\bENGR\.", "Engineer"), (r"\bJR\.", "Junior"), (r"\bSUPT\.", "Superintending"),
        (r"\bEX\.", "Executive"), (r"\bDY\.", "Deputy"), (r"\bSEC\b", "Section"))
UPPER = {"CLTC", "MIS", "IT", "WB", "PIU", "SBM"}


def items(get=None):
    return [{"key": f"{MODULE}-tax-collectors", "payload": {"reader": MODULE, "url": TC_URL, "state": STATE, "kind": "tax"}},
            {"key": f"{MODULE}-contacts", "payload": {"reader": MODULE, "url": PDF_URL, "state": STATE, "kind": "contacts"}}]


def plain_wards(codes):
    """["1", "1A", "47/1", "47A"] -> ["1", "47"]: the ward number before a holding-tax suffix."""
    out = []
    for c in codes:
        m = re.match(r"\s*(\d{1,3})", c)
        if m and str(int(m.group(1))) not in out:
            out.append(str(int(m.group(1))))
    return out


def parse_tax(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for bi, box in enumerate(soup.select("div.box"), 1):
        name = _esw.clean((box.select_one("p.name") or box).get_text(" ")) if box.select_one("p.name") else ""
        phone = _esw.clean(box.select_one("p.testimonial").get_text(" ")) if box.select_one("p.testimonial") else ""
        emp = _esw.clean(box.select_one("p.emp_code").get_text(" ")) if box.select_one("p.emp_code") else ""
        span = box.select_one("p.ward span")
        codes = [c.strip() for c in (span.get_text(" ") if span else "").split(",") if c.strip()]
        wards = plain_wards(codes)
        if not (name or phone) or not wards:
            continue
        recs.append(_ward.record(MODULE, f"tc:{_esw.slug(emp) or _esw.slug(name)}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="ward", area="Wards " + ", ".join(wards), post="Tax Collector",
                                 name=name, phone=phone, wards=wards, ward_codes=codes, employee_code=emp or None,
                                 source=p.get("url") or TC_URL, wing="revenue", src_pos={"selector": "div.box", "card": bi},
                                 method="html cards (div.box)"))
    return recs


def _runs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def contact_rows(pages, at=None):
    """[(serial, name, designation, [mobiles], [landlines])] from the telephone list pages (pypdf layout text). Per page: the name
    column starts where the honorifics (SHRI, SMT, DR.) start, the designation column where most other text runs start; lines
    above the first name line (title, helpline numbers, column heading) are skipped.
    at: a list; when given, it gets each row's src_pos (page, the serial number's line, "from" = the row's first line)."""
    rows = []
    for pn, page in enumerate(pages, 1):
        lines = page.splitlines()
        runs = [(x, t) for ln in lines for x, t in _runs(ln)]
        xs = [x for x, t in runs if HONORIFIC.match(t)]
        if not xs:
            continue
        name_x = min(xs)
        other = collections.Counter(x for x, t in runs if x > name_x + 12 and re.search("[A-Za-z]{2}", t) and not HONORIFIC.match(t))
        post_x = min((x for x, n in other.items() if n >= 3), default=name_x + 25)
        first = next(i for i, ln in enumerate(lines) if any(HONORIFIC.match(t) for _, t in _runs(ln)))
        cur = {"name": [], "post": [], "mob": [], "tel": []}
        start = first + 1
        for lno, ln in enumerate(lines[first:], first + 1):
            m = re.match(r"\s*(\d{1,3})(?=\s{2,}|\s*$)", ln)
            serial = m.group(1) if m else None
            for x, t in _runs(ln[m.end():] if m else ln):
                x += m.end() if m else 0
                if t in ("-", "--"):
                    continue
                if MOBILE.match(t):
                    cur["mob"].append(t)
                elif LANDLINE.match(t):
                    cur["tel"].append(t)
                elif x < post_x - 2:
                    cur["name"].append(t)
                else:
                    cur["post"].append(t)
            if serial:
                if cur["name"]:
                    rows.append((serial, " ".join(cur["name"]), " ".join(cur["post"]), cur["mob"], cur["tel"]))
                    if at is not None:
                        at.append(provenance.line_pos(pn, lno, ln, **({"from": start} if start < lno else {})))
                cur = {"name": [], "post": [], "mob": [], "tel": []}
                start = lno + 1
    return rows


def post_en(p):
    for rx, en in ABBR:
        p = re.sub(rx, en, p, flags=re.I)
    return " ".join(w if re.sub(r"\W", "", w) in UPPER else w.title() for w in _esw.clean(p).split())


def parse_contacts(pages, p):
    seen, recs, at = set(), [], []
    for (serial, name, post, mob, tel), pos in zip(contact_rows(pages, at), at):
        if not post:
            continue
        en = post_en(post)
        recs.append(_ward.record(MODULE, f"body:{_esw.slug(en)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="body", area=BODY, post=en, name=name,
                                 phone=", ".join(mob + [f"0651-{t}" for t in tel]), source=p.get("url") or PDF_URL,
                                 post_as_written=post, serial=serial, src_pos=pos, method="pdf text (pypdf layout)"))
    return recs


def parse(pages, p):
    """The telephone list from its page texts (the test entry point for the PDF)."""
    return parse_contacts(pages, p)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if p.get("kind") == "contacts" or r.content[:5] == b"%PDF-":
        if r.content[:5] != b"%PDF-":
            return [], [], "not a PDF"
        recs = parse_contacts(_esw.pdf_pages(r.content), p)
        return recs, [_esw.keep(MODULE, "contacts", r.content, "pdf")], "" if recs else "no rows"
    recs = parse_tax(r.text, p)
    return recs, [_esw.keep(MODULE, "tax-collectors", r.content)], "" if recs else "no tax collector cards"
