"""Chhapra Municipal Corporation (chapranagarnigam.com, Saran district): its officers directory. Two pages (ASP.NET; answer from
Germany; live samples 2026-11-11, not in archive.s1d.me; "Last Updated" is filled by script, so the date is not in the page):
  /Administrative.aspx  "Administrative Directory": SN | Designation | Name | Contact No (municipal and deputy municipal commissioner,
                        city managers, assistant public sanitary and waste management officers, assistant town planning supervisor,
                        clerks);
  /Engineering.aspx     "Engineering Directory": the same table for the executive, assistant and junior engineers.
The pages name no zone or ward for any officer (Chhapra has 45 wards): level "body" (a body-wide list that holds field posts:
junior engineers, sanitation officers). One queue item = one page. Record ids: dept:ward2s_chapra:<page>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_chapra"
BODY, LGD, STATE, DISTRICT = "Chhapra Municipal Corporation", "249612", "BR", "Saran"
PAGES = ("Administrative", "Engineering")
HONORIFIC = re.compile(r"(?i)^(shri|smt\.?|sushri|dr\.?)\s+")


def items(get=None):
    return [{"key": f"{MODULE}-{p.lower()}", "payload": {"reader": MODULE, "url": f"https://chapranagarnigam.com/{p}.aspx",
                                                          "state": STATE, "page": p.lower()}} for p in PAGES]


def parse(html, p):
    seen, recs = set(), []
    page = p.get("page") or "page"
    for head, rows in _ward.header_tables(html, "designation", "name"):
        for r in rows:
            post, name, phone = _ward.col(r, "designation"), _ward.col(r, "name"), _ward.col(r, "contact", "mobile", "phone")
            if not post or not (name or phone):
                provenance.skip_row(r, 'skip: not post or not (name or phone)')
                continue
            bare = HONORIFIC.sub("", name)
            recs.append(_ward.record(MODULE, f"{page}:{_esw.slug(post)}:{_esw.slug(bare) or 'post'}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="body", area=BODY, post=post, name=bare, phone=phone,
                                     source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("page") or "page", r.content)], "" if recs else "no directory table"
