"""Tamil Nadu: ward councillors' mobiles, addresses and e-mails from the municipalities' and corporations' own sites on the
state platform www.tnurbantree.tn.gov.in/<site>/ (WordPress multisite, ~150 bodies). Each body has one "Councillors" page,
but its address differs per body (councilars, councilors, municipal-councillors, corporation-councillor, ta/municipal-councillor
...), so the reader asks the site's own page search: <site>/wp-json/wp/v2/pages?search=counc (the public WordPress API, one
request, page content included) and takes the page whose table has the most councillor rows. Tables differ per body: ward
no, name, father's/husband's name, address, mobile or "Contact No./ Landline No.", e-mail, party, photo; in English.
Councillors of the 2022 term (the same as the SEC results that cforms/tn.py reads); our records have the Tamil names of
those results, so sql/72 must join TN on body + ward (the names are in two scripts).
Some bodies publish only a PDF of the list: the PDF goes to the bucket and its text layer is read (pdf_list(), rows by line,
Karaikudi); a PDF without a text layer gives "list is a PDF (stored)".
One queue item = one body: payload {"kind": "form-cp_tn", "state": "TN", "url" (the search url), "site", "body" (Tamil name as
in civic.councillor), "lgd_code", "record_prefix" (councillor:TN:<group>:<body> of cforms/tn.py), "name_en"}.
A payload url that is not a wp-json url is read as one HTML page. Record id cp:TN:<site>:<ward>."""
import gzip
import json
import re

from cforms.cp_common import column, emails, keyed, phones, record, table_rows, useful, ward_no

METHOD = "html table (in a WordPress search answer: json api)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://www.tnurbantree.tn.gov.in/"
TITLE = re.compile(r"^(?:(thiru|tmt|selvi|thirumathi|mr|mrs|ms|dr|adv)\b\.?|(?:திருமதி|திரு|செல்வி|முனைவர்|டாக்டர்)(?=[\s.]))\.?\s*", re.I)


def search_url(site):
    return f"{BASE}{site}/wp-json/wp/v2/pages?search=counc&_fields=link,title,content&per_page=50"


def name_of(s):
    s = re.sub(r"\((?:chair(?:man|person)|vice[- ]?chair(?:man|person)|mayor|deputy mayor)[^)]*\)", " ", s or "", flags=re.I)
    s = re.sub(r"\s+[SDWC]/[Oo]\b.*$", "", s)                 # "A.K.Ramesh S/o Kupusamy": the father's name is not part of it
    s = TITLE.sub("", s.strip())
    return " ".join(s.split()) or None


def parse(html, p, url, at_pos=None):
    """at_pos: what to put before each row's table position in src_pos (the search hit's place in the json answer)."""
    recs = []
    for head, cells in table_rows(html):
        if not head:
            continue
        # English or Tamil heads (Bhavani: வ. எண் | வார்டு எண் | பெயர் | முகவரி மற்றும் அலைப்பேசி எண் | கட்சியின் பெயர்)
        ni = column(head, r"name of (the )?(elected )?(councill?or|candidate|member)", r"councill?or name", r"^name",
                    r"^(?:உறுப்பினர்\s*)?பெயர்", r"மாமன்ற உறுப்பினர்|நகர்மன்ற உறுப்பினர்")
        wi = column(head, r"^ward", r"ward\s*(no|number)", r"^வார்டு")
        pi = column(head, r"mobile", r"contact", r"phone", r"cell", r"அலைப்பேசி|அலைபேசி|கைபேசி|தொலைபேசி|கைப்பேசி")
        ei = column(head, r"e-?\s*mail", r"மின்னஞ்சல்")
        ai = column(head, r"address", r"முகவரி")
        if ni is None or (pi is None and ei is None and ai is None) or len(cells) <= ni:
            continue
        at = lambda i: cells[i] if i is not None and i < len(cells) else ""
        name = name_of(at(ni))
        if not name or re.fullmatch(r"[\d\W]+", name):
            continue
        w = ward_no(at(wi)) if wi is not None else None
        tel = phones(at(pi))
        adr = at(ai) if ai != pi else re.sub(r"[\s,;/-]*(?:\+?91[\s-]?)?[6-9]\d{9}\b", "", at(ai)).strip(" ,;")   # one cell: address and mobile
        recs.append(record("TN", p["body"], w, name, url, phone=tel, email=emails(at(ei)) or emails(at(pi)), address=adr,
                           ward_label=at(wi), lgd_code=p.get("lgd_code"),
                           record_for=f"{p['record_prefix']}:{w}" if w and p.get("record_prefix") else None,
                           extra={"name_en": p.get("name_en")}, pos={**(at_pos or {}), **(cells.pos or {})}))
    return useful(recs)


PDF_ROW = re.compile(r"^\s*(\d{1,3})\s+(Ward\s*(?:No\.?\s*)?(\d{1,3}))(?:\s+(\S.*))?\s*$", re.I)
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def _cells(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def pdf_rows(pages):
    """Rows of a list PDF's text layer (pypdf layout): "<sl>  Ward <n>  <name>  <address part>  <mobile>", the address over
    the lines above and below (Karaikudi 2025). The address column is what is left of a line once the mobile is taken; an
    address starts with "No." (door number) or after an empty line, so the lines from one start to the next go to the row that
    falls among them (or the nearest row). A row with no name (ward 14: vacant) gives no record. Returns [{sl, ward, ward_label, name, phone, address, page, line, line_text}]."""
    raw = [(pg, i, ln) for pg, text in enumerate(pages, 1) for i, ln in enumerate(text.split("\n"), 1)]
    lines, gap, prev = [], set(), None
    for pg, i, ln in raw:
        if not ln.strip() or re.search(r"(?i)councill?ors? details|sl\.?\s*no|^\s*page\s*\d", ln):
            prev = None
            continue
        if prev is None or prev != pg:
            gap.add(len(lines))                 # the first line after an empty line, a heading or a page break
        lines.append((pg, i, ln))
        prev = pg
    rows, addr, phones_at = [], [], []          # addr: (index, text); phones_at: (index, number)
    for k, (pg, i, ln) in enumerate(lines):
        m = PDF_ROW.match(ln)
        cells = _cells(ln)
        if m:
            rest = _cells(m.group(4) or "")
            rows.append({"k": k, "sl": m.group(1), "ward": m.group(3), "ward_label": m.group(2), "name": rest[0][1] if rest else "",
                         "page": pg, "line": i, "line_text": ln})
            cells = rest[1:]
        for _, c in cells:
            phones_at += [(k, n) for n in MOBILE.findall(c)]
            c = MOBILE.sub(" ", c).strip(" ,")
            if c:
                addr.append((k, c))
    if not rows:
        return []
    near = lambda k: min(rows, key=lambda r: (abs(r["k"] - k), r["k"] > k))    # noqa: E731 (a tie goes to the row above)
    for k, n in phones_at:
        r = near(k)
        r["phone"] = (r.get("phone") + ", " + n) if r.get("phone") else n
    segs = []
    for k, c in addr:
        if not segs or k in gap and segs[-1][1] != k or re.match(r"(?i)no\s*\.", c):
            segs.append([k, k, [c]])
        else:
            segs[-1][1] = k
            segs[-1][2].append(c)
    for a, b, parts in segs:
        inside = [r for r in rows if a <= r["k"] <= b]
        r = inside[0] if inside else near((a + b) / 2)
        r["address"] = ", ".join(x for x in [r.get("address"), " ".join(parts)] if x)
    return rows


def pdf_list(content, p, url):
    """Records from a list PDF with a text layer ([] for a scan)."""
    import io
    from pypdf import PdfReader
    try:
        pages = [pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(io.BytesIO(content)).pages]
    except Exception:  # noqa: BLE001
        return []
    recs = []
    for r in pdf_rows(pages):
        name = name_of(r["name"])
        if not name:
            continue
        d = record("TN", p["body"], r["ward"], name, url, phone=r.get("phone"), address=r.get("address"), ward_label=r["ward_label"],
                   lgd_code=p.get("lgd_code"), record_for=f"{p['record_prefix']}:{r['ward']}" if p.get("record_prefix") else None,
                   extra={"name_en": p.get("name_en"), "name_as_listed": r["name"]},
                   pos={"page": r["page"], "line": r["line"], "line_text": r["line_text"]})
        d["method"] = "pdf text (pypdf layout), rows by line"
        recs.append(d)
    return useful(recs)


def best_page(pages, p):
    """(url, records) of the search hit with the most councillor rows; ([], pdf links) when only PDFs are linked."""
    best, pdfs = (None, []), []
    for i, pg in enumerate(pages if isinstance(pages, list) else []):
        html = (pg.get("content") or {}).get("rendered") or ""
        link = pg.get("link") or ""
        recs = parse(html, p, link, {"index": i, "id": pg.get("id"), "field": "content.rendered"})
        for d in recs:
            d["method"] = "json api + html table"
        if len(recs) > len(best[1]):
            best = (link, recs)
        title = ((pg.get("title") or {}).get("rendered") or "").lower()
        if re.search(r"councill?or|councilar|members", title + link):
            pdfs += [u for u in re.findall(r'href="([^"]+\.pdf)"', html, re.I) if u not in pdfs]
    return best, pdfs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/TN/cp-{p['site']}.json.gz" if "wp-json" in p["url"] else f"councillors/TN/cp-{p['site']}.html.gz",
              gzip.compress(r.content), "application/gzip")]
    if "wp-json" in p["url"]:
        try:
            pages = json.loads(r.text)
        except ValueError:
            return [], files, "search answer is not JSON"
        (link, recs), pdfs = best_page(pages, p)
        if not recs and pdfs:
            f = get(pdfs[0])
            if f is not None and f.content[:5] == b"%PDF-":
                files.append((f"councillors/TN/cp-{p['site']}.pdf", f.content, "application/pdf"))
                recs = pdf_list(f.content, p, pdfs[0])
                return keyed("TN", p["site"], recs), files, "" if recs else "list is a PDF (stored)"
    else:
        recs = parse(r.text, p, p["url"])
    return keyed("TN", p["site"], recs), files, "" if recs else "no councillor table with contacts"
