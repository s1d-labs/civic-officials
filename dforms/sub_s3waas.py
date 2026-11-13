"""Tehsil / taluk / block / sub-division / circle offices listed on S3WaaS district portals: "Public Utilities -> Tehsil / Tehsils /
Blocks / Block / SDM / Sub-divisional offices / Tahasil offices / Vikas Khand" pages (Kaushambi, Raigad, Sangrur, Samba, Azamgarh,
Mirzapur ...). One card per office (heading, address, "Phone :", "Email :", "Pincode :"), read with dforms/police_s3waas.cards()
(imported, not changed), paged with /page/N/ (dforms/_civic.s3waas_pages). The cards give the office phone and email, almost never
the officer's name.

The payload gives "kind" (tehsil | block | subdivision | circle), found from the category slug when the seed was made; the card
heading gives the area ("Chail Tehsil" -> Chail, "Block – Andana at Moonak" -> Andana at Moonak, "SDM GHAGWAL" -> Ghagwal).
Record fields: dept revenue (tehsil, circle), rural_development (block), administration (subdivision); level subdistrict / block /
subdivision; post = the officer who heads the office (Tahsildar, Block Development Officer, Sub-Divisional Magistrate, Circle Officer;
"Sub-Divisional Magistrate" for a tehsil card whose email starts with "sdm", as in Uttar Pradesh where the SDM heads the tehsil).
Seed: seeds/dept_sub_s3waas.json: the category pages that archive.s1d.me holds (keys "sub_s3waas-<host>-<kind>"), and one
"discover" item for every other district portal in sites.csv (keys "sub_s3waas-<host>"): it reads the home page, finds the linked
tehsil / block / sub-division / circle categories (categories()) and reads them; "no tehsil or block categories" when there are none.
Record ids: dept:sub_s3waas:<host>:<kind>:<slug of area>.
Fallback (2026-11-13): a discover item whose home page links no such category (655 of 1,391 failed items: the portal has only
the default banks / hospitals / schools ... categories) reads the portal's own pages that the home page links by path:
"Tehsil", "Subdivision & Blocks", "Mandals", "Taluka", "Blocks", "Sub-Division", "Administrative Setup" ... (PAGE_PATH).
Their tables are read by header words (dforms/_field.header_kind: name, post, area, phone, email, address); the kind of each
row comes from its post, then the column headers, the table caption and the page path (ROW_KINDS); a row of no kind (a judge,
a department list) is left out. A table with one phone column per post ("Tehsil | SDM Mobile No. | Tehsildar Mobile No.")
gives one record per post. Pages that field_revenue_s3waas already reads (seeds/dept_field_revenue_s3waas.json) are skipped.
Record ids of these rows: dept:sub_s3waas:<host>:page:<kind>:<slug of area> (a serial suffix when an area repeats). Until
2026-11-13 they had the ids of the category cards (no "page:"): a portal with both (Gadwal: /tehsil/ cards, /mandals/ table of
tahsildars) lost the names and mobiles of one of the two to the other item's write (7 of 14 mandals; found by the reader audit).
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from dforms import _civic, _esw
from dforms.police_s3waas import cards, last_updated
import provenance

METHOD = ("html cards (S3WaaS public utility, .public-utlty-catg; /page/N/ pages); fallback: html tables of the portal's "
          "tehsil / sub-division / block pages, columns by header words")     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_s3waas"

KIND = {
    "tehsil": ("revenue", "subdistrict", "Tahsildar"),
    "circle": ("revenue", "subdistrict", "Circle Officer"),
    "block": ("rural_development", "block", "Block Development Officer"),
    "subdivision": ("administration", "subdivision", "Sub-Divisional Magistrate"),
}
# words that name the office, not the place (English, Hindi, Marathi, Punjabi); removed from the card heading
OFFICE_WORDS = re.compile(
    r"(?i)\b(tehsil|tahsil|tahasil|tehsils|taluka?|block|blocks|office|offices|sdm|s\.d\.m\.?|sdo|s\.d\.o\.?|bdo|b\.d\.o\.?|"
    r"sub[- ]?divisional|sub[- ]?division|magistrate|officer|development|vikas\s*khand|vikaskhand|circle|anchal|prakhand|karyalay|"
    r"civil|revenue|mandal)\b\.?|तहसील|कार्यालय|विकास\s*खण्ड|विकास\s*खंड|विकासखण्ड|विकासखंड|ब्लॉक|प्रखंड|अंचल|अनुमंडल|उपविभागीय|"
    r"तहसिल|ਬਲਾਕ|ਤਹਿਸੀਲ|ਦਫਤਰ")


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def area(title):
    """'Chail Tehsil' -> 'Chail'; 'Block – Andana at Moonak' -> 'Andana at Moonak'; 'SDM GHAGWAL' -> 'Ghagwal'."""
    t = OFFICE_WORDS.sub(" ", title or "")
    t = re.sub(r"(?i)^\s*(of|at)\b|\b(of|at)\s*$", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—,.:;()/|")
    if t and (t.isupper() or t.islower()):
        t = t.title()
    return t


def post_of(kind, card):
    dept, level, post = KIND[kind]
    if kind == "tehsil" and re.match(r"(?i)\s*sdm", _esw.deob(card.get("email") or "")):
        post = "Sub-Divisional Magistrate"
    return dept, level, post


def records(pages, p):
    host = urlparse(p["url"]).netloc
    kind = p["kind"]
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    recs, seen = [], set()
    for url, html in pages:
        where = []
        try:
            cs = cards(html, where)
        except TypeError:          # police_s3waas.cards without positions
            cs, where = cards(html), []
        for ci, c in enumerate(cs):
            title = _esw.clean(c.get("title"))
            place = area(title)
            if not place:
                continue
            dept, level, post = post_of(kind, c)
            adr = _esw.clean(c.get("address"))
            m = re.search(r"(?i)(?:contact|phone|mob(?:ile)?|tel)[^:\d]{0,12}:?\s*((?:\+?\d[\d -]{5,}\d[,/ ]*)+)", adr or "")
            key = _civic.unique(f"{host}:{kind}:{_esw.slug(place)}", seen)
            regional = bool(re.search(r"[ऀ-ൿ]", place))
            rec = _esw.record(
                MODULE, key, dept=dept, level=level, area=place, area_regional=place if regional else None,
                office=title, post=post, phone=_esw.phones(c.get("phone") or "", m.group(1) if m else ""),
                email=_esw.emails(c.get("email") or ""), address=adr, pincode=re.sub(r"\D", "", c.get("pincode") or "")[:6],
                district=p.get("district"), state=p.get("state"), office_id=key, source=url, last_updated=lu, src_url=url,
                src_pos=where[ci] if ci < len(where) else {"selector": ".public-utlty-catg"})
            if rec[1].get("phone") or rec[1].get("email"):
                recs.append(rec)
    return recs


# category slugs (URL-decoded) -> kind; checked in this order ("tehsil-sub-division" is a sub-division page, "mandal-parishad" a block)
SLUG_KINDS = [
    ("subdivision", re.compile(r"(sub-?div|subdivision|\bsdm|\bsdo|sdokaryalay|अनुमंडल|उपविभाग|mahakuma|মহকুমা)")),
    ("circle", re.compile(r"(circle|anchal|अंचल)")),
    ("block", re.compile(r"(block|vikas-?kh|विकास-ख|प्रखंड|ब्लॉक|ਬਲਾਕ|ব্লক|\bbdo|panchayat-samiti|पंचायत-समिति|mandal-parishad|mpdo|janpad)")),
    ("tehsil", re.compile(r"(tehsil|tahsil|tahasil|taluk|तहसील|तहसिल|ਤਹਿਸੀਲ|તાલુકા|ತಾಲ್ಲೂಕು|\bmandal)")),
]
SLUG_SKIP = re.compile(r"(transport|परिवहन|போக்குவரத்து|प्राधिकरण|police|thana|court|bank|school|hospital|education|शिक्षा|post|डाक)")


def slug_kind(slug):
    """The kind of a public-utility category slug, or None."""
    from urllib.parse import unquote
    s = unquote(slug).lower()
    if SLUG_SKIP.search(s):
        return None
    return next((k for k, rx in SLUG_KINDS if rx.search(s)), None)


def categories(html, url):
    """Tehsil / block / sub-division / circle category pages linked from a site's home page: [(kind, url)], English first
    (a regional-language page only when the site has no English page of that kind)."""
    from urllib.parse import urljoin
    found = {}
    for m in re.finditer(r'href="([^"]*/public-utility-category/([^/"]+)/?)"', html):
        kind = slug_kind(m.group(2))
        if not kind:
            continue
        u = urljoin(url, m.group(1))
        u = u if u.endswith("/") else u + "/"
        regional = bool(re.search(r"/(hi|pa|bn|te|ta|gu|mr|kn|or|ml|as|mz|mn|kha|grt)/public-utility", u)) or "%" in m.group(2)
        found.setdefault(kind, set()).add((regional, u))
    out = []
    for kind, us in sorted(found.items()):
        eng = sorted(u for r, u in us if not r)
        out += [(kind, u) for u in (eng or sorted(u for _, u in us)[:1])]
    return out


# ---------------------------------------------------------------- fallback: the portal's tehsil / block pages, read as tables
# path of a page the home page links (after the host, an optional language prefix and "about-district/administrative-setup/")
PAGE_PATH = re.compile(
    r"^/(?:about-district/)?(?:administrative-setup/)?((?:sub-?divisions?|subdivisions?|sub-?divisions?-(?:and-)?blocks?|"
    r"subdivisions?-(?:and-)?blocks?|tehsils?|tahsils?|tehsil-[a-z-]+|tah?sildars?[a-z-]*|talukas?|taluks?|blocks?|block-[a-z-]+|"
    r"mandals?|mandal-[a-z-]+|circles?|circle-officers?|sub-divisional-magistrates?|revenue-administration|"
    r"administrative-setup[a-z-]*|district-administration)\d*)/?$")
REGIONAL = re.compile(r"^/(hi|pa|bn|te|ta|gu|mr|kn|or|ml|as|mz|mn|kha|grt)/")
MAX_PAGES = 8
# the kind of a table row: its post first, then the phone / name / area column headers, the caption, the page path
ROW_KINDS = [
    ("subdivision", re.compile(r"(?i)\bs\.?d\.?m\b|sub[- ]?div|subdivision|\bs\.?d\.?o\b|\bprant\b|\br\.?d\.?o\b|revenue divisional|"
                               r"अनुमंडल|उपविभाग|উপবিভাগ|মহকুমা")),
    ("block", re.compile(r"(?i)\bb\.?d\.?o\b|block development|\bm\.?p\.?d\.?o\b|mandal parishad|praja parishad|vikas ?khand|janpad|"
                         r"panchayat samiti|\bblocks?\b|विकास\s*खण्ड|विकास\s*खंड|प्रखंड|ब्लॉक")),
    ("circle", re.compile(r"(?i)circle officer|\banchal\b|\bc\.o\.|अंचल")),
    ("tehsil", re.compile(r"(?i)t[ae]h?a?sh?[ie]ldar|mamlatdar|\bm\.?r\.?o\b|mandal revenue|\btehsils?\b|\btah?sils?\b|"
                          r"\btalukas?\b|\btaluks?\b|\bmandals?\b|तहसील|तहसिल|ਤਹਿਸੀਲ")),
]
POST_NAMES = [
    (r"(?i)\bs\.?d\.?m\b|sub[- ]?divisional magistrate", "Sub-Divisional Magistrate"),
    (r"(?i)\br\.?d\.?o\b|revenue divisional", "Revenue Divisional Officer"), (r"(?i)\bprant\b", "Prant Officer"),
    (r"(?i)\bs\.?d\.?o\b|sub[- ]?divisional officer", "Sub-Divisional Officer"),
    (r"(?i)\bb\.?d\.?o\b|block development", "Block Development Officer"),
    (r"(?i)\bm\.?p\.?d\.?o\b|mandal parishad development|praja parishad", "Mandal Parishad Development Officer"),
    (r"(?i)circle officer", "Circle Officer"), (r"(?i)mamlatdar", "Mamlatdar"),
    (r"(?i)\bm\.?r\.?o\b|mandal revenue", "Mandal Revenue Officer"), (r"(?i)naib[- ]?tah?s[ie]ldar", "Naib Tahsildar"),
    (r"(?i)t[ae]h?a?sh?[ie]ldar", "Tahsildar"),
]
# a "name" column whose header names an office or a place, not a person ("Name of Sub Division", "Office", "Name of the Mandals")
PLACE_NAME_HEAD = re.compile(r"(?i)^(name\s+of\s+(the\s+)?)?(sub[- ]?div\w*|tehsils?|tah?sils?|talukas?|taluks?|mandals?|blocks?|"
                             r"divisions?|offices?|circles?|ulbs?|municipalit\w*)(\s+name)?s?$|^office( name)?$")
OFFICE_HEAD = re.compile(r"(?i)^(office|offices|office name|name of (the )?office)$")     # header_kind() maps none of these
NOT_OFFICE_TABLE = re.compile(r"(?i)scheme|website|department|court|bank|l\.\s?r\.\s?s|sakha")   # a scheme / court / LRS list


def page_links(html, url):
    """English pages of the same portal that the home page links by a tehsil / block / sub-division path: [url] (at most MAX_PAGES),
    without pages that field_revenue_s3waas reads."""
    from urllib.parse import urljoin
    host = urlparse(url).netloc
    try:
        taken = set(re.findall(r'"(https?://[^"]+)"', (Path(__file__).resolve().parent.parent / "seeds" /
                                                        "dept_field_revenue_s3waas.json").read_text()))
    except OSError:
        taken = set()
    out = []
    for m in re.finditer(r'href="([^"#?]+)"', html or ""):
        u = urljoin(url, m.group(1).replace("&amp;", "&"))
        pu = urlparse(u)
        if pu.netloc != host or REGIONAL.match(pu.path) or not PAGE_PATH.match(pu.path):
            continue
        u = u if u.endswith("/") else u + "/"
        if u not in out and u not in taken and u.rstrip("/") + "/" != url.rstrip("/") + "/":
            out.append(u)
    return out[:MAX_PAGES]


def _post_in(text):
    return next((pp for rx, pp in POST_NAMES if re.search(rx, text or "")), None)


def _kind_in(*texts):
    for t in texts:
        for k, rx in ROW_KINDS:
            if t and rx.search(t):
                return k
    return None


def _area_of(s):
    s = re.sub(r"^\s*\d{1,3}\s*[.)]\s*", "", _esw.clean(s))
    for rx, _ in POST_NAMES:
        s = re.sub(rx, " ", s)
    return area(s)


def _phoneish(vals):
    """True when most non-empty cells of a column are phone numbers (a column headed by a post: "Tehsil | SDM | Tehsildar")."""
    vals = [v for v in vals if v]
    return bool(vals) and sum(1 for v in vals if _esw.phones(v) and len(re.sub(r"[\d\s,+()/-]", "", v)) < 4) * 2 > len(vals)


def _columns(head, body):
    """{field: column} from the header words (dforms/_field.header_kind), "phones": [columns], "emails": [columns], or None.
    A column headed by a post whose cells are phone numbers is a phone column. Needs a phone or email or name column and an
    area, office, name or post column."""
    from dforms import _field
    cols, names, phones, emails = {}, [], [], []
    for i, h in enumerate(head):
        hc = _esw.clean(h).strip(" :.")
        k, _ = _field.header_kind(hc)
        colvals = [r[i] if i < len(r) else "" for r in body]
        if k == "phone" or (k in (None, "name", "post", "tehsil", "block", "circle") and _post_in(hc) and _phoneish(colvals)):
            phones.append(i)
        elif k == "email":
            emails.append(i)
        elif OFFICE_HEAD.match(hc):
            cols.setdefault("office", i)
        elif k == "name":
            if PLACE_NAME_HEAD.match(hc):
                cols.setdefault("place", i)
            else:
                names.append((bool(_field.PERSON_HEAD.search(hc)), i))
        elif k in ("area", "circle", "block", "tehsil"):
            cols.setdefault("place" if k == "area" else k, i)
        elif k in ("post", "address", "sno"):
            cols.setdefault(k, i)
    if names:
        cols["name"] = sorted(names, key=lambda x: (not x[0], x[1]))[0][1]
    cols["phones"], cols["emails"] = phones, emails
    if not (phones or emails or "name" in cols):
        return None
    if not ({"place", "office", "name", "post", "tehsil", "block", "circle"} & set(cols)) or len(set(cols) - {"phones", "emails", "sno"}) + bool(phones) + bool(emails) < 2:
        return None
    return cols


def _tables(html):
    """[(head, rows, caption, positions)] of the page's tables. A table with no usable header among its first 3 rows but rows
    "post - place | phone, email" gets the header ["Office", "Contact"] (Sheikhpura: "Block Development Officer – Barbigha")."""
    soup = _esw.soup(html)
    out = []
    for table in soup.find_all("table"):
        pos = []
        g = _esw.grid(table, pos=pos)
        if len(g) < 2:
            continue
        cap = table.find("caption")
        cap = _esw.clean(cap.get_text(" ")) if cap else ""
        if not cap:
            h = table.find_previous(["h2", "h3", "h4", "h5", "strong"])
            cap = _esw.clean(h.get_text(" ")) if h else ""
        hi = next((i for i, r in enumerate(g[:3]) if _columns(r, g[i + 1:])), None)
        if hi is not None:
            out.append((g[hi], g[hi + 1:], cap[:120], pos[hi + 1:]))
        elif all(len(r) >= 2 for r in g) and sum(1 for r in g if _post_in(r[0]) and (_esw.phones(*r[1:]) or _esw.emails(" ".join(r[1:])))) >= 2:
            out.append((["Office"] + ["Contact"] * (max(len(r) for r in g) - 1), g, cap[:120], pos))
    return out


def table_records(html, url, p):
    """Records of the tehsil / sub-division / block rows in the tables of one portal page (see the module doc)."""
    from dforms import _field
    host = urlparse(url).netloc
    path = urlparse(url).path
    lu = _field.last_updated(html) or last_updated(html)
    recs, seen = [], set()
    for head, body, cap, poss in _tables(html):
        cols = _columns(head, body)
        if head[0] == "Office" and cols is None:
            cols = {"office": 0, "phones": list(range(1, len(head))), "emails": list(range(1, len(head)))}
        if not cols:
            continue
        name_head = head[cols["name"]] if "name" in cols else ""
        if NOT_OFFICE_TABLE.search(name_head + " " + " ".join(head[cols[k]] for k in ("place", "office") if k in cols)):
            continue
        for row, pos in zip(body, poss):
            if [c.lower() for c in row] == [c.lower() for c in head] or (len(row) > 1 and len({c for c in row if c}) == 1):
                provenance.skip_row(row, 'skip: [c.lower() for c in row] == [c.lower() for c in head] or (len(row) ...')
                continue                   # a repeated header, or a section row ("Nizamabad Division" in every cell)

            def cell(k):
                i = cols.get(k)
                return _esw.clean(row[i]) if i is not None and i < len(row) else ""
            name, npost = _field.split_name(cell("name"))
            if name and _esw.clean(name_head).lower().strip(" :.") == "name" and "place" not in cols and \
                    re.fullmatch(r"[A-Za-z]+", name) and not cell("post"):
                cols_place, name = name, ""          # a bare "Name" column of one-word places (Ayodhya: "Masodha", "Sohawal")
            else:
                cols_place = ""
            name = re.sub(r"^\d+[.)]\s*", "", name)
            if _field.is_post_text(name) and not npost:
                npost, name = name, ""
            if _field.NOT_NAME.match(name) or re.fullmatch(r"[\d\s.,/-]*", name):
                name = ""
            office = cell("office")
            place = cell("place") or cols_place or next((cell(f) for f in ("circle", "block", "tehsil") if cell(f)), "") or office
            post_cell = cell("post") or npost
            # one record per phone column that names its own post ("SDM Mobile No.", "Tehsildar Mobile No."), else one record
            posted = [(i, _post_in(head[i])) for i in cols["phones"]]
            split = len(posted) > 1 and len({pp for _, pp in posted if pp}) > 1
            groups = [(pp, [i]) for i, pp in posted if pp] if split else [(None, cols["phones"])]
            for gpost, pcols in groups:
                phone = _esw.phones(*[row[i] for i in pcols if i < len(row)])
                email = _esw.emails(" ".join(row[i] for i in (cols["emails"] or pcols) if i < len(row)))   # "phone, email" cells
                if not (name or phone or email):
                    continue
                phead = " ".join(head[i] for i in pcols)
                post = post_cell or gpost or _post_in(office) or _post_in(phead) or _post_in(name_head) or _post_in(cap) or None
                kind = _kind_in(post_cell, gpost, office, phead, name_head, *(head[cols[k]] for k in ("place", "tehsil", "block",
                                                                                                    "circle") if k in cols), cap)
                if not kind and (phone or email) and not post_cell:
                    kind = _kind_in(path.replace("-", " "))      # the page path alone names the kind only of a row with a contact
                if not kind:
                    continue
                dept, level, dpost = KIND[kind]
                post = post or dpost
                src = office if office and not cell("place") else post_cell
                where = _area_of(place if place != office else "") or _area_of(
                    re.sub(r"(?i)^.*?(officer|magistrate|tah?s[ie]ldar|mamlatdar|prant|office)\b[\s,.–-]*", "", src or ""))
                key = _civic.unique(f"{host}:page:{kind}:{_esw.slug(where) or 'row'}", seen)
                regional = bool(re.search(r"[ऀ-ൿ]", where or ""))
                recs.append(_esw.record(
                    MODULE, key, dept=dept, level=level, area=where, area_regional=where if regional else None, post=post,
                    name=name, phone=phone, email=email, address=cell("address"), office=office or None,
                    district=p.get("district"), state=p.get("state"), office_id=key, source=url, last_updated=lu,
                    caption=cap or None, table_row={h: c for h, c in zip(head, row) if h and c} or None, src_url=url,
                    src_pos=pos, method="html table (portal page; columns by header words)"))
    return recs


def fallback(p, home_html, get):
    """(records, files, pages read) from the portal pages that page_links() finds on the home page."""
    host = urlparse(p["url"]).netloc
    recs, files, n = [], [_esw.keep(MODULE, f"{host}-home", home_html)], 0     # the home page: the source of the links
    for u in page_links(home_html, p["url"]):
        r = get(u)
        if r is None:
            continue
        n += 1
        files.append(_esw.keep(MODULE, f"{host}-{_esw.slug(urlparse(u).path)[-60:]}", r.content))
        got = table_records(r.text, u, p)
        ids = {k for k, _ in recs}
        recs += [(k, d) for k, d in got if k not in ids]
    return recs, files, n


def fetch(p, get):
    if p.get("discover"):
        # one item per district portal: read the home page, then every tehsil / block / sub-division category it links
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        cats = categories(r.text, p["url"])
        recs, files = [], []
        for kind, u in cats:
            pages, fs = _civic.s3waas_pages({**p, "url": u}, get, MODULE)
            if pages:
                recs += records(pages, {**p, "url": u, "kind": kind})
                files += fs
        if recs:
            return recs, files, ""
        # no category, or categories without cards: the portal's own tehsil / sub-division / block pages
        frecs, ffiles, n = fallback(p, r.text, get)
        files += ffiles
        if frecs:
            return frecs, files, ""
        if not cats:
            return [], files, "no tehsil or block categories" + (f"; no office table on {n} tehsil / block pages" if n else "")
        return [], files, "no cards"
    pages, files = _civic.s3waas_pages(p, get, MODULE)
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
