"""Vadodara Municipal Corporation (vmc.gov.in): the officers and offices of each of its 19 wards and the ward-to-zone mapping.
India only: vmc.gov.in does not answer from Germany (samples fetched from India 2026-11-11; not in archive.s1d.me). Three pages:
  /vmcengwing.aspx              "Ward Engineering Wing": one table per ward, ID | DESIGNATION | NAME | MOBILE NO; the ward is in the
                                post ("Deputy Engineer(WARD 04)", "Ad. Asst. Engineer(WARD 04)").
  /vmcrevwing.aspx              "Ward Revenue Wing": the same layout (Ward Officer, Revenue Officer of each ward).
  /ViewContactWardOffices.aspx  "Ward Offices": Zone | Ward | Address (Gujarati) | Address (English): the office of every ward and
                                the zone it belongs to (East | પૂર્વ ...).
Records: level "ward", wards = [the ward]. Ward offices: post "Ward Office", the address (area_regional / address_regional =
Gujarati), zone. Record ids: dept:ward_vadodara:w<NN>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_vadodara"
BODY, LGD, STATE, DISTRICT = "Vadodara Municipal Corporation", "251209", "GJ", "Vadodara"
BASE = "https://vmc.gov.in/"
PAGES = {"vmcengwing.aspx": "engineering", "vmcrevwing.aspx": "revenue", "ViewContactWardOffices.aspx": "offices"}


def items(get=None):
    return [{"key": f"{MODULE}-{k.split('.')[0].lower()}", "payload": {"reader": MODULE, "url": BASE + k, "state": STATE, "kind": v,
                                                                       "india_only": True}} for k, v in PAGES.items()]


def parse_wing(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "designation", "name", "mobile"):
        for r in rows:
            post, name, phone = _ward.col(r, "designation"), _ward.col(r, "name"), _ward.col(r, "mobile")
            m = re.search(r"\(\s*WARD\s*0*(\d+)\s*\)", post, re.I)
            if not m or not (name or phone):
                continue
            w = m.group(1)
            post = _esw.clean(post[:m.start()] + post[m.end():])
            recs.append(_ward.record(MODULE, f"w{int(w):02d}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}", seen, body=BODY, lgd=LGD,
                                     state=STATE, district=DISTRICT, level="ward", area=f"Ward {w}", post=post, name=name,
                                     phone=phone, wards=[w], wing="administration" if _ward.role_of(post) == "head" else
                                     p.get("kind") if p.get("kind") in ("engineering", "revenue") else None,
                                     source=p["url"]))
    return recs


def parse_offices(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "zone", "ward", "address"):
        for r in rows:
            w = _ward.wards_of(_ward.col(r, "ward"))
            if not w:
                continue
            zone_en, _, zone_gu = _ward.col(r, "zone").partition("|")
            zone = f"{zone_en.strip()} Zone"
            en = next((v for k, v in r.items() if "english" in k.lower()), "")
            gu = next((v for k, v in r.items() if "gujarati" in k.lower()), "")
            recs.append(_ward.record(MODULE, f"w{int(w[0]):02d}:ward-office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                     level="ward", area=f"Ward {w[0]}", post="Ward Office", address=en, address_regional=gu or None,
                                     zone=zone, zone_regional=zone_gu.strip() or None, wards=w, wing="administration",
                                     source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    kind = p.get("kind") or PAGES.get(p["url"].rsplit("/", 1)[-1], "engineering")
    recs = parse_offices(r.text, p) if kind == "offices" else parse_wing(r.text, dict(p, kind=kind))
    return recs, [_esw.keep(MODULE, kind, r.content)], "" if recs else "no ward tables"
