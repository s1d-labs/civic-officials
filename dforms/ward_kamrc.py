"""Karnataka city corporations on the state's municipal web platform (<city>.mrc.gov.in, Drupal; one site per body): the ward-wise
staff of every ward. India only: the sites refuse connections from Germany; they answer over plain http from India (https fails).
Three pages per corporation, each one table with a two-row heading ("Sl. No" | "Ward No." | "<Section> Wardwise Staff Details"
over the posts) and one row per ward:
  /en/Engwardstaffs           Engineering: AEE (Civil), AEE (Electrical), AE / JE (Civil), AE (Electrical), Valve man, Supervisor
  /en/Revenuestaffs           Revenue: Revenue Officer, Asst. Revenue Officer, Revenue Inspector, Bill Collector
  /en/wardwise_staff_details  Health: Sr. / Jr. Health Inspector, Supervisor, "PKs Nos" (number of pourakarmikas: a count, kept
                              as the extra key "pourakarmikas" on the ward's health inspector records)
Most pages give names only; some (Ballari engineering) write "NAME, mobile" or "A, B, C, m1/m2/m3" in a cell: people() takes the
numbers out of the name (one name: all its numbers; as many names as numbers: paired in order; else the numbers go to every name
of the cell as "group_phones"). Cells with several names on lines ("Veeresh | Nagaraj", Davanagere) give one record per name;
the line "From Jalsiri distribution channel" (the ward's water comes from the Jalsiri scheme) is a note, not a name. Sample: shivamoggacity.mrc.gov.in, live from India 2026-11-11 (page shows "Last Updated
On Mon 2 Feb 2026"); the hub's whoswho task read the same pages for these bodies on 2026-11-09 (civic.official). When /en/ has no
table, the reader tries /kn/ (names in Kannada: name and name_regional carry the same text).
Records: level "ward", one per officer and post with the wards that officer covers (the ward table of the body = its 35-82 wards).
One queue item = one page of one body. Record ids: dept:ward_kamrc:<city>:<page>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_kamrc"
STATE = "KA"
# city key -> (host, body, LGD code, district)
BODIES = {
    "hubballi-dharwad": ("hdmc.mrc.gov.in", "Hubballi-Dharwad Municipal Corporation", "251893", "Dharwad"),
    "mysuru": ("www.mysurucity.mrc.gov.in", "Mysuru City Corporation", "252045", "Mysuru"),
    "kalaburagi": ("www.kalaburagicity.mrc.gov.in", "Kalaburagi City Corporation", "248127", "Kalaburagi"),
    "mangaluru": ("www.mangalurucity.mrc.gov.in", "Mangaluru City Corporation", "252021", "Dakshina Kannada"),
    "belagavi": ("www.belagavicity.mrc.gov.in", "Belagavi City Corporation", "251824", "Belagavi"),
    "davanagere": ("davanagerecity.mrc.gov.in", "Davanagere City Corporation", "251941", "Davanagere"),
    "ballari": ("ballaricity.mrc.gov.in", "Ballari City Corporation", "251927", "Ballari"),
    "shivamogga": ("www.shivamoggacity.mrc.gov.in", "Shivamogga City Corporation", "251951", "Shivamogga"),
    "tumakuru": ("tumakurucity.mrc.gov.in", "Tumakuru City Corporation", "251973", "Tumakuru"),
    "raichur": ("www.raichurcity.mrc.gov.in", "Raichur City Corporation", "251876", "Raichur"),
    "bidar": ("www.bidarcity.mrc.gov.in", "Bidar City Corporation", "251867", "Bidar"),
    "hassan": ("www.hassancity.mrc.gov.in", "Hassan City Corporation", "252012", "Hassan"),
    "vijayapura": ("www.vijayapuracity.mrc.gov.in", "Vijayapura City Corporation", "251993", "Vijayapura"),
}
PAGES = {"Engwardstaffs": "engineering", "Revenuestaffs": "revenue", "wardwise_staff_details": "health"}
NAMESPLIT = re.compile(r"\s*(?:,|&|/|\||\band\b)\s*(?=[A-Za-zಀ-೿]{2})")
PHONE = re.compile(r"(?<![\d-])(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)|(?<!\d)0\d{2,4}[\s-]?\d{6,8}(?!\d)")
LABEL = re.compile(r"(?i)^from\b|\bchannel\b|\bdistribution\b")


def people(cell):
    """[(name, phones, group_phones, note)] of one cell. 'MAHINDRA, 8073055190' -> [('MAHINDRA', '8073055190', None, None)];
    'RAMANJI/TIRUPAL, 9980634475/7348898878' -> pairs; 'DASHARATH ,DEVENDRA, 9980722483' -> both with group_phones."""
    nums = [re.sub(r"[\s-]", "", n) if n.startswith(("+", "9", "8", "7", "6")) else n for n in PHONE.findall(cell)]
    nums = [re.sub(r"^\+?91(?=[6-9]\d{9}$)", "", n) for n in nums]
    text = PHONE.sub(" ", cell)
    text = re.sub(r"[\s,/|&]+$", "", text)
    names, notes = [], []
    for name in NAMESPLIT.split(text):
        name = _esw.clean(name).strip(" .,/|")
        if len(name) < 2 or re.fullmatch(r"[-–.\d\s]*|(?i:nil|na|n/a)", name):
            continue
        (notes if LABEL.search(name) else names).append(name)
    note = "; ".join(notes) or None
    if len(names) == 1:
        return [(names[0], ", ".join(nums) or None, None, note)]
    if names and len(names) == len(nums):
        return [(n, x, None, note) for n, x in zip(names, nums)]
    return [(n, None, ", ".join(nums) or None, note) for n in names]


def items(get=None):
    out = []
    for city, (host, *_rest) in BODIES.items():
        for page in PAGES:
            out.append({"key": f"{MODULE}-{city}-{page.lower()}",
                        "payload": {"reader": MODULE, "url": f"http://{host}/en/{page}", "state": STATE, "city": city, "page": page,
                                    "india_only": True}})
    return out


def _wardno(s):
    m = re.fullmatch(r"\s*(\d{1,3})\s*([A-Za-z])?\s*", s or "")
    return (str(int(m.group(1))) + (m.group(2) or "").upper()) if m else None


def table(html):
    """(posts, [(ward, [cell per post])]) of the ward-wise staff table, or ([], [])."""
    soup = _esw.soup(html)
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        hi = next((i for i, r in enumerate(g) if len(r) > 2 and re.search(r"ward", r[1], re.I) and not _wardno(r[2])
                   and not re.search(r"wardwise|details", r[2], re.I)), None)
        if hi is None:
            continue
        posts = [_esw.clean(c) for c in g[hi][2:]]
        rows = [(_wardno(r[1]), r[2:]) for r in g[hi + 1:] if len(r) > 2 and _wardno(r[1])]
        if rows:
            return posts, rows
    return [], []


def parse(html, p):
    city = p["city"]
    host, body, lgd, district = BODIES[city]
    page = p.get("page") or p["url"].rstrip("/").rsplit("/", 1)[-1]
    posts, rows = table(html)
    groups, pks = {}, {}
    for ward, cells in rows:
        for post, cell in zip(posts, cells):
            cell = _esw.clean(cell)
            if not post:
                continue
            if re.search(r"(?i)\bpk|pourakarmika", post):
                if re.fullmatch(r"\d+", cell):
                    pks[ward] = int(cell)
                continue
            if not cell or re.fullmatch(r"[-–.\d\s]*|(?i:nil|na|n/a)", cell):
                continue
            for name, phone, group_phones, note in people(cell):
                g = groups.setdefault((post, name.lower().replace(" ", "").replace(".", "")),
                                      {"post": post, "name": name, "wards": [], "phones": [], "group_phones": [], "notes": []})
                if ward not in g["wards"]:
                    g["wards"].append(ward)
                for k, v in (("phones", phone), ("group_phones", group_phones), ("notes", note)):
                    for x in (v.split(", ") if v and k != "notes" else [v] if v else []):
                        if x not in g[k]:
                            g[k].append(x)
    seen, recs = set(), []
    for g in groups.values():
        regional = bool(re.search(r"[ಀ-೿]", g["name"]))
        wing = _ward.wing_of(g["post"])
        if wing in ("other", "administration"):
            wing = PAGES.get(page, "other")
        extra = {}
        if PAGES.get(page) == "health" and re.search(r"(?i)health\s*inspector", g["post"]):
            n = sum(pks.get(w, 0) for w in g["wards"])
            if n:
                extra["pourakarmikas"] = n
        if g["group_phones"]:
            extra["group_phones"] = ", ".join(x for x in g["group_phones"] if x not in g["phones"]) or None
        if g["notes"]:
            extra["note"] = "; ".join(g["notes"])
        area = ("Ward " if len(g["wards"]) == 1 else "Wards ") + ", ".join(g["wards"])
        recs.append(_ward.record(MODULE, f"{city}:{_esw.slug(page)}:{_esw.slug(g['post'])}:{_esw.slug(g['name']) or 'n'}", seen,
                                 body=body, lgd=lgd, state=STATE, district=district, level="ward", area=area, post=g["post"],
                                 name=g["name"], name_regional=g["name"] if regional else None, phone=", ".join(g["phones"]) or None,
                                 wards=g["wards"], wing=wing, source=p["url"], **extra))
    return recs


def fetch(p, get):
    r = get(p["url"])
    recs = parse(r.text, p) if r is not None else []
    files = [_esw.keep(MODULE, f"{p['city']}-{p.get('page', 'page')}-en", r.content)] if r is not None else []
    if not recs and "/en/" in p["url"]:
        q = dict(p, url=p["url"].replace("/en/", "/kn/"))
        r2 = get(q["url"])
        if r2 is not None:
            files.append(_esw.keep(MODULE, f"{p['city']}-{p.get('page', 'page')}-kn", r2.content))
            recs = parse(r2.text, q)
    if r is None and not files:
        return [], [], "no answer"
    return recs, files, "" if recs else "no ward staff table"
