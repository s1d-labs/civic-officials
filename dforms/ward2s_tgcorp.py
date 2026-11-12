"""Telangana municipal corporations on the CDMA Telangana web platform (<city>corporation.telangana.gov.in, one site per body):
the staff directory of the body. One page per body, //pages/staff-directory (answers from Germany; Karimnagar, Khammam,
Nizamabad and Ramagundam saved in archive.s1d.me 2026-11-11; Meerpet answered live 2026-11-11): one table Sno | Name |
Designation | Mobile, every officer of the body in one list (Commissioner, Deputy / Assistant Commissioner, Revenue Officer,
Revenue Inspectors, Bill Collectors, Ward Officers, Sanitary Inspectors, Health Assistants, Municipal / Assistant / Deputy
Executive Engineers, TPBO / TPS, community organisers, clerks). The page does not say which ward or zone a person serves, so
records are level "body" (area = the body). The page shows no "last updated" date. The whoswho task reads the same pages into
civic.official; these records add the town_body tags (wing, role, local_body_code). Meerpet, Badangpet and Bandlaguda Jagir are
circles / parts of the 2026 GHMC now (www.ghmc.gov.in/KeyContacts.aspx lists Badangpet and Jalpally circles): their sites still
answer, but their lists may be stale. Greater Warangal (gwmc.gov.in) and GHMC have their own readers (ward2s_gwmc, ward2s_ghmc).
Record ids: dept:ward2s_tgcorp:<city>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_tgcorp"
STATE = "TG"
# city key -> (body, LGD code, district)
BODIES = {
    "karimnagar": ("Karimnagar Municipal Corporation", "251653", "Karimnagar"),
    "khammam": ("Khammam Municipal Corporation", "248105", "Khammam"),
    "nizamabad": ("Nizamabad Municipal Corporation", "248091", "Nizamabad"),
    "ramagundam": ("Ramagundam Municipal Corporation", "251648", "Peddapalli"),
    "meerpet": ("Meerpet Municipal Corporation", "276410", "Ranga Reddy"),
    "badangpet": ("Badangpet Municipal Corporation", "257865", "Ranga Reddy"),
    "bandlagudajagir": ("Bandlaguda Jagir Municipal Corporation", "290098", "Ranga Reddy"),
}


def url_of(city):
    return f"https://{city}corporation.telangana.gov.in//pages/staff-directory"


def items(get=None):
    return [{"key": f"{MODULE}-{c}", "payload": {"reader": MODULE, "url": url_of(c), "state": STATE, "city": c}} for c in BODIES]


def parse(html, p):
    body, lgd, district = BODIES[p["city"]]
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "name", "designation"):
        for row in rows:
            name, post, phone = _ward.col(row, "name"), _ward.col(row, "designation"), _ward.col(row, "mobile", "phone")
            if not post or not (name or phone) or post.lower() == "designation":
                continue
            post = post.title() if post.isupper() else post
            recs.append(_ward.record(MODULE, f"{p['city']}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=body, lgd=lgd,
                                     state=STATE, district=district, level="body", area=body, post=post, name=name, phone=phone,
                                     source=p["url"], src_pos=row.pos))
        break
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"{p['city']}-staff-directory", r.content)], "" if recs else "no staff table"
