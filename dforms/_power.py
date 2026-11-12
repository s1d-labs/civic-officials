"""Shared parts of the electricity-office readers (dforms/power_<discom>.py): cleaning, records, raw files, PDF text.

A record is one office post: {"type": "dept_office", "dept": "electricity", "level", "area", "post", "name", "phone", "email",
"address", "state", "district", "office_id", "source", "last_updated", "discom", "parents"}; "parents" = {"zone", "circle",
"division", "subdivision"} names above the office when the source gives them. Empty fields are left out.
Record id "dept:power_<discom>:<office key>"; office() keeps keys unique inside one fetch (a second "x" becomes "x~2").
"""
import gzip
import io
import re

LEVELS = ("state", "zone", "circle", "division", "subdivision", "section")
EMPTY = {"", "-", "--", "---", "na", "n/a", "nil", "vacant", "null", "none", ".", "0"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def clean(s):
    """Collapse whitespace; None for empty, '---', 'Vacant' and the like."""
    if s is None:
        return None
    s = " ".join(str(s).replace("\xa0", " ").split())
    return None if s.lower().strip(" .:-") in EMPTY or s.lower() in EMPTY else s


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:80]


def email(s):
    """De-obfuscate ([at], (at), [dot] ...) and return the addresses joined by ', ', or None."""
    s = clean(s)
    if not s:
        return None
    s = re.sub(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", "@", s, flags=re.I)
    s = re.sub(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", ".", s, flags=re.I)
    s = re.sub(r"\s+at\s+", "@", s) if "@" not in s else s
    found = []
    # spaces separate addresses; glue the pieces only when the source broke one address ("ab @ cd. in")
    for m in EMAIL.findall(s) or EMAIL.findall(re.sub(r"\s*([@.])\s*", r"\1", s)):
        m = m.strip(".").lower()
        if m not in found:
            found.append(m)
    return ", ".join(found) or None


def phone(*parts):
    """Phone numbers as the source writes them, several joined by ', '; None when there is no digit run of 5+."""
    out = []
    for p in parts:
        p = clean(p)
        if not p:
            continue
        for x in _numbers(re.split(r"\s*[,;/]\s*(?=\+?\d)|\s{2,}|\n", p)):
            x = clean(x)
            if x and re.search(r"\d{5,}|\d{2,5}[- ]\d{5,}", x.replace(" ", "")) and x not in out:
                out.append(x)
    return ", ".join(out) or None


def _numbers(parts):
    """Split '0824-2421833 9448289430' (two numbers, one space) but keep '080 2222 1111' (one number)."""
    for part in parts:
        group = []
        for tok in part.split(" "):
            if group and len(re.sub(r"\D", "", " ".join(group))) >= 8 and len(re.sub(r"\D", "", tok)) >= 6:
                yield " ".join(group)
                group = []
            group.append(tok)
        if group:
            yield " ".join(group)


def level_of(post, default=None):
    """A guess of the level from a designation (each reader may pass its own level instead)."""
    p = " " + re.sub(r"[^A-Za-z]+", " ", post or "").upper() + " "
    rules = (("section", r" (JUNIOR MANAGER|JUNIOR ENGINEER|JEE|JE|J E|SECTION OFFICER) "),
             ("subdivision", r" (ASSISTANT EXECUTIVE ENGINEER|AEE|A E E|ADE|DY EE|SDO|SDE|AEN) "),
             ("zone", r" (ZCE|ZONAL|C E|CE|CHIEF ENGINEER|GM ZONE|ED) "),
             ("circle", r" (SE|S E|SUPERINTENDING|DGM CIRCLE|ESE|CIRCLE) "),
             ("division", r" (EE|E E|XEN|SR XEN|EXECUTIVE ENGINEER|EEE|DIVISIONAL|DE|SENIOR MANAGER) "),
             ("subdivision", r" (AEE|A E E|AEN|ADE|SDO|SDE|DY EE|ASSISTANT EXECUTIVE|SUB DIVISION|SUBDIVISION|MANAGER) "),
             ("section", r" (AE|A E|JE|J E|JEE|SECTION|JUNIOR ENGINEER|ASSISTANT ENGINEER|JUNIOR MANAGER|SO) "))
    for lvl, rx in rules:
        if re.search(rx, p):
            return lvl
    return default


class Out:
    """Collects the records of one fetch and keeps their ids unique."""

    def __init__(self, module, state, source, discom=None, last_updated=None):
        self.module, self.state, self.source, self.discom, self.last_updated = module, state, source, discom, last_updated
        self.recs, self.seen = [], {}
        self.src = {}       # source trail: provenance.at(r, url) of the answer being read now (multi-source items); goes on each record

    def at(self, r, url=None):
        """The answer the next records are read from (an item that reads several pages / files)."""
        import provenance
        self.src = provenance.at(r, url)
        return self

    def add(self, key, level, area, post=None, name=None, phone_=None, email_=None, address=None, district=None, office_id=None,
            parents=None, source=None, last_updated=None, state=None, **extra):
        area, post, name = clean(area), clean(post), clean(name)
        if not (area or post):
            return None
        k = slug(key) or slug(f"{level}-{area}-{post}")
        n = self.seen.get(k, 0) + 1
        self.seen[k] = n
        if n > 1:
            k = f"{k}~{n}"
        par = {a: clean(b) for a, b in (parents or {}).items() if clean(b)}
        d = {"type": "dept_office", "dept": "electricity", "level": level, "area": area, "post": post, "name": name,
             "phone": phone_, "email": email_, "address": clean(address), "state": state or self.state, "district": clean(district),
             "office_id": clean(office_id), "source": source or self.source, "last_updated": last_updated or self.last_updated,
             "discom": self.discom, "parents": par or None, **extra}
        d = {a: b for a, b in d.items() if b not in (None, "", [], {})}
        for a, b in self.src.items():
            d.setdefault(a, b)
        self.recs.append((f"dept:{self.module}:{k}", d))
        return d


def raw(module, name, content, ext):
    """One raw answer for the bucket: depts/power/<module>/<name>.<ext>(.gz). PDFs and spreadsheets stay as they are."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")[:120] or "page"
    if ext in ("pdf", "xlsx", "xls"):
        ctype = {"pdf": "application/pdf"}.get(ext, "application/octet-stream")
        return f"depts/power/{module}/{name}.{ext}", content, ctype
    return f"depts/power/{module}/{name}.{ext}.gz", gzip.compress(content), "application/gzip"


def pdf_pages(content, layout=True):
    """Text of each page; layout mode keeps the columns apart (like pdftotext -layout)."""
    from pypdf import PdfReader
    pages = []
    for pg in PdfReader(io.BytesIO(content)).pages:
        try:
            t = pg.extract_text(extraction_mode="layout") if layout else pg.extract_text()
        except Exception:
            t = pg.extract_text() or ""
        pages.append(t or "")
    return pages


def cells(tr):
    return [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"])]


def tr_pos(tr):
    """Source trail position of a <tr>: {"table": the table's place among the page's <table> elements (1-based, document order,
    as officials.tables and _esw.table_no count), "row": the <tr>'s number among that table's own rows (1-based)}."""
    t = tr.find_parent("table")
    if t is None:
        return {"row": len(tr.find_all_previous("tr")) + 1}
    rows = [x for x in t.find_all("tr") if x.find_parent("table") is t]
    return {"table": len(t.find_all_previous("table")) + 1, "row": next((i for i, x in enumerate(rows, 1) if x is tr), None)}
