"""Tamil Nadu: Chennai Metropolitan Water Supply and Sewerage Board (CMWSSB, "Metrowater"), cmwssb.tn.gov.in. Answers only from
India (no connection from Germany; saved in archive.s1d.me 2026-11-07). Two queue items (payload "page"):
- "whoswho": /whos-who (Drupal page, English; /ta/whos-who is the same list in Tamil). Tables Name | Designation | Phone Number |
  Mobile number | Email: (1) head office, about 37 posts (MD, directors, chief engineers, the superintending engineers of the
  five O&M zones "Superintending Engineer (North) Zone-I,II&III", project and finance heads); (2) "Area Engineers", one per
  area office Zone - I .. XV; (3) "Region Engineers" REGION-I, II. The page shows "Last reviewed and updated on DD-MM-YYYY"
  (05-11-2026 in the saved copy). The reader also GETs the Tamil page (payload "url_ta") and takes name_regional from the row
  with the same table and row number when both tables have the same number of rows.
  Levels: chief engineers, directors and head-office posts = state; SE of an O&M zone group = circle; Area Engineer = division
  (the area office, one per GCC zone); Region Engineer = zone. About 54 rows, all with names.
- "depots": /sites/default/files/quick_links/Areaandepotofficeaddress.pdf ("Operation and Maintenance Offices", 29 pages, Word
  2007 file made 2022-03-18, no other date). Per area (AREA I - THIRUVOTTIYUR .. AREA XV - SHOLINGANALLUR): a table
  Designation | Name (Tvl.) | Mobile No. | Office Address with the Area Engineer and the Deputy Area Engineers (I, II, III, Elec.),
  then tables Sl. No. | Depot No. | Name of Assistant Engineer | Mobile No. | [Depot] Office Address | [Land Line], one row per
  depot (200 depots; "(i/c)" under the depot number = the AE holds that depot in charge). Cells wrap over several lines: each row
  has one name line (the anchor); the other columns are cut into items (an address ends at "Chennai ... <PIN>" and its "Ph:"
  lines) and each item goes to the nearest anchor. Names are from 2022 (the who's who page has newer Area Engineers), so the
  Area Engineer rows of the PDF are left out; the depot mobiles 81449300NN belong to the depot post.
  Levels: Deputy Area Engineer = subdivision, depot AE = section. About 70 deputy area engineers and 200 depots.
Record ids: dept:water2_cmwssb:ww:<slug of designation>[:n], dept:water2_cmwssb:area-<roman>:dae:<slug of designation>,
dept:water2_cmwssb:depot-<no>. Extra keys: org "CMWSSB", parents {"zone": "Area I Thiruvottiyur"} for PDF rows, depot_no, in_charge.
"""
import re

import provenance
from dforms import _esw
from dforms._water import unique

METHOD = "html table + pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://cmwssb.tn.gov.in/"
URLS = {"whoswho": BASE + "whos-who", "depots": BASE + "sites/default/files/quick_links/Areaandepotofficeaddress.pdf"}
MOD = "water2_cmwssb"
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13,
         "XIV": 14, "XV": 15}
ENDS = re.compile(r"(?i)chennai\W*\d|^\d{3}\s?\d{3}\.?$|\bph(?:one)?\b\W*\d")
MOBILE = re.compile(r"^(?:\+?91[\s-]?)?[6-9]\d{9}$")
MOBILE_IN = re.compile(r"\b[6-9]\d{9}\b")


def ww_level(post, table):
    p = post.upper()
    if table == "region" or re.match(r"REGION", p):
        return "zone"
    if re.search(r"AREA ENGINEER", p):
        return "division"
    if re.search(r"SUPERINTENDING ENGINEER.*ZONE", p):
        return "circle"
    return "state"


def ww_area(post, level):
    m = re.search(r"Zone\s*-?\s*([IVX]+(?:\s*,\s*[IVX]+)*(?:\s*&\s*[IVX]+)?)", post, re.I)
    if level == "division" and m:
        return f"Area {m.group(1)}"
    if level == "circle" and m:
        side = re.search(r"\(([^)]*)\)", post)
        return f"{side.group(1) + ' ' if side else ''}Zone {m.group(1)}".strip()
    if level == "zone":
        return _esw.clean(post).title()
    return "Head Office, Chennai"


def ww_tables(html, pos=None):
    """pos: a list; when given, it gets for each returned table the src_pos of each of its rows ({"table", "row"})."""
    s = _esw.soup(html)
    out = []
    for tn, tb in enumerate(s.find_all("table"), 1):
        rows = [([_esw.clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])], {"table": tn, "row": k})
                for k, tr in enumerate(tb.find_all("tr"), 1)]
        rows = [(r, at) for r, at in rows if any(r)]
        if rows and len(rows[0][0]) >= 5:
            out.append([r for r, _ in rows])
            if pos is not None:
                pos.append([at for _, at in rows])
    return out


def parse_whoswho(html, url, html_ta=None):
    upd = re.search(r"Last reviewed and updated on\s*(\d{2})-(\d{2})-(\d{4})", _esw.soup(html).get_text(" "))
    last = f"{upd.group(3)}-{upd.group(2)}-{upd.group(1)}" if upd else None
    tpos = []
    tables = ww_tables(html, tpos)
    ta = ww_tables(html_ta) if html_ta else []
    recs, seen = [], set()
    for ti, rows in enumerate(tables):
        rta = ta[ti] if ti < len(ta) and len(ta[ti]) == len(rows) else None
        kind = "region" if any(re.match(r"REGION", r[1] or "", re.I) for r in rows[1:]) else ""
        prev = None
        for ri, r in enumerate(rows[1:], 1):
            name, post, ph, mob, mail = (r + [""] * 5)[:5]
            if not post or post.lower() == "designation":
                continue
            if prev == r:                                          # the saved page repeats its last row
                continue
            prev = r
            name = "" if name.strip(" -") == "" else name.strip(" ,")
            level = ww_level(post, kind)
            key = unique("ww:" + _esw.slug(post), seen)
            extra = {}
            if rta and rta[ri][0].strip(" -") and name:
                extra["name_regional"] = rta[ri][0].strip(" ,")
            if rta and rta[ri][1] and rta[ri][1] != post:
                extra["post_regional"] = rta[ri][1]
            recs.append(_esw.record(MOD, key, dept="water", level=level, area=ww_area(post, level), post=post.strip(" ,"), name=name,
                                    phone=_esw.phones(ph, mob if mob.strip(" -") else ""), email=_esw.emails(mail), state="TN",
                                    district="Chennai", source=url, last_updated=last, org="CMWSSB", **extra,
                                    src_url=url, src_pos=tpos[ti][ri], method="html table"))
    return recs


# ---- the depot PDF -------------------------------------------------------------------------------------------------------------

HEADS = (("sl", r"^Sl\.?$|^Sl\.?\s*No"), ("depot", r"^Depot$|^Depot\s+No"), ("desig", r"^Designation"), ("name", r"^Name"),
         ("mobile", r"^Mobile"), ("landline", r"^Land\s*Line"), ("address", r"Office\s+Address"))


def chunks(line):
    """(start column, text) of each run of text separated by 2+ spaces."""
    return [(m.start(), m.group(0).strip()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def heading_cols(line):
    cols = {}
    for pos, t in chunks(line):
        for key, rx in HEADS:
            if key not in cols and re.search(rx, t, re.I):
                cols[key] = pos
                break
    return cols


def column(pos, text, cols):
    if MOBILE.match(text.replace(" ", "")):
        return "mobile"
    mob = cols.get("mobile")
    if "landline" in cols and pos >= cols["landline"] - 4:
        return "landline"
    if mob is not None and pos > mob + 5:
        return "address"
    best = min((abs(pos - p), k) for k, p in cols.items() if k not in ("address", "landline"))
    return best[1]


def items_of(lines, stop):
    """Cut a column's (line no, text) stream into items: a new item after a blank gap or after a line that ends the item."""
    out, cur, last = [], [], None
    for no, t in lines:
        if cur and (no - last > 1 or stop(cur)):
            out.append(cur)
            cur = []
        cur.append((no, t))
        last = no
    if cur:
        out.append(cur)
    return out


def addr_items(lines):
    """Address items: cut at blank gaps and after the line that ends an address ("Chennai - 600 019", "600 019", "Ph: 2599 1908")."""
    out = []
    for it in items_of(lines, lambda cur: False):                # blank gaps first
        cur = []
        for no, t in it:
            if cur and ENDS.search(cur[-1][1]) and not re.match(r"(?i)\(?ph(?:one)?\b|land|\d{3}\s?\d{3}\.?$", t):
                out.append(cur)
                cur = []
            cur.append((no, t))
        if cur:
            out.append(cur)
    return out


def desig_items(lines):
    out = []
    for no, t in lines:
        if out and not re.match(r"(?i)(area|deputy|executive|assistant|superintending|junior|chief)\b", t) and no - out[-1][-1][0] <= 2:
            out[-1].append((no, t))
        else:
            out.append([(no, t)])
    return out


def nearest(items, anchors):
    """{anchor line: [item, ...]}: each item goes to the anchor nearest to its middle line (a tie goes to the anchor above)."""
    got = {a: [] for a in anchors}
    for it in items:
        mid = (it[0][0] + it[-1][0]) / 2
        a = min(anchors, key=lambda x: (abs(x - mid), -x if x <= mid else x))
        got[a].append(it)
    return got


def shared(items, anchors):
    """Like nearest(), but when there are fewer items than anchors (one merged address cell for the whole area office), each
    anchor takes the item nearest to it, so several anchors can share one item."""
    if len(items) >= len(anchors):
        return nearest(items, anchors)
    got = {}
    for a in anchors:
        it = min(items, key=lambda it: max(it[0][0] - a, a - it[-1][0], 0), default=None)
        got[a] = [it] if it else []
    return got


def joined(its):
    return _esw.clean(" ".join(t for it in its for _, t in it))


def tables_of(pages):
    """Each table = (area, kind "head"/"depot", columns, [(line no, line)]); line numbers run across pages. A heading can wrap
    over three lines ("Sl. Depot Name of ... Land Line" / "No. No. Assistant Mobile No. Depot Office Address No." / "Engineer")."""
    area, out, cur, no, head = None, [], None, 0, 0
    for pg in pages:
        for line in pg.splitlines():
            no += 1
            m = re.match(r"\s*AREA\s+([IVX]+)\s*[–—-]\s*(.+?)\s*$", line)
            if m:
                area = (m.group(1), m.group(2).title())
                cur = None
                continue
            cols = heading_cols(line)
            if len(cols) >= 2 and ("sl" in cols or "desig" in cols):
                cur = (area, "depot" if "depot" in cols else "head", cols, [])
                out.append(cur)
                head = 2
                continue
            if head and cur is not None and re.match(r"\s*(No\.|Engineer|Assistant|Name of)\s", line + " ") and not MOBILE_IN.search(line):
                for k, v in heading_cols(line).items():
                    cur[2].setdefault(k, v)
                head -= 1
                continue
            head = 0
            if cur is not None and line.strip() and not re.match(r"\s*OPERATION AND MAINTENANCE", line):
                cur[3].append((no, line))
    return out


def name_items(lines):
    """Names: consecutive lines join ("B.Mohammed" / "Tajudeen")."""
    out = []
    for no, t in lines:
        if out and no - out[-1][-1][0] == 1:
            out[-1].append((no, t))
        else:
            out.append([(no, t)])
    return out


def parse_depots(content, url):
    return parse_pages(_esw.pdf_pages(content), url)


def parse_pages(pages, url):
    """Records from the text of each PDF page (pypdf layout mode)."""
    recs, seen = [], set()
    # source trail: tables_of numbers the lines across pages; line no -> (page, line in page, text)
    where = dict(enumerate(((pn, ln, x) for pn, pg in enumerate(pages, 1) for ln, x in enumerate(pg.splitlines(), 1)), 1))

    def lp(no):
        w = where.get(no)
        return provenance.line_pos(*w) if w else None
    for area, kind, cols, lines in tables_of(pages):
        if not area:
            continue
        stream = {}
        for no, line in lines:
            for pos, t in chunks(line):
                if kind == "depot" and re.fullmatch(r"(?i)no\.?|engineer|assistant", t):
                    continue
                stream.setdefault(column(pos, t, cols), []).append((no, t))
        names = [(no, t) for no, t in stream.get("name", []) if re.search(r"[A-Za-z]{2}", t)]
        mobiles = stream.get("mobile", [])
        zone = f"Area {area[0]} {area[1]}"
        if kind == "head":
            if not names:
                continue
            anchors = [no for no, _ in names]
            mob = nearest([[x] for x in mobiles], anchors)
            adr = shared(addr_items(stream.get("address", [])), anchors)
            des = nearest(desig_items(stream.get("desig", [])), anchors)
            for no, name in names:
                post = joined(des[no])
                if not post or re.match(r"(?i)area engineer\b", post):
                    continue                                      # the who's who page gives the current Area Engineer
                key = unique(f"area-{ROMAN.get(area[0], area[0])}:dae:{_esw.slug(post)}", seen)
                recs.append(_esw.record(MOD, key, dept="water", level="subdivision", area=f"{zone}, {post}", post=post,
                                        name=re.sub(r"\s*\(?i/c\)?\s*$", "", name), phone=_esw.phones(joined(mob[no])),
                                        address=joined(adr[no]), state="TN", district="Chennai", source=url,
                                        last_updated="2022-03-18", org="CMWSSB", parents={"zone": zone}, src_pos=lp(no),
                                        method="pdf text (pypdf layout)"))
            continue
        # a depot table: every row has the depot mobile 81449300NN (also a vacant depot), so the mobile line is the anchor
        anchors = [no for no, _ in mobiles] or [it[0][0] for it in name_items(names)]
        if not anchors:
            continue
        nam = nearest(name_items(names), anchors)
        adr = nearest(addr_items(stream.get("address", [])), anchors)
        land = nearest([[x] for x in stream.get("landline", [])], anchors)
        dep = nearest([[x] for x in stream.get("depot", [])], anchors)
        mob = {no: t for no, t in mobiles}
        for no in anchors:
            dtext = joined(dep[no])
            num = re.search(r"\b(\d{1,3})\b", dtext)
            if not num:
                tail = re.search(r"81449300?(\d{2,3})$", mob.get(no, ""))  # the depot mobile ends in the depot number
                num = tail
            if not num:
                continue
            n = int(num.group(1))
            name = joined(nam[no])
            ic = bool(re.search(r"i\s*/\s*c", dtext + name, re.I))
            key = unique(f"depot-{n}", seen)
            recs.append(_esw.record(MOD, key, dept="water", level="section", area=f"Depot {n}",
                                    post="Assistant Engineer" + (" (i/c)" if ic else ""),
                                    name=re.sub(r"\s*\(?\s*i\s*/\s*c\s*\)?\s*", " ", name).strip() if name else None,
                                    phone=_esw.phones(mob.get(no, ""), joined(land[no])), address=joined(adr[no]), state="TN",
                                    district="Chennai", source=url, last_updated="2022-03-18", org="CMWSSB",
                                    parents={"zone": zone}, depot_no=n, in_charge=ic or None, src_pos=lp(no),
                                    method="pdf text (pypdf layout)"))
    return recs


def fetch(p, get):
    page = p.get("page", "whoswho")
    url = p.get("url") or URLS[page]
    r = get(url)
    if r is None or r.status_code != 200:
        return [], [], f"no answer from {url}"
    if page == "depots":
        if not r.content.startswith(b"%PDF"):
            return [], [], "not a PDF"
        files = [_esw.keep(MOD, "depots", r.content, "pdf")]
        recs = parse_depots(r.content, url)
    else:
        ta = get(p.get("url_ta") or BASE + "ta/whos-who")
        html_ta = ta.text if ta is not None and ta.status_code == 200 else None
        files = [_esw.keep(MOD, "whos-who", r.content)] + ([_esw.keep(MOD, "whos-who-ta", ta.content)] if html_ta else [])
        recs = parse_whoswho(r.text, url, html_ta)
    return recs, files, "" if recs else "no rows"
