"""Agartala Municipal Corporation (agartalacity.tripura.gov.in, Drupal on the Tripura state platform): the ward secretary of each
of its 51 wards and the 4 zone offices. Two pages, one queue item each:
  /ward          "Ward Secretary List": one table Ward No | Name of Ward Secretary | Contact Number(s) (51 rows).
  /zonal_office  an ordered list "<North/East/South/Central> Zone Office <address>. Phone No. 0381-..." (no officer names and no
                 ward-to-zone mapping on the page).
India only: no answer from Germany (2026-11-11, connect timeout); both pages fetched live from India 2026-11-11 (not in archive.s1d.me,
which holds only the home page). The pages show no "Last Updated" date.
Records: ward secretaries level "ward" (wards = [the ward]); zone offices level "zone" with post "Zone Office", the address and the
office phone. Record ids: dept:ward2s_agartala:w<ward>:ward-secretary:<name slug> and dept:ward2s_agartala:<zone slug>:zone-office.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_agartala"
BODY, LGD, STATE, DISTRICT = "Agartala Municipal Corporation", "249785", "TR", "West Tripura"
BASE = "https://agartalacity.tripura.gov.in"
PAGES = {"ward-secretaries": "/ward", "zone-offices": "/zonal_office"}
ZONE = re.compile(r"(?i)^\s*(North|South|East|West|Central)\s+Zone\s+Office\s*(.*?)\s*Phone\s*No\.?\s*:?\s*([\d\s/,-]+)\s*$")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": BASE + v, "page": k, "state": STATE, "india_only": True}}
            for k, v in PAGES.items()]


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "ward", "secretary", soup=soup):
        for r in rows:
            ward = _ward.wards_of(_ward.col(r, "ward no"))
            name, phone = _ward.col(r, "name"), _ward.col(r, "contact", "phone", "mobile")
            if len(ward) != 1 or not (name or phone):
                provenance.skip_row(r, 'skip: len(ward) != 1 or not (name or phone)')
                continue
            w = ward[0]
            recs.append(_ward.record(MODULE, f"w{w}:ward-secretary:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="ward", area=f"Ward {w}", post="Ward Secretary",
                                     name=name, phone=phone, wards=[w], wing="administration", source=p["url"], src_pos=r.pos))
    for li_no, li in enumerate(soup.find_all("li"), 1):
        m = ZONE.match(_esw.clean(li.get_text(" ")))
        if not m:
            provenance.skip_row(li, 'skip: not m')
            continue
        zone = f"{m.group(1).title()} Zone"
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:zone-office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=zone, zone=zone, post="Zone Office", phone=m.group(3),
                                 address=m.group(2).strip(" ,."), wing="administration", source=p["url"],
                                 src_pos={"selector": "li", "index": li_no, "text": m.group(0)}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("page") or "page", r.content)], "" if recs else "no ward table or zone list"
