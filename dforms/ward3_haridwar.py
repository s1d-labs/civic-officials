"""Nagar Nigam Haridwar (nnharidwar.uk.gov.in, an S3WaaS WordPress site): the staff of each department. One page per department
(live sample 2026-11-13 from Mumbai, not in archive.s1d.me), each one table S.No | Name | Designation (no phones, no emails):
health (the senior medical officer of health, 9 chief sanitary inspectors, a sanitary inspector, sanitation supervisors), public
works (executive engineer, junior engineers), property tax, street light, establishment, accounts, PIU (AMRUT / NULM / PMAY),
trade licence. The pages name no zones or wards: records are at level "body". The site's Who's Who page is read by the whoswho
task, not here. Abbreviated posts are spelled out (C.S.I. -> Chief Sanitary Inspector); designation keeps the text as written.
Record ids: dept:ward3_haridwar:<page>:<post slug>:<row>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_haridwar"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Haridwar", "248485", "UK", "Haridwar"
SITE = "https://nnharidwar.uk.gov.in/"
PAGES = {"health-department": "health", "public-work-department": "engineering", "property-tax-department": "revenue",
         "street-light-section": "electrical", "establishment-cell": "administration", "account-section": "other",
         "piu-cell": "other", "trade-license": "revenue"}
ABBR = ((r"^S\.?\s*M\.?\s*O\.?\s*H\.?$", "Senior Medical Officer of Health"), (r"^C\.?\s*S\.?\s*I\.?$", "Chief Sanitary Inspector"),
        (r"^S\.?\s*I\.?$", "Sanitary Inspector"), (r"^T\.?\s*A\.?\s*O\.?$", "Tax Assessment Officer"),
        (r"^T\.?\s*I\.?$", "Tax Inspector"), (r"^S\.?\s*F\.?\s*O\.?$", "Senior Finance Officer"), (r"^Ex\.?\s*Engineer$", "Executive Engineer"),
        (r"^Varistha\s*Lipik$", "Senior Clerk"), (r"^Supervisor$", "Sanitation Supervisor"))


def items(get=None):
    return [{"key": f"{MODULE}-{p}", "payload": {"reader": MODULE, "url": f"{SITE}{p}/", "state": STATE, "page": p}}
            for p in PAGES]


def en_post(des, page):
    d = _esw.clean(des)
    for rx, en in ABBR:
        if re.match(rx, d, re.I):
            if en == "Sanitation Supervisor" and page != "health-department":
                return d
            return en
    return d


def parse(html, p):
    page = p.get("page") or ""
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "Name", "Designation")[:1]:
        for r in rows:
            name, des = _ward.col(r, "Name"), _ward.col(r, "Designation")
            if not (name and des):
                provenance.skip_row(r, 'skip: not (name and des)')
                continue
            post = en_post(des, page)
            sno = re.sub(r"\D", "", _ward.col(r, "S.No")) or str(len(recs) + 1)
            wing = PAGES.get(page)
            if page == "health-department" and re.search(r"(?i)sanit|supervisor", post):
                wing = "sanitation"
            recs.append(_ward.record(MODULE, f"{page}:{_esw.slug(post)}:{sno}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="body", area=BODY, post=post, designation=des, name=name,
                                     department=page.replace("-", " "), wing=wing or _ward.wing_of(post), source=p["url"],
                                     src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, p.get("page") or "page", r.content)]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no staff table"
