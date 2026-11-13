"""Goa panchayats: elected ward members (panchas) of the village panchayats and elected members of the two Zilla Panchayats, from
the "winning candidates" PDFs of the Goa State Election Commission (sec.goa.gov.in, elections/previous/...).

Sources (measured 2026-11-13 from dev-vps-3, Mumbai; no captcha, no login). Route "direct": the site answered dev-vps-3 (HTTP 200,
about 25 pages and 7 PDFs fetched by hand) but gave 403 to the GitHub runners (archive, 2026-11-11) and to an India server
(archive, 2026-11-13); the hub's Indian proxies are not checked.
- Village panchayats: "General Election to 186 Village Panchayat 2022" (section "WINNING CANDIDATES TALUKA WISE": one PDF per
  taluka, 12 PDFs, e.g. assets/media/docs/general-election-to-186-village-panchayat-2022/TISWADIWC.pdf), the three Pernem VPs
  (Alorna, Casarvarnem, Chandel-Hassapur 2022), Taleigao 2024, Harvalem 2024, and the bye-elections 2023-2026 ("List of
  Winning Candidates ..."). Table: Sr. No | Panchayat Name | Ward Name & Category | Name of the Elected Candidate | Address |
  Votes Gained | Votes Gained %age. The panchayat cell spans all its wards (its text sits in the middle row).
- Zilla Panchayats: "General Election to Zilla Panchayat 2025": winning-north.pdf, winning-south-1.pdf (one row per
  constituency: Sr No | Constituency | Category | Name | Party | Votes).
The SEC does not publish the sarpanch / deputy sarpanch (elected later by the panchas) or the ZP chairpersons. The Directorate of
Panchayats site (panchayatsgoa.gov.in) sends its VP pages to a login: not used.

How: the PDF's text layer in pypdf layout mode (no OCR). VP: a row starts at a ward mark ("Ward-IV", "WARD IV", "Ward No. I",
or a bare roman number) in the ward column; text blocks between blank lines belong to the ward mark in them; each run of text
(split at 2+ spaces) goes to the header column whose centre is nearest (Sr / Panchayat / Ward / Name / Address); numbers go to
votes / percent by their form. A new panchayat starts when the ward number does not go up or a new Sr. No appears.
ZP: one row per "<nn>-<constituency>" line; lines without one are continuation lines of the nearest row (name in capitals,
party in mixed case).
One queue item = one PDF: payload {"kind": "form-pri_ga", "state": "GA", "url", "level" ("gp" | "zp"), "election", "taluka",
"district", "bye" (bool), "poll_year"}. items(get) lists them from the SEC's pages (seed item {"kind": "seed", "module": "pri_ga"}).
Records pri_member (cforms/_pri.py). Id pri:GA:gp:<lgd>:w<ward> (general election) or ...:w<ward>-bye<year> (bye-election: the
newer record holds the seat; the loader keeps the newest poll_year per body and ward); pri:GA:zp:<lgd>:w<constituency no>.
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from cforms import _pri

METHOD = "pdf text (pypdf layout; rows at ward marks, columns by header position)"
BASE = "https://sec.goa.gov.in/"
LISTS = ("elections/previous/village-panchayat/", "elections/previous/zilla-panchayat/")
WIN = re.compile(r"(?i)winning|elected\s+(member|candidate)|list\s+of\s+elected")
# taluka -> the old district (the two Zilla Panchayats are North Goa and South Goa)
TALUKA_DISTRICT = {"bardez": "North Goa", "bicholim": "North Goa", "pernem": "North Goa", "sattari": "North Goa",
                   "tiswadi": "North Goa", "ponda": "North Goa", "salcete": "South Goa", "mormugao": "South Goa",
                   "quepem": "South Goa", "sanguem": "South Goa", "canacona": "South Goa", "dharbandora": "South Goa"}
# SEC spelling (cforms._pri.norm) -> LGD local_body_name, where the two differ (checked against lgd.pri_local_bodies 2026-11-13)
ALIAS = {"siridaopalem": "Siridao-Pale", "standregoavelha": "St. Andre", "stlawrenceagassaim": "Sao Lourence(Agassaim)",
         "chandelhassapur": "Chandel Hasapur", "casarvarnem": "Kasarvanem", "velingpriolcuncoliem": "Veling-Priol"}
YEAR_HINT = {"three-village-panchayats-of-pernem": "2022"}     # election pages whose title has no year (poll June 2022)
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
WARD_MARK = re.compile(r"(?i)^(?:ward(?:\s*no\.?)?[\s.-]*)?([IVXLC]{1,7}|\d{1,2})$")
CATS = ("OBC Women", "SC Women", "ST Women", "General", "Women", "OBC", "SC", "ST")
CAT_RX = re.compile(r"^(" + "|".join(re.escape(c) for c in CATS) + r")\b\s*", re.I)
UNOPP = re.compile(r"(?i)\s*[-(]*\s*unopposed\s*\)?\s*")


def roman(s):
    """Roman or arabic ward number as a digit string ("" when not a number)."""
    s = (s or "").strip().upper()
    if s.isdigit():
        return str(int(s))
    if not s or any(c not in ROMAN for c in s):
        return ""
    n = 0
    for i, c in enumerate(s):
        v = ROMAN[c]
        n += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
    return str(n)


def runs(line):
    """[(start, end, text)] of the text runs of a layout line (split at 2+ spaces)."""
    return [(m.start(), m.end(), m.group(0).strip()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def layout_pages(content):
    import io
    from pypdf import PdfReader
    return [(pg.extract_text(extraction_mode="layout") or "") for pg in PdfReader(io.BytesIO(content)).pages]


def label(text):
    t = text.lower()
    if re.search(r"%|percent", t):
        return "pct"
    if re.search(r"ward|categ", t):
        return "ward"
    if re.search(r"\bsr\b|sr\.|s\.\s*no|^no$", t):
        return "sr"
    if "panchayat" in t:
        return "panchayat"
    if re.search(r"elected|candidate|member", t):
        return "name"
    if "address" in t:
        return "address"
    if "vote" in t:
        return "votes"
    return ""


def header_columns(lines):
    """{role: centre} from the header lines: runs on different lines whose spans overlap form one column."""
    cols = []    # [start, end, [texts]]
    for ln in lines:
        for s, e, t in runs(ln):
            for c in cols:
                if s < c[1] and e > c[0]:
                    c[0], c[1] = min(c[0], s), max(c[1], e)
                    c[2].append(t)
                    break
            else:
                cols.append([s, e, [t]])
    out = {}
    for s, e, texts in cols:
        txt = " ".join(texts)
        # a column header that holds two headers ("Name of the Elected Candidate Address" on one run): split by words
        if re.search(r"(?i)candidate|member", txt) and re.search(r"(?i)address", txt) and "name" not in out:
            out["name"] = s + (e - s) * 0.3
            out["address"] = s + (e - s) * 0.8
            continue
        role = label(txt)
        if role == "ward" and re.search(r"(?i)elected|candidate", txt):
            role = "name"
        if role and role not in out:
            out[role] = (s + e) / 2
    return out


def nearest(cols, s, e, roles):
    c = (s + e) / 2
    best = min((abs(cols[r] - c), r) for r in roles if r in cols) if any(r in cols for r in roles) else (0, "")
    return best[1]


def join(parts):
    out = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        out = out + p if out.endswith("-") else (out + " " + p if out else p)
    return out


def vp_rows(pages):
    """[{sr, panchayat, ward_mark, ward_no, category, name, address, votes, pct, unopposed, page, line}] from the layout pages."""
    rows, cols = [], {}
    for pno, text in enumerate(pages, 1):
        lines = text.splitlines()
        # header: the lines before the first ward mark that hold header words
        first = None
        for i, ln in enumerate(lines):
            if any(WARD_MARK.match(t) for _, _, t in runs(ln)):
                first = i
                break
        if first is None:
            continue
        head, j = [], first - 1      # the block of non-blank lines just above the first ward mark (not the title)
        while j >= 0 and not lines[j].strip():
            j -= 1
        while j >= 0 and lines[j].strip():
            head.insert(0, lines[j])
            j -= 1
        if not any(re.search(r"(?i)panchayat|ward|elected|address|votes|categ|sr\.", ln) for ln in head):
            head = []
        if head:
            new = header_columns(head)
            if "ward" in new and ("name" in new or "address" in new):
                cols = new
        if "ward" not in cols:
            continue
        wc = cols["ward"]
        block, blocks = [], []
        for i in range(first, len(lines)):
            ln = lines[i]
            if not ln.strip() or re.match(r"(?i)^\s*total\b", ln):
                if block:
                    blocks.append(block)
                block = []
                continue
            block.append((i, ln))
        if block:
            blocks.append(block)
        page_rows = []
        for blk in blocks:
            marks = []
            for i, ln in blk:
                for s, e, t in runs(ln):
                    if WARD_MARK.match(t) and abs((s + e) / 2 - wc) < 12 and nearest(cols, s, e, ("sr", "panchayat", "ward", "name", "address")) == "ward":
                        marks.append((i, s, e, t))
                        break
            if not marks:
                if page_rows:
                    page_rows[-1]["lines"].extend(blk)
                continue
            for k, (i, s, e, t) in enumerate(marks):
                lo = blk[0][0] if k == 0 else i
                hi = marks[k + 1][0] if k + 1 < len(marks) else blk[-1][0] + 1
                page_rows.append({"mark": (i, s, e, t), "lines": [(j, l) for j, l in blk if lo <= j < hi], "page": pno})
        for r in page_rows:
            mi, ms, me, mt = r["mark"]
            got = {"sr": [], "panchayat": [], "ward": [], "name": [], "address": [], "votes": [], "pct": []}
            unopp = False
            for j, ln in r["lines"]:
                for s, e, t in runs(ln):
                    if (j, s) == (mi, ms):
                        continue
                    if UNOPP.fullmatch(t) or t.upper() == "UNOPPOSED":
                        unopp = True
                        continue
                    if re.fullmatch(r"[\d.]+\s*%|%", t):
                        got["pct"].append(t)
                        continue
                    m = re.fullmatch(r"(\d+)\s+([\d.]+\s*%)", t)
                    if m:
                        got["votes"].append(m.group(1))
                        got["pct"].append(m.group(2))
                        continue
                    role = nearest(cols, s, e, ("sr", "panchayat", "ward", "name", "address", "votes", "pct"))
                    if t.isdigit() and role in ("votes", "pct", "address", "name"):
                        got["votes"].append(t)
                        continue
                    if re.fullmatch(r"\d+\.\d+", t):
                        got["pct"].append(t)
                        continue
                    m = re.fullmatch(r"(\d{1,3})\s+(\D.*)", t)
                    if role in ("sr", "panchayat") and m:
                        got["sr"].append(m.group(1))
                        got["panchayat"].append(m.group(2))
                        continue
                    if role in ("votes", "pct"):
                        role = "address"         # text in a number column: a shifted address (page without header)
                    if role == "sr" and not t.isdigit():
                        role = "panchayat"
                    if role == "panchayat" and t.isdigit():
                        role = "sr"
                    if UNOPP.search(t):
                        unopp = True
                        t = UNOPP.sub(" ", t).strip()
                    got[role or "address"].append(t)
            # a page without its own header can shift the columns: text with digits is address, a lone text without is the name
            moved = [t for t in got["name"] if re.search(r"\d", t)]
            got["name"] = [t for t in got["name"] if t not in moved]
            got["address"] = moved + got["address"]
            if not got["name"] and got["address"] and not re.search(r"[\d,]", got["address"][0]):
                got["name"].append(got["address"].pop(0))
            wm = WARD_MARK.match(mt)
            cat = join(got["ward"]).strip("() ")
            pct = join(got["pct"]).replace(" ", "")
            rows.append({"sr": got["sr"][0] if got["sr"] else "", "panchayat": join(got["panchayat"]), "ward_mark": mt,
                         "ward_no": roman(wm.group(1)), "category": cat, "name": join(got["name"]),
                         "address": join(got["address"]), "votes": got["votes"][0] if got["votes"] else "",
                         "pct": pct if pct.endswith("%") or not pct else pct + "%", "unopposed": unopp,
                         "page": r["page"], "line": mi + 1})
    # panchayat groups: the panchayat cell sits in one row of its group
    groups, cur = [], None
    for r in rows:
        w = int(r["ward_no"]) if r["ward_no"].isdigit() else 0
        new = cur is None or (w and cur["last"] and w <= cur["last"]) or (r["sr"] and cur["sr"] and r["sr"] != cur["sr"])
        if new:
            cur = {"rows": [], "sr": "", "names": [], "last": 0}
            groups.append(cur)
        cur["rows"].append(r)
        cur["last"] = w
        if r["sr"]:
            cur["sr"] = r["sr"]
        if r["panchayat"]:
            cur["names"].append(r["panchayat"])
    for g in groups:
        name = join(g["names"])
        for r in g["rows"]:
            r["panchayat"] = name
            r["sr"] = g["sr"]
    return rows


PARTY = re.compile(r"(?i)\b(bharatiya\s+janata(\s+party)?|indian\s+national(\s+congress)?|independent|maharashtrawadi(\s+gomantak)?"
                   r"(\s+party)?|revolutionary\s+goans(\s+party)?|goa\s+forward(\s+party)?|aam\s+aadmi(\s+party)?|"
                   r"nationalist\s+congress(\s+party)?|shiv\s*sena|congress)\s*$")
CONST = re.compile(r"(?:^|\s)(\d{1,2})\s*-\s*[A-Za-z.]")


def pieces(content):
    """[(page, x, y, text)] of a PDF's text pieces (pypdf visitor; y grows upwards)."""
    import io
    from pypdf import PdfReader
    out = []
    for pno, pg in enumerate(PdfReader(io.BytesIO(content)).pages, 1):
        def v(t, cm, tm, fd, fs, pno=pno):
            if t and t.strip():
                out.append((pno, tm[4] * cm[0] + tm[5] * cm[2] + cm[4], tm[4] * cm[1] + tm[5] * cm[3] + cm[5], " ".join(t.split())))
        pg.extract_text(visitor_text=v)
    return out


def zp_rows(content):
    """[{sr, const_no, constituency, category, name, party, votes, page, y}] from a ZP winners PDF (Microsoft Print to PDF: a
    row is often one text piece; cells of two lines add pieces above and below it). Pieces go to the row whose
    "<nn>-<constituency>" piece is nearest in height; name / party split by the known party names, extra pieces by x
    (party column = x of the "Party" header)."""
    ps = pieces(content)
    out = []
    for pno in sorted({p[0] for p in ps}):
        pg = [p for p in ps if p[0] == pno]
        party_x = min((x for _, x, _, t in pg if re.search(r"(?i)^party$|affil", t)), default=None)
        anchors = [(x, y, t) for _, x, y, t in pg if CONST.search(t) and not re.search(r"(?i)constituency", t)]
        if not anchors:
            continue
        top = max(y for _, y, _ in anchors) + 14
        rows = {i: [] for i in range(len(anchors))}
        for _, x, y, t in pg:
            if y > top:
                continue
            i = min(range(len(anchors)), key=lambda k: abs(anchors[k][1] - y))
            if abs(anchors[i][1] - y) < 14:
                rows[i].append((x, y, t))
        for i, (ax, ay, at) in enumerate(anchors):
            items_ = sorted(rows[i], key=lambda p: (-round(p[1]), p[0]))
            sr, cno, const, cat, name, party, votes = "", "", "", "", [], [], ""
            for x, y, t in sorted(items_, key=lambda p: (0, 0, 0) if (p[0], p[1], p[2]) == (ax, ay, at) else (1, -round(p[1]), p[0])):
                if (x, y, t) == (ax, ay, at):
                    m = re.match(r"^\s*(?:(\d{1,3})\s+)?(\d{1,2})\s*-\s*(.*)$", t)
                    if m:
                        sr, cno, rest = m.group(1) or "", m.group(2), m.group(3)
                    else:
                        rest = t
                    mm = re.match(r"^([A-Za-z.\-]+(?:\s(?!(?:" + "|".join(CATS) + r")\b)[A-Za-z.\-]+)*?)(?:\s+|$)(.*)$", rest)
                    const, rest = (mm.group(1), mm.group(2)) if mm else (rest, "")
                    mc = CAT_RX.match(rest)
                    if mc:
                        cat, rest = mc.group(1), rest[mc.end():]
                    mv = re.search(r"\s*(\d+)\s*$", rest)
                    if mv:
                        votes, rest = mv.group(1), rest[:mv.start()]
                    mp = PARTY.search(rest)
                    if mp:
                        party.append(mp.group(0).strip())
                        rest = rest[:mp.start()]
                    if rest.strip():
                        name.append(rest.strip())
                    continue
                if re.fullmatch(r"\d+", t):
                    if not sr and x < ax:
                        sr = t
                    else:
                        votes = votes or t
                    continue
                mv = re.search(r"\s+(\d+)$", t)
                if mv:
                    votes, t = votes or mv.group(1), t[:mv.start()]
                if abs(x - ax) < 25 and const.endswith("-"):
                    const += t
                    continue
                mc = CAT_RX.match(t)
                if mc and not cat:
                    cat, t = mc.group(1), t[mc.end():].strip()
                    if not t:
                        continue
                if party_x is not None and x >= party_x - 15 or (party_x is None and PARTY.search(t)):
                    party.append(t)
                else:
                    mp = PARTY.search(t)
                    if mp and mp.start() > 0:
                        name.append(t[:mp.start()].strip())
                        party.append(mp.group(0).strip())
                    else:
                        name.append(t)
            # name / party pieces of two lines: upper line first
            out.append({"sr": sr, "const_no": str(int(cno)) if cno.isdigit() else "", "constituency": const,
                        "category": cat, "name": " ".join(" ".join(name).split()), "party": " ".join(" ".join(party).split()),
                        "votes": votes, "page": pno, "y": round(ay)})
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    try:
        pages = layout_pages(r.content)
    except Exception as e:
        return [], [], f"pdf: {type(e).__name__}"
    lgd = _pri.Lgd("GA")
    election = p.get("election") or ""
    recs = []
    if p.get("level") == "zp":
        dist = p.get("district") or ""
        body = f"{dist} Zilla Panchayat"
        code = lgd.match("zp", dist)
        for row in zp_rows(r.content):
            if not row["name"]:
                continue
            rid, d = _pri.record("GA", "zp", lgd_code=code, body=body, district=dist, post="Member", name=row["name"],
                                 party=row["party"], ward_no=row["const_no"], constituency=row["constituency"],
                                 category=row["category"], votes=row["votes"], election=election, url=p["url"],
                                 poll_year=p.get("poll_year"), src_url=p["url"],
                                 src_pos={"page": row["page"], "y": row["y"], "row": row["sr"]},
                                 body_key=code or _pri.norm(body))
            recs.append((rid, d))
    else:
        for row in vp_rows(pages):
            if not row["name"] or not row["ward_no"]:
                continue
            vp = row["panchayat"]
            code = lgd.match("gp", vp) or lgd.match("gp", ALIAS.get(_pri.norm(vp), ""))
            chain = lgd.chain(code) if code else []
            dist = next((lgd.by_code[c][2] for c in chain if lgd.by_code[c][1] == "zp"), "") or \
                TALUKA_DISTRICT.get((p.get("taluka") or "").lower(), "")
            extra = f"bye{p.get('poll_year') or ''}" if p.get("bye") else ""
            rid, d = _pri.record("GA", "gp", lgd_code=code, body=vp, district=dist, block=p.get("taluka") or "", post="Panch",
                                 name=row["name"], ward_no=row["ward_no"], ward_label=row["ward_mark"], category=row["category"],
                                 address=row["address"], votes=row["votes"], votes_pct=row["pct"],
                                 unopposed=row["unopposed"] or None, election=election, bye_election=bool(p.get("bye")) or None,
                                 poll_year=p.get("poll_year"), url=p["url"], src_url=p["url"],
                                 src_pos={"page": row["page"], "line": row["line"], "row": row["sr"]},
                                 body_key=code or _pri.norm(vp), pkey=_pri.post_key(ward_no=row["ward_no"], extra=extra))
            recs.append((rid, d))
    return recs, [], "" if recs else "no rows"


def base_of(soup, page_url):
    """The page's <base href> (the SEC pages use base "../../../../", the site root), else the page itself."""
    b = soup.find("base", href=True)
    return urljoin(page_url, b["href"]) if b else page_url


def links(html, page_url):
    """[(pdf url, link text, section heading)] of the winners PDFs on one election page."""
    soup = BeautifulSoup(html or "", "lxml")
    page_url = base_of(soup, page_url)
    out, head = [], ""
    for el in soup.find_all(["h1", "h2", "h3", "label", "a"]):
        if el.name in ("h1", "h2", "h3") or (el.name == "label" and el.get("for")):
            head = " ".join(el.get_text(" ", strip=True).split()) if el.name != "label" else head
            continue
        href = el.get("href") or ""
        txt = " ".join(el.get_text(" ", strip=True).split())
        if not href.lower().endswith(".pdf") or not txt:
            continue
        if WIN.search(txt) or (WIN.search(head) and not re.search(r"(?i)result\s*sheet", txt)):
            if re.search(r"(?i)result\s*sheet|turnout|counting", txt):
                continue
            out.append((urljoin(page_url, href), txt, head))
    return out


def election_pages(html, page_url):
    """[(url, title)] of the election pages listed on a "previous elections" page, newest first (the site's order)."""
    soup = BeautifulSoup(html or "", "lxml")
    page_url = base_of(soup, page_url)
    out = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if re.search(r"elections/previous/(village|zilla)-panchayat/[^/]+/?$", h):
            u = urljoin(page_url, h)
            t = " ".join(a.get_text(" ", strip=True).split())
            if u not in [x[0] for x in out] and t:
                out.append((u, t))
    return out


def item_for(pdf, txt, head, page_url, title):
    level = "zp" if "zilla-panchayat" in page_url else "gp"
    yr = re.search(r"(20\d\d)", title + " " + page_url)
    yr = yr.group(1) if yr else next((y for k, y in YEAR_HINT.items() if k in page_url), "")
    bye = bool(re.search(r"(?i)\bbye\b", title + " " + page_url))
    p = {"kind": "form-pri_ga", "state": "GA", "url": pdf, "level": level, "election": f"Goa SEC: {title}",
         "poll_year": yr, "bye": bye, "page": page_url, "route": "direct"}
    if level == "zp":
        p["district"] = "North Goa" if re.search(r"(?i)north", txt + pdf) else "South Goa" if re.search(r"(?i)south", txt + pdf) else ""
    else:
        tk = next((t for t in TALUKA_DISTRICT if re.search(t, (txt + " " + pdf).lower())), "")
        if tk:
            p["taluka"] = tk.title()
            p["district"] = TALUKA_DISTRICT[tk]
    key = "pri_ga:" + re.sub(r"[^a-z0-9]+", "-", pdf.lower().split("/docs/", 1)[-1]).strip("-")[:150]
    return {"key": key, "payload": p}


def items(get):
    """Winners PDFs of the current rounds: VP pages from the newest down to the last 2022 page (general election 2022 and
    the Pernem VPs; later general polls and bye-elections above it), ZP pages down to the 2025 general election."""
    out = []
    for path, last in ((LISTS[0], r"2022|three-village-panchayats-of-pernem"), (LISTS[1], r"zilla-panchayat-2025")):
        r = get(BASE + path)
        if r is None:
            continue
        pages = election_pages(r.text, BASE + path)
        keep = [i for i, (u, t) in enumerate(pages) if re.search(last, u + " " + t)]
        for url, title in pages[:keep[-1] + 1] if keep else []:
            pg = get(url)
            if pg is None:
                continue
            for pdf, txt, head in links(pg.text, url):
                out.append(item_for(pdf, txt, head, url, title))
    return out
