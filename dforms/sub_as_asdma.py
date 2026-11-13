"""Assam: district and revenue-circle disaster management officers, from the Assam State Disaster Management Authority (ASDMA) site
onlineasdma.assam.gov.in (NIC cloud, not the state data centre that hosts the unreachable district portals). Answers only from India.

Two queue items:
- page "emergency": emergency.html (about 120 KB). Table "Important Phone Nos. (District Level)": the Deputy Commissioner's office,
  residence and fax numbers of 34 districts (no names) -> dept administration, level district, post Deputy Commissioner; the DCs'
  satellite phones (GSPS numbers, 12 districts) join the same record as "satellite_phone". Table "Important Phone Nos. Of District
  Project Officers": the District Project Officer of each District Disaster Management Authority (33 districts; name, email,
  mobile, DEOC landline) -> dept revenue (Revenue and Disaster Management Department), level district.
- page "field": pdf/Field_Officers.xlsx (about 40 KB, linked from emergency.html "Details list Of Field Officers"): one disaster
  management Field Officer (FO) per revenue circle, about 160 rows: district, revenue circle, designation, name, mobile, email,
  office / fax / residence numbers -> dept revenue, level subdistrict, area = the revenue circle as the file spells it.
  Read with the standard library (zip + XML), no spreadsheet package.
Neither page shows a date. District names go to the LGD spelling with dforms.sub_as.district().
Record ids: dept:sub_as_asdma:AS-<district slug>:dc-office, :ddma-po[:<n>], :fo:<circle slug>.
"""
import io
import re
import zipfile
from xml.etree import ElementTree as ET

from dforms import _esw
from dforms.sub_as import district
import provenance

METHOD = "html table"     # page "field": "spreadsheet (xlsx)" on each record
METHOD_XLSX = "spreadsheet (xlsx, first worksheet)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_as_asdma"
BASE = "https://onlineasdma.assam.gov.in/"
PAGES = {"emergency": BASE + "emergency.html", "field": BASE + "pdf/Field_Officers.xlsx"}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def items(get=None):
    return [{"key": f"{MODULE}-{p}", "payload": {"reader": MODULE, "url": u, "state": "AS", "page": p, "india_only": True}}
            for p, u in PAGES.items()]


def _leaf_tables(soup):
    return [t for t in soup.find_all("table") if not t.find("table")]


def _std(std, num):
    std, num = re.sub(r"\D", "", std or ""), (num or "").strip()
    if not re.search(r"\d{5}", num):
        return ""
    return ", ".join(f"{std}-{n.strip()}" if std else n.strip() for n in re.split(r"\s*,\s*", num) if n.strip())


def parse_emergency(html, url=PAGES["emergency"]):
    soup = _esw.soup(html)
    dc, po, sat, satpos = {}, [], {}, {}
    for t in _leaf_tables(soup):
        tp = []
        rows = _esw.grid(t, pos=tp)
        if not rows:
            continue
        head = " ".join(rows[0]).lower()
        if "name of the districts" in head and "std code" in head:
            for r, pos in zip(rows[1:], tp[1:]):
                r = r + [""] * (6 - len(r))
                if not re.match(r"(?i)\s*d\.\s*c\.", r[1]):
                    provenance.skip_row(r, 'skip: not re.match(r"(?i)\\s*d\\.\\s*c\\.", r[1])')
                    continue
                d = district(re.sub(r"(?i)^\s*d\.\s*c\.\s*", "", r[1]))
                dc[d] = {"phone": _esw.phones(_std(r[2], r[3]), _std(r[2], r[4])), "fax": _esw.phones(_std(r[2], r[5])),
                         "office": _std(r[2], r[3]), "residence": _std(r[2], r[4]), "pos": pos}
        elif "allotted gsps" in head:
            for r, pos in zip(rows[1:], tp[1:]):
                m = re.match(r"(?i)\s*dc cum chairperson ddma\s*,\s*(.+)$", r[1] if len(r) > 1 else "")
                if m and len(r) > 2:
                    sat[district(m.group(1))] = re.sub(r"\D", "", r[2])
                    satpos[district(m.group(1))] = pos
        elif "name and designation" in head and "landline deoc" in head:
            for r, pos in zip(rows[1:], tp[1:]):
                r = r + [""] * (5 - len(r))
                m = re.match(r"^(.*?),\s*PO\s*,?\s*(.+)$", r[1])
                if not m:
                    provenance.skip_row(r, 'skip: not m')
                    continue
                po.append((m.group(1).strip(), district(m.group(2)), m.group(2).strip(), r[2], r[3], r[4], pos))
    recs = []
    for d, v in dc.items():
        recs.append(_esw.record(MODULE, f"AS-{_esw.slug(d)}:dc-office", dept="administration", level="district", area=d,
                                post="Deputy Commissioner", designation="Deputy Commissioner (office, residence)", phone=v["phone"],
                                fax=v["fax"], satellite_phone=sat.get(d, ""), district=d, state="AS", source=url,
                                src_pos={**v["pos"], **({"satellite_phone_row": satpos[d]} if d in satpos else {})}))
    seen = set()
    for name, d, where, mail, mob, deoc, pos in po:
        base = key = f"AS-{_esw.slug(d)}:ddma-po"
        n = 2
        while key in seen:
            key, n = f"{base}:{n}", n + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="revenue", level="district", area=d, post="District Project Officer, DDMA",
                                designation=f"Project Officer, District Disaster Management Authority, {where}", name=name,
                                phone=_esw.phones(mob, deoc), email=_esw.emails(mail), district=d, state="AS", source=url,
                                src_pos=pos))
    return recs


def sheet_rows(content, where=None):
    """Rows of the first worksheet of an .xlsx as lists of strings (shared strings resolved, columns by letter). where: a list;
    when given, it gets {"sheet": worksheet part, "row": the row's r number} per row."""
    z = zipfile.ZipFile(io.BytesIO(content))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(x.text or "" for x in si.iter("{%s}t" % NS["m"])))
    name = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))[0]
    out = []
    for row in ET.fromstring(z.read(name)).iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            col = re.sub(r"\d", "", c.get("r", ""))
            v = c.find("m:v", NS)
            val = v.text if v is not None and v.text else ""
            if c.get("t") == "s" and val:
                val = shared[int(val)]
            elif c.get("t") == "inlineStr":
                val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            cells[col] = _esw.clean(val)
        if any(cells.values()):
            width = max(_colno(k) for k in cells) + 1
            out.append([cells.get(_colname(i), "") for i in range(width)])
            if where is not None:
                rn = row.get("r")
                where.append({"sheet": name, "row": int(rn) if (rn or "").isdigit() else len(out)})
    return out


def _colno(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def _colname(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def parse_field(content, url=PAGES["field"]):
    where = []
    rows = sheet_rows(content, where)
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    col = {k: next((i for i, h in enumerate(head) if h.startswith(k)), None)
           for k in ("district", "revenue circle", "designation", "name", "mobile", "e-mail", "office", "fax", "residence")}
    if col["district"] is None or col["revenue circle"] is None:
        return []

    def cell(r, k):
        i = col[k]
        return r[i] if i is not None and i < len(r) else ""

    recs, seen = [], set()
    for r, pos in zip(rows[1:], where[1:]):
        circle, dname = cell(r, "revenue circle"), cell(r, "district")
        if not circle or not dname:
            provenance.skip_row(r, 'skip: not circle or not dname')
            continue
        d = district(dname)
        base = key = f"AS-{_esw.slug(d)}:fo:{_esw.slug(circle)}"
        n = 2
        while key in seen:
            key, n = f"{base}:{n}", n + 1
        seen.add(key)
        desig = cell(r, "designation")
        rec = _esw.record(MODULE, key, dept="revenue", level="subdistrict", area=circle,
                          post="Field Officer (Disaster Management)", designation=desig, name=cell(r, "name"),
                          phone=_esw.phones(cell(r, "mobile"), cell(r, "office"), cell(r, "residence")),
                          fax=_esw.phones(cell(r, "fax")), email=_esw.emails(cell(r, "e-mail")), district=d, state="AS",
                          source=url, src_pos=pos, method=METHOD_XLSX)
        if rec[1].get("name") or rec[1].get("phone") or rec[1].get("email"):
            recs.append(rec)
    return recs


def fetch(p, get):
    page = p.get("page", "emergency")
    url = p.get("url") or PAGES[page]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if page == "field":
        files = [_esw.keep(MODULE, "field_officers", r.content, ext="xlsx")]
        try:
            recs = parse_field(r.content, url)
        except (zipfile.BadZipFile, ET.ParseError, IndexError):
            return [], files, "not an xlsx file"
    else:
        files = [_esw.keep(MODULE, "emergency", r.content)]
        recs = parse_emergency(r.text, url)
    return recs, files, "" if recs else "no rows"
