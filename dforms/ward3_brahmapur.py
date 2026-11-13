"""Berhampur (Brahmapur) Municipal Corporation, Odisha (www.berhampur.gov.in, plain PHP site): the officers of each section of the
corporation. One page per section, /department.php?slug=<slug> (9 sections on /departments.php, 2026-11-13: account, engineering,
establishment, fees, health, planning, record, town-survey, welfare). Each page has a heading "Officers" and one table
Name | Designation | Phone (phone in a tel: link), e.g. engineering: City Engineer, Executive Engineers, Assistant Executive
Engineers, Assistant / Junior Engineers; health: Deputy Commissioner (Sanitation), Health Medical Officer. The pages show no
"last updated" date. Answers from Germany (archive.s1d.me copies of all 9 pages, vantage pool, 2026-11-05): route abroad.
The site does not say which ward or zone an officer serves (its ward-office directory, /amenities.php?cat=Ward%20Office, lists
one office, Ward 1, without staff), so the records are level "body" (area = the body). BeMC had no town_body records before.
Record ids: dept:ward3_brahmapur:<slug>:<post slug>:<name slug>.
"""
from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_brahmapur"
BODY, LGD, STATE, DISTRICT = "Berhampur Municipal Corporation", "250543", "OD", "Ganjam"
BASE = "https://www.berhampur.gov.in/department.php?slug="
SLUGS = ("account", "engineering", "establishment", "fees", "health", "planning", "record", "town-survey", "welfare")


def items(get=None):
    return [{"key": f"{MODULE}-{s}", "payload": {"reader": MODULE, "url": BASE + s, "state": STATE, "section": s, "route": "abroad"}} for s in SLUGS]


def section_name(soup):
    h = soup.find("h1")
    return _esw.clean(h.get_text(" ")) if h else ""


def parse(html, p):
    soup = _esw.soup(html)
    section = section_name(soup) or p.get("section", "")
    slug = p.get("section") or p["url"].rsplit("=", 1)[-1]
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "name", "designation", soup=soup):
        for r in rows:
            name, post, phone = _ward.col(r, "name"), _ward.col(r, "designation"), _ward.col(r, "phone", "mobile")
            if not post or not (name or phone):
                provenance.skip_row(r, 'skip: not post or not (name or phone)')
                continue
            recs.append(_ward.record(MODULE, f"{slug}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="body", area=BODY, post=post, name=name,
                                     phone=phone, section=section or None, source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("section") or "section", r.content)], "" if recs else "no officers table"
