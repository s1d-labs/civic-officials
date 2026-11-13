"""Andhra Pradesh and Telangana: village-level staff lists on the district portals (S3WaaS, <district>.ap.gov.in /
<district>.telangana.gov.in): panchayat secretaries of the gram panchayats (TG: Panchayat Secretary / Junior Panchayat
Secretary; AP: Panchayat Secretary = secretary of the Village Secretariat), village revenue officers (VRO, AP; Telangana
abolished the VRO posts in 2022, old lists may still be on the portals), and village / ward secretariat functionaries
(Grama / Ward Sachivalayam: Welfare & Education Assistant, Digital Assistant, ANM, Engineering Assistant ...).

Measured 2026-11-13 from Mumbai (archive + a few hand fetches): no state-wide open list exists. The GSWS portals
(gramawardsachivalayam.ap.gov.in, gsws-nbm.ap.gov.in) do not resolve; apseva.ap.gov.in reports need a login; the AEBAS
attendance portal of the GSWS department (apgvwvvs.attendance.gov.in/submis/regemp) redirects to a login. The district
portals carry the only lists, as PDF files linked from a department page, e.g. Mahabubnagar /panchayat/: "THE LIST OF
PANCHAYAT SECRETARIES OF GRAM PANCHAYATS WITH PHONE NUMBERS IN <X> DIVISION" (4 PDFs, Excel exports, 2018: mandal, gram
panchayat, secretary name, cadre, cell number; one secretary often serves a cluster of gram panchayats and is written on one
line of the cluster). Most district pages give counts only (Kadapa, Gadwal, Hanumakonda: "No. of Panchayat Secretaries
working").

One queue item = one district portal. Flow: GET the home page; follow up to MAX_PAGES menu links whose text or address names
panchayats / sachivalayam / GSWS / village secretariat / revenue villages / DRDA; on each page read the HTML tables (column
roles from header words, dforms/_field.py) and the PDF / Excel links whose link text names village staff (panchayat
secretaries, VRO, VRA, sachivalayam / secretariat functionaries, welfare assistant, digital assistant). Each file is kept in
the bucket; a PDF with a text layer is read here (header-word columns, dforms/_field.py; else the "list" reader below);
a PDF without text (scan) is noted as a source_file record with needs_ocr (OCR later on the runners).

"list" reader (PDFs whose header is spread over several lines; tried first for PDFs since 2026-11-14): the header block is the
lines around the cell / mobile header word up to the first data line; the header chunks that overlap in x form one column and
the column's joined words give its role (HEAD_ROLES: phone, other G.P.s, cadre, mandal, secretary name, G.P., remarks), else
(older rule) each header word gives a column anchor (start of its chunk); a data line's chunks (text runs split at 2+ spaces) go to the
nearest anchor on their left (within 6 characters to the right). A line with a person name or a phone gives one record; the
mandal of a line without one is carried down.

Records: type dept_office, dept rural_development (panchayat secretaries, secretariat staff) or revenue (VRO / VRA), level
gram_panchayat (panchayat secretary) or village (VRO, secretariat staff), post (from the cadre / header / link text),
name, phone, area (gram panchayat / village / secretariat as written), mandal, district, state, cadre, cluster_gps (the other
gram panchayats of the cluster, when the list writes them on lines without a name: the list puts the name on one line
of the cluster, so these are the lines between the previous name line and this one, same mandal; field gps_listed_before),
gps_additional (the other G.P.s of the secretary when the list has an "Additional G.P.s allotted" / "Incharge Gram Panchayats"
column), lgd_gp_code + lgd_gp_how + lgd_block_code (the G.P. and mandal tied by name to LGD, cforms/pri_lgd: inside the mandal,
else inside the districts of the list's mandals when the spelling key is the same: TG made new mandals in 2016-2019), src_url, src_pos (PDF: page + line;
HTML: table + row). Ids: dept:vil_s3waas_staff:<host>:<file tag>:<row>; files: dept:vil_s3waas_staff:<host>:file:<sha1 12>.
Nothing is masked.
"""
import hashlib
import re
from urllib.parse import urljoin, urlparse

import provenance
from dforms import _esw, _field

METHOD = "district portal pages -> staff list files (pdf text layout: header-word columns or list anchors; html tables)"
MODULE = "vil_s3waas_staff"
MAX_PAGES = 12
MAX_FILES = 30

DISTRICTS = {
    "AP": ["anakapalli", "ananthapuramu", "annamayya", "bapatla", "chittoor", "eastgodavari", "eluru", "guntur", "kadapa",
           "kakinada", "konaseema", "krishna", "kurnool", "nandyal", "ntr", "palnadu", "parvathipurammanyam", "prakasam",
           "spsnellore", "srikakulam", "srisathyasai", "tirupati", "visakhapatnam", "vizianagaram", "westgodavari"],
    "TG": ["adilabad", "asifabad", "bhoopalapally", "gadwal", "hanumakonda", "hyderabad", "jagtial", "jangaon", "kamareddy",
           "karimnagar", "khammam", "kothagudem", "mahabubabad", "mahabubnagar", "mancherial", "medak", "medchal-malkajgiri",
           "mulugu", "nagarkurnool", "nalgonda", "narayanpet", "nirmal", "nizamabad", "peddapalli", "rajannasircilla",
           "rangareddy", "sangareddy", "siddipet", "suryapet", "vikarabad", "wanaparthy", "warangal", "yadadri"],
}
DOMAIN = {"AP": "ap.gov.in", "TG": "telangana.gov.in"}

PAGE_RX = re.compile(r"(?i)panchay|sachivala|gsws|village\W*(secretariat|&|and|panchayat)|secretariat|\bdpo\b|drda|"
                     r"\bpr\W|\bpr$|zilla|revenue\W*villages?|mandals?\W*(and|&)\W*(gram|village)|grampanchayat")
NOT_PAGE = re.compile(r"(?i)tender|notice|recruit|award|event|gallery|press|news|engineer|/te/|feed|\.(pdf|jpe?g|png|xlsx?)$|"
                      r"service-category|/service/|election|sir-?20|budget")
FILE_RX = re.compile(r"(?i)panchayat\W*secretar|grama?\W*panchayat\W*secretar|\bj?ps\b.{0,20}(list|contact|phone|mobile)|"
                     r"secretaries|\bv\.?r\.?o\.?s?\b|\bv\.?r\.?a\.?s?\b|village\W*revenue|sachivalay|secretariat\W*(staff|functionar|"
                     r"employee|contact|list)|functionaries|welfare\W*(and|&)?\W*education\W*assistant|digital\W*assistant|"
                     r"village\W*administrative|\bvao\b")
POSTS = [  # (pattern on cadre / header / link text, post, dept, level)
    (r"(?i)junior\W*panchayat|\bjps\b", "Junior Panchayat Secretary", "rural_development", "gram_panchayat"),
    (r"(?i)panchayat\W*secretar|\bps\b|v\.?d\.?o|e\.?o\.?\W*p\.?r|executive\s+officer", "Panchayat Secretary",
     "rural_development", "gram_panchayat"),
    (r"(?i)\bv\.?r\.?o\b|village\W*revenue\W*officer", "Village Revenue Officer", "revenue", "village"),
    (r"(?i)\bv\.?r\.?a\b|village\W*revenue\W*assistant", "Village Revenue Assistant", "revenue", "village"),
    (r"(?i)welfare\W*(and|&)?\W*education", "Welfare and Education Assistant", "rural_development", "village"),
    (r"(?i)digital\W*assistant", "Digital Assistant", "rural_development", "village"),
    (r"(?i)sachivala|secretariat", "Village Secretariat functionary", "rural_development", "village"),
]
ANCHORS = [("mandal", r"(?i)mandal"), ("area", r"(?i)g\.?\s?p|gram\w*\s*panch|village|secretariat|panchayat\b(?!\s*secret)"),
           ("name", r"(?i)secretar|name\s+of\s+the\s*$|\bname\b(?!\s+of\s+the\s+(mandal|g))"),
           ("cadre", r"(?i)cadre|designation"), ("phone", r"(?i)cell|mobile|phone|contact")]
HEAD_LINE = re.compile(r"(?i)name\s+of|^\s*(sl|no)\.|^\s*no\.?\s+mandal|mandal\.?\s*$|secretar|g\.\s?ps|cadre|cell\s*no|^\s*page\s+\d|"
                       r"statement|phone\s+numbers")
PHONE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
NAMEY = re.compile(r"[A-Za-zఀ-౿]{3,}")


def items(get=None):
    out = []
    for st, names in DISTRICTS.items():
        for d in names:
            host = f"{d}.{DOMAIN[st]}"
            out.append({"key": f"{MODULE}:{d}", "payload": {"reader": MODULE, "url": f"https://{host}/", "host": host,
                                                           "district": d, "state": st, "india_only": False,
                                                           "route": "abroad"}})
    return out


def post_of(*texts):
    for t in texts:
        for rx, post, dept, level in POSTS:
            if t and re.search(rx, t):
                return post, dept, level
    return None


def menu_links(html, base):
    """Same-host links whose text or address names panchayats / sachivalayam / village secretariats, strongest first."""
    host = urlparse(base).netloc
    seen, out = set(), []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html or ""):
        u = urljoin(base, m.group(1).replace("&amp;", "&"))
        t = _esw.clean(re.sub(r"<[^>]+>", " ", m.group(2)))
        if urlparse(u).netloc != host or u in seen or len(u) > 160 or NOT_PAGE.search(u) or len(t) > 90:
            continue
        if PAGE_RX.search(t + " " + urlparse(u).path.replace("-", " ")):
            seen.add(u)
            strong = bool(re.search(r"(?i)panchay|sachivala|gsws|secretariat", t + u))
            out.append((not strong, len(out), u, t))
    return [(u, t) for _, _, u, t in sorted(out)]


def file_links(html, base):
    out, seen = [], set()
    for m in re.finditer(r'(?is)<a[^>]+href="([^"]+\.(?:pdf|xlsx?))"[^>]*>(.*?)</a>', html or ""):
        u = urljoin(base, m.group(1).replace("&amp;", "&"))
        t = _esw.clean(re.sub(r"<[^>]+>", " ", m.group(2)))
        if u not in seen and FILE_RX.search(t + " " + u.rsplit("/", 1)[-1]):
            seen.add(u)
            out.append((u, t))
    return out


def _anchor_cols(head_lines):
    """{role: x} from the header lines (chunks of 2+ space separated text)."""
    cols = {}
    for ln in head_lines:
        for x, c in _field._chunks(ln):
            if len(c) > 25:
                continue                  # a title line, not a column header
            for role, rx in ANCHORS:
                if role not in cols and re.search(rx, c):
                    cols[role] = x
                    break
    return cols


# Column roles of a header cell that the PDF writes over 2-3 lines ("Name of the" / "Mandal"), first match wins (2026-11-14)
HEAD_ROLES = [("phone", r"(?i)cell|mobile|phone|contact"),
              ("gps", r"(?i)incharge|in-charge|addit?i?onal|allotted|other\s+g"),
              ("cadre", r"(?i)cadre|designation|category"),
              ("mandal", r"(?i)mandal"),
              ("name", r"(?i)secretar|(?<![a-z.])p\.\s?s\b|\bname\s+of\s+the\s+ps\b"),
              ("area", r"(?i)g\.?\s?p|gram|head\s*quarter|regular|village"),
              ("remarks", r"(?i)remark"),
              ("sl", r"(?i)^\s*(sl|s\.\s?no|no)\b")]


def _header_cols(block):
    """{role: x} of a header whose cells are written over several lines: the chunks of the header lines that overlap
    (in x) form one column; the column's joined text gives its role (HEAD_ROLES); x = the column's left edge."""
    spans = []
    for ln in block:
        if re.search(r"(?i)statement|division|page\s+\d", ln) or re.fullmatch(r"[\d\s.]*", ln):
            continue                      # title lines, the "1 2 3 4 5" column number line
        for x, c in _field._chunks(ln):
            if len(c) <= 40:
                spans.append([x, x + len(c), c])
    cols = []
    for a, b, c in sorted(spans, key=lambda t: t[0]):
        for col in cols:
            if a < col[1] and col[0] < b:
                col[0], col[1], col[2] = min(a, col[0]), max(b, col[1]), col[2] + " " + c
                break
        else:
            cols.append([a, b, c])
    out = {}
    for a, _, text in sorted(cols):
        for role, rx in HEAD_ROLES:
            if re.search(rx, text):
                out.setdefault(role, a)
                break
    out.pop("sl", None)
    return out


def list_rows(text):
    """[(cells dict, src_pos)] of a list PDF whose header spreads over several lines (see the module text)."""
    pages = text.split("\f")
    out, cols, mandal = [], None, ""
    for pg, pt in enumerate(pages, 1):
        lines = pt.split("\n")
        for k, ln in enumerate(lines, 1):
            if not ln.strip():
                provenance.skipped("empty")
                continue
            if cols is None or (re.search(r"(?i)cadre|cell\s*no|mobile", ln) and not PHONE.search(ln)):
                if re.search(r"(?i)cell|mobile|phone|contact", ln) and not PHONE.search(ln):
                    block = []
                    for j in range(max(0, k - 5), min(len(lines), k + 4)):
                        if PHONE.search(lines[j]):
                            if block and j >= k - 1:
                                break         # the first data line ends the header
                            continue
                        block.append(lines[j])
                    c = _header_cols(block)
                    if not ({"name", "phone", "mandal"} <= set(c)):
                        c = _anchor_cols(block)
                    if {"name", "phone"} <= set(c) and len(c) >= 3:
                        cols = c
                continue
            if HEAD_LINE.search(ln) and not PHONE.search(ln):
                provenance.skip_line(ln, 'skip: HEAD_LINE.search(ln) and not PHONE.search(ln)')
                continue                  # the rest of the header block
            ch = _field._chunks(ln)
            if not ch:
                provenance.skip_line(ln, 'skip: not ch')
                continue
            order = sorted(cols.items(), key=lambda kv: kv[1])
            cells = {}
            for x, c in ch:
                role = None
                for r, ax in order:
                    if x + 6 >= ax:
                        role = r
                if role is None:
                    role = order[0][0]
                i = [r for r, _ in order].index(role)
                if role in cells and i + 1 < len(order) and order[i + 1][0] not in cells and \
                        abs(order[i + 1][1] - x) < abs(x - cols[role]):
                    role = order[i + 1][0]    # the page is shifted left: "8 Adula      M.Hanmanthu" (G.P., then the name)
                cells[role] = (cells.get(role, "") + " " + c).strip()
            if re.fullmatch(r"[\d\s.]*", " ".join(cells.values())):
                provenance.skip_line(ln, 'skip: re.fullmatch(r"[\\d\\s.]*", " ".join(cells.values()))')
                continue                      # the "1 2 3 4 5" column number line
            m = re.sub(r"^\d{1,3}\s+", "", cells.get("mandal", "")).strip(" .")
            g = re.match(r"(.+?)\.?\s+\d{1,3}\s+(\S.*)$", m)
            if g and "area" in cols and not cells.get("area"):
                m, cells["area"] = g.group(1), g.group(2)       # "Peddakothapally. 1 Sathapur": mandal and serial + G.P.
            g = re.match(r"(.+?)\s+((?:Sri|Smt|Kum|Dr)\b\.?\s*\S.*)$", m)
            if g and not cells.get("name"):
                m, cells["name"] = g.group(1), g.group(2)       # "NARWA Smt.Kavitha": the name ran into the mandal cell
            if m and not re.fullmatch(r"\d+", m):
                mandal = m
            cells["mandal"] = mandal
            cells["area"] = re.sub(r"^\d{1,3}\s+", "", cells.get("area", "")).strip(" .,")
            out.append((cells, provenance.line_pos(pg, k, ln)))
    return out


CADRE_TAIL = re.compile(r"(?i)\s+(contract\b.*|v\.?\s?d\.?\s?o\.?.*|e\.?\s?o\.?\s?gr.*|p\.?\s?s\.?\s?gr.*|"
                        r"medical\s+invali.*|irrigation.*|jr\.?\s*asst.*|other\s+dept.*|grade\s*-?\s*i.*|regular.*)$")
_LGD = {}


def _lgd(state):
    """LGD PRI bodies of the state (cforms/pri_lgd, DB civic lgd.pri_local_bodies): (Lgd, {mandal key: [ps rows]})."""
    if state not in _LGD:
        from cforms import _pri
        lg = _pri.Lgd(state) if state else None
        ps = {}
        for r in (lg.rows if lg else []):
            if r[1] == "ps":
                ps.setdefault(_pri.norm(r[2]), []).append(r)
        _LGD[state] = (lg, ps)
    return _LGD[state]


def skel(name):
    """Spelling key of a Telugu place name in Latin letters: oo/u, ee/i, th/t, w/v, -palle/-pally, -peta/-pet, double letters
    as one ("Alampoor" = "Alampur", "Achampet" = "Achampeta", "Gouthapoor" = "Gothapur" stays apart)."""
    from cforms import _pri
    k = _pri.norm(name)
    for a, b in (("oo", "u"), ("ee", "i"), ("th", "t"), ("dh", "d"), ("kh", "k"), ("bh", "b"), ("w", "v"), ("ou", "o"),
                 ("palle", "pally"), ("palli", "pally"), ("z", "j")):
        k = k.replace(a, b)
    k = re.sub(r"(.)\1+", r"\1", k)
    k = re.sub(r"peta$", "pet", k)
    return re.sub(r"[aiy]$", "", k)


def _close(key, keys, cut):
    """The one key nearest to key: the key itself, else one key with the same spelling key (skel), else (cut < 1) the one best
    difflib match with ratio >= cut and the same first letter; else None."""
    import difflib
    if key in keys:
        return key
    sk = [k for k in keys if skel(k) == skel(key)]
    if len(sk) == 1:
        return sk[0]
    if cut >= 1 or sk:
        return None
    best = [k for k in difflib.get_close_matches(key, list(keys), 3, cut) if k[:1] == key[:1]]
    if len(best) == 1 or (len(best) >= 2 and difflib.SequenceMatcher(None, key, best[0]).ratio() >
                          difflib.SequenceMatcher(None, key, best[1]).ratio()):
        return best[0]
    return None


def mandal_codes(state, mandals):
    """{mandal as written: LGD block (mandal panchayat) code}. Spelling may differ ("Achampet" / "Achampeta", ratio >= 0.8). A
    name that two districts use (Atmakur) goes to the district that holds most of the list's other mandals."""
    from cforms import _pri
    lg, ps = _lgd(state)
    if not lg:
        return {}
    cand = {}
    for m in mandals:
        k = _close(_pri.norm(m), ps, 0.8) if _pri.norm(m) else None
        if k:
            cand[m] = ps[k]
    zp = {}
    for rows in cand.values():
        if len(rows) == 1:
            z = rows[0][4]
            zp[z] = zp.get(z, 0) + 1
    out = {}
    for m, rows in cand.items():
        if len(rows) > 1:
            rows = sorted(rows, key=lambda r: -zp.get(r[4], 0))
            if zp.get(rows[0][4], 0) == zp.get(rows[1][4], 0):
                continue
        out[m] = rows[0][0]
    return out


def gp_of(state, ps_codes, text, cut=0.85):
    """(LGD gram panchayat code, the G.P. name as written, the rest of the text) when the text starts with the name of one
    gram panchayat under these LGD mandal codes (_close: same spelling key, or ratio >= cut), else ("", "", text). The
    shortest start that matches wins ("Remaddula P.Bal Raj" -> Remuddula, Pangal; rest "P.Bal Raj")."""
    from cforms import _pri
    lg, _ = _lgd(state)
    if not lg or not ps_codes or not text:
        return "", "", text
    gps = {}
    for r in lg.rows:
        if r[4] in ps_codes and r[1] == "gp":
            gps.setdefault(_pri.norm(r[2]), set()).add(r[0])
    words = text.split()
    for n in range(1, len(words) + 1):
        head = " ".join(words[:n])
        rest = " ".join(words[n:])
        if re.match(r"(?i)t[h]?anda\b|\(|colony\b", rest):
            continue                      # "Peddagudem Tanda" is its own G.P.
        k = _close(_pri.norm(head), gps, cut) if len(_pri.norm(head)) >= 3 else None
        if k and len(gps[k]) == 1:
            return next(iter(gps[k])), head.strip(" .,"), " ".join(words[n:]).strip(" .,")
    return "", "", text


def list_records(text, p, url, tag, linkpost):
    """Records of a list PDF (list_rows). Lines with only other G.P.s of the secretary (a column "Additional G.P.s allotted" /
    "Incharge Gram Panchayats", written on the lines above and below the secretary's line, or on own lines with the same phone)
    go to the nearest secretary line of the page (gps_additional). The G.P. of each record is tied to LGD by name inside the
    LGD mandal (lgd_gp_code, lgd_block_code); a G.P. cell that also holds the secretary's name ("Remaddula P.Bal Raj") is split
    there."""
    recs, pending, last_mandal = [], [], None
    host = p.get("host") or urlparse(url).netloc
    st = p.get("state") or ""
    rows = list_rows(text)
    mcode = mandal_codes(st, {c.get("mandal") for c, _ in rows if c.get("mandal")})
    lg = _lgd(st)[0]
    zps = {lg.by_code[c][4] for c in mcode.values()} if lg else set()
    region = {r[0] for r in (lg.rows if lg else []) if r[1] == "ps" and r[4] in zps}   # mandals of the list's districts
    extras = []
    for n, (c, pos) in enumerate(rows, 1):
        if c.get("mandal") != last_mandal:
            pending, last_mandal = [], c.get("mandal")
        name = re.sub(r"\s+\d[\d\s]*$", "", c.get("name", "")).strip(" .,")
        phone = _esw.phones(" ".join(PHONE.findall(c.get("phone", "") + " " + c.get("cadre", "") + " " + c.get("name", ""))))
        area, cadre = c.get("area"), c.get("cadre")
        if not cadre and c.get("phone"):
            cadre = re.sub(r"\s+\d{1,3}$", "", re.sub(r"[\d\s,/-]{6,}", " ", c["phone"])).strip(" ,-") or None  # "9885048178 Grade - I"
        if c.get("gps") and not NAMEY.search(name) and not area:
            extras.append((pos, phone, c["gps"]))
            continue
        ps_code = mcode.get(c.get("mandal"), "")
        gp, gp_name, rest = gp_of(st, {ps_code}, area)
        how = "G.P. name in the LGD mandal" if gp else None
        if not gp and region:              # mandals made after the list (2016-2019): the G.P. moved to a new mandal
            gp, gp_name, rest = gp_of(st, region, area, cut=1)      # same spelling key only
            how = "G.P. name in the LGD districts of the list (one match)" if gp else None
        if gp and rest and not NAMEY.search(name) and NAMEY.search(rest):
            g = CADRE_TAIL.search(rest)
            if g:
                cadre = cadre or g.group(1).strip()
                rest = rest[:g.start()].strip(" .,")
            area, name = gp_name, rest            # "Remaddula P.Bal Raj": G.P. and secretary in one cell
        if not (NAMEY.search(name) or phone):
            if area:
                pending.append(area)
            continue
        pdl = post_of(cadre, linkpost, p.get("post")) or ("Panchayat Secretary", "rural_development", "gram_panchayat")
        post = pdl[0]
        rid, d = _esw.record(
            MODULE, f"{host}:{tag}:{n}", dept=pdl[1], level=pdl[2], post=post, name=name, phone=phone,
            area=area, mandal=c.get("mandal"), tehsil=c.get("mandal"), district=p.get("district_name") or p.get("district"),
            state=p.get("state"), cadre=cadre, gps_listed_before=pending or None, caption=linkpost, source=url,
            office_id=f"{host}:{tag}:{n}", layer="field", src_url=url, src_pos=pos, lgd_gp_code=gp or None,
            lgd_gp_how=how, lgd_block_code=ps_code or None,
            method="pdf text (pdftotext -layout), list anchors from the header words", cells=c)
        recs.append((rid, d))
        pending = []
    for pos, phone, gps in extras:          # other G.P.s of a secretary: to the nearest secretary line of the page
        same = [d for _, d in recs if d["src_pos"]["page"] == pos["page"]]
        prev = [d for d in same if phone and d.get("phone") == phone and d["src_pos"]["line"] < pos["line"]]
        if prev:
            d = prev[-1]
        elif same:
            def rank(d):              # nearest line; on a tie the line before when its G.P. cell ends with ",", else the next
                before = d["src_pos"]["line"] < pos["line"]
                cont = before and d["cells"].get("gps", "").rstrip().endswith(",")
                return abs(d["src_pos"]["line"] - pos["line"]), not cont, before
            d = min(same, key=rank)
        else:
            continue
        d.setdefault("_extra", []).append((pos["line"], gps))
    for _, d in recs:
        parts = sorted(d.pop("_extra", []) + ([(d["src_pos"]["line"], d["cells"]["gps"])] if d["cells"].get("gps") else []))
        gps = [g for g in (x.strip(" .") for x in re.split(r",", ", ".join(t for _, t in parts))) if g and g != "--"]
        if gps:
            d["gps_additional"] = gps
    return recs


def file_records(content, url, p, tag, linktext):
    """Records of one staff list file (PDF bytes or HTML)."""
    pdl = post_of(linktext) or ("Panchayat Secretary", "rural_development", "gram_panchayat")
    q = dict(p, dept=pdl[1], level=pdl[2], post=pdl[0], tag=tag, layer_key="revenue", all_rows=True,
             district=p.get("district_name") or p.get("district"))
    recs = []
    if content[:5] == b"%PDF-":          # list reader first: the header-word reader takes these 3-line headers wrongly
        recs = list_records(_field.pdf_text(content), p, url, tag, linktext)
    if not recs:
        recs = _field.parse(content, url, q, MODULE)
    for _, d in recs:
        pp = post_of(d.get("post") or "", (d.get("table_row") or {}) and " ".join(d["table_row"]), linktext)
        if pp and d.get("post") in (None, "", "Panchayat Secretary"):
            d["post"], d["dept"], d["level"] = pp
        d.setdefault("src_url", url)
        d["list_title"] = linktext or None
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer from the district portal"
    host = urlparse(p["url"]).netloc
    files, recs, notes, done = [], [], [], set()
    pages = [(p["url"], "home", r)]
    for u, t in menu_links(r.text, p["url"])[:MAX_PAGES]:
        a = get(u)
        if a is not None and a.content[:5] != b"%PDF-":
            pages.append((u, t, a))
    nfile = 0
    for u, t, a in pages:
        html = a.text
        if u != p["url"]:
            for rid, d in _field.records(MODULE, _field.html_rows(html), dict(p, tag=_esw.slug(urlparse(u).path)[-50:] or "page",
                                                                               layer_key="revenue", all_rows=False,
                                                                               dept="rural_development"), u):
                pp = post_of(d.get("post") or "", d.get("caption") or "", " ".join(d.get("table_row") or {}))
                if pp and re.search(r"(?i)secretar|v\.?r\.?o|v\.?r\.?a|sachivala|assistant", " ".join(
                        [d.get("post") or "", d.get("caption") or ""] + list(d.get("table_row") or {}))):
                    d["post"], d["dept"], d["level"] = (d.get("post") or pp[0]), pp[1], pp[2]
                    recs.append((rid, d))
        for fu, ft in file_links(html, u):
            if fu in done or nfile >= MAX_FILES:
                continue
            done.add(fu)
            f = get(fu)
            if f is None:
                notes.append(f"no answer: {fu}")
                continue
            nfile += 1
            sha = hashlib.sha1(fu.encode()).hexdigest()[:12]
            tag = f"f{sha}"
            ext = "pdf" if f.content[:5] == b"%PDF-" else fu.rsplit(".", 1)[-1].lower()
            files.append(_esw.keep(MODULE, f"{host}-{tag}", f.content, ext))
            got = file_records(f.content, fu, p, tag, ft) if ext in ("pdf", "html") else []
            scan = ext == "pdf" and not _field.pdf_text(f.content).strip()
            recs += got
            recs.append(_esw.record(MODULE, f"{host}:file:{sha}", **{"type": "source_file"}, url=fu, title=ft, page=u,
                                    state=p.get("state"), district=p.get("district"), rows=len(got),
                                    needs_ocr=True if scan else None, kind=ext, source=u,
                                    **provenance.at(f, fu)))
    seen, out = set(), []
    for rid, d in recs:
        while rid in seen:
            rid += "-b"
        seen.add(rid)
        out.append((rid, d))
    staff = [x for x in out if x[1].get("type") == "dept_office"]
    why = "" if staff else ("no staff list on the portal pages" + (f" ({len(files)} files: scans or other tables)" if files else ""))
    return out, files, why
