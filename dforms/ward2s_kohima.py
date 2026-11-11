"""Kohima Municipal Council (kmc.nagaland.gov.in, WordPress; a municipal council, not a corporation: the capital of Nagaland, 19
wards): its field staff. One page, /index.php/employee-details/ (saved in archive.s1d.me 2026-11-06; shows no "Last Updated" date):
one table per branch, each under a heading ("Engineering Branch", "Market Branch", "Enforcement Branch", "Sanitary Branch",
"Convervancy Branch", "Labour Section", "Toll Gate Section" ...), columns Sl.No | Name of Officer | Designation. No phones, and no
ward or zone for anyone: records are level "body" (a body-wide staff list). Only the field posts are kept (engineers, sanitary,
conservancy, market, enforcement and labour inspectors, tax collectors); clerks (UDA, LDA), accountants and drivers are left out.
Records: extra key "branch" (the table heading). Record ids: dept:ward2s_kohima:<branch slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2s_kohima"
BODY, LGD, STATE, DISTRICT = "Kohima Municipal Council", "249722", "NL", "Kohima"
URL = "https://kmc.nagaland.gov.in/index.php/employee-details/"
FIELD = re.compile(r"(?i)engineer|inspector|collector|overseer|supervisor|sanitary|conservancy")


def items(get=None):
    return [{"key": f"{MODULE}-employee-details", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for t in soup.find_all("table"):
        h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "p"])
        branch = _esw.clean(h.get_text(" ")) if h else ""
        for r in _esw.grid(t)[1:]:
            r = [_esw.clean(c) for c in r] + ["", "", ""]
            name, post = re.sub(r"^(Shri|Smti|Smt|Kum|Sri|Dr)\.?\s*", "", r[1]).strip(), r[2]
            if not post or not name or not (FIELD.search(post) or "engineer" in branch.lower()):
                continue
            recs.append(_ward.record(MODULE, f"{_esw.slug(branch)}:{_esw.slug(post)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="body", area=BODY, post=post, name=name,
                                     branch=branch or None, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "employee-details", r.content)], "" if recs else "no branch tables"
