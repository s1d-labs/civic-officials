"""Andhra Pradesh: Tahsildar (MRO), MPDO and RDO of every mandal / revenue division, from the "Administrative Setup" pages of the 28
district portals (<district>.ap.gov.in, S3WaaS). No state-wide list with names was found (CCLA, PR&RD, APSDMA and the CEO's AERO
gazettes give posts only, see the report); these pages are one template on one platform, so one queue item per district.

Structure: the menu of every page links "Administrative Setup" pages: "MANDALS LIST" / "Mandals" / "Tehsil" (Tahsildar or MRO per
mandal, often only the CUG mobile, e.g. Prakasam /tehsil/: Division, Sl.No, Mandal, Designation, mobile), "MPDO LIST" / "MPDOs"
(Mandal, MPDO name, mobile, e-mail: Anakapalli /mpdos/, Annamayya /mpdo/) and "Revenue Divisions" / "Subdivision & Blocks" (RDO
name, mobile, e-mail: Ananthapuramu /subdivision-blocks/). Slugs and column orders differ per district: the reader finds the pages
by the menu link text and the columns by the header words. A page that only lists mandal names gives no record.
Who's Who / Contact Directory pages and public-utility categories are left out: whoswho.py and dforms/sub_s3waas.py read them;
the /tehsil/ pages in seeds/dept_field_revenue_s3waas.json are left out too (that reader has them).

One queue item = one district: 1 GET (home page, for the menu) + 1 GET per linked page (2-6). About 28 items, 60-150 requests.
The same reader serves Telangana (dforms/sub2_tg.py) and Karnataka (dforms/sub2_ka.py) with their own hosts and words.
Records: dept revenue / rural_development / administration, level subdistrict / block / subdivision, area = the mandal / division
as the page spells it ("MRO LRPalle" -> "LRPalle"). Ids: dept:sub2_ap:<host>:<level>:<slug of area>[:n].
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dforms import _esw
import provenance

METHOD = "html table (district portal pages from its menu)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_ap"
STATE = "AP"
# host -> LGD district name (lgd.districts, state 28)
HOSTS = {
    "allurisitharamaraju.ap.gov.in": "Alluri Sitharama Raju", "anakapalli.ap.gov.in": "Anakapalli",
    "ananthapuramu.ap.gov.in": "Ananthapuramu", "annamayya.ap.gov.in": "Annamayya", "bapatla.ap.gov.in": "Bapatla",
    "chittoor.ap.gov.in": "Chittoor", "eastgodavari.ap.gov.in": "East Godavari", "eluru.ap.gov.in": "Eluru",
    "guntur.ap.gov.in": "Guntur", "kadapa.ap.gov.in": "Y.S.R. Kadapa", "kakinada.ap.gov.in": "Kakinada",
    "konaseema.ap.gov.in": "Dr. B.R. Ambedkar Konaseema", "krishna.ap.gov.in": "Krishna", "kurnool.ap.gov.in": "Kurnool",
    "markapuram.ap.gov.in": "Markapuram", "nandyal.ap.gov.in": "Nandyal", "ntr.ap.gov.in": "Ntr", "palnadu.ap.gov.in": "Palnadu",
    "parvathipurammanyam.ap.gov.in": "Parvathipuram Manyam", "polavaram.ap.gov.in": "Polavaram", "prakasam.ap.gov.in": "Prakasam",
    "spsnellore.ap.gov.in": "Sri Potti Sriramulu Nellore", "srikakulam.ap.gov.in": "Srikakulam",
    "srisathyasai.ap.gov.in": "Sri Sathya Sai", "tirupati.ap.gov.in": "Tirupati", "visakhapatnam.ap.gov.in": "Visakhapatnam",
    "vizianagaram.ap.gov.in": "Vizianagaram", "westgodavari.ap.gov.in": "West Godavari",
}

# page kinds: (level, dept, default post, pattern on link text / slug / table caption)
KINDS = {
    "block": ("rural_development", "Mandal Parishad Development Officer",
              r"\bm\.?\s?p\.?\s?d\.?\s?o|mandal\s*parishad|mandal[\s-]*praja[\s-]*parishad|panchayat\s*samit|"
              r"taluk[a]?[\s-]*panchaya|\btp\s*eo|t\.p\.\s*e\.?o"),
    "subdivision": ("administration", "Revenue Divisional Officer",
                    r"revenue[\s-]*div|sub[\s-]*division|\brdos?\b|r\.d\.o|divisional\s*officer|sub[\s-]*collector|"
                    r"assistant[\s-]*commissioner"),
    "subdistrict": ("revenue", "Tahsildar", r"tah?si?ldar|tehsil|tahsil|\bmros?\b|m\.r\.o|mandal\s*revenue|mandals?\b|"
                    r"taluk[a]?(\s*office)?s?\b"),
}
# designation in a row -> level (a row's own post wins over the page kind)
POST_LEVEL = [("block", r"\bm\.?\s?p\.?\s?d\.?\s?o\b|mandal\s*parishad\s*development|mandal\s*praja\s*parishad|"
                        r"executive\s*officer.*taluk|taluk.*executive\s*officer|\bt\.?\s?p\.?\s?e\.?\s?o\b|block\s*development"),
              ("subdivision", r"revenue\s*divisional|\brdo\b|r\.d\.o|sub[\s-]*collector|assistant\s*commissioner|\bsdm\b"),
              ("subdistrict", r"tah?si?ldar|tehsildar|\bmro\b|m\.r\.o|mandal\s*revenue\s*officer|mamlatdar")]
SKIP_LINK = re.compile(r"whos?-?who|contact-directory|/directory|public-utility|/notice|/document|/gallery|/tender|/event|"
                       r"/te/|/kn/|/hi/|\.pdf$|\.jpe?g$|police|educat|\bmeo\b|school|mpdo-rti|tahsildars-rti|rdos-rti|"
                       r"rti-|-rti|-41b|4-1-b|pin-?codes|villages?/?$|mandals?-and-villages|mandals?-villages|municipal|\bmaps?\b|-maps?\b|"
                       r"gram[a]?[\s-]*panchay|grama?-panchay|sarpanch|panchayat-secretar", re.I)
SKIP_ROW = re.compile(r"municipal|corporation|zonal|\bzone\b|nagar\s*panchayat|\bgvmc\b|\bghmc\b|\bulb\b|\btotal\b", re.I)
MC = re.compile(r"^\s*m\.?\s?c\.?\s*$|^\s*m\.?\s?p\.?\s?o\.?\s*$|mandal\s*panchayat\s*officer", re.I)
VACANT = re.compile(r"^(vacant|-+|nil|na|n/a|\.+|fac|f\.a\.c)$", re.I)
NAME_HEAD = re.compile(r"officer|mpdo|m\.p\.d\.o|tahsildar|tehsildar|\bmro\b|rdo|incumbent|official|commissioner|executive|"
                       r"employee|person|^name$|^names?\s*$|^name\s*\(", re.I)
AREA_HEAD = re.compile(r"mandal|division|taluk|tehsil|tahsil|block|municipal|area|place|office|circle|jurisdiction|"
                       r"head\s*quarters|hq", re.I)
OFFICE_WORDS = re.compile(r"(?i)\bo/o\b|\b(mro|m\.r\.o\.?|mpdo|m\.p\.d\.o\.?|tahsildar|tahasildar|tehsildar|rdo|r\.d\.o\.?|office(r)?|"
                          r"of\s+the|mandal(am)?|revenue|division(al)?|parishad|development|praja|taluk(a)?|panchayat|executive|"
                          r"block|tehsil|tahsil|sub[\s-]*division|sub[\s-]*collector|assistant|commissioner)\b\.?")


def items(get=None, module=MODULE, hosts=None, state=STATE, path=""):
    """One item per district portal (path "en/" where the home page is in the regional language and the English menu is under
    /en/, as on the Karnataka portals)."""
    hosts = hosts or HOSTS
    return [{"key": f"{module}-{h.split('.')[0]}", "payload": {"reader": module, "url": f"https://{h}/{path}", "host": h,
                                                               "district": d, "state": state, "india_only": True}}
            for h, d in hosts.items()]


_TAKEN = None


def taken():
    """Page urls that dforms/field_revenue_s3waas.py already reads (from its seed file), without the scheme and final slash."""
    global _TAKEN
    if _TAKEN is None:
        _TAKEN = set()
        f = Path(__file__).resolve().parent.parent / "seeds" / "dept_field_revenue_s3waas.json"
        try:
            for s in json.loads(f.read_text()):
                u = (s.get("payload") or {}).get("url") or ""
                _TAKEN.add(norm_url(u))
        except (OSError, ValueError):
            pass
    return _TAKEN


def norm_url(u):
    p = urlparse(u or "")
    return (p.netloc.lower().split(":")[0] + p.path.rstrip("/")).lower()


def kind_of(text):
    """Page kind from a link text, slug or caption: block (MPDO) first, then subdivision (RDO), then subdistrict (Tahsildar)."""
    for k in ("block", "subdivision", "subdistrict"):
        if re.search(KINDS[k][2], text or "", re.I):
            return k
    return None


def links(html, url, host, kinds=None):
    """[(url, kind, link text)] of the menu pages that list mandal / division officers, same host, in page order."""
    kinds = kinds or KINDS
    english = urlparse(url).path.startswith("/en/")       # Karnataka: keep to the English pages, not their Kannada twins
    soup = _esw.soup(html)
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"].strip())
        pu = urlparse(href)
        if pu.netloc.split(":")[0].lower() != host or pu.query or pu.path in ("", "/", "/en/", "/en"):
            continue
        if english and not pu.path.startswith("/en/"):
            continue
        text = _esw.clean(a.get_text(" "))
        if SKIP_LINK.search(pu.path) or SKIP_LINK.search(text) or len(text) > 60:
            continue
        k = kind_of(text) or kind_of(pu.path.replace("-", " ").replace("/", " "))
        if not k or k not in kinds:
            continue
        n = norm_url(href)
        if n in seen or n in taken():
            continue
        seen.add(n)
        out.append((href.split("#")[0], k, text))
    return out[:8]


def header(row):
    """Column roles {area, name, post, phone, email, division} from a header row, or None when it is not a header."""
    if any(re.search(r"\d{6,}|@|\[at\]", c or "") for c in row):
        return None
    col = {}
    for i, h in enumerate(row):
        h = _esw.clean(h).lower()
        if not h or re.fullmatch(r"(s\.?\s*no\.?|sl\.?\s*no\.?|sr\.?\s*no\.?|#|serial.*)", h):
            continue
        if "mail" in h:
            col.setdefault("email", i)
        elif re.search(r"phone|mobile|contact|cell|cug|telephone|landline|number|\bno\.?$", h) and not re.search(r"name", h):
            col.setdefault("phone", [])
            col["phone"].append(i)
        elif re.search(r"location|address", h):
            col.setdefault("address", i)
        elif re.search(r"designation|post\b|cadre", h):
            col.setdefault("post", i)
        elif "name" in h and NAME_HEAD.search(h):
            col.setdefault("name", i)
        elif re.search(r"revenue\s*division|name\s*of\s*the\s*division|^division", h) and "mandal" not in h:
            col.setdefault("division", i)
        elif AREA_HEAD.search(h):
            col.setdefault("area", i)
        elif h in ("name", "names"):
            col.setdefault("name", i)
    if "area" not in col and "division" in col:
        col["area"] = col.pop("division")
    if ("area" in col or "post" in col) and ("phone" in col or "name" in col or "email" in col):
        return col
    return None


JUNK_AREA = re.compile(r"(?i)\b(sdc|law|a\.?o|dy\.?\s*chief|chief|spl\.?|special|collector|superintendent|section|admin\w*|ceo|"
                       r"zilla|krrc|ulc|land\s*acq\w*|accounts?|establishment|district|additional|joint|assistant\s*director|"
                       r"head\s*quarters?|hqrs?)\b")


def email_level(email):
    local = " ".join(e.split("@")[0] for e in (email or "").split(", "))
    for lv, pat in (("block", r"mpdo|mppo|mpp\b|tpeo|eotp|eo\.?tp"), ("subdistrict", r"tah|mro|tehsil"),
                    ("subdivision", r"\brdo|^rdo|rdo\.|rdo[a-z]|sdm|subcollector|acsub")):
        if re.search(pat, local, re.I):
            return lv
    return None


def clean_area(s):
    s = _esw.clean(re.sub(r"\(.*?\)|\|", " ", s or ""))
    s = re.sub(r"^\s*\d+\s*[.)-]\s*", "", s)
    s = OFFICE_WORDS.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" .,:-/")
    return s.title() if s.isupper() and len(s) > 3 else s


def level_of_post(post):
    for lv, pat in POST_LEVEL:
        if re.search(pat, post or "", re.I):
            return lv
    return None


def rows(html, page_kind, where=None):
    """[{area, division, name, post, phone, email, level}] from the tables of one page."""
    soup = _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        tp = []
        g = _esw.grid(t, pos=tp)
        col, start = None, 0
        for i, r in enumerate(g[:4]):
            col = header(r)
            if col:
                start = i + 1
                break
        if not col:
            continue
        cap = " ".join(_esw.clean(" ".join(r)) for r in g[:start - 1])      # a title row above the header
        tkind = kind_of(cap) or page_kind
        division = ""
        for r, pos in zip(g[start:], tp[start:]):
            r = r + [""] * (max(len(x) for x in g) - len(r))
            if len(set(x for x in r if x)) <= 1:            # a section row ("ONGOLE", "Kandukur Division")
                one = next((x for x in r if x), "")
                if one and not re.search(r"\d{6}|a/?c\b|constituency|\bac\b", one, re.I):
                    division = clean_area(re.sub(r"(?i)\bdivision\b", "", one))
                continue
            def cell(k):
                v = col.get(k)
                if v is None:
                    return ""
                return " | ".join(r[i] for i in v) if isinstance(v, list) else r[v]
            post = _esw.clean(cell("post"))
            name = _esw.clean(cell("name"))
            email = _esw.emails(" ".join([cell("email"), cell("phone")]))
            if "area" in col:
                raw_area = cell("area")
            elif level_of_post(post):                      # no place column: "Tahsildar, Ghatkesar", "RDO Keesara"
                raw_area = post
            else:
                continue
            if SKIP_ROW.search(raw_area) or SKIP_ROW.search(post) or SKIP_ROW.search(name) or MC.match(post):
                provenance.skip_row(r, 'skip: SKIP_ROW.search(raw_area) or SKIP_ROW.search(post) or SKIP_ROW.sear...')
                continue
            area = clean_area(raw_area)
            if not area or re.fullmatch(r"[\d\s.]+", area) or JUNK_AREA.search(area) or len(re.sub(r"[^A-Za-z]", "", area)) < 3:
                provenance.skip_row(r, 'skip: not area or re.fullmatch(r"[\\d\\s.]+", area) or JUNK_AREA.search(are...')
                continue
            lv = (level_of_post(post) or level_of_post(raw_area) or (level_of_post(name) if name else None) or email_level(email)
                  or tkind)
            if name and level_of_post(name) and _esw.slug(area) in _esw.slug(name):      # "MPDO ALLAGADDA": a post, not a name
                name = ""
            if VACANT.match(name or "") or re.search(r"\d{6,}", name or ""):
                name = ""
            name = name.split(" | ")[0].strip(" ,.-") if name else ""            # "G.Satyanarayana, | E.O.(PR&RD) (FAC)"
            name = re.sub(r"(?i)\b(mpdo|tahsildar|mro|rdo)\b[\s,:-]*$", "", name).strip(" ,.-") if name else ""
            phone = _esw.phones(cell("phone"))
            if not (name or phone or email):
                provenance.skip_row(r, 'skip: not (name or phone or email)')
                continue
            if "division" in col and clean_area(cell("division")):
                division = clean_area(re.sub(r"(?i)\bdivision\b", "", cell("division")))     # blank cell = as above
            div = division
            out.append({"area": area, "division": div, "name": name, "post": post, "phone": phone, "email": email, "level": lv,
                        "address": _esw.clean(cell("address"))})
            if where is not None:
                where.append(pos)
    return out


def build(module, state, host, district, url, page_kind, rws, upd, seen, posts=None, where=None):
    """where: src_pos of each row of rws (rows(..., where))."""
    recs = []
    for r, pos in zip(rws, where or [None] * len(rws)):
        lv = r["level"]
        dup = (lv, _esw.slug(r["area"]), r["phone"], r["name"].lower())
        if dup in seen:                                   # the same row again (Nellore shows the list in three tabs)
            continue
        seen.add(dup)
        dept, post, _ = KINDS[lv]
        post = (posts or {}).get(lv, post)
        base = f"{host}:{lv}:{_esw.slug(r['area'])}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(module, key, dept=dept, level=lv, area=r["area"], post=r["post"] or post, name=r["name"],
                                phone=r["phone"], email=r["email"], address=r.get("address", ""), district=district, state=state,
                                office_id=base,
                                division=r["division"] if lv != "subdivision" else "", source=url, last_updated=upd,
                                src_url=url, src_pos=pos))
    return recs


def last_updated(html):
    m = re.search(r"Last Updated:?\s*(?:<[^>]+>\s*)*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", html or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def read(p, get, module=MODULE, state=STATE, hosts=None, kinds=None, posts=None):
    hosts = hosts or HOSTS
    url = p.get("url") or f"https://{p['host']}/"
    host = (p.get("host") or urlparse(url).netloc).lower()
    district = p.get("district") or hosts.get(host, "")
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(module, f"{host}-home", r.content)]
    pages = links(r.text, url, host, kinds)
    for extra in p.get("pages") or []:                       # pages named in the seed (found in the archive)
        if norm_url(extra) not in {norm_url(u) for u, _, _ in pages} and norm_url(extra) not in taken():
            pages.append((extra, kind_of(urlparse(extra).path.replace("-", " ")) or "subdistrict", ""))
    if not pages:
        return [], files, "no mandal / division pages in the menu"
    recs, seen = [], set()
    for purl, k, _ in pages:
        a = get(purl)
        if a is None:
            continue
        files.append(_esw.keep(module, f"{host}-{_esw.slug(urlparse(purl).path) or 'page'}", a.content))
        where = []
        recs += build(module, state, host, district, purl, k, rows(a.text, k, where), last_updated(a.text), seen, posts, where)
    return recs, files, "" if recs else "no officer rows"


def fetch(p, get):
    return read(p, get)
