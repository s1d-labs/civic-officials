"""Shared helpers for the ward and zone offices of the big city corporations (dforms/ward_<city>.py).

Each reader gives the corporation's own zone / ward / division offices and their officers (zonal officers, assistant commissioners,
ward engineers, sanitary and health inspectors, tax officers, town planning, water and sewerage), in the depth of Vonter/city-officials.
record() builds one "dept:ward_<city>:<key>" dept_office record (depts.py fields) with:
  dept "town_body"; level "zone" (an office over a group of wards: zone, circle, borough, prabhag samiti, division) or "ward";
  area = the office's own name as the source writes it ("Central Zone", "Ward 31");
  extra keys: body (the corporation), local_body_code (LGD code of civic.ulb), wards (list of ward numbers as strings, the wards the
  office or officer covers), zone (the zone / circle the office belongs to), wing (from wing_of(post): administration, engineering,
  water, sewerage, sanitation, health, revenue, planning, electrical, horticulture, other), role ("head" for the officer who runs the
  office, else "staff").
wards_of() reads ward lists as the sources write them ("31, 32, 46", "1 to 10", "1-5 & 7", "Ward No. 12").
"""
import re

import provenance
from dforms import _esw

WINGS = (
    ("sewerage", r"\b(sewer\w*|sewage|ugd|under\s*ground\s*drainage|drainage|stp|nala)\b"),
    ("water", r"\b(water\s*(supply|works)?|w\.?\s?s\.?|phe|public\s*health\s*engineer\w*|jal\w*|hydraulic\w*|pani|pump\w*)\b"),
    ("planning", r"\b(town\s*planning|t\.?\s?p\.?\s?o\.?|a\.?\s?t\.?\s?p\.?\s?o?|planning|planner|building|architect\w*|"
                 r"nagar\s*rachana|encroachment|anti[\s-]*encroachment)\b"),
    ("revenue", r"\b(revenue|tax\w*|assessment|assessor|bill\s*collector|b\.?\s?c\.?|r\.?\s?i\.?|revenue\s*inspector|kar|"
                r"collection|property)\b"),
    ("sanitation", r"\b(sanitary|sanitation|s\.?\s?i\.?|conservancy|solid\s*waste|swm|swachh\w*|cleanliness|safai)\b"),
    ("health", r"\b(health|medical|m\.?\s?o\.?\s?h\.?|doctor|hospital|vector|malaria|food\s*safety|veterinar\w*)\b"),
    ("electrical", r"\b(electric\w*|street\s*light\w*|lighting)\b"),
    ("horticulture", r"\b(garden\w*|horticultur\w*|park\w*|tree|udyan)\b"),
    ("engineering", r"\b(engineer\w*|e\.?\s?e\.?|a\.?\s?e\.?\s?e?\.?|j\.?\s?e\.?|d\.?\s?e\.?\s?e?\.?|overseer|works|civil|"
                    r"p\.?\s?w\.?\s?d\.?|road\w*|sub\s*engineer)\b"),
    ("administration", r"\b(commissioner|zonal|zone\s*officer|ward\s*officer|ward\s*office|borough|administrat\w*|"
                       r"executive\s*officer|deputy|superintendent|clerk|secretary|officer\s*in\s*charge)\b"),
)
HEAD = re.compile(r"(?i)\b(zonal\s*(officer|commissioner|head)|zone\s*officer|ward\s*officer|assistant\s*commissioner|"
                  r"asst\.?\s*commissioner|deputy\s*commissioner|zonal\s*deputy\s*commissioner|additional\s*commissioner|"
                  r"deputy\s*municipal\s*commissioner|joint\s*commissioner|"
                  r"assistant\s*municipal\s*commissioner|executive\s*officer|borough\s*(executive|officer)|"
                  r"prabhag\s*adhikari|sahayak\s*ayukt|upayukt)\b|सहायक\s*आयुक्त|प्रभाग\s*अधिकारी|क्षेत्रीय\s*अधिकारी|"
                  r"झोनल\s*अधिकारी|उपायुक्त|जोनल\s*अधिकारी")


def wing_of(post):
    """The wing of the corporation that a post belongs to ("Assistant Engineer" -> engineering, "Sanitary Inspector" -> sanitation)."""
    p = _esw.clean(post).lower().replace("_", " ")
    for wing, rx in WINGS:
        if re.search(rx, p):
            return wing
    return "other"


def role_of(post):
    return "head" if HEAD.search(_esw.clean(post)) else "staff"


WARD_WORD = re.compile(r"(?i)\b(ward|wards|w\.?\s?no\.?|ward\s*no\.?|nos?\.?|prabhag|division|div\.?)\b")


def wards_of(text):
    """Ward numbers in a text, as strings, in order, without repeats: "31, 32, 46" -> ["31", "32", "46"], "1 to 5" -> 1..5,
    "1-5 & 7" -> 1..5, 7, "12A" -> ["12A"]. A range of more than 400 is not a ward range and is left out."""
    t = _esw.clean(text)
    t = WARD_WORD.sub(" ", t)
    t = re.sub(r"(?i)\s*(?:to|upto|up\s*to|till|–|—|−|-)\s*(?=\d)", "-", t)
    out = []
    for m in re.finditer(r"(\d{1,3})\s*([A-Za-z](?![A-Za-z]))?(?:-(\d{1,3}))?", t):
        a, suf, b = m.group(1), m.group(2), m.group(3)
        if b and not suf:
            lo, hi = int(a), int(b)
            if lo <= hi and hi - lo <= 400:
                for n in range(lo, hi + 1):
                    if str(n) not in out:
                        out.append(str(n))
                continue
        w = str(int(a)) + (suf.upper() if suf else "")
        if w not in out:
            out.append(w)
    return out


def unique(key, seen):
    k, i = key, 2
    while k in seen:
        k, i = f"{key}:{i}", i + 1
    seen.add(k)
    return k


def record(module, key, seen, *, body, lgd, state, level, area, post, source, name="", phone="", email="", wards=None,
           zone=None, district=None, address=None, wing=None, **extra):
    """(record id, data) for one officer or office of a corporation's zone or ward. seen: keys already used in this answer."""
    post = _esw.clean(post)
    raw = _esw.clean(name)
    name = re.sub(r"(?i)^(vacant|-+|nil|n/?a)\.?$", "", raw)
    w = [str(x) for x in (wards or [])]
    return _esw.record(module, unique(key, seen), dept="town_body", level=level, area=_esw.clean(area), post=post, name=name,
                       phone=_esw.phones(phone) if phone else "", email=_esw.emails(email) if email else "", state=state,
                       district=district, address=_esw.clean(address) or None, body=body, local_body_code=lgd, wards=w or None,
                       zone=_esw.clean(zone) or None, wing=wing or wing_of(post), role=extra.pop("role", None) or role_of(post),
                       vacant=extra.pop("vacant", None) or (True if re.match(r"(?i)vacant", raw) else None),
                       source=source, **extra)


def tag(recs, r, url=None, method=None, pos=None):
    """Source trail for records parsed from one response r of a multi-source item: src_url + src_sha256 (provenance.at), and
    method / src_pos when given and the record has none yet. Returns recs."""
    src = provenance.at(r, url)
    for _, d in recs:
        for k, v in src.items():
            d.setdefault(k, v)
        if method:
            d.setdefault("method", method)
        if pos:
            d.setdefault("src_pos", pos)
    return recs


def pdf_lines(pages):
    """[(page, line, text)] of PDF page texts: 1-based page, 1-based line of that page's text split at line ends."""
    return [(pn, ln, t) for pn, pg in enumerate(pages, 1) for ln, t in enumerate(pg.splitlines(), 1)]


def joined_at(pages):
    """For each line of "\n".join(pages).splitlines() (the joined text some readers parse): (page, line in that page), both
    1-based (source trail)."""
    text = "\n".join(pages).replace("\f", "\n")
    ends, n = [], 0
    for pg in pages:
        n += len(pg) + 1
        ends.append(n)
    out, off, pn = [], 0, 0
    for ln in text.splitlines(True):
        while pn < len(ends) - 1 and off >= ends[pn]:
            pn += 1
        start = ends[pn - 1] if pn else 0
        out.append((pn + 1, text.count("\n", start, off) + 1))
        off += len(ln)
    return out


def grid_pos(table, **kw):
    """[(row, src_pos)] of _esw.grid(table): each row with its {"table", "row"} (source trail)."""
    pos = []
    g = _esw.grid(table, pos=pos, **kw)
    return list(zip(g, pos))


def nth(tag, selector=None):
    """src_pos of an element: {"selector": "div.prof-card", "index": its place among the page's elements of that tag and first
    class (1-based, document order)}."""
    cls = (tag.get("class") or [None])[0]
    n = len(tag.find_all_previous(tag.name, class_=cls) if cls else tag.find_all_previous(tag.name)) + 1
    return {"selector": selector or (f"{tag.name}.{cls}" if cls else tag.name), "index": n}


def tr_pos(tr):
    """src_pos {"table", "row"} of one <tr> (the same numbers as _esw.grid(pos=) and officials.tables give)."""
    t = tr.find_parent("table")
    if t is None:
        return nth(tr)
    own = [x for x in t.find_all("tr") if x.find_parent("table") is t]
    return {"table": _esw.table_no(t), "row": next((i for i, x in enumerate(own, 1) if x is tr), None)}


class Row(dict):
    """A table row dict (header -> cell) that also carries its src_pos as an attribute (not a key: readers walk the items)."""
    pos = None


def header_tables(html, *words, soup=None):
    """[(heading cells, [row dict heading -> cell])] of every table that has a row holding all the words (case-insensitive) in its
    cells: that row is the heading, the rows below it are the data. rowspan / colspan are carried (_esw.grid).
    Each row is a Row: row.pos is its src_pos {"table", "row"}."""
    soup = soup or _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        for i, r in enumerate(g):
            low = [c.lower() for c in r]
            if all(any(w.lower() in c for c in low) for w in words):
                head = [_esw.clean(c) for c in r]
                rows = []
                for row, ps in zip(g[i + 1:], pos[i + 1:]):
                    if any(_esw.clean(c) for c in row):
                        d = Row(zip(head, [_esw.clean(c) for c in row]))
                        d.pos = ps
                        rows.append(d)
                out.append((head, rows))
                break
    return out


def col(row, *words):
    """The cell of a row dict whose heading has one of the words (first match, case-insensitive)."""
    for w in words:
        for k, v in row.items():
            if w.lower() in k.lower():
                return v
    return ""


# Hindi posts of the UP / MP / Rajasthan / Bihar corporations -> English (first match wins: longer posts first). hi_post() returns
# the English post; the reader keeps the Hindi as post_regional.
HI_POSTS = (
    (r"अपर\s*नगर\s*आयुक्त", "Additional Municipal Commissioner"), (r"उप\s*नगर\s*आयुक्त", "Deputy Municipal Commissioner"),
    (r"सहायक\s*नगर\s*आयुक्त", "Assistant Municipal Commissioner"), (r"जोनल\s*सैनेट्री\s*अधिकारी|जोनल\s*स्वच्छता\s*अधिकारी|"
                                                                        r"जेड0?\s*एस0?\s*ओ0?|ZSO", "Zonal Sanitary Officer"),
    (r"जोनल\s*प्रभारी", "Zonal Officer (in charge)"), (r"जोनल\s*अधिकारी|क्षेत्रीय\s*अधिकारी", "Zonal Officer"),
    (r"कर\s*निर्धारण\s*अधिकारी", "Tax Assessment Officer"), (r"कर\s*अधीक्षक", "Tax Superintendent"), (r"राजस्व\s*निरीक्षक", "Revenue Inspector"),
    (r"कर\s*निरीक्षक", "Tax Inspector"), (r"प्र0\s*अधि0\s*अभि(?:यं?(?:न्)?ता|0)", "Executive Engineer (in charge)"),
    (r"अधि0\s*अभि(?:यं?(?:न्)?ता|0)|अधिशा[षस]ी\s*अभियं?(?:न्)?ता", "Executive Engineer"),
    (r"सहायक\s*अभि(?:यं?(?:न्)?ता|0)", "Assistant Engineer"),
    (r"अवर\s*अभि(?:यं?(?:न्)?ता|0)|अ0\s*अभि0|कनिष्ठ\s*अभियं?(?:न्)?ता", "Junior Engineer"),
    (r"एस0?\s*एफ0?\s*आई0?|सफाई\s*(?:एवं\s*)?खाद्य\s*निरीक्षक|SFI", "Sanitary and Food Inspector"),
    (r"सफाई\s*निरीक्षक|स्वच्छता\s*निरीक्षक", "Sanitary Inspector"), (r"सफाई\s*नायक|सफाई\s*सुपरवाइजर", "Sanitation Supervisor"),
    (r"स्वास्थ्य\s*अधिकारी", "Health Officer"), (r"प्रकाश\s*निरीक्षक", "Lighting Inspector"), (r"उद्यान\s*सुपरवाइजर", "Garden Supervisor"),
    (r"उद्यान\s*अधीक्षक", "Garden Superintendent"), (r"कंप्यूटर\s*ऑपरेटर", "Computer Operator"), (r"प्रभारी\s*अधिकारी", "Officer in Charge"),
    (r"अभियं?(?:न्)?ता", "Engineer"),
)


def hi_norm(s):
    """Hindi in one spelling: nukta letters (ज़ as one code point or ज + ़) without the nukta, Devanagari digits / ० as ASCII."""
    s = _esw.clean(s).replace("ज़", "ज").replace("फ़", "फ").replace("़", "")
    return s.translate(str.maketrans("०१२३४५६७८९", "0123456789"))


def hi_post(post):
    p = hi_norm(post)
    for rx, en in HI_POSTS:
        if re.search(rx, p):
            return en
    return _esw.clean(post)


def layout_pages(content):
    """Text of each PDF page in layout mode: pdftotext -layout (poppler; keeps the table columns where the heading puts them),
    else pypdf layout mode (_esw.pdf_pages)."""
    import shutil
    import subprocess
    if shutil.which("pdftotext"):
        try:
            out = subprocess.run(["pdftotext", "-layout", "-", "-"], input=content, capture_output=True, timeout=120).stdout
            pages = out.decode("utf-8", "replace").split("\f")
            if any(p.strip() for p in pages):
                return pages
        except (OSError, subprocess.SubprocessError):
            pass
    return _esw.pdf_pages(content)
