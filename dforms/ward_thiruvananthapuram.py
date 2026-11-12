"""Thiruvananthapuram Municipal Corporation (tmc.lsgkerala.gov.in, the LSGD Kerala Drupal platform): its zonal offices, their
address and phone, and the wards each zonal office serves. One page, /en/corporation-zonal-offices (saved in archive.s1d.me
2026-11-05; the live site answers from Germany): text blocks "<Name> Zonal Office Address: ... Phone : ... Wards: Pallithura,
Kulathoor, ...". The page names the wards, not their numbers: the names go in the extra key "ward_names" (the site's DB matches
them to civic.ward_map by name; Kerala renumbered the wards in the 2025 delimitation). No officers are named: records are the
zonal offices (post "Zonal Office"). Records: level "zone". Record ids: dept:ward_thiruvananthapuram:<zone slug>:zonal-office.
"""
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_thiruvananthapuram"
BODY, LGD, STATE, DISTRICT = "Thiruvananthapuram Municipal Corporation", "252260", "KL", "Thiruvananthapuram"
URL = "https://tmc.lsgkerala.gov.in/en/corporation-zonal-offices"
BLOCK = re.compile(r"([A-Z][A-Za-z.]+)\s+Zonal\s+Office\s+Address\s*:\s*(.*?)\s*Phone\s*:\s*([\d\s,/-]+?)\s*"
                   r"Wards?\s*:\s*(.*?)(?=\s+[A-Z][A-Za-z.]+\s+Zonal\s+Office\s+Address|\s+Corporation\s+Zonal|\s+footer menu|$)", re.S)


def items(get=None):
    return [{"key": f"{MODULE}-zonal-offices", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    for t in soup(["script", "style"]):
        t.decompose()
    text = _esw.clean(soup.get_text(" "))
    i = text.find("Zonal offices")
    text = text[i:] if i >= 0 else text
    seen, recs = set(), []
    for m in BLOCK.finditer(text):
        zone, addr, phone, wards = m.group(1), m.group(2).strip(" ,"), m.group(3), m.group(4)
        names = [w.strip(" .") for w in re.split(r"\s*,\s*", wards) if w.strip(" .")]
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:zonal-office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=f"{zone} Zonal Office", zone=f"{zone} Zone", post="Zonal Office", address=addr,
                                 phone=phone, ward_names=names or None, wing="administration", source=p["url"],
                                 src_pos={"selector": "page text", "match": m.group(0)[:300]}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "zonal-offices", r.content)], "" if recs else "no zonal offices"
