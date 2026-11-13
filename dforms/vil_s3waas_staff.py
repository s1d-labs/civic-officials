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

"list" reader (PDFs whose header is spread over several lines): the header block is the first 8 lines before the first data
line that hold the words mandal / G.P. or village / secretar or name / cadre or designation / cell or mobile or phone; each of
these words gives a column anchor (start of its chunk); a data line's chunks (text runs split at 2+ spaces) go to the
nearest anchor on their left (within 6 characters to the right). A line with a person name or a phone gives one record; the
mandal of a line without one is carried down.

Records: type dept_office, dept rural_development (panchayat secretaries, secretariat staff) or revenue (VRO / VRA), level
gram_panchayat (panchayat secretary) or village (VRO, secretariat staff), post (from the cadre / header / link text),
name, phone, area (gram panchayat / village / secretariat as written), mandal, district, state, cadre, cluster_gps (the other
gram panchayats of the cluster, when the list writes them on lines without a name: the list puts the name on one line
of the cluster, so these are the lines between the previous name line and this one, same mandal; field gps_listed_before), src_url, src_pos (PDF: page + line;
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
HEAD_LINE = re.compile(r"(?i)name\s+of|^\s*(sl|no)\.|mandal\.?\s*$|secretar|g\.\s?ps|cadre|cell\s*no|^\s*page\s+\d|"
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


def list_rows(text):
    """[(cells dict, src_pos)] of a list PDF whose header spreads over several lines (see the module text)."""
    pages = text.split("\f")
    out, cols, mandal = [], None, ""
    for pg, pt in enumerate(pages, 1):
        lines = pt.split("\n")
        for k, ln in enumerate(lines, 1):
            if not ln.strip():
                continue
            if cols is None or (re.search(r"(?i)cadre|cell\s*no|mobile", ln) and not PHONE.search(ln)):
                if re.search(r"(?i)cell|mobile|phone|contact", ln) and not PHONE.search(ln):
                    block = [x for x in lines[max(0, k - 4):k + 5] if not PHONE.search(x)]
                    c = _anchor_cols(block)
                    if {"name", "phone"} <= set(c) and len(c) >= 3:
                        cols = c
                continue
            if HEAD_LINE.search(ln) and not PHONE.search(ln):
                continue                  # the rest of the header block
            ch = _field._chunks(ln)
            if not ch:
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
                cells[role] = (cells.get(role, "") + " " + c).strip()
            if re.fullmatch(r"[\d\s.]*", " ".join(cells.values())):
                continue                      # the "1 2 3 4 5" column number line
            m = re.sub(r"^\d{1,3}\s+", "", cells.get("mandal", "")).strip(" .")
            if m and not re.fullmatch(r"\d+", m):
                mandal = m
            cells["mandal"] = mandal
            cells["area"] = re.sub(r"^\d{1,3}\s+", "", cells.get("area", "")).strip(" .,")
            out.append((cells, provenance.line_pos(pg, k, ln)))
    return out


def list_records(text, p, url, tag, linkpost):
    recs, pending, last_mandal = [], [], None
    host = p.get("host") or urlparse(url).netloc
    rows = list_rows(text)
    for n, (c, pos) in enumerate(rows, 1):
        if c.get("mandal") != last_mandal:
            pending, last_mandal = [], c.get("mandal")
        name = re.sub(r"\s+\d[\d\s]*$", "", c.get("name", "")).strip(" .,")
        phone = _esw.phones(" ".join(PHONE.findall(c.get("phone", "") + " " + c.get("cadre", "") + " " + c.get("name", ""))))
        if not (NAMEY.search(name) or phone):
            if c.get("area"):
                pending.append(c["area"])
            continue
        pdl = post_of(c.get("cadre"), linkpost, p.get("post")) or ("Panchayat Secretary", "rural_development", "gram_panchayat")
        post = pdl[0]
        rid, d = _esw.record(
            MODULE, f"{host}:{tag}:{n}", dept=pdl[1], level=pdl[2], post=post, name=name, phone=phone,
            area=c.get("area"), mandal=c.get("mandal"), tehsil=c.get("mandal"), district=p.get("district_name") or p.get("district"),
            state=p.get("state"), cadre=c.get("cadre"), gps_listed_before=pending or None, caption=linkpost, source=url,
            office_id=f"{host}:{tag}:{n}", layer="field", src_url=url, src_pos=pos,
            method="pdf text (pdftotext -layout), list anchors from the header words", cells=c)
        recs.append((rid, d))
        pending = []
    return recs


def file_records(content, url, p, tag, linktext):
    """Records of one staff list file (PDF bytes or HTML)."""
    pdl = post_of(linktext) or ("Panchayat Secretary", "rural_development", "gram_panchayat")
    q = dict(p, dept=pdl[1], level=pdl[2], post=pdl[0], tag=tag, layer_key="revenue", all_rows=True,
             district=p.get("district_name") or p.get("district"))
    recs = _field.parse(content, url, q, MODULE)
    if not recs and content[:5] == b"%PDF-":
        recs = list_records(_field.pdf_text(content), p, url, tag, linktext)
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
