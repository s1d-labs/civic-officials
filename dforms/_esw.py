"""Shared helpers for the ERO, sub-registrar and water readers (dforms/ero_*.py, sro_*.py, water_*.py).

record() builds one "dept:<module>:<office key>" record with the depts.py fields and drops empty ones; keep() wraps a raw answer
as a bucket file under depts/<module>/; grid() reads an HTML table with rowspan/colspan carried; pdf_pages() gives the text of
each PDF page in layout mode; ac_no() finds the ECI assembly constituency number from its name (dforms/ac_no.json, built from the
AC boundary layer the site uses: geo.lgd_assembly_constituencies in DB civic).
"""
import gzip
import io
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

import provenance

FIELDS = ("dept", "level", "area", "area_regional", "post", "name", "name_regional", "phone", "email", "address", "state",
          "district", "office_id", "source", "last_updated", "lat", "lon")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_AC = None


def clean(s):
    """One line, single spaces, no zero-width characters. ZWNJ / ZWJ (U+200C, U+200D) and the BOM are deleted, not spaced:
    they sit inside Hindi words ("स्‍टेण्‍ड")."""
    if s is None:
        return ""
    s = re.sub("[\u200c\u200d\ufeff]", "", str(s))
    return " ".join(re.sub("[\u200b\xa0]", " ", s).split())


def deob(s):
    """dcurban[at]nic[dot]in -> dcurban@nic.in (NIC sites write emails this way)."""
    s = re.sub(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", "@", s or "", flags=re.I)
    s = re.sub(r"\s*[\[\(\{]\s*hyphen\s*[\]\)\}]\s*", "-", s, flags=re.I)
    s = re.sub(r"\s*[\[\(\{]\s*underscore\s*[\]\)\}]\s*", "_", s, flags=re.I)
    return re.sub(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", ".", s, flags=re.I).strip()


def emails(s):
    """Every email address in a text (after deob), lower case, joined by ", "."""
    out = []
    for e in EMAIL.findall(deob(s or "")):
        e = e.strip(".").lower()
        if e not in out:
            out.append(e)
    return ", ".join(out)


def phones(*parts):
    """Phone numbers from one or more cells, as written (STD code kept), joined by ", ". PIN codes ("Pin-695122") are left out."""
    out = []
    for p in parts:
        t = re.sub(r"\s*[\u2010-\u2015\u2212]\s*", "-", clean(p))
        t = re.sub(r"(?i)\b(pin(\s*code)?|p\.?\s*o\.?)[\s:.-]*\d{3}\s?\d{3}\b", " ", t)
        t = re.sub(r"(?i)-\s*\d{3}\s?\d{3}\b(?=[^\d]*$)", " ", t) if re.search(r"(?i)[a-z]{3,}\s*-\s*\d{6}\b", t) else t
        for m in re.findall(r"(?:\+?91[\s-]*)?(?:\(?0\d{2,5}\)?[\s-]*)?\d[\d\s-]{4,}\d", t):
            m = m.strip(" -")
            parts = [m] if len(re.sub(r"\D", "", m)) <= 13 else [x.strip(" -") for x in re.split(r"\s+(?=\d)", m)]
            for x in parts:
                if len(re.sub(r"\D", "", x)) >= 6 and x not in out:
                    out.append(x)
    return ", ".join(out)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", clean(s).lower()).strip("-")


def record(module, key, **f):
    """(record id, data) for one office; fields not in FIELDS go in as extra keys; empty values are dropped."""
    d = {"type": "dept_office"}
    for k, v in f.items():
        if isinstance(v, str):
            v = clean(v)
        if v not in (None, "", [], {}):
            d[k] = v
    return f"dept:{module}:{key}", d


def keep(module, name, content, ext="html"):
    """A raw answer as a bucket file (gzip), the same way councillors.py keeps them."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return (f"depts/{module}/{name}.{ext}.gz", gzip.compress(content), "application/gzip")


def soup(html):
    return BeautifulSoup(html, "lxml")


def cell_text(td):
    """Cell text with <br> and block breaks as " | ", so name / phone / email lines stay apart."""
    for br in td.find_all("br"):
        br.replace_with(" | ")
    for p in td.find_all(["p", "div", "li"]):
        p.insert_after(" | ")
    t = clean(td.get_text(" "))
    return re.sub(r"(\s*\|\s*)+", " | ", t).strip(" |")


def table_no(table):
    """Source trail: the table's place among the page's <table> elements (1-based, document order, nested tables counted) -
    the same number as officials.tables gives."""
    return len(table.find_all_previous("table")) + 1


def grid(table, text=cell_text, pos=None):
    """Rows of an HTML table as lists of cell texts, rowspan and colspan filled in (the value is repeated).
    pos: a list; when given, it gets for each returned row its src_pos {"table": table_no, "row": <tr> number in the table,
    1-based, header row counted}."""
    out, carry = [], {}
    tno = table_no(table) if pos is not None else 0
    trn = 0
    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table:
            continue
        trn += 1
        row, col = [], 0
        cells = tr.find_all(["td", "th"], recursive=False)
        pending = list(cells)
        while pending or col in carry:
            if col in carry:
                v, left = carry[col]
                row.append(v)
                if left <= 1:
                    del carry[col]
                else:
                    carry[col] = (v, left - 1)
                col += 1
                continue
            td = pending.pop(0)
            v = text(td)
            span = int(re.sub(r"\D", "", td.get("colspan") or "1") or 1)
            rs = int(re.sub(r"\D", "", td.get("rowspan") or "1") or 1)
            for _ in range(min(span, 50)):
                row.append(v)
                if rs > 1:
                    carry[col] = (v, rs - 1)
                col += 1
        if any(row):
            out.append(row)
            if pos is not None:
                pos.append({"table": tno, "row": trn})
        else:
            provenance.skipped("empty")
    provenance.given(len(out))     # row counts (provenance.py): the reader uses or skips these, the header row too
    return out


def pdf_pages(content):
    """Text of each page of a PDF (pypdf layout mode keeps the table columns apart). [] if the file is not a readable PDF."""
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(content))
        out = []
        for pg in reader.pages:
            try:
                out.append(pg.extract_text(extraction_mode="layout") or "")
            except Exception:
                out.append(pg.extract_text() or "")
        return out
    except Exception:
        return []


def norm_ac(s):
    s = re.sub(r"\((sc|st|gen)\)", "", (s or "").lower())
    return re.sub(r"[^a-z]", "", s)


def ac_no(state, name, district=None):
    """ECI AC number for an AC name in a state (two-letter code: BR, MZ, JH ...), or None. district settles the few names that two
    ACs share (Kalyanpur, Pipra in Bihar)."""
    global _AC
    if _AC is None:
        _AC = json.loads((Path(__file__).parent / "ac_no.json").read_text())
    d = _AC.get(state, {})
    k = norm_ac(name)
    if k in d:
        return d[k]
    if district:
        hit = d.get(k + "@" + norm_ac(district))
        if hit is None:      # "South 24 Parganas" = "southtwentyfourpargan" (the file spells the number and cuts long names)
            dk = _dist_key(district)
            hit = next((v for kk, v in d.items() if kk.startswith(k + "@") and _dist_key(kk.split("@", 1)[1]) == dk), None)
        return hit
    return None


def _dist_key(s):
    return norm_ac(re.sub(r"\b24\b", "twentyfour", s or ""))[:12]
