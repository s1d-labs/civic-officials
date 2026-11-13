"""Odisha: elected Panchayati Raj members of the General Election to PRIs 2022 (poll February 2022), from two open sources.

1. Panchayati Raj & Drinking Water Department (panchayat.odisha.gov.in, lists dated 2025-08, text PDFs, BookmanOldStyle):
   - "ZP President.pdf" (30 rows: district | elected Zilla Parishad President | party),
   - "ZP Vice President.pdf" (30 rows, same columns),
   - "PS Chairman and Vice Chairman.pdf" (314 panchayat samitis: district | samiti | chairman | vice chairman),
   - "ZP Member_0.pdf" (852 zones: district | zone no | constituency (the block) | member | party).
2. State Election Commission (sec.odisha.gov.in, page "Elected Sarpanch & P.S Member"): the page reads its file list from
   /CMS/GetCMSTableData?TableId=57 (JSON; file names carry a fresh uuid, so the item asks the list first):
   - "Name of Elected Sarpanch(All District)" (210 pages, about 6,790 gram panchayats: samiti | gram panchayat | sarpanch),
   - "Name of Elected P.S Member(All District)" (207 pages, one member per gram panchayat: samiti | GP constituency | member),
   - "Name of Elected Ward Member(All District)" (9 MB, not read here: noted as a source file).
Measured 2026-11-13 from Mumbai (sec.odisha.gov.in answered directly; the archive has both hosts only from Indian vantages).

Reading: `pdftotext -bbox-layout` gives every text line with its box. The columns have fixed x positions per file (SPECS);
a cell that wraps is printed on lines above and below its row (names are top-aligned and may sit a few points above their
row), so each line goes to the row of the nearest "anchor" line (the gram panchayat, or the name) by vertical centre.
Group cells (district, samiti, serial) are printed on the first row of their group and carried down. The district of the SEC
lists comes from the page title "DIST.-<NAME>"; ZP member districts restart the zone numbering at 1.
Records (type pri_member, dforms/_pri.py): one per person. src_pos = {"page", "y", "lines": the raw text lines of the row}.
Record ids: pri:pri_od:<list>:<district slug>:<samiti slug>:<body slug>[:<n>]. LGD codes are matched by the loader on
district + samiti + gram panchayat names (English names in both).
"""
import json
import re
import shutil
import subprocess
from html import unescape

from dforms import _pri
import provenance

METHOD = "pdf text boxes (pdftotext -bbox-layout; columns by x position, wrapped cells by nearest row)"
MODULE = "pri_od"
STATE = "OD"
ELECTION = "Odisha General Election to PRIs 2022"
PRD = "https://panchayat.odisha.gov.in/sites/default/files/2025-08/"
SEC = "https://sec.odisha.gov.in"
SEC_TABLE = SEC + "/CMS/GetCMSTableData?TableId=57"

# list -> columns (name, x start in points), anchor column, merge gap for wrapped anchor lines (points), source
SPECS = {
    "zp_president": {"url": PRD + "ZP%20President.pdf", "cols": [("sl", 0), ("district", 70), ("name", 190), ("party", 440)],
                     "anchor": "name", "gap": 12},
    "zp_vice_president": {"url": PRD + "ZP%20Vice%20President.pdf",
                          "cols": [("sl", 0), ("district", 70), ("name", 190), ("party", 440)], "anchor": "name", "gap": 12},
    "ps_chairman": {"url": PRD + "PS%20Chairman%20and%20Vice%20Chairman.pdf",
                    "cols": [("sl", 0), ("district", 50), ("sl2", 125), ("samiti", 145), ("name", 270), ("vice", 410)],
                    "anchor": "name", "gap": 12},
    "zp_member": {"url": PRD + "ZP%20Member_0.pdf",
                  "cols": [("sl", 0), ("district", 70), ("zone", 165), ("constituency", 200), ("name", 320), ("party", 500)],
                  "anchor": "name", "gap": 9},
    "sarpanch": {"sec_title": r"(?i)elected\s+sarpanch", "cols": [("sl", 0), ("samiti", 60), ("gp", 195), ("name", 355)],
                 "anchor": "gp", "gap": 13.5},
    "ps_member": {"sec_title": r"(?i)elected\s+p\.?\s*s\.?\s+member", "cols": [("sl", 0), ("samiti", 60), ("gp", 195), ("name", 355)],
                  "anchor": "gp", "gap": 13.5},
}
WARD_FILE = r"(?i)elected\s+ward\s+member"
# what each list gives: (level, role, post) per person column
POSTS = {
    "zp_president": [("name", "zp", "head", "Zilla Parishad President")],
    "zp_vice_president": [("name", "zp", "deputy", "Zilla Parishad Vice-President")],
    "ps_chairman": [("name", "ps", "head", "Panchayat Samiti Chairman"), ("vice", "ps", "deputy", "Panchayat Samiti Vice-Chairman")],
    "zp_member": [("name", "zp", "member", "Zilla Parishad Member")],
    "sarpanch": [("name", "gp", "head", "Sarpanch")],
    "ps_member": [("name", "ps", "member", "Panchayat Samiti Member")],
}
HEADER = re.compile(r"(?i)^(sl\.?|no\.?|sl\.?\s*no\.?|name of( the)?.*|district|constituencies|panchayat\s+samiti|zp|zone|no\.|"
                    r"elected .*|vice[- ]president\.?|pol\.?\s*party|political|party|[ivx]+\.?(\s+[ivx]+\.?)*|\d+(\s+\d+)+|general election.*|"
                    r"name of elected.*|dist\s*[.-].*|constituency|p\.?\s*s\.?\s*member|zp member|sarpanch|samiti|.*affiliation)$")
DIST = re.compile(r"(?i)^\s*dist\s*[.-]\s*-?\s*([a-z][a-z .]+?)\s*$")
TWO = re.compile(r"(?i)\S\s+(smt|sri|shri)\.?\s")     # a second honorific inside a name: two names joined
# district as the lists write it -> LGD district name (lgd.pri_local_bodies Zilla Parishad names)
LGD_DISTRICT = {"Angul": "Anugul", "Balasore": "Baleshwar", "Bolangir": "Balangir", "Jagatsinghpur": "Jagatsinghapur",
                "Jajpur": "Jajapur", "Kendrapada": "Kendrapara", "Keonjhar": "Kendujhar", "Subarnapur": "Sonepur",
                "Khurda": "Khordha", "Nawarangpur": "Nabarangpur"}
GROUP = ("sl", "district", "samiti", "sl2")
END = re.compile(r"(?i)^abstract\b")
TOTAL = re.compile(r"(?i)^(bjd|bjp|inc|congress|others?|ind\w*|total)\s*\d+$")


def items(get=None):
    out = [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "list": k, "url": v["url"], "state": STATE,
                                                "expected": {"zp_president": 30, "zp_vice_president": 30, "ps_chairman": 628,
                                                             "zp_member": 852}[k], "route": "proxy"}}
           for k, v in SPECS.items() if "url" in v]
    out += [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "list": k, "url": SEC_TABLE, "state": STATE,
                                                 "expected": 6790, "route": "proxy"}} for k in ("sarpanch", "ps_member")]
    out.append({"key": f"{MODULE}:ward_member_file", "payload": {"reader": MODULE, "list": "ward_member_file", "url": SEC_TABLE,
                                                                  "state": STATE, "expected": 0, "route": "proxy"}})
    return out


def pdftotext():
    if shutil.which("pdftotext"):
        return True
    subprocess.run("sudo -n apt-get -o DPkg::Lock::Timeout=600 install -y -q poppler-utils", shell=True, capture_output=True)
    return bool(shutil.which("pdftotext"))


def bbox_pages(content):
    """[[(x, y0, y1, text), ...] per page] from `pdftotext -bbox-layout` (lines, page order)."""
    r = subprocess.run(["pdftotext", "-bbox-layout", "-", "-"], input=content, capture_output=True, timeout=600)
    return parse_bbox(r.stdout.decode("utf-8", "replace"))


def parse_bbox(xhtml):
    pages = []
    for pg in xhtml.split("<page ")[1:]:
        lines = []
        for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">(.*?)</line>', pg, re.S):
            words = [(float(x), unescape(w)) for x, w in re.findall(r'<word xMin="([\d.]+)"[^>]*>([^<]*)</word>', m.group(4))]
            text = _pri.clean(" ".join(w for _, w in words))
            if text:
                lines.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), text, words))
        pages.append(lines)
    return pages


def col_of(x, cols):
    name = cols[0][0]
    for c, x0 in cols:
        if x >= x0 - 2:
            name = c
    return name


def rows_of(lines, spec):
    """One page's lines -> rows {column: text} (+ "_y", "_lines") anchored on spec["anchor"]; the page's DIST title in "_dist"."""
    cols, anchor = spec["cols"], spec["anchor"]
    dist, body = None, []
    end = min([ln[1] for ln in lines if END.match(ln[3])] or [1e9])
    head = max([ln[2] for ln in lines if HEADER.match(ln[3]) and not DIST.match(ln[3]) and ln[1] < 250] or [-1e9])
    for x, y0, y1, t, words in lines:
        if y0 >= end:
            continue
        m = DIST.match(t)
        if m and dist is None and y0 < 200:
            dist = m.group(1).strip()
            continue
        if HEADER.match(t) or TOTAL.match(t):
            provenance.skip_line(x, 'skip: HEADER.match(t) or TOTAL.match(t)')
            continue
        if re.fullmatch(r"[\dIVX.\s]+", t) and y0 < head + 12:
            continue                  # the column number row under the header ("1 2 3 4 5 6", "I. II. III. IV.")
        parts = {}                    # a line that crosses a column start ("10 Kaniha", "1 Angul") is split word by word
        for wx, w in words:
            parts.setdefault(col_of(wx, cols), []).append(w)
        for c, ws in parts.items():
            body.append((c, (y0 + y1) / 2, y0, _pri.clean(" ".join(ws))))
    rows = []
    for c, yc, y0, t in sorted((b for b in body if b[0] == anchor), key=lambda b: b[2]):
        if rows and y0 - rows[-1]["_y0"] < spec["gap"]:
            rows[-1][anchor] += " " + t           # a wrapped anchor cell
            rows[-1]["_ys"].append(yc)
            rows[-1]["_lines"].append(t)
            continue
        rows.append({anchor: t, "_y0": y0, "_ys": [yc], "_lines": [t]})
    if not rows:
        return [], dist
    for r in rows:
        r["_y"] = sum(r["_ys"]) / len(r["_ys"])
    for c in [c for c, _ in cols if c != anchor]:
        mine = sorted((b for b in body if b[0] == c), key=lambda b: b[2])
        cells = []                                  # the column's lines grouped into cells (wrapped lines are close together)
        for _, yc, y0, t in mine:
            if cells and y0 - cells[-1]["y0"] < spec["gap"]:
                cells[-1]["t"].append(t)
                cells[-1]["ys"].append(yc)
                cells[-1]["y0"] = y0
            else:
                cells.append({"t": [t], "ys": [yc], "y0": y0})
        if c not in GROUP and len(cells) == len(rows):
            pairs = zip(rows, cells)                # one cell per row: pair them in order (cells may sit half a row off)
        else:
            # else each line to the row nearest to it (a wrapped name is printed around its row's centre)
            pairs = [(min(rows, key=lambda r: abs(r["_y"] - yc)), {"t": [t], "ys": [yc]})
                     for x in cells for t, yc in zip(x["t"], x["ys"])]
        for r, x in pairs:
            t = " ".join(x["t"])
            r[c] = (r[c] + " " + t) if c in r else t
            r["_lines"].extend(x["t"])
    return rows, dist


def table(pages, spec):
    """Every row of a list with group cells carried down: [(page, row)]."""
    out, carry, dist = [], {}, None
    group = [c for c, _ in spec["cols"] if c in GROUP]
    for n, lines in enumerate(pages, 1):
        rows, d = rows_of(lines, spec)
        if d:
            if d != dist:
                carry = {}
            dist = d
        for r in rows:
            for c in group:
                if r.get(c):
                    carry[c] = r[c]
                    if c == "district":
                        carry.pop("samiti", None)
                elif c in carry:
                    r[c] = carry[c]
            if dist:
                r.setdefault("district", dist)
            out.append((n, r))
    return out


def zp_districts(pages, rows):
    """ZP members: the district label is printed in the middle of its group (often below its first rows), so rows take the
    district by group order: the k-th district serial (column "sl") gets the k-th district label of the file."""
    spec = SPECS["zp_member"]
    labels = []
    for lines in pages:
        for x, y0, y1, t, words in sorted(lines, key=lambda ln: ln[1]):
            if col_of(x, spec["cols"]) in ("sl", "district") and not HEADER.match(t) and re.fullmatch(r"[A-Za-z .]+", t):
                labels.append(t.title())
    k, prev = -1, None
    for _, r in rows:
        if r.get("sl") != prev:
            k, prev = k + 1, r.get("sl")
        r["district"] = labels[k] if 0 <= k < len(labels) else None
    return rows


def person(name):
    """'Smt. Babita Pradhan' -> (name as written, gender from the honorific or None)."""
    n = _pri.clean(name).strip(" .")
    g = "female" if re.match(r"(?i)^(smt|kumari|ku)\b", n) else "male" if re.match(r"(?i)^(sri|shri)\b", n) else None
    return n, g


def records(content, lst, url, source=None):
    spec = SPECS[lst]
    pages = bbox_pages(content)
    rows = table(pages, spec)
    if lst == "zp_member":
        rows = zp_districts(pages, rows)
    out, seen = [], {}
    for page, r in rows:
        for col, level, role, post in POSTS[lst]:
            if not r.get(col) or _pri.int_or_none(r[col]) is not None:
                continue
            name, gender = person(r[col])
            district = (r.get("district") or "").title() or None
            samiti = r.get("samiti")
            if samiti:
                samiti = re.sub(r"^\d+\s+", "", samiti)
            f = dict(state=STATE, level=level, role=role, post=post, name=name, gender=gender,
                     party=r.get("party") if col == "name" else None, district=district,
                     district_lgd=LGD_DISTRICT.get(district, district),
                     election=ELECTION, election_year=2022, source=source or url, src_url=url,
                     src_pos={"page": page, "y": round(r["_y"], 1), "lines": r["_lines"]},
                     cells={c: r[c] for c in r if not c.startswith("_")},
                     check="two names may be joined" if TWO.search(name) else None)
            if lst in ("zp_president", "zp_vice_president", "zp_member"):
                f.update(body_name=district)
                if lst == "zp_member":
                    f.update(ward_no=str(_pri.int_or_none(r.get("zone")) or "") or None, constituency=r.get("constituency"),
                             block=r.get("constituency"))
                key = f"{lst}:{_pri.slug(district or '')}" + (f":{f.get('ward_no') or 'row'}" if lst == "zp_member" else "")
            elif lst == "ps_chairman":
                f.update(body_name=samiti, block=samiti)
                key = f"{lst}:{_pri.slug(district or '')}:{_pri.slug(samiti or '')}:{role}"
            elif lst == "sarpanch":
                f.update(body_name=r["gp"], block=samiti)
                key = f"{lst}:{_pri.slug(district or '')}:{_pri.slug(samiti or '')}:{_pri.slug(r['gp'])}"
            else:                           # ps_member: one member per gram panchayat constituency of the samiti
                f.update(body_name=samiti, block=samiti, constituency=r["gp"])
                key = f"{lst}:{_pri.slug(district or '')}:{_pri.slug(samiti or '')}:{_pri.slug(r['gp'])}"
            k = seen[key] = seen.get(key, 0) + 1
            out.append(_pri.record(MODULE, key + (f":{k}" if k > 1 else ""), **f))
    return out


def sec_file(get, rx):
    """(file url, title) from the SEC CMS table of the 'Elected Sarpanch & P.S Member' page."""
    r = get(SEC_TABLE)
    if r is None:
        return None, None
    try:
        rows = json.loads(r.json()[0]["tableData"])["rows"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None, None
    for row in rows:
        if re.search(rx, row.get("Title", "")) and row.get("Download"):
            return SEC + row["Download"], row["Title"]
    return None, None


def fetch(p, get):
    lst = p["list"]
    if lst == "ward_member_file":
        url, title = sec_file(get, WARD_FILE)
        if not url:
            return [], [], "ward member file not listed"
        r = get(url)        # the trail copies the file to the bucket (sources/<sha>); OCR / text reading later
        if r is None:
            return [], [], "no answer"
        return [(f"pri:{MODULE}:file:ward_member", {"type": "pri_source_file", "state": STATE, "url": url, "title": title,
                                                    "size": len(r.content), "election": ELECTION, "src_url": url,
                                                    "src_pos": {"file": url},
                                                    "note": "ward members of all gram panchayats: not read yet"})], [], ""
    if not pdftotext():
        return [], [], "pdftotext not available"
    spec = SPECS[lst]
    source = None
    if "sec_title" in spec:
        url, _ = sec_file(get, spec["sec_title"])
        if not url:
            return [], [], "file not listed in the SEC table"
        source = SEC + "/Landing/ElectedSarpanchPSMember"
    else:
        url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    recs = records(r.content, lst, url, source)
    return recs, [], "" if recs else "no rows read"
