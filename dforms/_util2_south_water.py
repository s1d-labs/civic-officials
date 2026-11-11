"""Shared parts of the south_water readers (dforms/water2_tg_mb.py, dforms/water2_ap_rws.py): the department pages of the district
web sites (S3WaaS / WordPress, <district>.telangana.gov.in and <district>.ap.gov.in).

Each district site has its own page for the rural water department (Telangana: "RWS & Mission Bhagiratha", "Mission Bhagiratha
Grid / Intra"; Andhra Pradesh: "Rural Water Supply and Sanitation", "Public Health"). Page names and ids differ per site, so
search_items() asks each site's own search (/?s=<word>, the WordPress search box) and keeps the result links whose title names the
department. Some pages hold an officer table (Name | Designation | Circle / Division / Sub-Division / Mandal | Contact | E-mail),
some name the officers in text lines ("Executive Engineer, RWS & S, Kakinada, Contact No.9100121101, Email : ..."), many hold
only a description (then fetch() returns no rows and says so).

parse_page() reads every table that has a phone column and a name or designation column, and the text lines that hold a
designation and a phone number. Levels (rural water wing of TG / AP): Engineer-in-Chief / Chief Engineer = state, Superintending
Engineer / District RWS Engineering Officer = circle, Executive Engineer = division, Deputy Executive Engineer (DEE, Dy.E.E) =
subdivision, Assistant Executive Engineer / Assistant Engineer / Junior Engineer (the mandal section officer) = section.
"""
import re

from dforms import _esw
from dforms._water import unique

MOBILE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
LEVEL_RX = (
    ("state", r"ENGINEER[\s-]*IN[\s-]*CHIEF|\bENC\b|\bE\.?\s?N\.?\s?C\b|CHIEF\s+ENGINEER|\bC\.?\s?E\b"),
    ("circle", r"SUPERINTEND|\bS\.?\s?E\b|DISTRICT\s+RWS|ENGINEERING\s+OFFICER|\bCIRCLE\b"),
    ("subdivision", r"DEPUTY\s+EXEC|\bDY\.?\s*E\.?\s?E\b|\bD\.?\s?E\.?\s?E\b|DY\.?\s*EXEC|SUB[\s-]*DIVISION"),
    ("section", r"ASS(?:IS)?T(?:AN)?T\.?\s*EXEC|\bA\.?\s?E\.?\s?E\b|ASSISTANT\s+ENGINEER|\bA\.?\s?E\b|\bJ\.?\s?E\b|JUNIOR\s+ENGINEER|\bMANDAL\b"),
    ("division", r"EXECUTIVE\s+ENGINEER|\bE\.?\s?E\b|\bDIVISION\b"),
)
COLS = (("sl", r"^s\.?\s*l?\.?\s*no|^sl\b|^s\.no"), ("email", r"e-?\s?mail"), ("phone", r"contact|phone|mobile|cell|tel"),
        ("name", r"name\s+of\s+the\s+(officer|official)|^name\b|officer\s*name"),
        ("post", r"designation|^post\b"), ("place", r"place|division|mandal|circle|office|jurisdiction|area|attached"))


def level_of(post, default="district"):
    p = " " + re.sub(r"\s+", " ", (post or "").upper()) + " "
    for level, rx in LEVEL_RX:
        if re.search(rx, p):
            return level
    return default


def head_map(cells):
    m = {}
    for i, c in enumerate(cells):
        c = c.lower().strip()
        for key, rx in COLS:
            if key not in m and re.search(rx, c):
                m[key] = i
                break
    return m


def last_updated(soup):
    t = soup.get_text(" ")
    m = re.search(r"Last\s+Updated\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", t)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def clean_name(s):
    s = re.sub(r"\s*,\s*$", "", _esw.clean(s))
    s = re.sub(r"^(Sri|Smt|Kum|Dr|Shri|Thiru)\s*[.,]?\s*", lambda m: m.group(1) + ". ", s)
    return re.sub(r"\s+,", ",", s).strip(" ,.")


def area_of(post, place):
    """The office's place: the place cell, else the part of the post after the first comma."""
    if place:
        return place.strip(" ,.")
    parts = re.split(r"\s*,\s*", post or "", maxsplit=1)
    return parts[1].strip(" ,.") if len(parts) == 2 else ""


def content(soup):
    m = soup.find("main") or soup.find(id="SkipContent") or soup
    for x in m.select("nav, header, footer, script, style, form, .breadcrumbs, .searchResult"):
        x.decompose()
    for a in m.select('a[href^="mailto:"]'):                    # the link text can be cut short ("...@telangana.gov")
        a.string = a["href"][7:].split("?")[0]
    return m


def parse_page(html, url, module, state, district, wing, extra=None):
    """Records of one district department page. wing: "rws" (rural water) or "ph" (public health)."""
    soup = _esw.soup(html)
    last = last_updated(soup)
    title = soup.find("h1")
    title = _esw.clean(title.get_text(" ")) if title else ""
    main = content(soup)
    recs, seen = [], set()
    base = dict(dept="water", state=state, district=district, source=url, last_updated=last, wing=wing, **(extra or {}))

    def add(post, name, place, phone, email):
        post, name, place = _esw.clean(post).strip(" ,."), clean_name(name or ""), _esw.clean(place)
        if not post and not name:
            return
        if not re.search(r"(?i)engineer|\bA\.?E\.?E?\b|\bD\.?E\.?E\b|\bJ\.?E\b|\bE\.?E\b|\bS\.?E\b|officer|chemist|consultant", post + " " + place):
            return
        lvl = level_of(post) if level_of(post) != "district" else level_of(place)
        area = area_of(post, place) or district
        key = unique(_esw.slug(f"{lvl}-{area}-{post}") or "office", seen)
        recs.append(_esw.record(module, f"{_esw.slug(district)}:{key}", level=lvl, area=area, post=post, name=name,
                                phone=phone, email=email, **base))

    for tb in main.find_all("table"):
        rows = _esw.grid(tb, _esw.cell_text)
        if not rows or not MOBILE.search(tb.get_text(" ")) and not re.search(r"\d{5,}", tb.get_text(" ")):
            continue
        head, cols = None, None
        for r in rows:
            m = head_map(r)
            if cols is None and len(m) >= 2 and ("phone" in m or "email" in m):
                cols = m
                continue
            if cols is None:
                continue
            def col(k):
                i = cols.get(k)
                return r[i] if i is not None and i < len(r) else ""
            post, place = col("post"), col("place")
            if not post and place and level_of(place) != "district" and re.search(r"(?i)engineer|officer", place):
                post, place = place, ""                          # "Division/Mandal Attached" = "Executive Engineer(P),Vijayawada."
            if not cols.get("post") and not cols.get("name") and not post:
                continue
            add(post, col("name"), place, _esw.phones(col("phone")), _esw.emails(col("email")))
    if not recs:                                                  # officers named in text lines
        lines = [l for l in main.get_text("\n").split("\n")]
        for i, line in enumerate(lines):
            t = _esw.clean(line)
            if not MOBILE.search(t):
                continue
            ctx = t
            if not re.search(r"(?i)engineer|officer", t):         # "Contact No.…" on its own line: the post is on the line above
                prev = [_esw.clean(x) for x in lines[max(0, i - 3):i] if _esw.clean(x)]
                ctx = (prev[-1] + ", " + t) if prev else t
            m = re.match(r"(?i)\s*(?:sri|smt|kum|dr)?\.?\s*(.*?(?:engineer|officer)[^,]*)\s*,\s*(.*?)\s*,?\s*(?:contact|ph|cell|mobile|mob)", ctx)
            if not m:
                continue
            post = m.group(1)
            place = re.sub(r"(?i)^(rws\s*&\s*s|rws&s|rws)\s*,?\s*", "", m.group(2)).strip(" ,")
            add(f"{post}, {m.group(2)}".strip(" ,"), "", place, _esw.phones(*MOBILE.findall(ctx)), _esw.emails(ctx))
    return recs, title


def search_items(get, module, state, hosts, words, title_rx, wing, india_only=False):
    """Queue items for the department pages that each district site's own search finds (one GET per host and word)."""
    out, seen = [], set()
    for host, district in hosts:
        for w in words:
            r = get(f"https://{host}/?s={w.replace(' ', '+')}")
            if r is None or r.status_code != 200:
                continue
            soup = _esw.soup(r.text)
            for a in soup.select(".searchItem h2 a[href], .searchItem h3 a[href]"):
                href, title = a["href"], _esw.clean(a.get("title") or a.get_text(" "))
                if host not in href or not re.search(title_rx, title, re.I) or href in seen:
                    continue
                seen.add(href)
                key = f"{module}:{host.split('.')[0]}:{_esw.slug(re.sub(r'^https?://[^/]+', '', href)) or 'home'}"
                pay = {"reader": module, "url": href, "state": state, "district": district, "wing": wing, "title": title}
                if india_only:
                    pay["india_only"] = True
                out.append({"key": key, "payload": pay})
    return out


def fetch_page(p, get, module, state):
    url = p["url"]
    r = get(url)
    if r is None or r.status_code != 200:
        return [], [], f"no answer from {url}"
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    name = host.split(".")[0] + "-" + (_esw.slug(re.sub(r"^https?://[^/]+", "", url)) or "home")
    recs, title = parse_page(r.text, url, module, state, p.get("district") or host.split(".")[0].title(), p.get("wing", "rws"),
                             {"org": p["org"]} if p.get("org") else None)
    files = [_esw.keep(module, name[:100], r.content)]
    return recs, files, "" if recs else f"no officer table or contact lines on the page ({title or 'no title'})"
