"""Manipur: Public Health Engineering Department (PHED), directory of officers in the RTI suo-motu disclosure,
www.phedmanipur.gov.in/wp-content/uploads/2026/06/SUO-MOTU-DISCLOSURES-PHED-30-06-2026.pdf (30 pages, 1 MB; the directory is
Section 4(1)(b)(ix), "Directory of officers of the Department as on 03/06/2026", printed pages 14-15). Answers from Germany and India.
Columns: S. No., Name of the Officers, Office (post, e.g. "i/c EE/Imphal East"), Contact No., Email. Cells wrap over 2-3 lines and
the row number sits in the middle of its cell, so every unnumbered line goes to the nearest numbered line (a tie goes to the row
above, except when the line starts a new e-mail address). 40 officers. One queue item.
Record ids: dept:water_mn:<slug of the office without "i/c">[:n].
"""
import re

import provenance
from dforms import _esw

METHOD = "pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_mn"
URL = "https://www.phedmanipur.gov.in/wp-content/uploads/2026/06/SUO-MOTU-DISCLOSURES-PHED-30-06-2026.pdf"
MOBILE = re.compile(r"^\d{10}$")
ORG = "Public Health Engineering Department, Manipur"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "MN"}}]


def _runs(line):
    return [(m.start(), m.group(0).strip()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def directory(pages):
    """(as-on date, [{"no", "name", "office", "phone", "email"}]) from the pages of the directory section."""
    lines, date, on = [], None, False
    where = []
    for pn, text in enumerate(pages, 1):
        for li, ln in enumerate(text.splitlines(), 1):
            if re.search(r"Directory of officers", ln, re.I):
                on = True
                m = re.search(r"as on\s*(\d{1,2})/(\d{1,2})/(\d{4})", ln)
                date = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
                continue
            if on and re.search(r"Section\s*4\s*\(", ln):
                return date, _rows(lines, where)
            if on:
                lines.append(ln)
                where.append((pn, li, ln))
    return date, _rows(lines, where)


def _rows(lines, where=None):
    # columns from the mobile numbers: name < office < phone < email
    xs = sorted(x for ln in lines for x, t in _runs(ln) if MOBILE.match(t))
    if not xs:
        return []
    px = xs[len(xs) // 2]
    parsed = []
    for li, ln in enumerate(lines):
        runs = _runs(ln)
        if not runs or re.match(r"^\s*(S\.|No\b|Officers\b)", ln) or re.fullmatch(r"\s*\d{1,3}\s*", ln):
            provenance.skip_line(ln, 'skip: not runs or re.match(r"^\\s*(S\\.|No\\b|Officers\\b)", ln) or re.fullma...')
            continue
        row = {"no": None, "name": [], "office": [], "phone": [], "email": [], "li": li}
        for x, t in runs:
            if x < 4 and re.fullmatch(r"\d{1,2}", t):
                row["no"] = int(t)
                continue
            m = re.match(r"^(\d{1,2})\s+(.*)$", t)
            if x < 4 and m:
                row["no"], t, x = int(m.group(1)), m.group(2), x + len(m.group(1)) + 1
            if MOBILE.match(t) or (abs(x - px) <= 3 and re.fullmatch(r"[\d ]{6,}", t)):
                row["phone"].append(t)
            elif x > px + 6:
                row["email"].append(t)
            elif px - 26 <= x < px - 1:
                row["office"].append(t)
            else:
                row["name"].append(t)
        if any(row[k] for k in ("name", "office", "phone", "email")) or row["no"]:
            parsed.append(row)
    anchors = [i for i, r in enumerate(parsed) if r["no"] is not None]
    if not anchors:
        return []
    owner = {}
    for i, r in enumerate(parsed):
        if r["no"] is not None:
            owner[i] = i
            continue
        prev = max((a for a in anchors if a < i), default=None)
        nxt = min((a for a in anchors if a > i), default=None)
        if prev is None or (nxt is not None and i - prev > nxt - i):
            owner[i] = nxt if nxt is not None else prev
        elif nxt is not None and i - prev == nxt - i:
            pe = "".join(e for j, o in owner.items() if o == prev for e in parsed[j]["email"])
            frag = "".join(r["email"])
            starts_new = (len(frag) > 3 and "@" not in frag and not frag.startswith((".", "@"))
                          and re.search(r"@[\w-]+(\.[\w-]+)*\.(com|in|org|net)$", pe))
            owner[i] = nxt if starts_new else prev
        else:
            owner[i] = prev
    out = []
    for a in anchors:
        parts = [parsed[j] for j in sorted(owner) if owner[j] == a]
        pos = None
        if where:                         # source trail: the lines of the row on the page of its numbered line
            at = [where[p["li"]] for p in parts if where[p["li"]][0] == where[parsed[a]["li"]][0]]
            pos = provenance.line_pos(at[0][0], at[0][1], "\n".join(w[2] for w in at),
                                      lines=[w[1] for w in at] if len(at) > 1 else None)
        out.append({"no": parsed[a]["no"], **({"pos": pos} if pos else {}), "name": " ".join(t for p in parts for t in p["name"]),
                    "office": " ".join(t for p in parts for t in p["office"]),
                    "phone": " ".join(t for p in parts for t in p["phone"]),
                    "email": "".join(t.replace(" ", "") for p in parts for t in p["email"])})
    return out


def _level(office):
    o = office.lower()
    if re.search(r"\bse\b|superintending", o):
        return "circle"
    if re.search(r"\bee\b|executive", o):
        return "division"
    return "state"


def parse(pages, url=URL):
    date, rows = directory(pages)
    recs, seen = [], set()
    for r in rows:
        office = _esw.clean(r["office"])
        core = _esw.clean(re.sub(r"\bi/c\b", " ", office, flags=re.I))
        m = re.match(r"^(SE|EE)\s*[/,]\s*(.+)$", core)
        area = m.group(2) if m and m.group(2).upper() != "PHED" else ("Manipur" if _level(core) == "state" else "")
        key = _esw.slug(core) or str(r["no"])
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="water", level=_level(core), area=area, post=office, name=_esw.clean(r["name"]),
                                phone=_esw.phones(r["phone"]), email=_esw.emails(r["email"]), state="MN",
                                office_id=f"MN-PHED-{k.replace(':', '-')}", org=ORG, source=url, last_updated=date,
                                src_pos=r.get("pos")))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "suo-motu-disclosure", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p.get("url", URL))
    return recs, files, "" if recs else "no directory"
