"""Surendranagar Municipal Corporation (snmcgujarat.com; corporation since 2025): its 2 administrative zones (North, South) and the
zonal officer of each branch in each zone (Administration, Tax, Sanitation, Civil / Mechanical / Electrical Engineering, Health,
Town Planning and Estate, Cattle Nuisance Control, Fire, Garden, Public Relations, Urban Community Development). One page,
/zones_wards (answers from Germany; live sample 2026-11-11, not in archive.s1d.me): per zone a heading "North Zone (Mr. ... -
Deputy Commissioner (GAS))" and a table SR.NO. | BRANCH NAME | NAME OF ZONAL OFFICER. The page gives no phones and no ward lists.
Records: level "zone"; the Deputy Commissioner of each zone (role head) and one record per branch ("-" = vacant).
Record ids: dept:ward2n_surendranagar:<zone slug>:<branch slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_surendranagar"
BODY, LGD, STATE, DISTRICT = "Surendranagar Municipal Corporation", "251114", "GJ", "Surendranagar"
URL = "https://snmcgujarat.com/zones_wards"
BRANCH_WING = (("tax", "revenue"), ("sanitation|cattle", "sanitation"), ("civil", "engineering"), ("mechanical", "engineering"),
               ("electrical", "electrical"), ("health", "health"), ("town planning", "planning"), ("garden", "horticulture"),
               ("administration", "administration"))


def items(get=None):
    return [{"key": f"{MODULE}-zones-wards", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def _wing(branch):
    b = branch.lower()
    return next((w for rx, w in BRANCH_WING if re.search(rx, b)), "other")


def parse(html, p):
    seen, recs = set(), []
    soup = _esw.soup(html)
    for t in soup.find_all("table"):
        h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "h6", "p", "strong"])
        head = _esw.clean(h.get_text(" ")) if h else ""
        m = re.match(r"(?i)\s*((?:north|south|east|west|central)\s*zone)\s*(?:\((.*)\))?", head)
        if not m:
            continue
        zone = m.group(1).title()
        if m.group(2):
            nm, _, post = m.group(2).partition(" - ")
            nm = re.sub(r"(?i)^(mr|mrs|ms|shree|shri)\.?\s+", "", nm.strip())
            recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:deputy-commissioner", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=zone, zone=zone, post=post.strip() or "Deputy Commissioner",
                                     name=nm, wing="administration", source=p["url"]))
        g = _esw.grid(t)
        for r in g[1:]:
            if len(r) < 3 or not r[1]:
                continue
            branch, raw = _esw.clean(r[1]), _esw.clean(r[2])
            nm = re.sub(r"(?i)^(shree|shri|smt)\.?\s+", "", raw)
            recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:{_esw.slug(branch)[:60]}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=f"{zone} - {branch}", zone=zone,
                                     post=f"Zonal Officer, {branch}", name=nm, wing=_wing(branch),
                                     vacant=True if re.fullmatch(r"-*", raw) else None, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "zones-wards", r.content)], "" if recs else "no zone tables"
