"""Municipal Corporation Jalandhar (mcjalandhar.in): the officers of each wing, from the page "Administration" (/administration/,
"Staff List: OFFICERS OF THE MUNICIPAL CORPORATION JALANDHAR"; WordPress; in archive.s1d.me, saved 2026-11-09; the page shows no
date). Tables of rows S.No. | Name of the officers | Designation | Telephone (Office, Mobile), with full-width section rows:
ADMINISTRATION, CIVIL ENGINEERING WING, STREET LIGHT BRANCH, ENGINEERING WING (O&M CELL), TOWN PLANNING WING, FIRE BRIGADE,
HEALTH BRANCH (SANITATION), Complaint Cell, TEHBAZARI, HOUSE TAX / PROPERTY TAX, TRADE LICENSE BRANCH, BIRTH & DEATH BRANCH ...
The page writes "XXXXXXXX" or "………" where a post has no holder or no number: such rows are kept as vacant posts (vacant: true),
as the page shows them. The page names no zones or wards: records are at level "body". The elected Mayor and Deputy Mayors are
left out (councillor data). Record ids: dept:ward2n_jalandhar:<section slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_jalandhar"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Jalandhar", "248296", "PB", "Jalandhar"
URL = "https://mcjalandhar.in/administration/"
HOLDER = re.compile(r"^(Sh|Smt|Dr|Ms|Mr|Mrs|Er)\s?\.", re.I)
EMPTY = re.compile(r"^(?:[Xx….\s—-]{3,}[A-Za-z]?|[….\s—-]*)$")
SEC_WING = (("engineering", "engineering"), ("street light", "electrical"), ("o&m", "water"), ("town planning", "planning"),
            ("health", "sanitation"), ("sanitation", "sanitation"), ("tax", "revenue"), ("tehbazari", "revenue"),
            ("license", "revenue"), ("birth", "health"), ("fire", "other"))


def items(get=None):
    return [{"key": f"{MODULE}-administration", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs, section = set(), [], ""
    for t in soup.find_all("table"):
        for r in _esw.grid(t):
            cells = [_esw.clean(c) for c in r]
            if len(set(cells)) == 1 and cells[0]:
                section = cells[0]
                continue
            cells = [c for i, c in enumerate(cells) if c and (i == 0 or c != cells[i - 1])]
            if cells and re.fullmatch(r"\d{1,3}\.?", cells[0]):
                cells = cells[1:]
            if len(cells) < 2 or re.search(r"(?i)^(s\.?\s*no|name of)", cells[0]) or cells[0] in ("Office", "Mobile"):
                continue
            name, post, rest = cells[0], cells[1], " ".join(cells[2:])
            if not HOLDER.match(name) and not EMPTY.match(name) and HOLDER.match(post):
                name, post = post, name
            if re.search(r"(?i)\bmayor\b", post) or EMPTY.match(post) or not re.search(r"[A-Za-z]{2}", post):
                continue
            vacant = bool(EMPTY.match(name)) or bool(re.search(r"(?i)\bvacant\b", name + " " + post))
            name = "" if EMPTY.match(name) or re.fullmatch(r"(?i)vacant", name) else name
            phone = _esw.phones(re.sub(r"[Xx]{4,}[^|]*", " ", rest))
            wing = _ward.wing_of(post)
            if wing in ("other", "engineering", "administration"):
                wing = next((w for k, w in SEC_WING if k in section.lower()), wing)
            recs.append(_ward.record(MODULE, f"{_esw.slug(section) or 'staff'}:{_esw.slug(post)}:{_esw.slug(name) or 'vacant'}", seen,
                                     body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="body", area=BODY, post=post, name=name,
                                     phone=phone, vacant=True if vacant else None, section=section or None, wing=wing, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "administration", r.content)], "" if recs else "no staff tables"
