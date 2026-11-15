"""Madhya Pradesh: elected ward councillors (parshad) and mayors of the 2022 urban body elections (and the January 2023 polls),
from the Madhya Pradesh Gazette Extraordinary (govtpress.mp.gov.in), read by OCR.

After each poll the State Election Commission (department "राज्य निर्वाचन आयोग") notified the winners under section 45 of the
MP Municipalities Act 1961: one notice per body, several bodies and districts per Gazette Extraordinary issue (No. 411 of
26 July 2022: 43 pages, 33 bodies of Shajapur, Betul, Sheopur, Dhar, Neemuch, Satna, Burhanpur and Dewas districts). Each
notice has a preamble ("... राज्य में नगरपालिका परिषद् शाजापुर जिला शाजापुर के माह-जुलाई 2022 में कराये गये आम निर्वाचन में
निम्नलिखित व्यक्ति पार्षद निर्वाचित हुए है") and a ruled table: serial | body, district | post (पार्षद / महापौर) | ward number in
figures | ward number in words | name of the elected person | party.
The issues are scans (no text layer). The table grid comes from the ruled lines of the page image at 100 dpi (pure Python;
skew, faint and lost lines handled: grid()), each cell is read by Tesseract (hin) at 300 dpi (one run per page,
cforms/gj.ocr_boxes), and the column roles come from what the cells hold (post words, numbers, party names). The body comes
from the preamble of its notice, and is tied to its LGD body by sound (cw_mp_lgd.json: code, name, district, type, wards), so an
OCR slip in a town name still lands on the right body. Ward numbers run 1, 2, 3 ... in a notice (sequence() repairs misread ones).
Measured on issue 411 (2026-11-11, all 43 pages): 650 of the 666 seats of the 33 bodies it read (98%), 654 rows, 14 without a
party; 4 more bodies of Neemuch district (Kukdeshwar, Diken, Nayagaon, Ratangarh) sit on pages whose lines are too faint.

Two steps (bucket rule: the India-only download happens once):
- seed item (councillors project, India servers): items(get) lists the gazette search (POST Gazette/ajaxPaginationData/<offset>,
  category 15 = Extraordinary, department 1 = State Election Commission, years 2022 and 2023; also the archive list
  gazette/archive/ when its page offers its own search call), keeps the general-election notices whose subject says
  "पार्षद निर्वाचित", downloads each PDF once, saves it in the bucket (councillors/MP/<slug>.pdf) and lists OCR items of 4 pages
  each with a "stored" key. Not yet seen working: the one search tried by hand (title "पार्षद", SEC, 2022) answered "no record",
  so the 2022 issues may sit in the archive list only; the seed record then says "no items".
- OCR items (kind "form-cw_mp", councillors-ocr project): read the saved copy (cforms/tn.stored), else the gazette site.
Record id councillor:MP:<LGD name slug>-<district slug>:<ward>:gz<issue>-p<page> ("mayor" for the mayor; the page since 2026-11-15)."""
import functools
import hashlib
import io
import os
import re
import subprocess
import tempfile

from bs4 import BeautifulSoup

import provenance
from cforms import gj, tn
from cforms.cg import roman

METHOD = "ocr tesseract hin (one image per ruled cell, scan without text layer; whole-page text lines where no grid is read)"     # source trail (provenance.py): how this reader reads its sources

SITE = "https://govtpress.mp.gov.in"
PAGE = SITE + "/gazette"
LIST = SITE + "/Gazette/ajaxPaginationData/{}"
ARCHIVE = SITE + "/gazette/archive/"     # older issues ("संग्रहीत"): the current list may hold only recent years
CAT_EXTRA, DEPT_SEC = "15", "1"
CHUNK = 4
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
WORDS = {w: i for i, w in enumerate(
    "शून्य एक दो तीन चार पांच छः सात आठ नौ दस ग्यारह बारह तेरह चौदह पन्द्रह सोलह सत्रह अठारह उन्नीस बीस इक्कीस बाईस तेईस चौबीस "
    "पच्चीस छब्बीस सत्ताईस अट्ठाईस उन्तीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उन्तालीस चालीस इकतालीस बयालीस "
    "तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरेपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ "
    "इकसठ बासठ तिरेसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर "
    "उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी".split())}
WORDS.update({"सौलह": 16, "उनन्नीस": 19, "उन्नीस": 19, "पाँच": 5, "छह": 6, "छ": 6, "पंद्रह": 15, "उन्नतीस": 29, "अठ्ठाईस": 28, "अड्डाईस": 28})
PARTY = ((r"[भम]ारत\S?य\s*जन|[भम]ारतीय|भा\.?\s*ज\.?\s*पा|जनता\s*पा|जनत्?त?ा?\s*पा[दटर्ी]", "BJP"),
         (r"इंडियन|इण्डियन|नेशनल|[कग][ाॉ]ँ?ं?\s*ग्र?े?स|कांग्रेस|संग्रेस", "INC"),
         (r"निर्दलीय|निर्दली|निदलीय|न\S{0,2}र्?द\S{0,2}ीय|स्वतंत्र", "Independent"), (r"आम\s*आदमी", "AAP"),
         (r"बहुजन|समाज\s*पा", "BSP"), (r"सोशल\s*ड", "SDPI"),
         (r"समाजवादी", "SP"), (r"मजलिस|मजलीस|इत्तेहाद|एआईएमआईएम", "AIMIM"), (r"गोंडवाना|गोण्डवाना", "GGP"),
         (r"मार्क्सवादी", "CPI(M)"), (r"कम्युनिस्ट", "CPI"), (r"राष्ट्रवादी", "NCP"), (r"शिवसेना", "SHS"),
         (r"जनता\s*दल", "JD(U)"), (r"जयस|आदिवासी", "JAYS / tribal party"))
HEADER = re.compile(r"निर्वाचित|व्यक्ति|सम्बद्ध|संबद्ध|का नाम|शब्दों|अंकों|क्रमांक|^पद\b|पद पा")
POST = re.compile(r"पा\s?(?:र्?)?\s?[षशघ]|पार्?\s?द|महापौर|महापोर")      # पार्षद, also cut ("पार्ष") or misread
TYPES = (("नगरपालिक निगम", "Municipal Corporation"), ("नगर पालिक निगम", "Municipal Corporation"), ("नगर निगम", "Municipal Corporation"),
         ("नगरपालिका परिषद", "Municipality"), ("नगर पालिका परिषद", "Municipality"), ("नगरपालिका", "Municipality"),
         ("नगर परिषद", "Nagar Parishad"))
PREAMBLE = re.compile(r"राज्य\s*में\s*(.{3,80}?)\s*के\s*माह\s*[-–—]*\s*(\S+?)\s*(?:वर्ष)?\s*[-–—]*\s*([0-9०-९]{4})")
# the same preamble with the OCR slips of faint scans (ocr-gap round 2026-11-15): "राज्य में" read as "चाज्य 7", "शज्य में",
# "र|ज्य में"; "के माह" read as "के.माह", "क॑ माह", "के भाह". The body starts at its type word (नगर ...).
PREAMBLE_LOOSE = re.compile(r"\S{0,3}ज्य\S{0,2}\s*\S{0,4}\s+((?:न\S?ग\S?र|नगरपालिक)\S*\s*.{2,80}?)\s*[कंक]\S{0,2}[\s.]*[मभ]ाह\s*"
                            r"[-–—.]*\s*(\S+?)\s*(?:वर्ष)?\s*[-–—]*\s*([0-9०-९]{4})")


def tools():
    return gj.tools("hin")


def norm(s):
    return gj.norm(s)


# ---------------------------------------------------------------- listing (seed step)

def listing(html):
    """Rows of one answer of the gazette search: [{no, date, kind, dept, subject, url}] and the next page offsets."""
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    head = None
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        texts = [norm(c.get_text(" ")) for c in cells]
        if tr.find("th") or any(t.startswith("राजपत्र क्र") for t in texts):
            head = texts
            continue
        if not head or len(cells) < len(head) - 1:
            provenance.skip_row(tr, 'skip: not head or len(cells) < len(head) - 1')
            continue
        row = dict(zip(head, texts))
        links = [a["href"] for a in tr.find_all("a", href=True)]
        pdf = next((h for h in links if ".pdf" in h.lower()), links[0] if links else "")
        if not pdf:
            provenance.skip_row(tr, 'skip: not pdf')
            continue
        out.append({"no": row.get("राजपत्र क्र.", "").translate(DIGITS), "date": row.get("दिनांक", ""),
                    "kind": row.get("राजपत्र प्रकार", ""), "dept": row.get("विभाग", ""), "subject": row.get("विषय", ""),
                    "url": pdf if pdf.startswith("http") else SITE + "/" + pdf.lstrip("/")})
    offsets = sorted({int(x) for x in re.findall(r"searchFilter\((\d+)", html or "")})
    return out, offsets


def wanted(row):
    """General-election winner notices. By-election notices are left out: they name single wards and would replace the
    general-election record of the same ward in an order nobody controls."""
    s = row["subject"]
    return bool(re.search(r"पार्षद", s) and re.search(r"निर्वाचित", s) and not re.search(r"उप\s*-?\s*निर्वाचन|उपनिर्वाचन", s))


def slug_of(row):
    d = re.sub(r"\D", "", row["date"].translate(DIGITS))
    return f"mp-gz-{d or 'nodate'}-{row['no'] or hashlib.sha1(row['url'].encode()).hexdigest()[:8]}"


def items(get):
    """Seed step on an India server: list the notices, save each PDF in the bucket once, return the OCR items."""
    from pypdf import PdfReader
    hub = getattr(get, "hub", None)
    project = os.environ.get("SCRAPE_POOL_PROJECT", "civic-officials-councillors")
    rows, seen = [], set()
    pages = [(PAGE, LIST)]
    first = get(PAGE)                           # the search page: session cookie and the address of its search call
    for page_url in (PAGE, ARCHIVE):
        r = first if page_url == PAGE else get(page_url)
        call = re.search(r"url:\s*'([^']*ajaxPaginationData[^']*)'", r.text if r is not None else "")
        if call and page_url == ARCHIVE and call.group(1).rstrip("/") + "/{}" != LIST:
            pages.append((ARCHIVE, call.group(1).rstrip("/") + "/{}"))
    for _, call in pages:
        for year in ("2022", "2023"):
            todo, done, token = [0], set(), ""
            while todo and len(done) < 80:
                off = todo.pop(0)
                if off in done:
                    continue
                done.add(off)
                r = get(call.format(off), method="POST", data={"page": off, "sTitle": "", "ci_csrf_token": token,
                                                               "cat_id": CAT_EXTRA, "department_id": DEPT_SEC, "year": year})
                if r is None:
                    continue
                tm = re.search(r'name="ci_csrf_token" value="([^"]*)"', r.text)   # the answer carries the form's next token
                token = tm.group(1) if tm else token
                found, offsets = listing(r.text)
                for row in found:
                    if row["url"] not in seen and wanted(row):
                        seen.add(row["url"])
                        rows.append(row)
                todo += [o for o in offsets if o > off and o not in done and o not in todo]
    out = []
    for row in rows:
        slug = slug_of(row)
        r = get(row["url"])
        if r is None or r.content[:5] != b"%PDF-":
            continue
        try:
            n = len(PdfReader(io.BytesIO(r.content)).pages)
        except Exception:  # noqa: BLE001 - a broken file: no items
            continue
        stored = None
        if hub is not None:
            path = f"councillors/MP/{slug}.pdf"
            hub.upload_many([(path, r.content, "application/pdf")])
            stored = f"{project}/{path}"
        for first in range(1, n + 1, CHUNK):
            p = {"kind": "form-cw_mp", "state": "MP", "url": row["url"], "gazette_no": row["no"], "gazette_date": row["date"],
                 "subject": row["subject"], "first": first, "last": min(n, first + CHUNK - 1), "pages": n, "slug": slug}
            if stored:
                p["stored"] = stored
            out.append({"key": f"{slug}-p{first}", "payload": p})
    return out


# ---------------------------------------------------------------- page grid (scan)

DARK = bytes(1 if i < 200 else 0 for i in range(256))   # faint scanned lines need a light threshold
GDPI = 100


def _or(*bs):
    n = len(bs[0])
    v = 0
    for b in bs:
        v |= int.from_bytes(b, "big")
    return v.to_bytes(n, "big")


def _longest(b, gap):
    best = 0
    for m in re.finditer(rb"\x01(?:\x01|\x00{1,%d}(?=\x01))*" % gap, b):
        best = max(best, m.end() - m.start())
    return best


def _cluster(marks, tol=3):
    out, cur = [], []
    for v in marks:
        if cur and v - cur[-1] > tol:
            out.append(sum(cur) / len(cur))
            cur = []
        cur.append(v)
    if cur:
        out.append(sum(cur) / len(cur))
    return out


def grid(w, h, pix):
    """Ruled lines of a page image (8-bit gray bytes, w x h): (horizontal ys, vertical xs, table bands [(top, bottom)]) in
    pixels. A table band is a strip between two horizontal lines that vertical lines cross (masthead rules are not)."""
    m = pix.translate(DARK)
    rows = [m[y * w:(y + 1) * w] for y in range(h)]
    # horizontal lines: rows (7 together, for skew) dark across a quarter of the page, with one unbroken piece of a fifth of it
    # (a text line's headline is dark too, but broken at every word space)
    hy = []
    for y in range(3, h - 3):
        r = _or(*rows[y - 3:y + 4])
        if r.count(1) >= 0.25 * w and _longest(r, 3) >= 0.2 * w:
            hy.append(y)
    hs = _cluster(hy)
    # vertical lines: an x that is dark in nearly every row of most table bands (text strokes fill only part of a band).
    # Per band, the rows' bytes are added as big integers: each byte then holds that x's dark count (no carry: < 256 rows).
    bands = [(int(a) + 2, int(b) - 1) for a, b in zip(hs, hs[1:]) if 15 <= b - a <= 160]
    if len(bands) < 2:
        return hs, [], []
    found = []                                   # (x, band) of the line pieces in each band
    full = (1 << (8 * w)) - 1
    for i, (a, b) in enumerate(bands):
        tot = 0
        for y in range(a, b):          # each row widened by one pixel on both sides: a line that steps sideways in the band
            v = int.from_bytes(rows[y], "big")
            tot += v | ((v << 8) & full) | (v >> 8)
        cnt = tot.to_bytes(w, "big")
        need = 0.88 * (b - a)
        found += [(x, i) for x in _cluster([x for x in range(1, w - 1) if cnt[x] >= need])]
    # a scan is a little skewed: the same line sits a few pixels apart from band to band, so pieces join within 8 px
    found.sort()
    groups, cur = [], []
    for x, i in found:
        if cur and x - cur[-1][0] > 8:
            groups.append(cur)
            cur = []
        cur.append((x, i))
    if cur:
        groups.append(cur)
    vs = [sum(x for x, _ in g) / len(g) for g in groups if len({i for _, i in g}) >= 0.4 * len(bands)]
    # the outer borders are sometimes too faint: the ends of the horizontal lines stand in for them (the outermost pieces of
    # 20 px or more on each table line, median over the lines)
    ends = []
    for y in hs:
        y = int(y)
        row = _or(rows[max(0, y - 1)], rows[y], rows[min(h - 1, y + 1)])
        segs = [(mm.start(), mm.end()) for mm in re.finditer(rb"\x01(?:\x01|\x00{1,3}(?=\x01))*", row) if mm.end() - mm.start() >= 20]
        if segs and max(e - s for s, e in segs) >= 0.15 * w:
            ends.append((segs[0][0], segs[-1][1]))
    if ends:
        left = sorted(e[0] for e in ends)[len(ends) // 2]
        right = sorted(e[1] for e in ends)[len(ends) // 2]
        if not any(abs(v - left) <= 10 for v in vs):
            vs.append(left)
        if right - max(vs, default=0) > 10:
            vs.append(right)
    # text right of the last line found (the party column, its right border lost): a closing line after the text
    if vs and bands:
        acc = 0
        for a, b in bands:
            for y in range(a, b):
                acc |= int.from_bytes(rows[y], "big")
        ink = acc.to_bytes(w, "big").rstrip(b"\x00")
        last_ink = len(ink) - 1
        if last_ink - max(vs) > 30:
            vs.append(min(w - 2, last_ink + 3))
    pieces = {}
    for x, i in found:
        pieces[i] = pieces.get(i, 0) + 1
    table = [(bands[i][0] - 2, bands[i][1] + 1) for i in range(len(bands)) if pieces.get(i, 0) >= 3]
    return hs, sorted(vs), table


def render(pdf, page, dpi, tmp):
    base = os.path.join(tmp, f"g{page}")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True)
    try:
        with open(base + ".pgm", "rb") as f:
            img = f.read()
        os.remove(base + ".pgm")
    except OSError:
        return 0, 0, b""
    mm = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", img)
    if not mm:
        return 0, 0, b""
    return int(mm.group(1)), int(mm.group(2)), img[mm.end():]


# ---------------------------------------------------------------- cells -> members

def num(t):
    t = norm(t).translate(DIGITS)
    t = t.replace("O", "0").replace("o", "0")
    mm = re.search(r"\d{1,3}", t)
    return str(int(mm.group(0))) if mm else ""


def word_num(t):
    for w in re.findall(r"[ऀ-ॿ]+", norm(t).replace(":", "")):
        if w in WORDS:
            return str(WORDS[w])
    return ""


def party_of(t):
    t = norm(t)
    for k, v in PARTY:
        if re.search(k, t):
            return v
    return ""


def roles(table):
    """Column roles from the read cells of a page: {role: column}. table = [[cell text]]."""
    if not table:
        return {}
    ncol = max(len(r) for r in table)

    def share(c, f):
        vals = [r[c] for r in table if c < len(r) and r[c].strip()]
        return (sum(bool(f(v)) for v in vals) / len(vals)) if vals else 0.0
    post = max(range(ncol), key=lambda c: share(c, POST.search))
    party = max(range(ncol), key=lambda c: share(c, party_of))
    out = {}
    if share(post, POST.search) >= 0.3:
        out["post"] = post
    if share(party, party_of) >= 0.3 and party != out.get("post"):   # (a party cell read "पार्दी" made it the post column)
        out["party"] = party
    after = [c for c in range(ncol) if c > out.get("post", -1) and c != out.get("party")]
    nums = [c for c in after if share(c, lambda v: re.fullmatch(r"[\s(|]*[0-9०-९]{1,3}[\s.)|]*", v)) >= 0.5]
    if nums:
        out["ward"] = nums[0]
    words = [c for c in after if c != out.get("ward") and share(c, word_num) >= 0.4]
    if words:
        out["ward_words"] = words[0]
    if "post" in out and out["post"] > 0:
        out["body"] = out["post"] - 1
    if "party" in out:
        # the name: of the two columns left of the party (a doubled border makes an empty sliver column), the fuller one
        left = [c for c in range(out["party"] - 1, -1, -1) if c not in out.values()][:2]
        if left:
            out["name"] = max(left, key=lambda c: (sum(len(r[c].strip()) for r in table if c < len(r)), c))
    elif "ward_words" in out and out["ward_words"] + 1 < ncol:
        # no party column read (the right border lost in a skewed scan, Kotma 2022): the name is the column after the ward in words
        out["name"] = out["ward_words"] + 1
    return out


def clean_name(t):
    t = gj.clean_cell(t)
    t = re.sub(r"^[\d०-९.\s]+", "", t)
    return t.strip(" .,:;-—|")


def junk(name):
    """OCR noise from a border or a stamp read as a name: mostly one- and two-letter pieces, or few Devanagari letters."""
    toks = name.split()
    letters = sum(1 for ch in name if "ऀ" <= ch <= "ॿ")
    return (not toks or sum(len(x) <= 2 for x in toks) > len(toks) / 2 or len(toks) > 7
            or letters < 0.7 * len(name.replace(" ", "")))


class Row(list):
    """The cell texts of one table row; .box = the row's band in PDF points (x0, y0, x1, y1, top-left origin)."""
    box = None


def members(table, rl, tno=None):
    """Members from the read rows of one page and the column roles. tno: the table's place on the page (source trail)."""
    out = []
    if "name" not in rl:
        return out
    for ri, r in enumerate(table, 1):
        cell = lambda k: r[rl[k]] if k in rl and rl[k] < len(r) else ""   # noqa: E731
        post = norm(cell("post"))
        # the party: every cell right of the name (a stray line can split the party column)
        party_local = gj.clean_cell(" ".join(r[rl["name"] + 1:]))
        # a post cell the scan left unread: still a member row when its party cell names a party (header rows have none);
        # the ward number then comes from the run of numbers (sequence())
        if not POST.search(post) and not party_of(party_local):
            provenance.skip_row(r, 'skip: not POST.search(post) and not party_of(party_local)')
            continue
        name = clean_name(cell("name"))
        if len(name) < 3 or HEADER.search(name) or HEADER.search(post) or junk(name):
            provenance.skip_row(r, 'skip: len(name) < 3 or HEADER.search(name) or HEADER.search(post) or junk...')
            continue
        mayor = "महापौर" in post or "महापोर" in post
        ward = "" if mayor else (word_num(cell("ward_words")) or num(cell("ward")) or num(post))
        out.append({"position": "Mayor" if mayor else "Councillor", "ward_no": ward, "ward_read": num(cell("ward")),
                    "post_read": bool(POST.search(post)), "body_cell": norm(cell("body")),
                    "ward_words": word_num(cell("ward_words")), "name": name,
                    "party": party_of(party_local), "party_local": party_local,
                    "_pos": {k: v for k, v in (("table", tno), ("row", ri), ("box_pt", getattr(r, "box", None)),
                                                     ("ocr_line", getattr(r, "line", None))) if v is not None}})
    return out


def body_from(text):
    """(body, district, body type, month, year) from a notice preamble."""
    t = norm(text).replace("परिषद्", "परिषद").replace("परिषद्‌", "परिषद").replace("–", "-")
    t = t.replace("ग़", "ग").replace("ज़", "ज")
    # stray nasal marks in the body type ("नंगरपालिका", "नगंर परिषद") and a cut "निगः": else the type stays in the name and the
    # sound match goes astray (Khachrod and Ratlam went to Nainpur, Gurh to Dongar Parasia)
    t = re.sub(r"न[ंँ]?ग[ंँ]?र", "नगर", t)
    t = re.sub(r"(नगर\s*पालिक\s*)नि[गन]\S?(?=\s)", r"\1निगम", t)        # "निगः", "निनः"
    t = re.sub("[\u0951\u0952]", "", t)                                   # Vedic stress marks: "प॑रिषद्" (Sehore)
    mm = PREAMBLE.search(t) or PREAMBLE_LOOSE.search(t)
    if not mm:
        return None
    full, month, year = mm.group(1), mm.group(2), mm.group(3).translate(DIGITS)
    full = re.sub(r"\s+", " ", full).strip(" ,.;:|-")       # "राज्य में . नगरपालिका परिषद् -सीघी" (Sidhi)
    dist = ""
    # the district: one or two words after जिला (also read as जिलः, जिंला, जिले; "धार जिला, धार"; "आगर मालवा")
    dm = re.search(r"(.*?)\s*[^\sऀ-ॿ]?\s*(?:जि\S?ल[ाःे]|ज़िला)[\s,.:;_*-]+(?:[^\sक-ह]+\s+)*(\S+(?:\s+\S+)?)\s*$", full)   # (\W would eat a vowel sign)
    if dm:
        full, dist = dm.group(1), dm.group(2)
    btype = ""
    for k, v in TYPES:
        if full.replace(" ", "").startswith(k.replace(" ", "")):
            btype = v
            full = full[len(k):].strip() if full.startswith(k) else re.sub(r"^\S+\s+\S+\s*", "", full)
            break
    else:
        # "नगर परिषद्" with OCR slips ("नगर प्ररिषद्", "नगर ८ ..."): नगर, then a word that starts with प or a stray mark
        mm2 = re.match(r"नगर\s+(?:प\S*|\S{1,2})\s+(\S.*)$", full)
        if mm2 and not re.match(r"नगर\s*(?:पालि|निगम)", full):
            btype, full = "Nagar Parishad", mm2.group(1)
    full = re.sub(r"[।॥०-९]", " ", full)
    name = re.sub(r"[^ऀ-ॿ ()-]", "", full).strip(" ,-")
    name = " ".join(name.split())
    dist = re.sub(r"[^ऀ-ॿ]|[।॥०-९]", "", dist)
    return {"body_local": name, "district_local": dist or name, "body_type": btype, "month": month, "year": year}


def page_cells(pdf, page, tmp):
    """The page as blocks from top to bottom: ("pre", text of the strip above a table: a notice preamble or the page header)
    and ("rows", [[cell text]]) for each table."""
    w, h, pix = render(pdf, page, GDPI, tmp)
    if not w:
        return []
    hs, vs, table = grid(w, h, pix)
    if len(vs) < 4 or not table:
        return []
    k = 72 / GDPI
    # a band as tall as two or more rows: a row line the scan lost; it is cut into rows of the usual height
    hts = sorted(b - a for a, b in table)
    med = hts[len(hts) // 2]
    cut = []
    for a, b in table:
        n = round((b - a) / med) if med >= 15 and b - a >= 1.6 * med else 1
        cut += [(a + (b - a) * j / n, a + (b - a) * (j + 1) / n) for j in range(n)]
    table = cut
    segs = []                                   # runs of touching table bands
    for a, b in table:
        if segs and a - segs[-1][-1][1] <= 6:
            segs[-1].append((a, b))
        else:
            segs.append([(a, b)])
    boxes, plan, top = [], [], 0
    for seg in segs:
        if seg[0][0] - top > 15:
            plan.append(("pre", len(boxes), 1))
            boxes.append((0, top * k, w * k, (seg[0][0] - 1) * k))
        shape, bands = [], []
        last = len(vs) - 2
        for a, b in seg:
            bands.append((round(vs[0] * k, 1), round(a * k, 1), round(vs[-1] * k, 1), round(b * k, 1)))
            n = 0
            for j, (x0, x1) in enumerate(zip(vs, vs[1:])):
                if x1 - x0 < 22:                 # a doubled border, not a column (the narrowest column, serial, is ~30 px)
                    continue
                if j == last:                    # the right border can be lost in a scan: the last cell reaches a bit further
                    x1 = min(w - 4, x1 + 0.06 * w)
                boxes.append(((x0 + 3) * k, (a + 2) * k, (x1 - 3) * k, (b - 2) * k))
                n += 1
            shape.append(n)
        plan.append(("rows", len(boxes) - sum(shape), (shape, bands)))
        top = seg[-1][1] + 1
    if h - top > 60:                            # text below the last table: a notice whose table starts on the next page
        plan.append(("pre", len(boxes), 1))
        boxes.append((0, top * k, w * k, (h - 1) * k))
    texts = gj.ocr_boxes(pdf, page, boxes, tmp, "hin", dpi=300, psm=6)
    out = []
    for kind, i, shape in plan:
        if kind == "pre":
            out.append(("pre", texts[i]))
        else:
            rows = []
            for n, band in zip(*shape):
                row = Row(texts[i:i + n])
                row.box = list(band)
                rows.append(row)
                i += n
            out.append(("rows", rows))
    return out


# ---------------------------------------------------------------- pages without a ruled grid: text lines

# Some issues print the member table without row lines (Ex-543, 550, 551 of Sept-Oct 2022: one body per page, columns only
# spaced), and some ruled pages are too faint for grid(). On such a page the whole page is read by Tesseract (hin, psm 6) and
# each text line with a post word (पार्षद / महापौर) followed by a party name is a member row:
#   "<serial>. [body cell] पार्षद <ward in figures> <ward in words> <name> <party>"
# The ward in words is the surer number (Tesseract reads 11 as ")]" and 12 as "32"). Other lines are kept as text blocks
# ("pre"), so the notice preamble names the body as on a ruled page.
TEXT_POST = re.compile(r"(?:^|\s)(पा\s?(?:र्?)?\s?[षशघ]\S*|महापौर|महापोर)\s+")
FIG = re.compile(r"^[\s(|\[\])}0-9०-९.,:;'\"-]*$")


def text_row(line):
    """A member row from one OCR'd text line: Row([body cell, post, ward figures, ward words, name, party]) or None."""
    t = norm(line)
    mm = TEXT_POST.search(t)
    if not mm:
        return None
    rest = t[mm.end():]
    starts = [m.start() for k, _ in PARTY for m in [re.search(k, rest)] if m]
    if not starts:
        return None
    cut = min(starts)
    party, before = rest[cut:].strip(), rest[:cut].split()
    mayor = mm.group(1).startswith("महा")
    fig = words = ""
    before = [w for w in before if re.search(r"[ऀ-ॿA-Za-z0-9]", w.replace("।", "").replace("॥", ""))]
    if not mayor:
        for i, tok in enumerate(before[:3]):
            if word_num(tok):
                words, fig, before = tok, " ".join(before[:i]), before[i + 1:]
                break
        else:
            if before and FIG.match(before[0]):
                fig, before = before[0], before[1:]
                # the ward-in-words cell is always there: a word OCR spoilt ("पन्रह") is that cell, not part of the name
                if len(before) >= 3 or (len(before) == 2 and before[0].endswith(".")):
                    before = before[1:]
    name = " ".join(before).strip(" .,:;-|")
    pre = re.sub(r"^[\s0-9०-९.,:;|)\]'\"-]*\S{0,1}[0-9०-९]*[.,]\s*", "", t[:mm.start()]).strip()
    row = Row([pre, mm.group(1), fig, words, name, party])
    row.rl = {"body": 0, "post": 1, "ward": 2, "ward_words": 3, "name": 4}
    return row


def page_text(pdf, page, tmp):
    """The page as blocks like page_cells(), from a whole-page OCR: text runs ("pre") and member lines ("rows")."""
    base = os.path.join(tmp, f"t{page}")
    subprocess.run(["pdftoppm", "-r", "300", "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base], capture_output=True)
    if not os.path.exists(base + ".pgm"):
        return []
    r = subprocess.run(["tesseract", base + ".pgm", "-", "-l", "hin", "--psm", "6"], capture_output=True, text=True, timeout=600)
    os.remove(base + ".pgm")
    out, pre = [], []
    for ln, line in enumerate(r.stdout.splitlines(), 1):
        row = text_row(line)
        if row is None:
            pre.append(line)
            continue
        row.box = None
        row.line = ln
        if pre:
            out.append(("pre", "\n".join(pre)))
            pre = []
        if out and out[-1][0] == "rows":
            out[-1][1].append(row)
        else:
            out.append(("rows", [row]))
    if pre:
        out.append(("pre", "\n".join(pre)))
    return out


def page_blocks(pdf, page, tmp):
    """page_cells(), or page_text() when the grid gives fewer than 3 member rows and the text lines give more."""
    bl = page_cells(pdf, page, tmp)
    rows = [r for kind, v in bl if kind == "rows" for r in v]
    n = len(members(rows, roles(rows))) if rows else 0
    if n >= 3:
        return bl
    tb = page_text(pdf, page, tmp)
    nt = sum(len(v) for kind, v in tb if kind == "rows")
    return tb if nt > n else bl


def read_pages(blocks, body=None):
    """Members of consecutive pages: blocks = [(page, page_cells())]; body = the notice open at the first page (or None).
    Returns [(body, member, page)]."""
    out, since = [], 0                                  # since: rows read since the last preamble
    for page, bl in blocks:
        fixed = next((r.rl for kind, v in bl if kind == "rows" for r in v if getattr(r, "rl", None)), None)
        rl = fixed or roles([r for kind, v in bl if kind == "rows" for r in v])
        tno = 0
        for kind, v in bl:
            if kind == "pre":
                b = body_from(v)
                if b:
                    body, since = b, 0
                continue
            tno += 1
            ms = members(v, rl, tno)
            # a table that starts again at ward 1 with no preamble read before it: a new notice whose preamble the scan lost.
            # Its body cell ("नगर परिषद् X जिला Y", over the first rows) names it; else its rows are left out.
            if ms and since and "1" in (ms[0].get("ward_read"), ms[0].get("ward_words")):
                body, since = body_from_cell(" ".join(m["body_cell"] for m in ms[:4]), body), 0
            elif ms and body and not since and len(re.sub(r"[^क-ह]", "", body["body_local"])) < 2:
                # a preamble whose body name the scan lost ("नगर परिषद् जिला सिवनी", "नगर परिषद् ४२७ जिला कटनी"): the body cell
                # of the first rows names it (Barghat, Ex-427 p. 55; Vijayraghavgarh, Ex-392 p. 12)
                cell = body_from_cell(" ".join(m["body_cell"] for m in ms[:4]), body)
                if cell:
                    cell = dict(cell, district_local=body["district_local"] if cell["district_local"] == cell["body_local"] else cell["district_local"])
                    body = cell
            elif ms and since and body and backwards(ms[0], since):
                body = None                             # numbers run backwards: another notice, its start not read
            if body:
                out += [(body, m, page) for m in ms]
                since += len(ms)
    return sequence(out)


def backwards(m, since):
    """True when a table's first row has a ward number well below the count of rows read in this notice so far (a new
    notice began unseen). The count, not the last number read: OCR reads 19 as 49."""
    try:
        first = int(m.get("ward_words") or m.get("ward_read") or 0)
    except ValueError:
        return False
    return 0 < first < since - 2


def body_from_cell(text, last):
    """The body named in the table's body column, read like a preamble; None if it cannot be read."""
    t = norm(text)
    if not t or not re.search(r"नगर", t):
        return None
    t = re.split(r"[,|]\s*(?!जि)", t)[0]          # "नगर परिषद बेरघाट, पर्रिषद": the cell's repeat after a comma or a stray line
    b = body_from(f"राज्य में {t} के माह {(last or {}).get('month', '')} {(last or {}).get('year', '2022')}")
    return b if b and b["body_local"] else None


def sequence(found):
    """Ward numbers in a notice run 1, 2, 3 ... in table order. OCR reads 1 as 4 or loses a number now and then, so a number
    that breaks the run while the figures or the words say "next" becomes the next number; a lost one too."""
    prev, key = 0, None
    for b, m, _ in found:
        k = (b["body_local"], b["district_local"])
        if k != key:
            prev, key = 0, k
        if m["position"] == "Mayor":
            continue
        # a corporation's first row with no ward and no post word read: the mayor (महापौर is listed first)
        if prev == 0 and b.get("body_type") == "Municipal Corporation" and not m.get("ward_read") and not m.get("ward_words") \
                and not m.get("post_read"):
            m["position"], m["ward_no"] = "Mayor", ""
            continue
        nxt = str(prev + 1)
        if m["ward_no"] == str(prev):                  # the same number twice: the second row is the next ward
            m["ward_no"] = nxt
        if m["ward_no"] != nxt and (nxt in (m.get("ward_read"), m.get("ward_words")) or not m["ward_no"]
                                    or m["ward_no"].replace("4", "1") == nxt       # Tesseract hin reads 1 as 4
                                    or (len(nxt) == 2 and len(m["ward_no"]) == 2 and m["ward_no"][1] == nxt[1]
                                        and m["ward_no"][0] in "34" and nxt[0] == "1")    # ... and 12 as 32 (page text)
                                    or (len(nxt) == 2 and m["ward_no"] == nxt[1] and nxt[0] == "1")):   # ... and 14 as 4
            m["ward_no"] = nxt
        prev = int(m["ward_no"]) if m["ward_no"].isdigit() else prev + 1
    return found


def fetch(p, get):
    if not tools():
        return [], [], "tesseract not available"
    content = tn.stored(p, get)
    src = provenance.file_src(content, p["url"], p["stored"]) if content is not None else None
    files = []
    if content is None:
        r = get(p["url"])
        if r is None or r.content[:5] != b"%PDF-":
            return [], [], "no answer"
        content = r.content
        if int(p.get("first", 1)) == 1:
            files = [(f"councillors/MP/{p.get('slug') or hashlib.sha1(p['url'].encode()).hexdigest()[:16]}.pdf", content,
                      "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "g.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        first, last = int(p.get("first", 1)), int(p.get("last", p.get("first", 1)))
        blocks = [(page, page_blocks(pdf, page, tmp)) for page in range(first, last + 1)]
        # an item that starts mid-notice: the notice's body from the last preamble on the pages before it
        body = None
        lead = blocks[0][1] if blocks else []
        if not (lead and lead[0][0] == "pre" and body_from(lead[0][1])):
            for back in range(first - 1, max(0, first - 4), -1):
                pres = [body_from(v) for kind, v in page_blocks(pdf, back, tmp) if kind == "pre"]
                pres = [b for b in pres if b]
                if pres:
                    body = pres[-1]
                    break
        recs = [record(p, b, m, page) for b, m, page in read_pages(blocks, body)]
    if src:
        for _, d in recs:
            d["src"] = dict(src)
    return recs, files, "" if recs else "no members read"


_LGD = None
LGD_TYPE = {"Municipal Corporation": "Municipal Corporation", "Municipality": "Municipality", "Nagar Parishad": "Town Panchayat"}


def skel(s):
    """Sound key of a Latin name (as civic.skel in DB civic): no vowels after the first letter, aspirates and doubles merged."""
    s = re.sub(r"[^a-z]", "", (s or "").lower())
    s = s.replace("garh", "gad").replace("gadh", "gad")
    s = re.sub(r"([tdkgbpsc])h", r"\1", s)
    s = re.sub(r"[cq]", "k", s)
    s = re.sub(r"[wv]", "b", s).replace("h", "")
    s = s[:1] + re.sub(r"[aeiouy]", "", s[1:])
    return re.sub(r"(.)\1+", r"\1", s)


@functools.lru_cache(maxsize=2048)
def lgd_match(body_local, district_local, btype):
    """The LGD body for an OCR'd Hindi name: the best sound match of the name, with the district as a tie-break.
    Returns [code, name, district, type, wards] or None. OCR slips (बिरसिंहपुर read as विरसिंल्युर) still land on the right body
    when no closer name exists (the district counts a quarter)."""
    import difflib
    import json
    import pathlib
    global _LGD
    if _LGD is None:
        _LGD = json.loads((pathlib.Path(__file__).parent / "cw_mp_lgd.json").read_text())
    ratio = lambda a, b: difflib.SequenceMatcher(None, a, b).ratio()   # noqa: E731

    def sim(x, name, dist=""):              # x: romanised OCR text; name: an LGD name ("Khandwa (East Nimar)": each part)
        parts = [name] + re.findall(r"[^()]+", name) + [x for x in re.split(r"\s+-\s*|\s*-\s+", name) if x != name]   # "Nowrozabad - Khodargama"
        if dist and dist.split()[0].lower() in name.lower() and name.lower() != dist.lower():
            # LGD adds the district to a name two towns share ("Shahpura Dindori", "Pichhore Gwalior"): the name without it
            parts.append(re.sub(re.escape(dist.split()[0]), "", name, flags=re.I).strip(" -"))
        return max(0.6 * ratio(skel(x), skel(p)) + 0.4 * ratio(x.lower(), re.sub(r"[^a-z ]", "", p.lower()).strip())
                   for p in parts if p.strip())
    br, dr = roman(body_local), roman(district_local)
    # districts are a tie-break, not a filter: LGD moved some towns to new districts (New Ramnagar: Satna -> Maihar)
    scored = sorted(((sim(br, r[1], r[2]), sim(dr, r[2]), r) for r in _LGD), key=lambda x: -(x[0] + 0.25 * x[1]
                                                                                       + (0.05 if LGD_TYPE.get(btype) == x[2][3] else 0)))
    if not scored or scored[0][0] < 0.55:
        return None
    # a district the notice names clearly: a body of that district whose name is nearly as close wins (Shahpura of Dindori,
    # not Shahpura of Jabalpur; gap round 2026-11-15)
    if dr and district_local != body_local:      # (a preamble cut that gave no district repeats the body name)
        dists = {r[2] for r in _LGD}
        dbest = max(dists, key=lambda d: sim(dr, d))
        if sim(dr, dbest) >= 0.7 and scored[0][2][2] != dbest:
            inside = [x for x in scored if x[2][2] == dbest and x[0] >= max(0.55, scored[0][0] - 0.15)]
            if inside:
                return inside[0][2]
    return scored[0][2]


def split_body(body_local, district_local):
    """(body, district) of a preamble cut that kept too much: "बड़ौद जिला आगर मालवा" (body and district in one cell),
    "ह॒ गरप़ालिका परिषद गाडरवाड़ा" (the body type in front), "पंरिषद् करेली ह" (a stray letter at the end). Gap round
    2026-11-14: 18 bodies (352 members in civic.councillor) had no LGD code because of these cuts."""
    b, d = body_local or "", district_local or ""
    m = re.search(r"\s+जिं?ला(ँ|ं)?\s+", b)
    if m:
        b, rest = b[:m.start()], b[m.end():]
        if not d or d == body_local or "जि" in d:
            d = rest
    b = re.sub(r"^.*?(प[ंॅ]?रिषद्?|पालिका|निगम)\s+", "", b) if re.search(r"(प[ंॅ]?रिषद्?|पालिका|निगम)\s+\S", b) else b
    b = re.sub(r"\s+\S$", "", b.strip())           # a stray one-letter OCR mark at the end
    return b.strip(" -") or body_local, d.strip() or district_local


# OCR'd preamble names that no sound match reaches, checked by hand against the LGD list (gap round 2026-11-14)
ALIASES = {"कैंटनी": "250979",          # Katni Municipal Corporation (LGD "Murwara - Katni")
           "गाशसिवनी": "251037",        # वारासिवनी, Waraseoni (Balaghat)
           "जुन्नारदेव": "JAMAI",       # Junnardeo Municipality: LGD name "Jamai"
           "फूप": "250683",              # Phuphkalan (Bhind)
           "छनेरा": "250920",            # Chhanera = Harsud (Khandwa; LGD keeps the old name)
           "चैंदिया": "250800", "चंदिया": "250800",   # Chandia (Umaria), not Chand (Chhindwara)
           "बाड़ी": "250961",             # Badi (Raisen), not Bareli
           # ocr-gap round 2026-11-15, each checked on the scan
           "माखन नगर": "250975", "माखननगर": "250975",   # Makhan Nagar = LGD Babai (Narmadapuram), Ex-428 p. 12
           "पांडल्थाखुर्द": "293822", "पाडल्याखुर्द": "293822", "करही पाडल्याखुर्द": "293822",   # Karahi-Padlya Khurd (Khargone), Ex-428 p. 19
           "बरेली": "250962", "बरेलीं": "250962",          # Bareli (Raisen), Ex-426 p. 6
           "नौरोजाबाद": "250803",                           # Nowrozabad - Khodargama (Umaria), Ex-429 p. 18
           "नैनपुर": "248075",                              # Nainpur (Mandla; LGD "Nagar Palika, Nainpur"), not Dhanpuri, Ex-551 p. 2
           "बोड़ा": "250938", "बोडा": "250938",               # Boda (Rajgarh), not Biaora, Ex-432 p. 28
           "छापीहेड़ा": "262992", "छापीहेडा": "262992",       # Chhapiheda (Rajgarh), not Chhapara, Ex-432 p. 35
           "बिछिया": "253171",                              # Bichhiya (Mandla; LGD "Bhuwa Bichhia"), not Bichhua, Ex-551 p. 4
           "पानखेड़ी": "263010", "पानखेडी": "263010"}         # Pankhedi Kalapipal (Shajapur), Ex-428 p. 6


def lgd_of_split(body_local, district_local, btype):
    """The LGD body of a preamble cut (split_body): ALIASES first, then the sound match inside the named district when the
    district is clear (Badod, Agar-Malwa: the open match gave Bairad, Shivpuri), else the open match."""
    import difflib
    lgd_match("", "", "")                    # loads _LGD
    b, d = split_body(body_local, district_local)
    code = ALIASES.get(b)
    if code:
        return next((r for r in _LGD if r[0] == code or (code == "JAMAI" and r[1] == "Jamai")), None)
    dsim = lambda x: difflib.SequenceMatcher(None, skel(roman(d)), skel(x)).ratio()    # noqa: E731
    open_ = lgd_match(b, d, btype)
    if open_ is not None and dsim(open_[2]) >= 0.7:
        return open_
    best = max({r[2] for r in _LGD}, key=dsim)
    if dsim(best) >= 0.8:
        br = roman(b)
        inside = sorted(((difflib.SequenceMatcher(None, skel(br), skel(r[1])).ratio(), r) for r in _LGD if r[2] == best),
                        key=lambda x: -x[0])
        # with an open match at hand the district-scoped one must be clearly good (Mihona: OCR "मिण्ड" is closer to Mandla
        # than to Bhind, and Mandla district has a body Mandla)
        floor = 0.75 if open_ is not None else 0.6
        if inside and inside[0][0] >= floor and (len(inside) == 1 or inside[0][0] - inside[1][0] >= 0.1):
            return inside[0][1]
    return open_


def title(s):
    return " ".join(w.capitalize() for w in s.split())


def record(p, body, m, page):
    alias = ALIASES.get(split_body(body["body_local"], body["district_local"])[0])
    # a body name that still holds its district ("सुसनेर जिला आएर मालवा"): the split reading (the open match gave Seoni-Malwa)
    alias = alias or re.search(r"\sजि\S?ल", body["body_local"])
    lgd = lgd_of_split(body["body_local"], body["district_local"], body["body_type"]) if alias else \
        lgd_match(body["body_local"], body["district_local"], body["body_type"])
    if lgd is None and body["body_local"]:
        lgd = lgd_of_split(body["body_local"], body["district_local"], body["body_type"])
    name_en = lgd[1] if lgd else title(roman(body["body_local"]))
    dist_en = lgd[2] if lgd else title(roman(body["district_local"]))
    slug = re.sub(r"[^a-z0-9]+", "-", f"{name_en}-{dist_en}".lower()).strip("-")
    # the gazette page in the id: two notices tied to one body (a wrong tie, or two lost body names in one district) overwrote
    # each other's rows (Seondha's page tied to Sawer replaced Sawer's own page; Ex-392 p. 12 and Ex-433 p. 28). sql/70 ties a
    # page to its body again where the tie is wrong.
    page_tag = f"gz{p.get('gazette_no') or ''}-p{page}"
    month_year = f"{body['month']} {body['year']}".strip()
    d = {"type": "councillor", "state": "MP", "name": m["name"], "position": m["position"], "ward_no": m["ward_no"] or None,
         "party": m["party"] or m["party_local"] or None, "party_local": m["party_local"], "body": name_en, "body_en": name_en,
         "body_local": body["body_local"], "body_type": body["body_type"], "district": dist_en,
         "district_local": body["district_local"], "lgd_code": lgd[0] if lgd else None,
         "election": f"MP urban body general election {body['year']}", "election_month": month_year,
         "gazette_no": p.get("gazette_no"), "gazette_date": p.get("gazette_date"), "page": page, "url": p["url"],
         "source": "Madhya Pradesh Gazette Extraordinary (State Election Commission notice, section 45)",
         # source trail: the table on the page (1-based, top to bottom), the row in it (1-based) and the row band in PDF points
         "src_pos": {"page": page, **(m.get("_pos") or {})}}
    ward = m["ward_no"] or ("mayor" if m["position"] == "Mayor" else f"p{page}-{hashlib.sha1(m['name'].encode()).hexdigest()[:6]}")
    return f"councillor:MP:{slug}:{ward}:{page_tag}", d
