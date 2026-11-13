"""Maharashtra: the Talathi (since 2025 "Gram Mahsul Adhikari", ग्राम महसूल अधिकारी = village revenue officer) of every saja
(तलाठी सजा: one or more revenue villages) and the Circle Officer (मंडळ अधिकारी) of every revenue circle, with mobile numbers
and @mah.gov.in mail ids, from the open lists of the district collectorate portals (S3WaaS, <district>.gov.in /
<district>.maharashtra.gov.in).

Two source shapes (measured 2026-11-13 from Mumbai):
- PDF per tahsil (Ahilyanagar, page /en/circle-officer-and-talathi/, 14 tahsils, June-July 2023, one template, text layer,
  English): Sr.No | Circle Name | Circle Officer | Circle Officer Mobile No | Circle Officer Email-ID | Saja | Village (serial
  + name) | Talathi | Talathi Mobile No | Talathi Email-ID. A circle spans many lines; a saja starts at the line that carries
  the Talathi's mobile; every village has its own serial number; names, sajas, villages and mail ids wrap onto the next lines.
  The reader learns the columns on each page from its own lines (the page offsets differ between pages): the village serial
  column, the Talathi's mobile column and the mail column. Left of the village serial: circle, circle officer name / mobile /
  mail, saja; right of it: village, Talathi name, mobile, mail. Wrapped pieces join the open saja / village / circle.
  A saja whose Talathi post is vacant has no mobile in the list: its villages join the saja above (the list gives no line
  to tell them apart).
- HTML table (Jalna, Partur taluka page, Marathi): अ.क्र. | मंडळ विभाग (circle) | मंडळ अधिकारी यांचे नांव (circle officer,
  "मो." + mobile in the same cell) | ग्राम महसूल अधिकारी यांचे नांव | मोबाईल क्रमांक | मुळ/अति (regular / additional
  charge) | तलाठी सजा | सजातर्गत असलेली गावे (villages of the saja). Columns come from the header words (Marathi or English).

Records: one per saja: dept revenue, level village, post "Talathi (Gram Mahsul Adhikari)", post_regional "ग्राम महसूल अधिकारी
(तलाठी)", name, phone, email, area = the saja as written, villages (list, as written; with the list's serial numbers in
village_serials), circle, circle_officer (name), charge (मुळ / अतिरिक्त), tehsil, district, state MH. One per circle: level
circle, post "Circle Officer (Mandal Adhikari)", area = the circle. Nothing is masked.
src_pos: PDF line_pos(page, line, line text) of the line where the saja (or circle) starts; HTML {table, row}.
Ids: dept:vil_mh_talathi:<host>:<tag>:s<n> (saja n of the file) / :c<n> (circle n).
"""
import re
from urllib.parse import urlparse

import provenance
from dforms import _esw, _field

METHOD = "pdf layout text (pypdf; columns learned per page from the village serial and mobile columns) or html table (header words)"

MODULE = "vil_mh_talathi"
POST = "Talathi (Gram Mahsul Adhikari)"
POST_MR = "ग्राम महसूल अधिकारी (तलाठी)"
CO_POST = "Circle Officer (Mandal Adhikari)"
CO_POST_MR = "मंडळ अधिकारी"
MOB = re.compile(r"^(?:\+?91)?[6-9]\d{9}$")
SERIAL = re.compile(r"^\d{1,3}\.?$")
HEADER = re.compile(r"(?i)\b(circle name|talathi|viilage|village|saja|email-?id|mobile no|sr\.?\s*no)\b")
MAILISH = re.compile(r"(?i)@|^co-|^tal\.|^v\.in$|^\.?gov\.in$|^mah\.?go|^[a-z]+-$|^[a-z]+-[a-z]+@|^\.in$|^n$")
WORD = re.compile(r"\S+")
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _words(line):
    return [(m.start(), m.group()) for m in WORD.finditer(line)]


def _chunks(line):
    return [(m.start(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def _join_mail(parts):
    """Mail id pieces of one cell joined; anything after the first complete "...gov.in" / "nic.in" is the next row's."""
    t = "".join(parts).replace(" ", "").strip(".").lower() if parts else ""
    m = re.match(r"^.*?@[a-z0-9.-]*?(?:gov|nic)\.in", t)
    return m.group(0) if m else t


def _jw(words):
    """Words of one cell joined; a short lower-case piece is the wrapped end of the word before ("Samasherap" + "ur")."""
    out = []
    for t in words:
        if out and re.fullmatch(r"[a-z]{1,3}\.?", t) and re.search(r"[A-Za-z]$", out[-1]):
            out[-1] += t
        else:
            out.append(t)
    return " ".join(out)


def page_cols(lines):
    """Column anchors of one page from its saja lines (a village serial left of a mobile): v = x of the village serial,
    m = x of the Talathi's mobile, e = x of the Talathi's mail, b = border between village and Talathi name."""
    vs, ms, es, vend, nst = [], [], [], [], []
    for ln in lines:
        w = _words(ln)
        mobs = [(x, t) for x, t in w if MOB.match(t)]
        sers = [(x, t) for x, t in w if SERIAL.match(t) and x > 12]
        if not mobs or not sers:
            continue
        sx = sers[0][0]
        right = [(x, t) for x, t in mobs if x > sx]
        if not right:
            provenance.skip_line(ln, 'skip: not right')
            continue
        mx = right[-1][0]
        vs.append(sx)
        ms.append(mx)
        tail = [x for x, t in w if x > mx and t.lower().startswith("tal")]
        if tail:
            es.append(tail[0])
        mid = [c for c in _chunks(ln[:mx]) if c[0] > sx + len(sers[0][1])]
        if len(mid) >= 2:
            vend.append(mid[0][0] + len(mid[0][1]))
            nst.append(mid[-1][0])
    if not vs:
        return None
    med = lambda a: sorted(a)[len(a) // 2]
    v, m = med(vs), med(ms)
    e = med(es) if es else m + 12
    b = (med(vend) + med(nst)) / 2 if vend and nst else v + (m - v) / 2
    return {"v": v, "m": m, "e": e, "b": b}


def circle_cols(lines, v):
    """x of the circle officer's mobile and of the start of his mail column, from the lines that open a circle."""
    cm, ce, cn = [], [], []
    for ln in lines:
        w = _words(ln)
        if not w or not (w[0][0] < 8 and SERIAL.match(w[0][1])):
            continue
        mobs = [x for x, t in w if MOB.match(t) and x < v]
        if not mobs:
            provenance.skip_line(ln, 'skip: not mobs')
            continue
        if mobs:
            cm.append(mobs[0])
            mails = [x for x, t in w if x > mobs[0] and x < v and MAILISH.search(t)]
            if mails:
                ce.append(mails[0])
        ch = [c for c in _chunks(ln) if c[0] < (mobs[0] if mobs else v)]
        if len(ch) >= 3:
            cn.append((ch[1][0] + len(ch[1][1]) + ch[2][0]) / 2)
    med = lambda a: sorted(a)[len(a) // 2] if a else None
    return med(cm), med(ce), med(cn)


def parse_pdf_text(text, p, url):
    """Records from the layout text of one tahsil PDF (Ahilyanagar template)."""
    host = urlparse(url).netloc
    tag = p.get("tag") or "pdf"
    tehsil = p.get("tehsil")
    m = re.search(r"(?i)Tah?a?sil\s+Office\s+([A-Za-z .-]+)", text)
    if m and not tehsil:
        tehsil = _esw.clean(m.group(1))
    circles, sajas, ccols = [], [], (None, None, None)
    for pg, pt in enumerate(text.split("\f"), 1):
        lines = pt.split("\n")
        cols = page_cols(lines)
        if not cols:
            provenance.skipped('skip: not cols')
            continue
        got = circle_cols(lines, cols["v"])
        if got[0] is not None:
            shift = 0
        else:       # no circle starts on this page: the last page's circle columns, moved by the shift of the village column
            shift = cols["v"] - (ccols[3] if len(ccols) > 3 else cols["v"])
            got = tuple(None if x is None else x + shift for x in ccols[:3])
        cmx, cex, cnb = got
        ccols = (cmx, cex, cnb, cols["v"])
        cur_v, cont = None, False
        for ln_no, ln in enumerate(lines, 1):
            if not ln.strip() or HEADER.search(ln) and not any(MOB.match(t) for _, t in _words(ln)):
                provenance.skip_line(ln, 'skip: not ln.strip() or HEADER.search(ln) and not any(MOB.match(t) for _,...')
                continue
            if re.search(r"(?i)tah?a?sil\s+office", ln):
                provenance.skip_line(ln, 'skip: re.search(r"(?i)tah?a?sil\\s+office", ln)')
                continue
            w = _words(ln)
            # a new circle
            if w[0][0] < 8 and SERIAL.match(w[0][1]) and circles and circles[-1]["sno"] == w[0][1].strip("."):
                w = w[1:]           # the circle's row goes on over a page break: the list repeats its cells
                cont = True
            elif w[0][0] < 8 and SERIAL.match(w[0][1]):
                cont = False
                circles.append({"sno": w[0][1].strip("."), "circle": [], "name": [], "phone": "", "mail": [],
                                "pos": provenance.line_pos(pg, ln_no, ln)})
                w = w[1:]
            sers = [(x, t) for x, t in w if SERIAL.match(t) and abs(x - cols["v"]) <= 4]
            tmob = [(x, t) for x, t in w if MOB.match(t) and x > cols["v"]]
            if tmob:
                sajas.append({"saja": [], "villages": [], "serials": [], "name": [], "phone": tmob[-1][1], "mail": [],
                              "circle": len(circles), "pos": provenance.line_pos(pg, ln_no, ln)})
                cur_v = None
            sx = sers[0][0] if sers else None
            for x, t in w:
                c = circles[-1] if circles else None
                s = sajas[-1] if sajas else None
                if MOB.match(t):
                    if x < cols["v"] and c is not None and not c["phone"]:
                        c["phone"] = t
                    continue
                if x >= cols["e"] - 3 or (x > cols["m"] and MAILISH.search(t)):
                    if s is not None:
                        s["mail"].append(t)
                    continue
                if sx is not None and x == sx:
                    if s is not None:
                        s["serials"].append(t.strip("."))
                        s["villages"].append([])
                        cur_v = s["villages"][-1]
                    continue
                if x > cols["v"] + 1:
                    if x < cols["b"]:
                        if cur_v is not None:
                            cur_v.append(t)
                    elif x < cols["m"] and s is not None:
                        s["name"].append(t)
                    continue
                # left of the village serial: circle columns or the saja
                if c is None:
                    continue
                if cont:            # repeated cells of a circle continued from the last page: only the saja is new
                    if cex is not None and x >= cex - 2 and not MAILISH.search(t) and s is not None and \
                            not (x < cex + 14 and re.fullmatch(r"[a-z.@-]+", t)):
                        s["saja"].append(t)
                    continue
                if cex is not None and x >= cex - 2:
                    if MAILISH.search(t) or (x < cex + 14 and re.fullmatch(r"[a-z.@-]+", t)):
                        c["mail"].append(t)
                    elif s is not None:
                        s["saja"].append(t)
                elif cmx is not None and x >= cmx - 2:
                    if MAILISH.search(t):
                        c["mail"].append(t)
                    elif s is not None and (cex is None):
                        s["saja"].append(t)
                elif cnb is not None and x < cnb:
                    c["circle"].append(t)
                else:
                    c["name"].append(t)
    recs = []
    base = dict(state="MH", district=p.get("district"), tehsil=tehsil, source=url, src_url=url)
    for n, c in enumerate(circles, 1):
        recs.append(_esw.record(
            MODULE, f"{host}:{tag}:c{n}", dept="revenue", level="circle", post=CO_POST, post_regional=CO_POST_MR,
            name=_jw(c["name"]), phone=c["phone"], email=_esw.emails(_join_mail(c["mail"])) or None,
            area=_jw(c["circle"]), circle=_jw(c["circle"]), office_id=f"{host}:{tag}:c{n}", vacant=None if c["name"] else True,
            src_pos=c["pos"], **base))
    for n, s in enumerate(sajas, 1):
        c = circles[s["circle"] - 1] if s["circle"] else None
        villages = [_jw(v) for v in s["villages"] if v]
        recs.append(_esw.record(
            MODULE, f"{host}:{tag}:s{n}", dept="revenue", level="village", post=POST, post_regional=POST_MR,
            name=_jw(s["name"]), phone=s["phone"], email=_esw.emails(_join_mail(s["mail"])) or None,
            area=_jw(s["saja"]) or (villages[0] if villages else None), villages=villages,
            village_serials=[x for x, v in zip(s["serials"], s["villages"]) if v],
            circle=_jw(c["circle"]) if c else None, circle_officer=_jw(c["name"]) if c else None,
            vacant=None if s["name"] else True, office_id=f"{host}:{tag}:s{n}", src_pos=s["pos"], **base))
    return recs


# ---- HTML tables (Marathi or English headers) ----
ROLES = [("sno", r"^(अ\.?\s*क्र|क्र|sr|s\.?\s*no|sl)"), ("co_name", r"मंडळ\s*अधिकारी|circle officer|राजस्व निरीक्षक|revenue inspector|गिरदावर|girdawar|कानूनगो|kanungo|r\.?i\.?\s*name"),
         ("talathi", r"ग्राम\s*महसूल|तलाठी\s*(यांचे)?\s*ना|talathi(?!.*sajj?a)|village revenue officer|पटवारी(?!\s*(हल्का|मंडल|सर्किल))|"
                     r"patwari(?!\s*(halka|halqa|mandal|circle))|ग्राम\s*सेवक|ग्रामसेवक|gram\s*sevak|पंचायत\s*सचिव|सचिव\s*का\s*नाम|"
                     r"panchayat secretary|ग्राम\s*पंचायत\s*अधिकारी|ग्राम\s*विकास\s*अधिकारी|village development officer|gram vikas adhikari|"
                     r"તલાટી|talati|village accountant"),
         ("phone", r"मोबा|mobile|संपर्क|phone|contact"), ("email", r"ई-?मेल|e-?mail"),
         ("charge", r"मुळ|अति|charge|regular|additional"), ("villages", r"गावे|villages|सजातर्गत|ग्राम(ों)?\s*के\s*नाम|शामिल\s*ग्राम|ગામો"),
         ("saja", r"सजा|saja|sajja|हल्का|halka|halqa|पटवार\s*(मंडल|मण्डल)|patwar\s*mandal|ग्राम\s*पंचायत|gram\s*panchayat|ग्रामपंचायत|ગ્રામ\s*પંચાયત|"
                  r"gram panchayat|village|गांव|ग्राम|गाव|ગામ"),
         ("circle", r"मंडळ|circle")]


def roles(head):
    out = {}
    for i, h in enumerate(head):
        h = _esw.clean(h).lower()
        for role, rx in ROLES:
            if re.search(rx, h) and role not in out.values():
                out[i] = role
                break
    return out


GP_POST = re.compile(r"(?i)सेवक|sevak|सचिव|secretary|पंचायत\s*अधिकारी|विकास\s*अधिकारी|development officer|vikas adhikari|talati")
PATWARI = re.compile(r"(?i)पटवारी|patwari")


def post_of(header):
    """(post, post_regional, dept, level) from the header of the official's column."""
    h = _esw.clean(header)
    if GP_POST.search(h) and not re.search(r"(?i)तलाठी|talathi|महसूल", h):
        return "Gram Panchayat Secretary", h, "rural_development", "gram_panchayat"
    if PATWARI.search(h):
        return "Patwari", "पटवारी", "revenue", "village"
    if re.search(r"(?i)village accountant", h):
        return "Village Accountant", h, "revenue", "village"
    return POST, POST_MR, "revenue", "village"


def parse_html(html, p, url, module=MODULE):
    MODULE = module
    host = urlparse(url).netloc
    tag = p.get("tag") or _esw.slug(urlparse(url).path)[-40:] or "page"
    soup = _esw.soup(html)
    recs, circles = [], {}
    lu = _field.last_updated(html)
    for table in soup.find_all("table"):
        pos = []
        g = _esw.grid(table, pos=pos)
        hi = next((i for i, r in enumerate(g[:3]) if "talathi" in roles(r).values() and "saja" in roles(r).values()), None)
        if hi is None:
            continue
        rl = roles(g[hi])
        col = {v: k for k, v in rl.items()}
        post, post_reg, dept, level = post_of(g[hi][col["talathi"]])
        coh = _esw.clean(g[hi][col["co_name"]]) if "co_name" in col else ""
        co_post = ("Revenue Inspector" if re.search(r"(?i)राजस्व निरीक्षक|revenue inspector|r\.?i\.?", coh) else
                   "Girdawar / Kanungo" if re.search(r"(?i)गिरदावर|girdawar|कानूनगो|kanungo", coh) else CO_POST)
        for row, sp in zip(g[hi + 1:], pos[hi + 1:]):
            cell = lambda k: _esw.clean(row[col[k]]).translate(DEV_DIGITS) if k in col and col[k] < len(row) else ""
            name, saja = cell("talathi"), cell("saja")
            if not (name or saja) or name == _esw.clean(g[hi][col["talathi"]]):
                provenance.skip_row(row, 'skip: not (name or saja) or name == _esw.clean(g[hi][col["talathi"]])')
                continue
            co_raw = cell("co_name")
            co_phone = _esw.phones(co_raw)
            co_name = _esw.clean(re.sub(r"(?i)(?:,?\s*(?:मो|mob(?:ile)?)\.?)?\s*[6-9]\d{9}", "", co_raw).replace("|", " ")).strip(" ,.")
            circle = cell("circle")
            ck = (circle, co_name)
            if ck not in circles and (co_name or circle):
                circles[ck] = len(circles) + 1
                k = f"{host}:{tag}:c{circles[ck]}"
                recs.append(_esw.record(MODULE, k, dept="revenue", level="circle", post=co_post,
                                        post_regional=CO_POST_MR if co_post == CO_POST else coh,
                                        name=co_name, phone=co_phone, area=circle, circle=circle, state=p.get("state") or "MH",
                                        district=p.get("district"), tehsil=p.get("tehsil"), source=url, src_url=url,
                                        last_updated=lu, office_id=k, src_pos=sp))
            vill = [v.strip() for v in re.split(r"\s*[,،]\s*", cell("villages")) if v.strip()]
            k = f"{host}:{tag}:s{len([r for r in recs if ':s' in r[0]]) + 1}"
            recs.append(_esw.record(
                MODULE, k, dept=dept, level=level, post=post, post_regional=post_reg, name=name,
                phone=_esw.phones(cell("phone")), email=_esw.emails(cell("email")) or None, area=saja, villages=vill,
                circle=circle, circle_officer=co_name, charge=cell("charge"), state=p.get("state") or "MH", district=p.get("district"),
                tehsil=p.get("tehsil"), source=url, src_url=url, last_updated=lu, office_id=k, src_pos=sp,
                table_row={_esw.clean(h): _esw.clean(c) for h, c in zip(g[hi], row) if h and c}))
    return recs


def parse(content, url, p):
    if content[:5] == b"%PDF-":
        # pypdf layout first: it keeps one x offset per page; pdftotext -layout moves some lines left (2026-11-13, Nagar: 3
        # sajas lost); pdftotext only when pypdf gives no text
        text, engine = "\f".join(_esw.pdf_pages(content)), "pypdf layout"
        if not text.strip():
            text, engine = _field.pdf_text_engine(content)
        recs = parse_pdf_text(text, p, url)
        for _, d in recs:
            d["method"] = f"pdf text ({engine}), columns learned per page"
        return recs, bool(text.strip())
    return parse_html(content.decode("utf-8", "replace"), p, url), True


def items(get=None):
    return _field.seed(MODULE)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    tag = p.get("tag") or _esw.slug(urlparse(p["url"]).path)[-40:] or "page"
    pdf = r.content[:5] == b"%PDF-"
    files = [_esw.keep(MODULE, f"{host}-{tag}", r.content, "pdf" if pdf else "html")]
    recs, has_text = parse(r.content, p["url"], p)
    if not recs:
        return [], files, "no talathi rows" + ("" if has_text else " (scanned PDF: needs OCR)")
    return recs, files, ""
