"""Task `audit`: check each reader's records against the source copy it read (owner, 2026-11-13).

Why: a reader (dforms/power_mvvnl.py) dropped 181 of 308 rows of its page (7-cell rows, rows inside HTML comments) and its trimmed
test page hid it. This task counts the data rows in every saved source and compares them with the records made from that source.

No request goes to a government site. Each source is read from the family bucket: the copy that provenance.py saved at
<project>/sources/<sha[:2]>/<sha><ext>.gz (hub.read_urls signs a read link; the runner never holds a storage key).

One queue item = a batch of sources (seeds/build_audit.py makes them). Payload:
  {"sources": [{"sha256", "project", "file", "url", "content_type", "reader", "records": N,
                "id_prefix": "<common start of the record ids>", "recs": [[id_rest, name, phones, email], ...]}]}
(the hub has no API that lists records by source, so the item carries the records' names, phones and emails).

Per source one record "audit:<sha256>" (type audit_source):
  kind              html / pdf / json / csv / xlsx / text / other
  rows_visible      HTML: table rows (<tr>) with >= 3 filled cells and a person-like value (a name with a title, a phone, an
                    e-mail); PDF: text lines with a phone or an e-mail, or with >= 3 columns and a name-like column; JSON: the
                    length of the largest array of objects; CSV / XLSX: rows with >= 3 filled cells and a person-like value
  rows_hidden       HTML only: such rows inside HTML comments (<!-- ... -->)
  rows_left_out     rows of tables that the reader leaves out on purpose (its AUDIT_LEAVES_OUT; not in the coverage)
  rows_matched      source rows whose phone (last 8 digits) or name a record gives
  records           records made from this source; records_person: those with a name, phone or e-mail
  coverage          records_person / (rows_visible + rows_hidden)
  names_found       share of the records with a name whose name is in the source text
  phones_found      share of the records with a phone whose last 8 digits are in the source digits
  on_source         {"both", "name", "phone", "neither"}: per record, what of it the source text holds
  unmatched_rows    up to 10 source rows (text) that no record matches
  unmatched_records up to 10 record ids whose name and phone are not in the source
  verdict           ok: coverage >= 0.9 and names_found >= 0.95 (phones_found when no record has a name)
                    low: coverage < 0.6
                    check: the rest
                    not_tabular: no data rows in the source (maps, scans without text, pages without tables), or no record
                    with a name, phone or e-mail (records of files, layers, pages)
                    When records > 1.1 x rows (a reader that makes several records from one row), the share of rows matched
                    takes the place of coverage in the verdict.

A reader can name the tables it leaves out on purpose: AUDIT_LEAVES_OUT = r"<regex>" in its module, matched against the text of
a table's first row (e.g. power_mvvnl: the head quarter, store and workshop tables). Those rows are counted in rows_left_out.

`python audit.py --local items.json [--keys FILE] [--limit N] [--out FILE]` runs items without the hub: it reads the bucket
with a read-only key (an env file with B2_BUCKET, B2_ENDPOINT, B2_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).
"""
import csv
import datetime
import gzip
import hashlib
import hmac
import importlib
import io
import json
import os
import re
import signal
import sys
import time
import unicodedata
import zipfile
from urllib.parse import quote, urlsplit

TASK = "audit"
VERDICT_OK_COVERAGE, VERDICT_OK_NAMES, VERDICT_LOW = 0.9, 0.95, 0.6
MAX_SAMPLE = 10
HONORIFIC = re.compile(r"(?i)^(shri|sri|smt|shrimati|srimati|kumari|km|kum|dr|mr|mrs|ms|miss|er|adv|prof|capt|col|lt|thiru|"
                       r"tmt|selvi|janab|sh|thiru\.?)\b\.?|^(श्री|श्रीमती|सुश्री|डॉ|कु|श्रीमान|ஸ்ரீ|திரு|திருமதி|শ্রী|শ্রীমতী)")
HONOR_TOKENS = {"shri", "sri", "smt", "shrimati", "kumari", "km", "kum", "dr", "mr", "mrs", "ms", "miss", "er", "sh", "thiru",
                "tmt", "selvi", "श्री", "श्रीमती", "सुश्री", "डॉ", "कु", "ias", "ips", "ifs", "pcs", "hcs", "ras", "late"}
HEADER_WORDS = {"name", "names", "designation", "post", "s no", "sno", "sl no", "sr no", "s.no", "sl.no", "sr.no", "mobile",
                "phone", "email", "e-mail", "contact", "contact no", "mobile no", "phone no", "address", "office", "नाम", "पद",
                "क्रम", "क्र", "मोबाइल", "फोन", "पदनाम", "क्रमांक", "officer", "name of officer", "name of the officer"}
# words of posts, offices and places: a cell with one of them is not a person's name ("Executive Engineer", "Electricity Test Division")
NOT_NAME = set("""engineer engineers officer officers division divisional circle electricity distribution department dept office offices
assistant asst executive superintending chief deputy dy joint addl additional commissioner collector secretary director manager
general inspector station police district block sub zone zonal magistrate tehsildar tahsildar clerk section junior senior head
member members president chairman chairperson mayor ward municipal corporation council panchayat samiti construction works urban
rural test billing service services centre center computer line board account accounts accountant branch unit cell the of and for
in at to from with total grand list name designation contact phone mobile email address fax telephone details sl no sr date
government govt state india officer-in-charge incharge in-charge sdo sdm bdo ceo cmo dm sp ssp dsp sho circle-officer area
nagar nigam parishad taluk tehsil mandal village gram court hospital school college bank road street building floor
अधिकारी अभियंता कार्यालय विभाग जिला सहायक अधिशासी अधीक्षण मुख्य उप निरीक्षक सचिव थाना खंड प्रखंड ब्लॉक नाम पद मोबाइल
क्रम संख्या पता""".split())
PHONE = re.compile(r"(?<![\d])(?:\+?91[\s\-]?|0)?(?:[6-9]\d{4}[\s\-]?\d{5}|\d{2,4}[\s\-/]{0,2}\d{6,8})(?![\d])")
EMAIL = re.compile(r"(?i)[a-z0-9._%+\-]+\s*(?:@|\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\})\s*[a-z0-9\-]+(?:\s*(?:\.|\[\s*dot\s*\]|"
                   r"\(\s*dot\s*\))\s*[a-z0-9\-]+)+")
DIGIT_JOIN = re.compile(r"(?<=\d)[ \t\-–/().]{1,3}(?=\d)")
DATE = re.compile(r"(?<!\d)\d{1,2}[./\-]\d{1,2}[./\-](?:19|20)\d{2}(?!\d)")
stop = False


def on_signal(*_):
    global stop
    stop = True


# ---- text helpers

def norm(s):
    """Lower case, letters / marks / digits kept (any script), every other character a space, spaces collapsed."""
    s = unicodedata.normalize("NFKC", s or "").lower()
    out = []
    for ch in s:
        c = unicodedata.category(ch)
        out.append(ch if c[0] in "LMN" else " ")
    return " ".join("".join(out).split())


def skeleton(s):
    """Letters only: no vowel signs, no spaces, no punctuation. PDF text of Indian scripts often loses or moves vowel signs and
    breaks words ("रे खा" for "रेखा"); the letters stay in order."""
    s = unicodedata.normalize("NFKC", s or "").lower()
    return "".join(ch for ch in s if unicodedata.category(ch)[0] in "LN")


def name_tokens(name):
    return [t for t in norm(name).split() if len(t) >= 2 and t not in HONOR_TOKENS]


def digit_runs(text):
    """Digit sequences of 8+ digits, separators inside a number removed (0522-2287801 -> 05222287801); dates left out."""
    t = DATE.sub(" ", text or "")
    t = DIGIT_JOIN.sub("", t)
    return re.findall(r"\d{8,}", t)


def phone8s(phones):
    """Last 8 digits of each phone of a record ("phones" = one string, numbers split by , ; / or spaces)."""
    out = set()
    for p in re.split(r"[,;|]|\s{2,}|/(?=\s*\+?\d{6})", phones or ""):
        d = re.sub(r"\D", "", p)
        if len(d) >= 8:
            out.add(d[-8:])
    return out


def has_contact(text):
    return bool(EMAIL.search(text or "")) or any(len(re.sub(r"\D", "", m)) >= 8 for m in PHONE.findall(DATE.sub(" ", text or "")))


def name_like(cell):
    """A cell that looks like a person's name: a title (Shri, Smt, Dr, श्री ...), or 2-6 words of letters, 4-60 characters."""
    c = " ".join((cell or "").split())
    if not c or len(c) > 80:
        return False
    if HONORIFIC.search(c):
        return True
    if not 4 <= len(c) <= 60 or any(ch.isdigit() for ch in c) or "@" in c:
        return False
    words = norm(c).split()
    return 2 <= len(words) <= 6 and norm(c) not in HEADER_WORDS and not any(w in NOT_NAME for w in words)


def is_header(cells):
    n = sum(1 for c in cells if norm(c) in HEADER_WORDS or norm(c).rstrip(".") in HEADER_WORDS)
    return n >= 2


def person_row(cells):
    """A data row: >= 3 filled cells and a phone, an e-mail or a name-like cell; header rows are not."""
    filled = [c for c in cells if c and c.strip()]
    if len(filled) < 3 or is_header(filled):
        return False
    return has_contact(" | ".join(filled)) or any(name_like(c) for c in filled)


# ---- sources

def kind_of(body, ctype, file):
    c = (ctype or "").lower()
    f = (file or "").lower().removesuffix(".gz")
    head = body[:1024].lstrip()
    if body[:5] == b"%PDF-" or "pdf" in c or f.endswith(".pdf"):
        return "pdf"
    if body[:2] == b"PK" and (f.endswith(".xlsx") or "spreadsheet" in c or b"xl/" in body[:4000]):
        return "xlsx"
    if head[:1] in (b"{", b"[") and ("json" in c or f.endswith(".json") or "html" not in c):
        return "json"
    if "html" in c or f.endswith((".html", ".htm", ".aspx", ".php")) or re.search(rb"(?i)<(html|table|tr|body|div)\b", head + body[:200000]):
        return "html"
    if "csv" in c or f.endswith(".csv"):
        return "csv"
    if "xml" in c or f.endswith(".xml"):
        return "xml"
    if "javascript" in c or f.endswith(".js"):
        return "script"
    if c.startswith("text/") or f.endswith(".txt"):
        return "text"
    if c.startswith("image/") or f.endswith((".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff")):
        return "image"
    return "other"


def decode(body):
    for enc in ("utf-8", "cp1252"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", "replace")


class Source:
    """What the audit needs of one source: rows (text, cells, hidden, table title, table index) and the whole text."""

    def __init__(self, kind):
        self.kind, self.rows, self.text, self.note = kind, [], "", ""


def html_source(body):
    from lxml import html as LH
    s = decode(body)
    # comments opened in place, their rows marked (the reader of power_mvvnl does the same): single rows inside visible tables
    # and whole tables in comments both keep their place
    s = re.sub(r"(?s)<!--(.*?)-->", lambda m: re.sub(r"(?i)<tr\b", '<tr data-audit-hidden="1"', m.group(1)), s)
    src = Source("html")
    try:
        doc = LH.fromstring(s)
    except Exception:  # noqa: BLE001 - an empty or broken page
        src.text, src.note = s, "page did not parse"
        return src
    for bad in doc.xpath("//style"):
        bad.drop_tree()
    for ti, t in enumerate(doc.iter("table")):
        trs = [tr for tr in t.iter("tr") if tr.getparent() is t or tr.getparent().getparent() is t]
        if not trs:
            continue
        title = " ".join(trs[0].text_content().split())[:200]
        for tr in trs:
            cells = [" ".join(c.text_content().split()) for c in tr if c.tag in ("td", "th")]
            if person_row(cells):
                src.rows.append({"cells": cells, "hidden": bool(tr.get("data-audit-hidden")), "table": ti, "title": title})
    if not src.rows:
        blocks = repeated_blocks(doc)
        if blocks:
            src.rows = blocks
            src.note = "no table rows: repeated blocks (cards, list items)"
    src.text = " | ".join(x for x in doc.itertext())
    return src


def repeated_blocks(doc):
    """Pages without tables (cards, list items, page-builder sections): the elements of one tag + class that repeat >= 3 times
    and each hold >= 2 text pieces with a phone, an e-mail or a name-like piece. The signature with the most such blocks wins;
    blocks inside another counted block are not counted again."""
    groups = {}
    for el in doc.iter():
        if not isinstance(el.tag, str) or el.tag in ("html", "body", "head", "script", "style", "table", "tbody", "tr", "td"):
            continue
        sig = (el.tag, " ".join(sorted((el.get("class") or "").split())))
        groups.setdefault(sig, []).append(el)
    best = []
    for sig, els in groups.items():
        if len(els) < 3:
            continue
        rows = []
        for el in els:
            parts = [" ".join(t.split()) for t in el.itertext()]
            parts = [t for t in parts if t]
            if 2 <= len(parts) <= 40 and (has_contact(" | ".join(parts)) or any(name_like(t) for t in parts)):
                rows.append({"cells": parts, "hidden": False, "table": None, "title": "", "el": el})
        # prefer the innermost signature with as many blocks: more blocks first, then fewer pieces per block
        if len(rows) > len(best) or (best and len(rows) == len(best) and
                                     sum(len(r["cells"]) for r in rows) < sum(len(r["cells"]) for r in best)):
            best = rows
    for r in best:
        r.pop("el", None)
    return best if len(best) >= 3 else []


def pdf_source(body):
    src = Source("pdf")
    try:
        from dforms._pdftext import layout_pages
        pages, engine = layout_pages(body)
    except Exception as e:  # noqa: BLE001 - a broken PDF
        src.note = f"PDF did not open: {type(e).__name__}"
        return src
    lines = [ln for p in pages for ln in (p or "").splitlines()]
    src.text = "\n".join(lines)
    if not norm(src.text):
        src.note = "no text layer (a scan: records come from OCR)"
        return src
    for ln in lines:
        cols = [c for c in re.split(r"\s{2,}|\t", ln.strip()) if c]
        phone = any(len(re.sub(r"\D", "", m)) >= 8 for m in PHONE.findall(DATE.sub(" ", ln)))
        mail = bool(EMAIL.search(ln))
        # an e-mail alone is often the wrapped end of a mail id: the line counts with a phone or a name-like column
        if phone or ((mail or len(cols) >= 3) and not is_header(cols) and any(name_like(c) for c in cols)):
            src.rows.append({"cells": cols, "hidden": False, "table": None, "title": ""})
    src.note = engine
    return src


def json_source(body):
    """Rows = the objects at the JSON path that holds the most person-like objects (lists inside lists are one path:
    data[].blocks[].candidates[]). JSON text inside strings (ASP.NET "d") is read too. When strings hold HTML with data rows
    (WordPress "content.rendered", "menuName"), those rows are used instead."""
    src = Source("json")
    try:
        data = json.loads(decode(body))
    except ValueError:
        src.text, src.note = decode(body), "not valid JSON"
        return src
    paths, html_parts = {}, []

    def walk(x, path, depth=0):
        if depth > 30:
            return
        if isinstance(x, str):
            t = x.strip()
            if t[:2] in ('[{', '{"') and len(t) > 20:
                try:
                    walk(json.loads(t), path + "<json>", depth + 1)
                    return
                except ValueError:
                    pass
            if "<" in t and re.search(r"(?i)<(tr|td|div|li|p|table)\b", t):
                html_parts.append(t)
        elif isinstance(x, list):
            for o in x:
                if isinstance(o, dict):
                    props = o.get("properties") if isinstance(o.get("properties"), dict) else \
                        o.get("attributes") if isinstance(o.get("attributes"), dict) else o
                    cells = [str(v) for v in props.values() if isinstance(v, (str, int, float)) and str(v).strip()]
                    if person_row(cells):
                        paths.setdefault(path + "[]", []).append(cells)
                walk(o, path + "[]", depth + 1)
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, path + "." + str(k), depth + 1)
    walk(data, "")
    texts = [json.dumps(data, ensure_ascii=False)]
    if html_parts:
        h = html_source("\n".join(html_parts).encode("utf-8"))
        texts.append(h.text)
        if h.rows:
            src.rows, src.note = h.rows, "HTML inside JSON strings" + (f" ({h.note})" if h.note else "")
    if not src.rows and paths:
        path, rows = max(paths.items(), key=lambda kv: len(kv[1]))
        src.rows = [{"cells": c, "hidden": False, "table": None, "title": ""} for c in rows]
        src.note = f"objects at {path[:120]}"
    src.text = "\n".join(texts)
    return src


def csv_source(body):
    src = Source("csv")
    t = decode(body)
    src.text = t
    for cells in csv.reader(io.StringIO(t)):
        if person_row(cells):
            src.rows.append({"cells": cells, "hidden": False, "table": None, "title": ""})
    return src


def xlsx_source(body):
    src = Source("xlsx")
    try:
        z = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile:
        src.note = "not a valid xlsx"
        return src
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in re.findall(r"(?s)<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8", "replace")):
            shared.append(unescape_xml("".join(re.findall(r"(?s)<t[^>]*>(.*?)</t>", si))))
    texts = []
    for n in sorted(x for x in z.namelist() if x.startswith("xl/worksheets/sheet")):
        xml = z.read(n).decode("utf-8", "replace")
        for row in re.findall(r"(?s)<row\b.*?</row>", xml):
            cells = []
            for attrs, inner in re.findall(r"(?s)<c\b([^>]*)>(.*?)</c>", row):
                v = re.search(r"(?s)<v>(.*?)</v>", inner)
                tx = "".join(re.findall(r"(?s)<t[^>]*>(.*?)</t>", inner))
                if 't="s"' in attrs and v and v.group(1).strip().isdigit() and int(v.group(1)) < len(shared):
                    cells.append(shared[int(v.group(1))])
                else:
                    cells.append(unescape_xml(tx or (v.group(1) if v else "")))
            texts.append(" | ".join(cells))
            if person_row(cells):
                src.rows.append({"cells": cells, "hidden": False, "table": None, "title": ""})
    src.text = "\n".join(texts)
    return src


def unescape_xml(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


def read_source(body, ctype="", file=""):
    k = kind_of(body, ctype, file)
    if k == "html":
        return html_source(body)
    if k == "pdf":
        return pdf_source(body)
    if k == "json":
        return json_source(body)
    if k == "csv":
        return csv_source(body)
    if k == "xlsx":
        return xlsx_source(body)
    src = Source(k)
    if k in ("text", "xml", "script"):
        src.text = decode(body)
    return src


# ---- the comparison

def leaves_out(reader):
    """The reader module's AUDIT_LEAVES_OUT regex (tables it leaves out on purpose), or None."""
    if not reader:
        return None
    for name in (reader, "dforms." + reader, "cforms." + reader, "forms." + reader):
        try:
            mod = importlib.import_module(name)
        except Exception:  # noqa: BLE001 - not a module of this checkout
            continue
        rx = getattr(mod, "AUDIT_LEAVES_OUT", None)
        return re.compile(rx) if isinstance(rx, str) else rx
    return None


def audit_source(src, recs, reader="", left_out=None):
    """Compare a parsed Source with the records made from it. recs = [(record id, name, phones, email)].
    Returns the fields of the audit record (no id, url or reader)."""
    rx = left_out if left_out is not None else leaves_out(reader)
    rows, out_rows = [], []
    for r in src.rows:
        (out_rows if rx is not None and r["title"] and rx.search(r["title"]) else rows).append(r)
    text_n = norm(src.text)
    text_tokens = set(text_n.split())
    text_digits = "\n".join(digit_runs(src.text))
    text_emails = norm(src.text.replace("[at]", "@").replace("[dot]", "."))
    recs = [(rid, (nm or "").strip(), phone8s(ph), (em or "").strip().lower()) for rid, nm, ph, em in recs]

    text_skel = None

    def name_in_text(nm):
        nonlocal text_skel
        toks = name_tokens(nm)
        if not toks:
            return False
        if all(t in text_tokens for t in toks):      # every word of the name is in the source
            return True
        sk = skeleton(" ".join(toks))
        if len(sk) < 4:
            return False
        if text_skel is None:
            text_skel = skeleton(src.text)
        return sk in text_skel
    on = {"both": 0, "name": 0, "phone": 0, "neither": 0}
    n_name = n_name_found = n_phone = n_phone_found = 0
    unmatched_recs = []
    person = 0
    for rid, nm, ph, em in recs:
        has_name = bool(name_tokens(nm))
        if has_name or ph or em:
            person += 1
        nf = has_name and name_in_text(nm)
        pf = bool(ph) and any(p in text_digits for p in ph)
        if not pf and em:
            pf = norm(em) in text_emails
        n_name += has_name
        n_name_found += nf
        if ph:
            n_phone += 1
            n_phone_found += any(p in text_digits for p in ph)
        on["both" if nf and pf else "name" if nf else "phone" if pf else "neither"] += 1
        if not nf and not pf and len(unmatched_recs) < MAX_SAMPLE:
            unmatched_recs.append(rid)
    # which source rows some record matches: by phone (last 8 digits) or by every word of a name in the row
    rec_phones = {p for _, _, ph, _ in recs for p in ph}
    rec_emails = {norm(em) for _, _, _, em in recs if em}
    by_token = {}
    for _, nm, _, _ in recs:
        toks = name_tokens(nm)
        if toks:
            by_token.setdefault(max(toks, key=len), []).append(toks)
    rec_skel = {k for _, nm, _, _ in recs for k in [skeleton(" ".join(name_tokens(nm)))] if len(k) >= 5}
    matched, unmatched_rows = 0, []
    for r in rows:
        line = " | ".join(r["cells"])
        ok = any(run[i:i + 8] in rec_phones for run in digit_runs(line) for i in range(len(run) - 7))
        if not ok:
            ln = norm(line)
            toks = set(ln.split())
            ok = any(all(t in toks for t in cand) for t in toks for cand in by_token.get(t, ()))
            if not ok and rec_emails:
                ok = any(e and e in ln for e in rec_emails)
            if not ok and len(rec_skel) * len(rows) <= 3_000_000:
                rs = skeleton(line)
                ok = any(k in rs for k in rec_skel)
        matched += ok
        if not ok and len(unmatched_rows) < MAX_SAMPLE:
            unmatched_rows.append(("[in an HTML comment] " if r["hidden"] else "") + line[:300])
    vis = sum(1 for r in rows if not r["hidden"])
    hid = len(rows) - vis
    n_rows = vis + hid
    coverage = round(person / n_rows, 3) if n_rows else None
    row_match = round(matched / n_rows, 3) if n_rows else None
    names_found = round(n_name_found / n_name, 3) if n_name else None
    phones_found = round(n_phone_found / n_phone, 3) if n_phone else None
    verdict, reason = verdict_of(src, n_rows, person, coverage, row_match, names_found, phones_found)
    return {"kind": src.kind, "rows_visible": vis, "rows_hidden": hid, "rows_left_out": len(out_rows),
            "tables_left_out": sorted({r["title"][:80] for r in out_rows})[:20], "rows_matched": matched,
            "records": len(recs), "records_person": person, "coverage": coverage, "row_match": row_match,
            "names_found": names_found, "phones_found": phones_found, "on_source": on, "unmatched_rows": unmatched_rows,
            "unmatched_records": unmatched_recs, "verdict": verdict, "reason": reason, "note": src.note}


def verdict_of(src, n_rows, person, coverage, row_match, names_found, phones_found):
    if not person:
        return "not_tabular", "no record has a name, phone or e-mail (records of files, layers or pages)"
    if not n_rows:
        return "not_tabular", src.note or f"no data rows found in the {src.kind} source"
    eff = coverage if coverage <= 1.1 else row_match
    found = names_found if names_found is not None else phones_found
    if eff < VERDICT_LOW:
        return "low", f"{person} records for {n_rows} rows" + (f" ({row_match:.0%} of rows matched)" if coverage > 1.1 else "")
    if eff >= VERDICT_OK_COVERAGE and (found is None or found >= VERDICT_OK_NAMES):
        return "ok", ""
    if found is not None and found < VERDICT_OK_NAMES:
        return "check", f"{found:.0%} of the records' names (or phones) are in the source"
    return "check", f"{person} records for {n_rows} rows"


def audit_item_source(s, body):
    """The audit record (id, data) of one payload source and its decompressed bytes."""
    src = read_source(body, s.get("content_type", ""), s.get("file", ""))
    pre = s.get("id_prefix", "")
    recs = [(pre + r[0], r[1], r[2] if len(r) > 2 else "", r[3] if len(r) > 3 else "") for r in s.get("recs", [])]
    out = audit_source(src, recs, s.get("reader", ""))
    data = {"type": "audit_source", "sha256": s["sha256"], "project": s.get("project", ""), "file": s.get("file", ""),
            "url": s.get("url", ""), "reader": s.get("reader", ""), "bytes": len(body), **out,
            "records_listed": s.get("records", len(recs)), "audited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        import provenance
        data["commit"] = provenance.commit()
    except Exception:  # noqa: BLE001
        pass
    return f"audit:{s['sha256']}", data


def unpack(raw, file=""):
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    return raw


def bad_copy(s, raw):
    """Why a copy cannot be used, else "": the bytes must hash to the sha256 they are saved under."""
    if hashlib.sha256(raw).hexdigest() != s["sha256"]:
        return "copy does not match its sha256"
    return ""


# ---- the pool loop

def main():
    import requests
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 300
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    s = requests.Session()

    def fetch(src):
        key = f"{src['project']}/{src['file']}"
        url = hub.read_urls(src["project"], [key])[key]
        t = time.time()
        try:
            r = s.get(url, timeout=(20, 300))
        except requests.RequestException:
            hub.metric("http_error")
            hub.error()
            return None
        hub.metric("n_http")
        hub.metric("t_http_s", time.time() - t)
        if r.status_code != 200:
            hub.metric(f"http_{r.status_code}")
            return None
        return r.content
    try:
        while time.time() < deadline and not stop:
            if hub.settings.get("paused"):
                time.sleep(30)
                continue
            try:
                items = hub.claim(1, steal=True, retry_failed=True)
            except requests.RequestException:
                time.sleep(30)
                continue
            if not items:
                break
            item = items[0]
            n, errors = run_item(item, fetch, hub.record, hub.failure, hub.metric)
            if errors and not n:
                hub.complete([item["key"]], "failed", error="; ".join(errors)[:200])
            else:
                hub.complete([item["key"]], "done", fetched=n)
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


def run_item(item, fetch, record, failure=None, metric=None):
    """Audit every source of one item. fetch(source) -> the stored (gzip) bytes or None. Returns (records written, errors)."""
    n, errors = 0, []
    for s in item["payload"].get("sources", []):
        if stop:
            break
        raw = fetch(s)
        why = "copy not in the bucket" if raw is None else ""
        body = None
        if raw is not None:
            try:
                body = unpack(raw, s.get("file", ""))
                why = bad_copy(s, body)
            except (OSError, EOFError) as e:
                why = f"copy did not decompress: {type(e).__name__}"
        if why:
            errors.append(f"{s['sha256'][:12]}: {why}")
            if failure:
                failure(TASK, f"audit:{s['sha256']}", why, file=s.get("file", ""), project=s.get("project", ""))
            continue
        try:
            rid, data = audit_item_source(s, body)
        except Exception as e:  # noqa: BLE001 - one bad source must not stop the batch
            errors.append(f"{s['sha256'][:12]}: {type(e).__name__}: {e}"[:200])
            if failure:
                failure(TASK, f"audit:{s['sha256']}", f"{type(e).__name__}: {e}"[:200])
            continue
        record(rid, data)
        if metric:
            metric(f"verdict_{data['verdict']}")
        n += 1
    return n, errors


# ---- local runs (no hub): read the bucket with a read-only key

def read_env(path):
    try:
        text = open(path, encoding="utf-8").read()
    except PermissionError:      # root-only key file: read through sudo, never printed
        import subprocess
        text = subprocess.run(["sudo", "-n", "cat", path], capture_output=True, text=True, check=True).stdout
    env = {}
    for ln in text.splitlines():
        if "=" in ln and not ln.lstrip().startswith("#"):
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def s3_get(env, key, session=None):
    """GET one object with AWS signature v4 (path style). Returns bytes or None."""
    import requests
    endpoint = env.get("B2_ENDPOINT") or env.get("AWS_ENDPOINT_URL")
    region = env.get("B2_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1"
    host = urlsplit(endpoint).netloc
    path = "/" + quote(env["B2_BUCKET"]) + "/" + quote(key, safe="/")
    now = datetime.datetime.now(datetime.timezone.utc)
    amz, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    ph = hashlib.sha256(b"").hexdigest()
    canon = f"GET\n{path}\n\nhost:{host}\nx-amz-content-sha256:{ph}\nx-amz-date:{amz}\n\nhost;x-amz-content-sha256;x-amz-date\n{ph}"
    scope = f"{day}/{region}/s3/aws4_request"
    sts = f"AWS4-HMAC-SHA256\n{amz}\n{scope}\n{hashlib.sha256(canon.encode()).hexdigest()}"
    k = ("AWS4" + env["AWS_SECRET_ACCESS_KEY"]).encode()
    for part in (day, region, "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    auth = (f"AWS4-HMAC-SHA256 Credential={env['AWS_ACCESS_KEY_ID']}/{scope}, "
            f"SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature={sig}")
    r = (session or requests).get(f"https://{host}{path}", headers={"Authorization": auth, "x-amz-date": amz,
                                                                    "x-amz-content-sha256": ph}, timeout=(20, 300))
    return r.content if r.status_code == 200 else None


def local(items_file, keys="/etc/scrape-hub/member-keys/sarthak.env", limit=None, out=None):
    import requests
    env = read_env(keys)
    sess = requests.Session()
    items = json.load(open(items_file, encoding="utf-8"))
    results = []
    done = 0
    for item in items:
        srcs = item["payload"]["sources"]
        if limit is not None:
            srcs = srcs[:max(0, limit - done)]
        if not srcs:
            break
        done += len(srcs)
        n, errors = run_item({**item, "payload": {**item["payload"], "sources": srcs}},
                             lambda s: s3_get(env, f"{s['project']}/{s['file']}", sess),
                             lambda rid, d: results.append((rid, d)))
        for e in errors:
            print("error", e, file=sys.stderr)
    for rid, d in results:
        print(json.dumps({"id": rid, "reader": d["reader"], "kind": d["kind"], "verdict": d["verdict"],
                          "rows": [d["rows_visible"], d["rows_hidden"], d["rows_left_out"]], "records": d["records_person"],
                          "coverage": d["coverage"], "row_match": d["row_match"], "names_found": d["names_found"],
                          "phones_found": d["phones_found"], "reason": d["reason"]}, ensure_ascii=False))
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump([{"id": rid, **d} for rid, d in results], f, ensure_ascii=False, indent=1)
    return results


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--local":
        a = sys.argv[2:]
        opt = {a[i].lstrip("-"): a[i + 1] for i in range(1, len(a) - 1, 2)}
        local(a[0], keys=opt.get("keys", "/etc/scrape-hub/member-keys/sarthak.env"),
              limit=int(opt["limit"]) if "limit" in opt else None, out=opt.get("out"))
    else:
        sys.exit(main())
