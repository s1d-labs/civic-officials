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
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from dforms import _civic, _esw
from dforms.police_s3waas import cards, last_updated

METHOD = "html cards (S3WaaS public utility, .public-utlty-catg; /page/N/ pages)"     # source trail (provenance.py): how this reader reads its sources

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


def fetch(p, get):
    if p.get("discover"):
        # one item per district portal: read the home page, then every tehsil / block / sub-division category it links
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        cats = categories(r.text, p["url"])
        if not cats:
            return [], [], "no tehsil or block categories"
        recs, files = [], []
        for kind, u in cats:
            pages, fs = _civic.s3waas_pages({**p, "url": u}, get, MODULE)
            if pages:
                recs += records(pages, {**p, "url": u, "kind": kind})
                files += fs
        return recs, files, "" if recs else "no cards"
    pages, files = _civic.s3waas_pages(p, get, MODULE)
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
