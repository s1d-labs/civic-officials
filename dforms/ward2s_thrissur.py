"""Thrissur Municipal Corporation (thrissurcorporation.lsgkerala.gov.in, the LSGD Kerala Drupal platform): its 5 zonal offices
(Ayyanthole, Koorkanchery, Ollukara, Ollur, Vilvattom) and their phones, and the corporation's own Electricity Department. One
page, /en/address/12 ("Address"; answers from Germany; saved in archive.s1d.me 2026-11-07; the page shows "Last Updated: Friday,
November 6, 2026"). The body text has one line per zonal office ("Ayyanthole Zonal : 0487-2360308") and a block "Electricity
department ... Email : ... Ph : ...". The page names no zonal officers and does not say which of the 56 wards each zone holds,
so records have a post "Zonal Office", a phone and no "wards" key. The other zone, ward and staff pages of the site
(/en/establishment/396, /en/administration/393, /en/organisation-structure/394, /en/departments) hold no officer lists.
Records: zonal offices at level "zone", the Electricity Department at level "body". Record ids:
dept:ward2s_thrissur:<zone slug>:zonal-office, dept:ward2s_thrissur:electricity-department.
"""
import datetime
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_thrissur"
BODY, LGD, STATE, DISTRICT = "Thrissur Municipal Corporation", "252194", "KL", "Thrissur"
URL = "https://thrissurcorporation.lsgkerala.gov.in/en/address/12"
ZONE = re.compile(r"([A-Z][a-z]+)\s+Zonal\s*:\s*([\d\s-]{8,})")
ELEC = re.compile(r"(?is)Electricity\s+department(.*?)(?:Social\s+security|$)")


def items(get=None):
    return [{"key": f"{MODULE}-address", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def last_updated(html):
    m = re.search(r"Last Updated:\s*(?:<[^>]+>\s*)*\w+day,\s*(\w+ \d{1,2}, \d{4})", html)
    try:
        return datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat() if m else None
    except ValueError:
        return None


def parse(html, p):
    soup = _esw.soup(html)
    # the page body is the "field--name-body" block that holds the zonal lines (the footer blocks use the same class)
    blocks = [b for b in soup.find_all(class_="field--name-body") if "Zonal" in b.get_text()]
    text = _esw.clean((blocks[0] if blocks else soup).get_text(" "))
    seen, recs, upd = set(), [], last_updated(html)
    for m in ZONE.finditer(text):
        zone = m.group(1)
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:zonal-office", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=f"{zone} Zonal Office", zone=zone, post="Zonal Office",
                                 phone=m.group(2), source=p["url"], last_updated=upd,
                                 src_pos={"selector": ".field--name-body text", "match": m.group(0)[:300]}))
    e = ELEC.search(text)
    if e:
        recs.append(_ward.record(MODULE, "electricity-department", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="body", area=BODY, post="Electricity Department", wing="electrical",
                                 phone=re.sub(r"(\d)\s*-\s*(\d)", r"\1-\2", re.sub(r"(?i).*?\bPh\s*:", "", e.group(1))), email=e.group(1), source=p["url"],
                                 last_updated=upd, src_pos={"selector": ".field--name-body text", "match": e.group(0)[:300]}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "address", r.content)], "" if recs else "no zonal office lines"
