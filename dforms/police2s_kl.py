"""Kerala Police district sites (<unit>.keralapolice.gov.in, one Laravel CMS for the 20 police districts and the coastal police):
officer pages with names, which the statewide connectivity PDF (police_kl) does not give. Three page formats, one payload kind each:
- "cards" (default): profile cards div.cardpro: h6 = name, p.cap = post or rank, p.loc = unit or station (sometimes with the
  email), p.date = CUG mobile, email or "From: dd.mm.yyyy" (date of posting). Lists are paged with ?page=N (15 cards per page, Laravel: ?page=1 is the first page);
  the reader follows the next-page links. Pages: who-is-who, who-is-who-<unit>, station-house-officers, shos, circle-inspectors,
  circle-office, law-and-order-of-<unit>.
- "blocks": ckeditor blocks div.comment-list: a <strong> heading (station or office), then <p> lines: name, post, landline,
  mobile, email (Kollam City station and who-is-who pages).
- "table": an HTML table with a name column (Sl No | Name | Designation | Sub Division | Phone; CPS | ISHO name | phone).
Names are published in Malayalam on most units and in English on some: the text is kept as published in name, and Malayalam
text also goes to name_regional. Mobiles are the Kerala Police CUG series 9497xxxxxx. Levels: SHO / ISHO / station posts =
police_station, circle inspectors (CI) = circle, DySP / ACP / ASP of a sub division = subdivision, SP / DPC / Commissioner /
DCP / Addl. SP = district; branch posts (narcotic cell, DCRB, control room ...) = district with office_type "unit".
Works from outside India (the archive saved them from India; the hosts answer abroad too). One queue item = one list (all its
pages). Record id dept:police2s_kl:<unit>:<slug of area>:<slug of name or post>."""
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police2s_kl"
MAL = re.compile(r"[ഀ-ൿ]")
ENT = re.compile(r"&(?:amp)?(?:zwj|zwnj|nbsp|amp);?")
DATE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
NUM = re.compile(r"(?<![\d])(?:0\d{2,4}[\s-]?\d{6,8}|[6-9]\d{4}\s?\d{5})(?![\d])")
MAILRE = re.compile(r"[\w.+-]+(?:@|\[at\])[\w-]+(?:\.|\[dot\])[\w.\[\]-]+")

# Malayalam chillu letters and virama + ZWJ forms are made the same before matching (clean() removes the ZWJ).
CHILLU = str.maketrans({"ൺ": "ണ്", "ൻ": "ന്", "ർ": "ര്", "ൽ": "ല്",
                        "ൾ": "ള്", "ൿ": "ക്"})
DISTRICT = re.compile(r"\b(?:S\.?P\b|Superintendent|DPC|District Police Chief|Commissioner|DCP|Addl\.?\s*S\.?\s?P|Additional S\.?P|"
                      r"Addl\.?\s*Supdt|Deputy Commissioner)|എസ്\s?പി$|ജില്ലാ പോലീസ് മേധാവി|കമ്മീഷണ|സൂപ്രണ്ട്", re.I)
SUBDIV = re.compile(r"\b(?:Dy\.?\s?SP|DYSP|ACP|A\.C\.P|ASP|Assistant Commissioner|Deputy Superintendent|Sub[- ]?Division)\b|"
                    r"ഡി[\s.]*വൈ[\s.]*എസ്[\s.]*പി|എ[\s.]*സി[\s.]*പി|എ[\s.]*എസ്[\s.]*പി|സബ്\s?ഡിവിഷ|ഡെപ്യൂട്ടി (?:പോലീസ് )?സൂപ്രണ്ട്|"
                    r"അസിസ്റ്റന്റ് (?:പോലീസ് )?കമ്മീഷണ", re.I)
SUBDIV_AREA = re.compile(r"sub[- ]?division|സബ്\s?ഡിവിഷ", re.I)
CIRCLE = re.compile(r"\bcircle\b|\bC\.?I\b|സ(?:ര്|ർ)ക്കി(?:ള്|ൾ)", re.I)
STATION = re.compile(r"\bI?SHO\b|\bS\.?H\.?O\b|\bP\.?\s?S\b\.?|police station|station house|"
                     r"പി\.?\s?എസ്|സ്റ്റേഷ(?:ന്|ൻ)|എസ്\s?എച്ച്\s?ഒ|എസ്എച്ച്ഒ", re.I)
UNIT = re.compile(r"cell|branch|\bS\.?B\b|എസ്\.?\s?ബി|DCRB|D\.C\.R\.B|control room|narcotic|special branch|\bDHQ\b|\bAR\b|camp|bureau|traffic enforcement|"
                  r"സെൽ|സെല്|ബ്രാഞ്ച്|കൺട്രോൾ|ഡി എച്ച് ക്യു|ഡിസിആർബി|ഡി\s?സി\s?ആർ\s?ബി|ബ്യൂറോ|ക്രൈം", re.I)
OFFICE = re.compile(r"circle office|police station|sub ?division|\bP\.?S\.?$|സർക്കിൾ ഓഫീസ്|സ്റ്റേഷൻ$|ഓഫീസ്$", re.I)
VACANT = re.compile(r"^(?:vacant|ഒഴിവ്)$", re.I)
RANK_WORDS = re.compile(r"^(?:(?:I?SHO|S\.?H\.?O|Station House Officer|Inspector of Police|Inspector|Sub Inspector of Police|SI|CI|"
                        r"Circle Inspector|In-?\s?charge|I/C)\b[\s,.:-]*)+", re.I)
INSPECTOR = re.compile(r"\b(?:Inspector|S\.?I|IP|IOP|SHO|ISHO)\b|ഇൻസ്പെക്ടർ|ഇന്‍സ്പെക്ടര്‍", re.I)
POSTLIKE = re.compile(r"\b(?:ACP|ISHO|SHO|Inspector|Supdt|Superintendent|Chief|DySP|Officer|Commissioner|Branch|Cell)\b", re.I)

# match every pattern against norm(text): the patterns get the same chillu -> virama spelling
DISTRICT, SUBDIV, SUBDIV_AREA, CIRCLE, STATION, UNIT, OFFICE, VACANT, INSPECTOR = (re.compile(x.pattern.translate(CHILLU), x.flags) for x in (
    DISTRICT, SUBDIV, SUBDIV_AREA, CIRCLE, STATION, UNIT, OFFICE, VACANT, INSPECTOR))


def tidy(s):
    return clean(ENT.sub(" ", s or "")) or ""


def norm(s):
    return tidy(s).translate(CHILLU)


def mobiles(*texts):
    out = []
    for t in texts:
        t = DATE.sub(" ", tidy(t))
        for m in NUM.finditer(t):
            d = re.sub(r"\D", "", m.group(0))
            n = d if len(d) == 10 and d[0] in "6789" else (f"{d[:len(d) - 7]}-{d[-7:]}" if d.startswith("0") and len(d) == 11 else
                                                          f"{d[:4]}-{d[4:]}" if d.startswith("0") else d)
            if n not in out:
                out.append(n)
    mob = [n for n in out if "-" not in n]
    return ", ".join(mob + [n for n in out if n not in mob]) or None


def mail(*texts):
    for t in texts:
        for m in MAILRE.finditer(tidy(t)):
            e = email(m.group(0))
            if e:
                return e
    return None


def classify(post, area, subdiv_column=False):
    """(level, office_type) from the post and the area text."""
    p, a = norm(post), norm(area)
    t = f"{p} {a}"
    if subdiv_column and SUBDIV.search(p):
        return "subdivision", "office"
    if SUBDIV.search(p) or (SUBDIV.search(a) and not STATION.search(a)):
        if UNIT.search(t) and not SUBDIV_AREA.search(a):
            return "district", "unit"
        return "subdivision", "office"
    if DISTRICT.search(p):
        return ("district", "unit") if UNIT.search(a) else ("district", "office")
    if CIRCLE.search(t) and not STATION.search(a):
        return "circle", "office"
    if STATION.search(t) and not UNIT.search(a):
        return "police_station", "police station"
    if DISTRICT.search(a):
        return "district", "office"
    if INSPECTOR.search(p) and a and not UNIT.search(a) and not DISTRICT.search(a):
        return "police_station", "police station"   # Kerala: the inspector (or SI) of a place is its station house officer
    return "district", "unit"


def area_of(level, post, loc):
    """The station / circle / sub division name; for district posts the post itself."""
    a = tidy(re.sub(r"\S+@\S+|" + MAILRE.pattern, "", loc or "")).strip(" ,;:-")
    if not a or re.fullmatch(r"[\d\s,/-]+", a):
        a = tidy(post)
    if level == "police_station":
        a = RANK_WORDS.sub("", a).strip(" ,.-")
    return a or tidy(post)


def regional(s):
    return s if s and MAL.search(s) else None


def unit_of(url, p):
    return p.get("unit") or urlparse(url).hostname.split(".")[0]


def card_records(html, url, p):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for c in soup.select(".cardpro"):
        h = c.find("h6")
        name = tidy(h.get_text(" ", strip=True)) if h else ""
        cap = tidy(" ".join(x.get_text(" ", strip=True) for x in c.select("p.cap")))
        loc = tidy(" ".join(x.get_text(" ", strip=True) for x in c.select("p.loc")))
        rest = [tidy(x.get_text(" ", strip=True)) for x in c.select("p") if not {"cap", "loc"} & set(x.get("class") or [])]
        since = next((DATE.search(x).group(0) for x in rest if re.match(r"From", x, re.I) and DATE.search(x)), None)
        extra = {"since": since}
        if MAILRE.fullmatch(cap or "") or (OFFICE.search(norm(name)) and not POSTLIKE.search(name or "")):
            loc, rest, cap, name = name, rest + [cap, loc], None, None     # an office card: h6 = the office
        if VACANT.match(norm(name)):
            extra["notes"], name = "vacant", None
        level, otype = classify(cap or loc, loc)
        out.append(make(p, url, level, otype, area_of(level, cap, loc), cap or ("Circle Inspector" if level == "circle" else None),
                        name, mobiles(loc, *rest), mail(loc, *rest), **extra))
    return out


def block_records(html, url, p):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for b in soup.select(".comment-list"):
        if b.find(class_="comment-list"):
            continue                      # an outer wrapper
        st = b.find("strong")
        head = tidy(st.get_text(" ", strip=True)) if st else ""
        body = b.select_one(".single-title") or b
        lines = [tidy(x.get_text(" ", strip=True)) for x in body.find_all("p")]
        lines = [x for x in lines if x and x != head]
        words = [x for x in lines if not NUM.search(x) and not MAILRE.search(x)]
        name = words[0] if words and not POSTLIKE.search(words[0]) else None
        post = next((x for x in words if x != name), None) or head
        if not head and not lines:
            continue
        level, otype = classify(post, head)
        area = re.sub(r"^P\d+\s+", "", head) if level == "police_station" else head
        out.append(make(p, url, level, otype, area_of(level, post, area), post, name, mobiles(*lines), mail(*lines)))
    return out


HEAD = [("sno", r"^s\.?\s?l?\.?\s?no|^sl|ക്രമ"), ("area", r"station|cps|unit|സ്റ്റേഷ|^place"),
        ("name", r"^name$|പേര്|name of|isho|sho ന്റെ|officer"), ("post", r"designation|rank|തസ്തിക"),
        ("subdivision", r"sub ?division|സബ്"), ("phone", r"phone|mobile|ഫോൺ|ഫോണ്|നമ്പർ")]


def table_records(html, url, p):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.select(".maindiv table, .innercont table"):
        rows = [[tidy(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])] for tr in t.find_all("tr")]
        rows = [r for r in rows if any(r)]
        if not rows:
            continue
        cols = {}
        for i, h in enumerate(rows[0]):
            h2 = h.lower()
            for k, pat in HEAD:
                if k not in cols and re.search(pat, h2, re.I):
                    cols[k] = i
                    break
        if "name" not in cols:
            continue
        for r in rows[1:]:
            g = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else ""  # noqa: E731
            name, post, sub, area = g("name"), g("post"), g("subdivision"), g("area")
            post = post or p.get("post") or ""
            nums = mobiles(g("phone"))
            if (re.fullmatch(r"[\d\s,]*", name or "") and not area) or (area and not re.search(r"[^\W\d_]", area)):
                continue
            if NUM.search(name or ""):
                nums, name = nums or mobiles(name), None
            level, otype = classify(post, area or sub, subdiv_column="subdivision" in cols)
            if p.get("level"):
                level, otype = p["level"], "police station" if p["level"] == "police_station" else "office"
            out.append(make(p, url, level, otype, area or sub or post, post or ("SHO" if level == "police_station" else None),
                            name, nums, mail(*r), subdivision=sub if level != "subdivision" else None))
    return out


def make(p, url, level, otype, area, post, name, phone, mail_, **extra):
    unit = unit_of(url, p)
    name = re.sub(r"\s*\((?:I/?C|i/c)\)\s*$", " (i/c)", name or "").strip() or None
    key = f"{slug(unit)}:{slug(area)}:{slug(name or post or '')}"
    return rec(M, key, level=level, office_type=otype, area=area, area_regional=regional(area), post=post,
               name=name, name_regional=regional(name), phone=phone, email=mail_, state="KL",
               district=p.get("district"), unit=unit, source=url, **extra)


PARSE = {"cards": card_records, "blocks": block_records, "table": table_records}


def page_links(html, url):
    base = url.split("?")[0]
    nums = set()
    for m in re.finditer(r'href="([^"]*\?page=(\d+))"', html):
        if urljoin(url, m.group(1).replace("&amp;", "&")).split("?")[0] == base:
            nums.add(int(m.group(2)))
    return base, nums


def fetch(p, get):
    url, kind = p["url"], p.get("kind", "cards")
    r = get(url)
    if r is None:
        return [], [], "no answer"
    name = slug(re.sub(r"^https?://", "", url))[:80]
    files, pages = [gz(M, f"{name}.html", r.content)], [(url, r.text)]
    if kind == "cards":
        base, nums = page_links(r.text, url)
        done = {0, 1} if "page=" not in url else {int(re.search(r"page=(\d+)", url).group(1))}   # Laravel: ?page=1 is the list itself
        while True:
            todo = sorted(n for n in nums if n not in done and n <= int(p.get("max_pages", 20)))
            if not todo:
                break
            n = todo[0]
            done.add(n)
            u = f"{base}?page={n}"
            x = get(u)
            if x is None:
                continue
            files.append(gz(M, f"{name}-page-{n}.html", x.content))
            pages.append((u, x.text))
            nums |= page_links(x.text, u)[1]
    recs = []
    for u, h in pages:
        recs += PARSE[kind](h, u, p)
    seen, out = set(), []
    for rid, d in recs:                      # the same card on two pages (lists overlap when the site re-sorts)
        k = (d.get("name"), d.get("post"), d.get("area"), d.get("phone"))
        if k not in seen:
            seen.add(k)
            out.append((rid, d))
    recs = uniq(out)
    return recs, files, "" if recs else "no officers on the page"
