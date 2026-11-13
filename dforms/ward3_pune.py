"""Pune Municipal Corporation (pmc.gov.in): the 5 zones (Deputy Commissioner of each zone) and the 15 ward offices (Assistant
Municipal Commissioner of each ward office, with the electoral wards / prabhags it covers). The site is a Next.js app; its pages
read two JSON answers of the site's own content API (webadmin.pmc.gov.in, base url in the site's _app script, 2026-11-13):
  /api/zone-officer-data/zone_officers?lang=en    list: title, address, contact_no, email, designation, zone_name, officers[name, phone]
  /api/ward/ward_offices?zone=&lang=en            {"data": list}: title, address, contact_no, email, ward_name, zone_name,
                                                  prabhag[prabhag_number, name], officers[name, phone] (empty zone = all 15)
Live sample from dev-vps-3 (Mumbai) 2026-11-13: 5 zones, 15 ward offices, 41 prabhags. Not in archive.s1d.me.
Records: one per officer (or one per office when it names no officer): zone heads at level "zone", ward office heads at level
"ward" (wards = the prabhag numbers). Ids: dept:ward3_pune:<zone|ward>:<office slug>:<n>.
"""
import json

import provenance
from dforms import _esw, _ward

METHOD = "json api (site content API)"

MODULE = "ward3_pune"
BODY, LGD, STATE, DISTRICT = "Pune Municipal Corporation", "251530", "MH", "Pune"
API = "https://webadmin.pmc.gov.in/api"
ZONES = f"{API}/zone-officer-data/zone_officers?lang=en"
WARDS = f"{API}/ward/ward_offices?zone=&lang=en"


def items(get=None):
    return [{"key": f"{MODULE}-zones-wards", "payload": {"reader": MODULE, "url": ZONES, "url_wards": WARDS, "state": STATE}}]


def _people(o):
    out = [(x.get("name", ""), x.get("phone", "")) for x in o.get("officers") or [] if x.get("name") or x.get("phone")]
    return out or [("", "")]


def parse_zones(rows, url):
    seen, recs = set(), []
    for i, o in enumerate(rows):
        zone = _esw.clean(o.get("title") or o.get("zone_name"))
        for n, (name, phone) in enumerate(_people(o), 1):
            recs.append(_ward.record(MODULE, f"zone:{_esw.slug(zone)}:{n}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=zone, zone=zone,
                                     post=o.get("designation") or "Deputy Commissioner", name=name,
                                     phone=", ".join(p for p in (phone, o.get("contact_no")) if p), email=o.get("email") or "",
                                     address=o.get("address"), role="head", source=url, src_pos={"index": i, "id": zone}))
    return recs


def parse_wards(rows, url):
    seen, recs = set(), []
    for i, o in enumerate(rows):
        office = _esw.clean(o.get("title") or o.get("ward_name"))
        wards = [str(int(p["prabhag_number"])) for p in o.get("prabhag") or []
                 if str(p.get("prabhag_number", "")).strip().isdigit()]
        names = "; ".join(_esw.clean(p.get("name")) for p in o.get("prabhag") or [] if p.get("name"))
        for n, (name, phone) in enumerate(_people(o), 1):
            recs.append(_ward.record(MODULE, f"ward:{_esw.slug(office)}:{n}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="ward", area=office, zone=o.get("zone_name"),
                                     post="Assistant Municipal Commissioner (Ward Office)", name=name,
                                     phone=", ".join(p for p in (phone, o.get("contact_no")) if p), email=o.get("email") or "",
                                     address=o.get("address"), wards=wards, ward_names=names or None, role="head",
                                     wing="administration", source=url, src_pos={"index": i, "id": office}))
    return recs


def _json(r):
    try:
        return json.loads(r.content)
    except (ValueError, TypeError):
        return None


def fetch(p, get):
    recs, files, why = [], [], []
    for url, name, parse in ((p["url"], "zones", parse_zones), (p.get("url_wards", WARDS), "ward-offices", parse_wards)):
        r = get(url)
        if r is None:
            why.append(f"{name}: no answer")
            continue
        files.append(_esw.keep(MODULE, name, r.content, "json"))
        d = _json(r)
        rows = d.get("data") if isinstance(d, dict) else d
        if not isinstance(rows, list):
            why.append(f"{name}: not a json list")
            continue
        recs += _ward.tag(parse(rows, url), r, url, METHOD)
    return recs, files, "; ".join(why) if not recs else ""
