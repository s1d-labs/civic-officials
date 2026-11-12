"""Salem City Municipal Corporation (www.salemcorporation.gov.in): the officers of its 4 zone offices (Suramangalam, Hasthampatty,
Ammapet, Kondalampatty). One page, /zonal-officers.php (PHP; answers from Germany; saved in archive.s1d.me 2026-11-05): per zone a
heading "<Zone> Zone" and a table Name | Designation | Phone No (Assistant Commissioner, Assistant Revenue Officer, Revenue
Inspectors, Administrative Officer, Superintendent, Executive / Assistant Executive / Assistant / Junior Engineers, Sanitary
Officers and Inspectors). The page does not give the wards of each zone (Salem has 60 wards), so records have no "wards" key.
Records: level "zone". Record ids: dept:ward_salem:<zone>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_salem"
BODY, LGD, STATE, DISTRICT = "Salem City Municipal Corporation", "252474", "TN", "Salem"
URL = "https://www.salemcorporation.gov.in/zonal-officers.php"
ZONES = ("Suramangalam", "Hasthampatty", "Ammapet", "Kondalampatty")


def items(get=None):
    return [{"key": f"{MODULE}-zonal-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def _zone_before(t):
    """The nearest text before the table that names a zone."""
    for el in t.find_all_previous(string=True, limit=80):
        m = re.search(r"([A-Z][a-z]+)\s+Zone\b", el)
        if m:
            return f"{m.group(1)} Zone"
    return None


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs, n = set(), [], 0
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not g or [c.lower() for c in g[0][:2]] != ["name", "designation"]:
            continue
        zone = _zone_before(t) or (f"{ZONES[n]} Zone" if n < len(ZONES) else f"Zone {n + 1}")
        n += 1
        for r in g[1:]:
            if len(r) < 3:
                continue
            name, post, phone = (_esw.clean(c) for c in r[:3])
            name = "" if name in ("-", "") else name
            phone = "" if phone == "-" else phone
            if not post or not (name or phone):
                continue
            post = post.title() if post.isupper() else post
            recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=BODY,
                                     lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone, post=post,
                                     name=name, phone=phone, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "zonal-officers", r.content)], "" if recs else "no zone tables"
