"""Uttar Pradesh: Directorate of Local Bodies (localbodies.up.nic.in), the statewide lists of the town bodies' officials.
Answers from outside India too (checked 2026-11-11). All lists are in Hindi; the area and district stay as the lists write them.

Seed items (payload "kind"):
- "nn": listnn.htm, one HTML table of the 17 nagar nigams (2023 election): district, body + website, mayor (name | mobile |
  address), nagar ayukt (name | office phone, CUG mobile | email). Two records per body: महापौर (chair) and नगर आयुक्त (head).
  The page shows no date.
- "npp": pdf/elected-npp.pdf, 6 pages, the chairpersons (अध्यक्ष) of the 199 nagar palika parishads elected in May 2023.
- "np": pdf/elected-np.pdf, 16 pages, the chairpersons of the 544 nagar panchayats elected in May 2023.
  PDF columns: serial, district, body, reservation of the post, member, father / husband, mobile. One record per body (post
  अध्यक्ष, role chair); reservation, relative (पिता/पति) and election go in as extra keys. The PDFs show no date.

Quirks of the two PDFs (Word, font Nirmala UI Bold): the ToUnicode map has no entry for the conjunct glyphs, so pypdf prints
chr(glyph id) for them ("Ů" = प्र, "Ɨ" = क्ष). dforms/ulb_up_nirmala.json maps each glyph id to its text (from the font's cmap and
GSUB, built with fontTools from the embedded font). The text comes in visual order: the i-sign stands before its consonant and the
reph (र्) after its syllable; fix() puts both back in logical order and joins the gaps pypdf leaves after क / फ + sign and after
half forms. pdftotext drops those glyphs, so this reader reads with pypdf only. Cells wrap onto a second line (serial, "नगर",
"महिला" ...): the line with the mobile starts a record and the lines below it belong to it. Columns are found per page from the
data: the reservation words and the mobile mark their columns, the gaps between district / body and member / relative are
the median gaps of the one-line rows.

Extra keys: lgd_code (civic.ulb local_body_code from dforms/ulb_up_lgd.json: the bodies of these lists matched once, by name
inside the district, 725 of 760), area_latin / district_latin (a rough Latin form: civic.skel of it fits the LGD name), and the
record id / office id use that Latin form, because _esw.slug drops Devanagari.

No head (EO) list exists for the nagar palikas and nagar panchayats in text form: pdf/ulb-cug2005.pdf (16 scanned pages,
18-03-2021) gives the CUG mobile of the nagar ayukt / adhishasi adhikari of every body, but it needs OCR (not done here).
"""
import json
import re
import statistics
import unicodedata
from pathlib import Path

from dforms import _esw, _ulb
from dforms._water import unique

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_up"
BASE = "https://localbodies.up.nic.in/"
KINDS = {"nn": BASE + "listnn.htm", "npp": BASE + "pdf/elected-npp.pdf", "np": BASE + "pdf/elected-np.pdf"}
BODY_TYPE = {"nn": "नगर निगम", "npp": "नगर पालिका परिषद", "np": "नगर पंचायत"}
HONORIFIC = re.compile(r"^(?:श्रीमती|श्रीमति|सुश्री|श्री|कु0|कुमारी)\s+")
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
_MAP = None
_LGD = None


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "kind": k, "url": u, "state": "UP", "india_only": False}}
            for k, u in KINDS.items()]


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


# ---------------------------------------------------------------- Nirmala UI glyphs -> text in logical order
def glyphs():
    global _MAP
    if _MAP is None:
        d = json.loads((Path(__file__).parent / "ulb_up_nirmala.json").read_text(encoding="utf-8"))
        _MAP = ({chr(int(g)): t for g, t in d["glyphs"].items()}, {chr(int(g)) for g in d["reph"]})
    return _MAP


C = "[\u0915-\u0939\u0958-\u095f]\u093c?"                 # a consonant (with nukta)
CL = f"(?:{C}\u094d)*{C}"                                    # a conjunct cluster
MARKS = "[\u0900-\u0903\u093c\u093e-\u094d\u0962\u0963]"     # signs that follow their consonant
REPH = "\ue000"


def fix(s):
    """pypdf text of the Nirmala UI PDFs -> plain Hindi in logical order."""
    table, reph = glyphs()
    s = "".join((table[ch].replace("र्", "") + REPH) if ch in reph else table.get(ch, ch) for ch in s or "")
    s = s.replace("\u0902\u0941", "\u0941\u0902").replace("\u0902\u0942", "\u0942\u0902")   # कंुवर -> कुंवर
    s = re.sub("\u25cc" + MARKS + "?", "", s)                                   # dotted circle + a repeated sign
    s = re.sub(r"\u094d +(?=[\u0900-\u097f])", "\u094d", s)                     # half form, then a gap
    s = re.sub(r"([कफ][\u0941\u0942\u0943\u0947\u0948\u0902\u0901]) {1,2}(?=[\u0915-\u0939\u093f])", r"\1", s)
    s = re.sub(" +(?!\u093f)(" + MARKS + ")", r"\1", s)                         # a gap before a sign
    s = re.sub("\u093f(" + CL + ")", "\\1\u093f", s)                            # i-sign after its consonant cluster
    s = re.sub("(" + CL + MARKS + "*)" + REPH, "र्\\1", s)                      # reph before its syllable
    return nfc(s.replace(REPH, ""))


# ---------------------------------------------------------------- Latin keys and records
# Devanagari -> rough Latin (the kd_dirs.py scheme in civic-india): for record ids and office ids (_esw.slug keeps only a-z0-9,
# so a Hindi body name gives an empty slug) and for the extra keys area_latin / district_latin that a name match can use.
CONS = dict(zip("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ",
                "k kh g gh n ch chh j jh n t th d dh n t th d dh n p ph b bh m y r l v sh sh s h l".split()))
CONS.update({"क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y"})
VOW = dict(zip("अआइईउऊऋएऐओऔ", "a a i i u u ri e ai o au".split()))
SIGN = dict(zip("ािीुूृेैोौॅॉ", "a i i u u ri e ai o au e o".split()))
POST_KEY = {"महापौर": "mayor", "अध्यक्ष": "chairperson", "नगर आयुक्त": "nagar-ayukt"}


def latin(s):
    s = unicodedata.normalize("NFC", s or "")
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if nxt == "\u093c" and ch + nxt in CONS:
            ch, i = ch + nxt, i + 1
            nxt = s[i + 1] if i + 1 < len(s) else ""
        if ch in CONS:
            out.append(CONS[ch])
            if nxt not in SIGN and nxt not in ("\u094d", "") and ("\u0900" <= nxt <= "\u097f" or nxt == " ") and nxt not in "ंँः":
                out.append("a")
            elif nxt in "ंँः" and nxt:
                out.append("a")
        elif ch in VOW:
            out.append(VOW[ch])
        elif ch in SIGN:
            out.append(SIGN[ch])
        elif ch in "ंँ":
            out.append("n")
        elif ch in "\u094d\u093cः":
            pass
        else:
            out.append(ch if ch.isascii() else " ")
        i += 1
    t = re.sub(r"a\b", "", "".join(out))             # a word-final inherent a is not spoken
    return " ".join(t.split()).title()


def lgd_code(district, body, body_type):
    """civic.ulb local_body_code of a body as the lists write it (dforms/ulb_up_lgd.json, matched once by name in the district)."""
    global _LGD
    if _LGD is None:
        _LGD = json.loads((Path(__file__).parent / "ulb_up_lgd.json").read_text(encoding="utf-8"))["codes"]
    return _LGD.get(f"{district}|{body}|{body_type}")


def rec(body, post, seen, district=None, **f):
    """_ulb.record with an id and office id from the Latin form of district + body (stable across runs), and the LGD code."""
    code = lgd_code(_esw.clean(district or ""), _esw.clean(body), f.get("body_type"))
    if code:
        f["lgd_code"] = code
    _, d = _ulb.record(MODULE, "UP", body, post, set(), district=district, **f)
    lb, ld = latin(body), latin(district or "")
    d["area_latin"] = lb
    if district:
        d["district_latin"] = ld
    kind = next((k for k, t in BODY_TYPE.items() if t == f.get("body_type")), "ulb")   # Faridpur (Bareilly) is an NPP and an NP
    d["office_id"] = f"UP-{kind.upper()}-{_esw.slug(ld)}-{_esw.slug(lb)}"
    key = unique(f"UP-{kind}-{_esw.slug(ld)}-{_esw.slug(lb)}-{POST_KEY.get(post, _esw.slug(latin(post)))}", seen)
    return f"dept:{MODULE}:{key}", d


# ---------------------------------------------------------------- nagar nigams (HTML)
def person(s):
    s = HONORIFIC.sub("", _esw.clean(s)).strip(" ,।")
    return "" if re.fullmatch(r"[-–\s.]*", s) else s


def parse_nn(html, url=KINDS["nn"]):
    recs, seen = [], set()
    for t in _esw.soup(html).find_all("table"):
        for row in _esw.grid(t):
            if len(row) < 5 or not re.fullmatch(r"\d+", row[0].strip()):
                continue
            district = nfc(_esw.clean(row[1]))
            m = re.match(r"\s*(.*?)\s*(?:\|\s*)?((?:https?://|www\.)\S+)?\s*$", row[2])
            body, site = nfc(_esw.clean(m.group(1)).strip(" |")), (m.group(2) or "")
            common = dict(district=district or None, body_type=BODY_TYPE["nn"], source=url, website=site or None, election="2023")
            parts = [p.strip() for p in row[3].split("|")]
            mob = _esw.phones(parts[1]) if len(parts) > 1 else ""
            addr = ", ".join(p for p in parts[2:] if p) or None
            if person(parts[0]) or mob:
                recs.append(rec(body, "महापौर", seen, name=nfc(person(parts[0])), phone=mob, address=addr, **common))
            parts = [p.strip() for p in row[4].split("|")]
            phone = _esw.phones(*[p for p in parts[1:] if "@" not in p])
            email = _esw.emails(" ".join(p for p in parts if "@" in p))
            if person(parts[0]) or phone or email:
                recs.append(rec(body, "नगर आयुक्त", seen, name=nfc(person(parts[0])), phone=phone, email=email,
                                        **common))
    return recs


# ---------------------------------------------------------------- chairpersons (PDF)
RES = nfc("(?:अनारक्षित|महिला|अन्य पिछड़ा वर्ग|अनुसूचित जाति|अनुसूचित जनजाति)(?: महिला)?")
RES_WORD = re.compile("^(?:" + RES + ")$")


def chunks(line):
    """Pieces of a layout line split at gaps of two or more spaces: (start, end, text)."""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def is_res(raw):
    return bool(RES_WORD.match(fix(raw)))


def gap_bound(pairs):
    """Boundary between two columns from the one-line rows: the median of the gap midpoints."""
    mids = [(a_end + b_start) / 2 for a_end, b_start in pairs]
    return statistics.median(mids) if mids else None


def page_rows(page):
    """Records of one page: lists of 7 cells (serial, district, body, reservation, member, relative, mobile) of raw text."""
    # the footer "Page 7" can share a line, even a cell ("पिछड़ा Page 7वर्ग"): out, keeping the columns
    lines = [re.sub(r"Page \d+", lambda m: "" if m.end() < len(ln) and ln[m.end()] != " " else " " * len(m.group(0)), ln)
             for ln in page.split("\n")]
    lines = [ln for ln in lines if ln.strip()]
    hi = next((i for i, ln in enumerate(lines) if "मोबाइल" in fix(ln)), None)
    if hi is None:
        return []
    body = lines[hi + 1:]
    res_lo, res_hi, mob_lo, ser_hi, db, cf = 10 ** 6, 0, 10 ** 6, 0, [], []
    for ln in body:
        ch = chunks(ln)
        for a, b, c in ch:
            if is_res(c):
                res_lo, res_hi = min(res_lo, a), max(res_hi, b)
            elif MOBILE.fullmatch(c):
                mob_lo = min(mob_lo, a)
            elif re.fullmatch(r"\d{1,3}", c) and a < 12:
                ser_hi = max(ser_hi, b)
    if res_hi == 0:
        return []
    for ln in body:                       # one-line rows: two pieces left of the reservation, two between it and the mobile
        ch = [x for x in chunks(ln) if not (re.fullmatch(r"\d{1,3}", x[2]) and x[0] < 12)]
        left = [x for x in ch if x[1] <= res_lo]
        mid = [x for x in ch if x[0] >= res_hi and not MOBILE.search(x[2])]
        if any(MOBILE.search(x[2]) for x in ch):
            if len(left) == 2:
                db.append((left[0][1], left[1][0]))
            if len(mid) == 2:
                cf.append((mid[0][1], mid[1][0]))
    b_db, b_cf = gap_bound(db), gap_bound(cf)
    if b_db is None or b_cf is None:
        return []
    recs, cur = [], None
    for ln in body:
        cells = [[] for _ in range(7)]
        left, right = [], []
        for a, b, c in chunks(ln):
            if re.fullmatch(r"\d{1,3}", c) and a < max(ser_hi, 6) + 2:
                cells[0].append(c)
                continue
            m = MOBILE.search(c)
            if m and a >= res_hi:
                cells[6].append(m.group(0))
                c = (c[:m.start()] + c[m.end():]).strip()
                if not c:
                    continue
                b = a + len(c)
            x = (a + b) / 2
            if is_res(c) and res_lo - 2 <= x <= res_hi + 2:
                cells[3].append(c)
            elif x < res_lo:
                left.append((x, c))
            elif x <= res_hi:
                cells[3].append(c)
            else:
                right.append((x, c))
        # two pieces on one side of the reservation are the two columns of that side; one piece goes by the median gap
        for side, bound, (k1, k2) in ((left, b_db, (1, 2)), (right, b_cf, (4, 5))):
            if len(side) == 2:
                cells[k1].append(side[0][1])
                cells[k2].append(side[1][1])
            else:
                for x, c in side:
                    cells[k1 if x < bound else k2].append(c)
        if cur is None or cells[6] or (cells[0] and cur[0]):
            cur = [[] for _ in range(7)]
            recs.append(cur)
        for i in range(7):
            cur[i] += cells[i]
    return recs


def parse_pdf(content, kind, url=None):
    url = url or KINDS[kind]
    recs, seen = [], set()
    for page in _esw.pdf_pages(content):
        for r in page_rows(page):
            serial, district, body, res, name, rel, mob = (_esw.clean(fix(" ".join(c))) for c in r)
            if not re.fullmatch(r"\d+", serial) or not body:
                continue
            name = person(name)
            if not (name or mob):
                continue
            recs.append(rec(body, "अध्यक्ष", seen, name=name, phone=mob, district=district or None,
                                    body_type=BODY_TYPE[kind], source=url, serial=int(serial), reservation=res or None,
                                    relative=person(rel) or None, election="2023"))
    return recs


def fetch(p, get):
    kind = p.get("kind", "nn")
    url = p.get("url") or KINDS[kind]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if kind == "nn":
        files = [_esw.keep(MODULE, "listnn", r.content, "html")]
        r.encoding = "utf-8"
        recs = parse_nn(r.text, url)
    else:
        if r.content[:5] != b"%PDF-":
            return [], [], "not a PDF"
        files = [_esw.keep(MODULE, f"elected-{kind}", r.content, "pdf")]
        recs = parse_pdf(r.content, kind, url)
    return recs, files, "" if recs else "no rows"
