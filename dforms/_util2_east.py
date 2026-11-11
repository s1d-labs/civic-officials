"""Shared parts of the east / north-east electricity readers (power2_tpodisha, power2_wbsedcl_ccc, power2_sikkim_staff,
power2_cesc, power2_mspdcl): spreadsheet and Word tables read with the standard library only (no openpyxl / python-docx on the
runners), and the tidy-up of names and mobiles that these sources share.

xlsx_rows(content) -> {sheet name: [[cell text, ...], ...]} (shared strings, inline strings and numbers; empty cells kept as "").
docx_tables(content) -> [[[cell text, ...], ...], ...] (one list of rows per <w:tbl>, paragraphs of a cell joined by " ").
"""
import io
import re
import zipfile
from xml.etree import ElementTree as ET

from dforms import _power

NS_X = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
HONORIFIC = re.compile(r"^\s*((sh|shri|shree|smt|mr|mrs|ms|miss|sri|er|dr)\.?\s+|(sh|shri|smt|mr|mrs|ms|er|dr)\.(?=\S))+", re.I)


def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def _text(el):
    return "".join(t.text or "" for t in el.iter("{%s}t" % NS_X["m"]))


def xlsx_rows(content):
    z = zipfile.ZipFile(io.BytesIO(content))
    names = z.namelist()
    shared = []
    if "xl/sharedStrings.xml" in names:
        shared = [_text(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS_X)]
    rels = {}
    if "xl/_rels/workbook.xml.rels" in names:
        for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
            rels[r.get("Id")] = r.get("Target")
    out = {}
    for sh in ET.fromstring(z.read("xl/workbook.xml")).iter("{%s}sheet" % NS_X["m"]):
        target = rels.get(sh.get(REL + "id"), "")
        path = "xl/" + target.lstrip("/").removeprefix("xl/")
        if path not in names:
            continue
        rows = []
        for row in ET.fromstring(z.read(path)).iter("{%s}row" % NS_X["m"]):
            cells = {}
            for c in row.findall("m:c", NS_X):
                t, v = c.get("t"), c.find("m:v", NS_X)
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr":
                    val = _text(c)
                else:
                    val = v.text if v is not None and v.text else ""
                    if re.fullmatch(r"\d+\.0", val):
                        val = val[:-2]
                cells[_col(c.get("r"))] = " ".join(val.replace("\xa0", " ").split())
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        out[sh.get("name")] = rows
    return out


def docx_tables(content):
    z = zipfile.ZipFile(io.BytesIO(content))
    root = ET.fromstring(z.read("word/document.xml"))
    tables = []
    for tbl in root.iter(W + "tbl"):
        rows = []
        for tr in tbl.findall(W + "tr"):
            row = []
            for tc in tr.findall(W + "tc"):
                paras = [" ".join("".join(t.text or "" for t in p.iter(W + "t")).split()) for p in tc.findall(W + "p")]
                row.append(" ".join(x for x in paras if x))
            rows.append(row)
        tables.append(rows)
    return tables


def person(name):
    """'Mr. Jitendra Behera ' -> 'Jitendra Behera'; None for empty or digit-only cells."""
    n = _power.clean(name)
    if not n:
        return None
    n = HONORIFIC.sub("", n).strip(" .,")
    return _power.clean(n) if n and not re.fullmatch(r"[\d\s.]*", n) else None


def head_map(row, names):
    """{key: column index} for a header row: names = {key: regex}; the first header cell that matches wins."""
    out = {}
    for i, c in enumerate(row):
        for k, rx in names.items():
            if k not in out and re.search(rx, c or "", re.I):
                out[k] = i
                break
    return out
