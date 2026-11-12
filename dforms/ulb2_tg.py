"""Telangana: heads and chairpersons of the urban bodies that DB civic had no official for on 2026-11-11 (the "ulb2" gap list).
Four page kinds, one queue item per page (payload "kind"). Every item carries the body's LGD code ("lgd_code"), so the tie to
civic.ulb is sure. All answer only from India (this box in Germany got no answer from any of them on 2026-11-11).

- kind "cdma": the CDMA Telangana town site platform, <town>municipality.telangana.gov.in/pages/<page> (the platform of the 112
  sites in platform_sites.csv). Pages: "chairman-details" (table Sno / Name / Designation / Photo / Mobile: Chairman and Vice
  Chairman), "staff-directory" (Sno / Name / Designation / Mobile: Commissioner first), "office-contact" (key/value rows for the
  office phone, email and address, then Sno / Name / Designation / Email / Mobile). Names are written as the site writes them
  ("SmtKadakanchiBalamani"). The pages show no date. Samples: Jangaon (live from the India server, 2026-11-11) and Alair
  (archive.s1d.me, saved 2026-11-11).
- kind "tgnew": the new town site platform of the bodies formed in 2024-2025 (<town>municipality.telangana.gov.in, server
  13.126.8.141, server-rendered React). The home page redirects to /<slug>; its links give the slug. Pages read:
  /<slug>/chairperson (one card per post: h2 = post, p.font-bold = name, tel: link = mobile) and /<slug>/contact (address, tel:,
  mailto: of the office). /<slug>/organizational-chart is read with the same card rule (not seen yet: no sample). Sample: Asifabad
  (live, 2026-11-11: chairperson Akash Mengre, vice chairperson MD Ahmed).
- kind "gwmc": Greater Warangal Municipal Corporation, gwmc.gov.in/ContactUs_New.aspx?status=99 (Commissioner: Name /
  Designation / Phone Number / Email Id) and ?Status=29 (Mayor: empty on 2026-11-05, the council has no members now: Warangal is not
  in the State Election Commission's 2026 municipal election list). Sample: archive.s1d.me, saved 2026-11-05.
- kind "ghmc": www.ghmc.gov.in/KeyContacts.aspx, table "DEPUTY COMMISSIONER" (Name / Designation / Zone / Circle / Contact Number /
  Email ID). G.O.Ms.No.264 (03.12.2025) and No.292 (24.12.2025) merged 27 urban bodies around the Outer Ring Road into GHMC (the GHMC
  home page says so); four of them are now GHMC circles with their own Deputy Commissioner: Badangpet, Shamshabad, Jalpally,
  Adibatla. One record for each of these circles, tied to the old body's LGD code, with merged_into "GHMC" (the body itself no
  longer exists: the circle officer is the officer for its area). Sample: live from the India server, 2026-11-11 (cut down).
"""
import re

from dforms import _esw, _ulb

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_tg"
STATE = "TG"
GHMC = "https://www.ghmc.gov.in/KeyContacts.aspx"
GWMC = "https://gwmc.gov.in/"

# lgd | area (LGD name) | district | kind | host or circle
BODIES = """251690|Jangaon|Jangoan|cdma|jangoanmunicipality
251654|Sircilla|Rajanna Sircilla|cdma|sircillamunicipality
294879|Nandikonda|Nalgonda|cdma|nandikondamunicipality
263216|Jadcherla|Mahabubnagar|cdma|jadcherlamunicipality
297017|Kothur|Ranga Reddy|cdma|kothurmunicipality
290064|Kothapally|Karimnagar|cdma|kothapallymunicipality
302289|Aswaraopeta|Bhadradri Kothagudem|tgnew|aswaraopetamunicipality
302292|Station Ghanpur|Jangoan|tgnew|stationghanpurmunicipality
302293|Edulapuram|Khammam|tgnew|edulapurammunicipality
302727|Kalluru|Khammam|tgnew|kallurumunicipality
301596|Asifabad|Kumuram Bheem Asifabad|tgnew|asifabadmunicipality
302303|Kesamudram|Mahabubabad|tgnew|kesamudrammunicipality
302291|Devarakadara|Mahabubnagar|tgnew|devarakadaramunicipality
302731|Mulugu|Mulugu|tgnew|mulugumunicipality
302301|Maddur|Narayanpet|tgnew|maddurmunicipality
302290|Chevella|Ranga Reddy|tgnew|chevellamunicipality
302299|Moinabad|Ranga Reddy|tgnew|moinabadmunicipality
302294|Gaddapotharam|Sangareddy|tgnew|gaddapotharammunicipality
302324|Gummadidala|Sangareddy|tgnew|gummadidalamunicipality
302732|Indresham|Sangareddy|tgnew|indreshammunicipality
302304|Isnapur|Sangareddy|tgnew|isnapurmunicipality
302736|Jinnaram|Sangareddy|tgnew|jinnarammunicipality
302302|Kohir|Sangareddy|tgnew|kohirmunicipality
251691|Warangal|Hanumakonda|gwmc|
257865|Badangpet|Ranga Reddy|ghmc|Badangpet
290149|Shamshabad|Ranga Reddy|ghmc|Shamshabad
276409|Jalapally|Ranga Reddy|ghmc|Jalpally
290099|Adibatla|Ranga Reddy|ghmc|Adibatla"""
CDMA_PAGES = ("chairman-details", "staff-directory", "office-contact")
GWMC_PAGES = (("commissioner", "ContactUs_New.aspx?status=99"), ("mayor", "contactus_new.aspx?Status=29"))
COLS = {"name": re.compile(r"(?i)^name"), "post": re.compile(r"(?i)^designation"), "phone": re.compile(r"(?i)mobile|phone|contact"),
        "email": re.compile(r"(?i)e-?mail"), "circle": re.compile(r"(?i)^circle")}


def bodies():
    for line in BODIES.splitlines():
        lgd, area, district, kind, host = line.split("|")
        yield {"lgd_code": lgd, "body": area, "district": district, "kind": kind, "host": host}


def items(get=None):
    out, ghmc = [], []
    for b in bodies():
        base = {"reader": MODULE, "state": STATE, "india_only": True, "kind": b["kind"], "body": b["body"],
                "district": b["district"], "lgd_code": b["lgd_code"]}
        if b["kind"] == "cdma":
            for pg in CDMA_PAGES:
                out.append({"key": f"{MODULE}-{_esw.slug(b['body'])}-{pg}",
                            "payload": dict(base, url=f"https://{b['host']}.telangana.gov.in/pages/{pg}", page=pg)})
        elif b["kind"] == "tgnew":
            out.append({"key": f"{MODULE}-{_esw.slug(b['body'])}", "payload": dict(base, url=f"https://{b['host']}.telangana.gov.in/")})
        elif b["kind"] == "gwmc":
            for pg, path in GWMC_PAGES:
                out.append({"key": f"{MODULE}-{_esw.slug(b['body'])}-{pg}", "payload": dict(base, url=GWMC + path, page=pg)})
        else:
            ghmc.append({"lgd_code": b["lgd_code"], "body": b["body"], "district": b["district"], "circle": b["host"]})
    out.append({"key": f"{MODULE}-ghmc-circles",
                "payload": {"reader": MODULE, "state": STATE, "india_only": True, "kind": "ghmc", "url": GHMC, "circles": ghmc}})
    return out


def header_map(cells):
    """{field: column index} from a heading row."""
    m = {}
    for i, c in enumerate(cells):
        for f, rx in COLS.items():
            if f not in m and rx.search(c):
                m[f] = i
                break
    return m


def tables(soup):
    """Every (heading map, data rows) of the page's tables that have a Name and a Designation column."""
    for tb in soup.find_all("table"):
        rows = [[_esw.clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])] for tr in tb.find_all("tr")]
        rows = [r for r in rows if any(r)]
        for i, r in enumerate(rows):
            h = header_map(r)
            if "name" in h and "post" in h:
                yield h, rows[i + 1:]
                break


def kv(soup):
    """Key/value rows ("Email ids:" | "x@y") of the office-contact page."""
    out = {}
    for tr in soup.find_all("tr"):
        c = [_esw.clean(x.get_text(" ")) for x in tr.find_all(["td", "th"])]
        if len(c) == 2 and c[0].endswith(":"):
            out[c[0].rstrip(":").lower()] = c[1]
    return out


def common(p):
    return {"district": p.get("district"), "lgd_code": p.get("lgd_code"), "source": p.get("url", "")}


def parse_cdma(html, p, seen=None):
    soup, seen = _esw.soup(html), seen if seen is not None else set()
    recs = []
    for h, rows in tables(soup):
        for r in rows:
            g = {f: (r[i] if i < len(r) else "") for f, i in h.items()}
            if not g.get("post") or not (g.get("name") or g.get("phone") or g.get("email")):
                continue
            recs.append(_ulb.record(MODULE, STATE, p["body"], g["post"], seen, name=g.get("name", ""), phone=g.get("phone", ""),
                                    email=g.get("email", ""), page=p.get("page"), **common(p)))
    o = kv(soup)
    office = {k: v for k, v in (("office_phone", _esw.phones(next((v for k, v in o.items() if "contact number" in k), ""))),
                                ("office_email", _esw.emails(next((v for k, v in o.items() if "email" in k), ""))),
                                ("address", next((v for k, v in o.items() if "address" in k), ""))) if v and v != "-"}
    if office:
        if recs:
            recs[0][1].update(office)
        else:
            recs.append(_ulb.record(MODULE, STATE, p["body"], "Office", seen, phone=office.get("office_phone", ""),
                                    email=office.get("office_email", ""), address=office.get("address"), page=p.get("page"), **common(p)))
    return recs


def slug_of(html):
    """The town slug of the new platform from the home page links (href="/asifabad/chairperson")."""
    m = re.search(r'href="/([a-z0-9-]+)/(?:chairperson|contact|about)"', html or "")
    return m.group(1) if m else None


def cards(html, p, page, seen):
    """One record per card of the new platform: h2/h3 = post, p.font-bold = name, tel: = phone, mailto: = email."""
    soup = _esw.soup(html)
    main = soup.find("main") or soup
    recs = []
    for c in main.find_all("div", class_="bg-card"):
        h = c.find(["h2", "h3"])
        post = _esw.clean(h.get_text(" ")) if h else ""
        if not post:
            continue
        n = c.find("p", class_="font-bold")
        name = _esw.clean(n.get_text(" ")) if n else ""
        phone = _esw.phones(*[a["href"][4:] for a in c.find_all("a", href=re.compile("^tel:"))])
        email = _esw.emails(" ".join(a["href"][7:] for a in c.find_all("a", href=re.compile("^mailto:"))))
        if name or phone or email:
            recs.append(_ulb.record(MODULE, STATE, p["body"], post.title(), seen, name=name, phone=phone, email=email, page=page,
                                    **dict(common(p), source=p["page_url"])))
    return recs


def contact(html):
    """(address, phone, email) of the office from the new platform's contact page."""
    soup = _esw.soup(html)
    main = soup.find("main") or soup
    c = main.find("div", class_="bg-card")
    if not c:
        return "", "", ""
    span = c.find("span")
    phone = _esw.phones(*[a["href"][4:] for a in c.find_all("a", href=re.compile("^tel:"))])
    email = _esw.emails(" ".join(a["href"][7:] for a in c.find_all("a", href=re.compile("^mailto:"))))
    return (_esw.clean(span.get_text(" ")) if span else ""), phone, email


def fetch_tgnew(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    slug = slug_of(r.text)
    if not slug:
        return [], [_esw.keep(MODULE, _esw.slug(p["body"]) + "-home", r.content)], "no town slug"
    base = p["url"].rstrip("/") + "/" + slug + "/"
    recs, files, seen = [], [], set()
    for page in ("chairperson", "organizational-chart", "contact"):
        a = get(base + page)
        if a is None:
            continue
        files.append(_esw.keep(MODULE, f"{_esw.slug(p['body'])}-{page}", a.content))
        if page == "contact":
            addr, ph, em = contact(a.text)
            office = {k: v for k, v in (("address", addr), ("office_phone", ph), ("office_email", em)) if v}
            if recs:
                recs[0][1].update(office)
            elif ph or em:
                recs.append(_ulb.record(MODULE, STATE, p["body"], "Office", seen, phone=ph, email=em, address=addr or None,
                                        page=page, **dict(common(p), source=base + page)))
        else:
            recs += cards(a.text, dict(p, page_url=base + page), page, seen)
    return recs, files, "" if recs else "no rows"


def parse_ghmc(html, p):
    """Deputy Commissioners of the GHMC circles that were urban bodies until December 2025."""
    soup, seen, recs = _esw.soup(html), set(), []
    want = {c["circle"].lower(): c for c in p.get("circles", [])}
    for h, rows in tables(soup):
        if "circle" not in h:
            continue
        for r in rows:
            g = {f: (r[i] if i < len(r) else "") for f, i in h.items()}
            c = want.get(g.get("circle", "").lower())
            if not c or not re.match(r"(?i)deputy\s+commissioner", g.get("post", "")):
                continue
            recs.append(_ulb.record(MODULE, STATE, c["body"], g["post"].title(), seen, name=g.get("name", ""), phone=g.get("phone", ""),
                                    email=g.get("email", ""), district=c["district"], lgd_code=c["lgd_code"], source=p["url"],
                                    merged_into="GHMC", ghmc_circle=g["circle"],
                                    notes="the body was merged into GHMC (G.O.Ms.No.264, 03.12.2025); this is the officer of its GHMC circle"))
        break                                   # the first table with a Circle column is the Deputy Commissioners' table
    return recs


def fetch(p, get):
    if p["kind"] == "tgnew":
        return fetch_tgnew(p, get)
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    name = "ghmc-keycontacts" if p["kind"] == "ghmc" else f"{_esw.slug(p['body'])}-{p.get('page', 'page')}"
    files = [_esw.keep(MODULE, name, r.content)]
    recs = parse_ghmc(r.text, p) if p["kind"] == "ghmc" else parse_cdma(r.text, p)
    return recs, files, "" if recs else "no rows"
