"""Andhra Pradesh: elected Panchayati Raj representatives, from the State Election Commission's results files (sec.ap.gov.in, a
React site; the file names are in its JS bundle /static/js/main.<hash>.js, page /ElectedCandidates and the "Results" tabs).

Files (Excel exports with a text layer: pdftotext -layout, no OCR; measured 2026-11-13):
- Gram panchayats, ordinary elections February 2021, one file per old district (13):
  Uploads/Doc21/Ele_Relts21/<DISTRICT>.pdf, "ELECTED SARPANCHES (S), UPA-SARPANCHES (US) & WARD MEMBERS (WM)". Columns:
  Revenue Division | Mandal | Gram Panchayat | Ward Code | Post | Reservation | Elected Candidate | Community | Educational
  Qualification. Ward code 0 = the sarpanch; the upa-sarpanch is the member of the ward in "Ward Code". Srikakulam: 317 pages,
  12,040 rows (1,164 sarpanches); YSR Kadapa: 8,498 rows (790 sarpanches). Revenue division and mandal are sometimes
  separated by one space only; a long name wraps onto the line(s) above its row.
- Uploads/Doc21/MPTC.pdf (580 pages, ~9,700 rows) and Uploads/Doc21/ZPTC.pdf (44 pages, ~650 rows), elections of 2021
  (poll 08.04.2021, count 19.09.2021): Sl.No | District | Mandal | MPTC (ZPTC) | Reservation | Candidate Name | Party |
  Gender | Community; a column-number line "1 2 3 ... 9" on every page.
- Uploads/Doc21/MPP_PRESIDENTS_VICE_PRESIDENTS_and_Co_OPTED_MEMBERS_LIST.pdf (42 pages, ~650 mandals): District | Mandal Parishad
  | Reserved | President | Party | Vice President | Party | one more Vice President | Party | Co-opted Member.
- Uploads/Doc21/ZPP_CHAIRPERSON_VICE_CHAIRPERSONS_and_Co_OPTED_MEMBERS_LIST.pdf (2 pages, 13 ZPPs): District | ZPP | Reserved |
  Chairperson | Party | Vice-Chairpersons (two, on the lines above and below) | Party | Co-opted Members (two).
Rows: a data line starts with the serial number (GP files: the ward code and post S/US/WM). Wrapped cell text on other lines is
joined to the nearest data line (a tie goes to the next row: GP names wrap upwards) and to the column whose position is nearest
(page column-number line, else the median positions of the page's complete rows).

Term: the GP bodies of February 2021 and the MPP/ZPP bodies of September 2021 were elected for five years. The SEC held the
second ordinary MPTC/ZPTC poll on 05.11.2026; on 2026-11-13 the site lists only reservations for 2026 rural bodies (no results).
The records say which election they come from ("election"); the loader decides what is current.

One queue item = one file. Payload {"kind": "form-pri_ap", "state": "AP", "url", "file" ("gp" | "mptc" | "zptc" | "mpp" |
"zpp"), "district" (gp files), "level", "election", "route"; optional "stored" (bucket copy: then the site is not asked)}.
Records: type pri_member (cforms/_pri.py). Ids: pri:AP:gp:<lgd or names>:head|vice|w<ward>; pri:AP:ps:<mandal>:head|vice|
vice-2|coopted|w<MPTC name>; pri:AP:zp:<zpp>:head|vice|vice-2|coopted-1|coopted-2|w<ZPTC name>.
"""
import os
import re
import statistics
import subprocess
import tempfile

import provenance
from cforms import _pri

METHOD = "pdf text (pdftotext -layout; rows by serial number or ward code, wrapped cells joined by line distance and column)"

BASE = "https://sec.ap.gov.in/Uploads/Doc21/"
GP_FILES = {  # SEC district name (as the site lists it) -> file name (page /ElectedCandidates, map Ib of the JS bundle)
    "Srikakulam": "SRIKAKULAM.pdf", "Vizianagaram": "VIZIANAGARAM.pdf", "Visakhapatnam": "VISAKHAPATNAM.pdf",
    "East Godavari": "EAST_GODAVARI.pdf", "West Godavari": "WEST_GODAVARI.pdf", "Krishna": "KRISHNA.pdf", "Guntur": "GUNTUR.pdf",
    "Prakasam": "PRAKASAM.pdf", "SPSR Nellore": "SPSR_NELLORE.pdf", "Chittoor": "CHITTOOR.pdf", "YSR Kadapa": "YSR_KADAPA.pdf",
    "Kurnool": "KURNOOL.pdf", "Ananthapuram": "ANANTAPURAMU.pdf",
}
STATE_FILES = {
    "mptc": ("MPTC.pdf", "ps"), "zptc": ("ZPTC.pdf", "zp"),
    "mpp": ("MPP_PRESIDENTS_VICE_PRESIDENTS_and_Co_OPTED_MEMBERS_LIST.pdf", "ps"),
    "zpp": ("ZPP_CHAIRPERSON_VICE_CHAIRPERSONS_and_Co_OPTED_MEMBERS_LIST.pdf", "zp"),
}
ELECTION_GP = "Andhra Pradesh gram panchayat ordinary elections 2021 (February 2021)"
ELECTION_PZ = "Andhra Pradesh MPTC / ZPTC ordinary elections 2021 (poll 08.04.2021, count 19.09.2021)"
# the 13 old districts: LGD keeps the zilla parishads under these (names as LGD writes them)
LGD_ZP = {"srikakulam": "Srikakulam", "vizianagaram": "Vizianagaram", "vizainagaram": "Vizianagaram",
          "visakhapatnam": "Visakhapatanam", "eastgodavari": "East Godavari", "westgodavari": "West Godavari",
          "krishna": "Krishna", "guntur": "Guntur", "prakasam": "Prakasam", "spsrnellore": "Spsr Nellore", "nellore": "Spsr Nellore",
          "chittoor": "Chittoor", "ysrkadapa": "Y.S.R.", "kadapa": "Y.S.R.", "ysr": "Y.S.R.", "kurnool": "Kurnool",
          "ananthapuram": "Anantapur", "ananthapuramu": "Anantapur", "anantapuramu": "Anantapur", "anantapur": "Anantapur"}
GP_ROW = re.compile(r"^(?P<pre>\S.*?)\s+(?P<ward>\d+)\s+(?P<post>S|US|WM)\s+(?P<res>[A-Z]{2,3}\s*(?:\(\s*[GW]\s*\))?)\s+(?P<rest>\S.*)$")
GP_HEAD = re.compile(r"(?i)revenue\s+division|ordinary elections to gram|ward\s+code|elected candidate")
DATA = re.compile(r"^\s*(\d+)\s+[A-Za-z]")
NUMS = re.compile(r"^\s*1\s+2\s+3\s+4\s+5")
PIECE = re.compile(r"\S+(?: \S+)*")
COLS = {  # columns after the serial number
    "mptc": ["sl", "district", "mandal", "seat", "reservation", "name", "party", "gender", "community"],
    "zptc": ["sl", "district", "mandal", "seat", "reservation", "name", "party", "gender", "community"],
    "mpp": ["sl", "district", "mandal", "reservation", "name", "party", "vice", "vice_party", "vice2", "vice2_party", "coopted"],
    "zpp": ["sl", "district", "zpp", "reservation", "name", "party", "vice", "vice_party", "coopted"],
}
HEADER_WORDS = re.compile(r"(?i)^(particulars.*|.*ordinary elections.*|.*affiliation|s\.?\s*l?\.?\s*no\.?|reserved|reservation|"
                          r"name of the.*|.*declared.*|elected as.*|\(s/sri/smt\)|for|as|party|zpp|mandal|districts?|"
                          r"candidate.*|gender|community|mptc|zptc|.*president.*|.*chairperson.*|co-opted members?|person.*|"
                          r"vice\s*-\s*chairpersons|zilla praja parishads?.*|mandal parishads?.*|parishad)$")


def norm(s):
    return _pri.norm(s)


def lgd_zp(district):
    return LGD_ZP.get(re.sub(r"[^a-z]", "", (district or "").lower()), district or "")


def pieces(line):
    return [(m.start(), m.end(), m.group(0)) for m in PIECE.finditer(line)]


def pages_of(raw):
    return raw.split("\f")


# ---------------------------------------------------------------- gram panchayat files
def split_pre(pre, divisions, mandals):
    """Revenue division, mandal, gram panchayat from the text before the ward code."""
    parts = re.split(r"\s{2,}", pre.strip())
    if len(parts) >= 3:
        return parts[0], parts[1], " ".join(parts[2:])
    if len(parts) == 2:
        a, gp = parts
        for d in sorted(divisions, key=len, reverse=True):          # a division name seen in a clean row of the same file
            if a.startswith(d + " "):
                return d, a[len(d) + 1:], gp
        toks = a.split(" ")
        for i in range(1, len(toks)):                                 # the longest LGD mandal name at the end
            if norm(" ".join(toks[i:])) in mandals:
                return " ".join(toks[:i]), " ".join(toks[i:]), gp
        if len(toks) > 1:
            return toks[0], " ".join(toks[1:]), gp
        return "", a, gp
    return "", "", pre.strip()


def split_rest(rest):
    """Elected candidate, community, educational qualification (the last two columns are short words)."""
    parts = re.split(r"\s{2,}", rest.strip())
    if len(parts) >= 3:
        return " ".join(parts[:-2]), parts[-2], parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], "", ""


def parse_gp(raw, mandals=frozenset()):
    """pdftotext text of one district file -> rows [{division, mandal, gp, ward, post, reservation, name, community, education,
    page, line, line_text, wrapped}]."""
    divisions = set()
    for pg in pages_of(raw):
        for ln in pg.split("\n"):
            m = GP_ROW.match(ln)
            if m:
                parts = re.split(r"\s{2,}", m.group("pre").strip())
                if len(parts) >= 3:
                    divisions.add(parts[0])
    rows = []
    for pno, pg in enumerate(pages_of(raw), 1):
        lines = pg.split("\n")
        frags = []
        for lno, ln in enumerate(lines, 1):
            if not ln.strip():
                frags = []      # a blank line ends a wrapped cell
                continue
            m = GP_ROW.match(ln)
            if not m:
                if not GP_HEAD.search(ln):
                    frags.append(ln.strip())
                continue
            div, mandal, gp = split_pre(m.group("pre"), divisions, mandals)
            name, comm, edu = split_rest(m.group("rest"))
            if frags:
                name = " ".join(frags + [name])
            rows.append({"division": div, "mandal": mandal, "gp": gp, "ward": m.group("ward"), "post": m.group("post"),
                         "reservation": " ".join(m.group("res").split()), "name": name, "community": comm, "education": edu,
                         "page": pno, "line": lno, "line_text": ln, "wrapped": frags or None})
            frags = []
    return rows


# ---------------------------------------------------------------- MPTC / ZPTC / MPP / ZPP files
def layout_of(lines, ncols):
    """Column positions of one page: ("starts", left edges) as the median of the page's rows that have every column, else
    ("centers", positions of the column-number line "1 2 3 ...")."""
    full = [pieces(ln) for ln in lines if DATA.match(ln) and not NUMS.match(ln)]
    full = [p for p in full if len(p) == ncols]
    if len(full) >= 3:
        return "starts", [statistics.median(p[i][0] for p in full) for i in range(ncols)]
    for ln in lines:
        if NUMS.match(ln):
            nums = [(a + b) / 2 for a, b, t in pieces(ln) if t.isdigit()]
            if len(nums) >= ncols:
                return "centers", nums[:ncols]
    return None


def column(lay, a, b):
    kind, pos = lay
    if kind == "starts":
        return max([i for i, s in enumerate(pos) if s <= a + 3] or [0])
    c = (a + b) / 2
    return min(range(len(pos)), key=lambda i: abs(pos[i] - c))


def parse_table(raw, kind):
    """pdftotext text -> rows {column: [text pieces in line order]} + page, line, line_text of the data line."""
    cols = COLS[kind]
    rows, lay = [], None
    for pno, pg in enumerate(pages_of(raw), 1):
        lines = pg.split("\n")
        lay = layout_of(lines, len(cols)) or lay
        if lay is None:
            continue
        data = [i for i, ln in enumerate(lines) if DATA.match(ln) and not NUMS.match(ln)]
        if not data:
            continue
        # blocks = runs of non-blank lines. A line without a serial number belongs to the nearest data line of its own block
        # (a tie goes to the next row); a block without a data line is a page header or footer.
        owner, dset = {}, set(data)
        for i, ln in enumerate(lines):
            if not ln.strip() or i in dset or NUMS.match(ln):
                provenance.skip_line(ln, 'skip: not ln.strip() or i in dset or NUMS.match(ln)')
                continue
            if all(HEADER_WORDS.search(t) for _, _, t in pieces(ln)):
                provenance.skip_line(ln, 'skip: all(HEADER_WORDS.search(t) for _, _, t in pieces(ln))')
                continue
            mates = [d for d in data if blockmate(lines, d, i)]
            if mates:
                owner[i] = min(mates, key=lambda d: (abs(d - i), 0 if d > i else 1))
        for d in data:
            cells = {c: [] for c in cols}
            at = {c: [] for c in cols}          # line index (on the page) of each piece
            for idx in sorted([d] + [i for i, o in owner.items() if o == d]):
                ps = pieces(lines[idx])
                if idx == d and len(ps) == len(cols):      # a complete row: columns in order
                    for c, (_, _, t) in zip(cols, ps):
                        cells[c].append(t)
                        at[c].append(idx)
                    continue
                for n, (a, b, t) in enumerate(ps):
                    # serial, district and mandal / ZPP are never empty on a data line: the first three pieces, in order
                    k = n if idx == d and n < 3 else max(column(lay, a, b), 3 if idx == d else 0)
                    cells[cols[k]].append(t)
                    at[cols[k]].append(idx)
            rows.append({"cells": cells, "at": at, "page": pno, "line": d + 1, "line_text": lines[d],
                         "wrapped": sorted(i + 1 for i, o in owner.items() if o == d) or None})
    return rows


def blockmate(lines, a, b):
    """True when no blank line and no column-number line stands between lines a and b."""
    lo, hi = sorted((a, b))
    return all(lines[k].strip() and not NUMS.match(lines[k]) for k in range(lo, hi + 1))


RES_NAME = re.compile(r"^((?:UR|BC|SC|ST|OC|S\.C|B\.C|S\.T|U\.R|GENERAL)(?:\s*\(\s*[A-Za-z]+\s*\)|[\s-]*(?:GENERAL|GENRAL|WOMEN|GEN|G|W)\b)?)"
                      r"\s+(\S.*)$", re.I)
VACANT = re.compile(r"(?i)^(expired|resignation|resigned|re-?\s*poll|not\s+held|vacant|disqualified|no\s+nominations?|"
                    r"election\s+not\s+held|countermanded|court\s+case|stayed)$")


def fix_cells(c):
    """c: column -> text. A reservation written in words can run into the name with one space ("BC GENERAL Manyapuri
    Ramarao"): split it. A seat without a member has a remark ("Expired", "Resignation", "Re-Poll", "Not held") instead of
    the name: returned as the remark, the cell is emptied."""
    remark = ""
    for k in ("name", "party", "gender", "community", "vice", "coopted"):
        if k in c and VACANT.match(c[k] or ""):
            remark, c[k] = c[k], ""
    if not c.get("name") and c.get("reservation"):
        m = RES_NAME.match(c["reservation"])
        if m:
            c["reservation"], c["name"] = m.group(1), m.group(2)
    return remark


def j(v):
    return " ".join(v or [])


# ---------------------------------------------------------------- records
def base(p, url, level, **f):
    return {"election": p.get("election") or (ELECTION_GP if p.get("file") == "gp" else ELECTION_PZ), "url": url,
            "src_url": url, **f}


def gp_records(rows, p, lgd):
    url, dist = p["url"], p["district"]
    recs, seen = [], {}
    for r in rows:
        code = lgd.match("gp", r["gp"], district=lgd_zp(dist), block=r["mandal"]) if lgd else ""
        post = {"S": "Sarpanch", "US": "Upa-Sarpanch", "WM": "Ward Member"}[r["post"]]
        ward = r["ward"] if r["ward"].isdigit() and r["ward"] != "0" else ""
        f = dict(lgd_code=code, body=r["gp"], district=dist, block=r["mandal"], division=r["division"], post=post,
                 post_code=r["post"], name=r["name"], ward_no=ward, reservation=r["reservation"], community=r["community"],
                 education=r["education"])
        if r["post"] in ("S", "US"):
            f.update(head=True, head_rank=1 if r["post"] == "S" else 2)
        if r["wrapped"]:
            f["name_wrapped"] = r["wrapped"]
        bkey = code or "~".join(norm(x) for x in (dist, r["mandal"], r["gp"]))
        pkey = "head" if r["post"] == "S" else "vice" if r["post"] == "US" else _pri.post_key(ward_no=r["ward"])
        rid = _pri.rid("AP", "gp", bkey, pkey)
        if rid in seen:          # the same GP name twice in one mandal: keep both, the second with its row number
            rid = f"{rid}-p{r['page']}l{r['line']}"
        seen[rid] = 1
        _, d = _pri.record("AP", "gp", body_key=bkey, pkey=pkey, **base(p, url, "gp", **f),
                           src_pos=provenance.line_pos(r["page"], r["line"], r["line_text"], row=r["ward"]))
        recs.append((rid, d))
    return recs


def pz_records(rows, p, lgd):
    kind, url = p["file"], p["url"]
    recs, seen = [], {}

    def add(level, bkey, pkey, row, **f):
        rid = _pri.rid("AP", level, bkey, pkey)
        if rid in seen:
            rid = f"{rid}-p{row['page']}l{row['line']}"
        seen[rid] = 1
        extra = {"cells_wrapped_lines": row["wrapped"]} if row["wrapped"] else {}
        if row.get("remark") and not f.get("name"):
            extra["seat_status"] = row["remark"]        # no member: the file's remark (Expired, Resignation, Re-Poll ...)
        _, d = _pri.record("AP", level, body_key=bkey, pkey=pkey, **base(p, url, level, **f), **extra,
                           src_pos=provenance.line_pos(row["page"], row["line"], row["line_text"], row=j(row["cells"]["sl"])))
        recs.append((rid, d))

    for r in rows:
        c = {k: j(v) for k, v in r["cells"].items()}
        r["remark"] = fix_cells(c)
        sl = _pri.digits(c["sl"])
        dist = c["district"]
        if kind in ("mptc", "mpp"):
            mandal = c["mandal"]
            code = lgd.match("ps", mandal, district=lgd_zp(dist)) if lgd else ""
            bkey = code or "~".join(norm(x) for x in (dist, mandal))
            common = dict(lgd_code=code, body=f"Mandal Parishad {mandal}".strip(), district=dist, block=mandal, serial=sl)
            if kind == "mptc":
                add("ps", bkey, _pri.post_key(ward_no=c["seat"]), r, **common, post="MPTC Member", ward_no=c["seat"],
                    ward_name=c["seat"], name=c["name"], party=c["party"], reservation=c["reservation"], gender=c["gender"],
                    community=c["community"])
            else:
                add("ps", bkey, "head", r, **common, post="Mandal Parishad President", name=c["name"], party=c["party"],
                    reservation=c["reservation"], head=True, head_rank=1)
                if c["vice"]:
                    add("ps", bkey, "vice", r, **common, post="Vice President", name=c["vice"], party=c["vice_party"],
                        head=True, head_rank=2)
                if c["vice2"]:
                    add("ps", bkey, "vice-2", r, **common, post="Vice President (one more)", name=c["vice2"],
                        party=c["vice2_party"], head=True, head_rank=2)
                if c["coopted"]:
                    add("ps", bkey, "coopted", r, **common, post="Co-opted Member", name=c["coopted"])
        else:
            zp = lgd_zp(dist)
            code = lgd.match("zp", zp) if lgd else ""
            bkey = code or norm(zp)
            common = dict(lgd_code=code, body=f"Zilla Praja Parishad {c.get('zpp') or dist}".strip(), district=dist, serial=sl)
            if kind == "zptc":
                add("zp", bkey, _pri.post_key(ward_no=c["seat"]), r, **common, block=c["mandal"], post="ZPTC Member",
                    ward_no=c["seat"], ward_name=c["seat"], name=c["name"], party=c["party"], reservation=c["reservation"],
                    gender=c["gender"], community=c["community"])
            else:
                # a short co-opted name ("Md. Gouse", "M. Ameen") can stand nearer the party column: back to the co-opted cell
                cl, at = r["cells"], r.setdefault("at", {})
                if len(at.get("vice_party") or []) == len(cl["vice_party"]):
                    keep = [(t, ln) for t, ln in zip(cl["vice_party"], at["vice_party"]) if PARTY.fullmatch(t)]
                    moved = [(t, ln) for t, ln in zip(cl["vice_party"], at["vice_party"]) if not PARTY.fullmatch(t)]
                    if moved:
                        co = sorted(list(zip(cl["coopted"], at.get("coopted") or [])) + moved, key=lambda x: x[1])
                        cl["vice_party"], at["vice_party"] = [t for t, _ in keep], [ln for _, ln in keep]
                        cl["coopted"], at["coopted"] = [t for t, _ in co], [ln for _, ln in co]
                add("zp", bkey, "head", r, **common, post="Zilla Praja Parishad Chairperson", name=c["name"], party=c["party"],
                    reservation=c["reservation"], head=True, head_rank=1, vice_chairpersons_lines=r["cells"]["vice"],
                    vice_parties=r["cells"]["vice_party"], coopted_members_lines=r["cells"]["coopted"])
                # the two vice-chairpersons and the two co-opted members stand in one cell each, over several lines (a long
                # name wraps around the line of its party). One person per party line: each line goes to the nearest party line
                vices = persons(r, "vice", "vice_party")
                for n, (name, party) in enumerate(vices, 1):
                    add("zp", bkey, "vice" if n == 1 else f"vice-{n}", r, **common, post="Zilla Praja Parishad Vice-Chairperson",
                        name=name, party=party, head=True, head_rank=2)
                for n, (name, _) in enumerate(persons(r, "coopted", "vice_party"), 1):
                    add("zp", bkey, f"coopted-{n}", r, **common, post="Co-opted Member", name=name)
    return recs


PARTY = re.compile(r"[A-Z][A-Z()&.\-]{1,11}|(?i:independent|ind)")


def persons(row, col, anchor):
    """[(name, party)] of a cell that holds several persons over several lines (ZPP file): the lines of the anchor column (the
    vice-chairpersons' party, one per person) are the persons; every line of the cell joins the nearest anchor line (a tie goes
    to the earlier one). Without anchors, each line is one person."""
    texts, lines = row["cells"].get(col) or [], (row.get("at") or {}).get(col) or []
    anc = list(zip((row.get("at") or {}).get(anchor) or [], row["cells"].get(anchor) or []))
    if not texts:
        return []
    if not anc or len(lines) != len(texts):
        return [(t, "") for t in texts]
    groups = {i: [] for i in range(len(anc))}
    for t, ln in zip(texts, lines):
        groups[min(range(len(anc)), key=lambda i: (abs(anc[i][0] - ln), anc[i][0]))].append(t)
    return [(" ".join(g), anc[i][1] if col != "coopted" else "") for i, g in groups.items() if g]


def fetch(p, get):
    from cforms.tn import stored
    from cforms.tn_text import pdftotext
    if not pdftotext():
        return [], [], "pdftotext not available"
    content = stored(p, get)
    files, src = [], None
    if content is not None:
        src = provenance.file_src(content, p.get("url"), p.get("stored"))
    else:
        r = get(p["url"])
        if r is None or r.content[:5] != b"%PDF-":
            return [], [], "no answer"
        content = r.content
        if not p.get("stored"):
            files = [(f"pri/AP/{p['file']}-{norm(p.get('district', '')) or 'state'}-2021.pdf", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        raw = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    lgd = _pri.Lgd("AP")
    if p["file"] == "gp":
        zp = lgd_zp(p["district"])
        mandals = {norm(r[2]) for r in lgd.rows if r[1] == "ps" and lgd.by_code.get(r[4], [None, None, ""])[2] == zp}
        recs = gp_records(parse_gp(raw, frozenset(mandals)), p, lgd)
    else:
        recs = pz_records(parse_table(raw, p["file"]), p, lgd)
    if src:
        for _, d in recs:
            d["src"] = dict(src)
    return recs, files, "" if recs else "no rows read"


def items(get=None):
    out = []
    for dist, fn in GP_FILES.items():
        out.append({"key": f"pri-ap-gp2021-{norm(dist)}", "payload": {
            "kind": "form-pri_ap", "state": "AP", "url": BASE + "Ele_Relts21/" + fn, "file": "gp", "level": "gp",
            "district": dist, "lgd_zp": lgd_zp(dist), "election": ELECTION_GP, "route": "direct", "india_only": True}})
    for kind, (fn, level) in STATE_FILES.items():
        out.append({"key": f"pri-ap-{kind}2021", "payload": {
            "kind": "form-pri_ap", "state": "AP", "url": BASE + fn, "file": kind, "level": level, "election": ELECTION_PZ,
            "route": "direct", "india_only": True}})
    return out
