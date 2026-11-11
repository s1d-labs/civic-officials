"""Surat Municipal Corporation (www.suratmunicipal.gov.in): the officers of its 9 zones. Answers from Germany (live sample
2026-11-11; the RTI zone files are in archive.s1d.me, these pages are not). One page per zone, /Zones/<Area>/<Zone> (ASP.NET MVC):
  1. a box table: the zone, the zone office address and phones, then the Zonal Chief (name | post | (M) mobile | (O) office | email
     name);
  2. a table with three columns Administrative | Engineering | Health; each cell: <span class="text-bold">name</span><br>post<br>
     (M) mobile<br>(O) office phone<br><div class="contact-email govdotin">local part</div>. The page shows only the local part of
     the email ("amc.wz"; the domain is added by the site's style sheet), kept as the extra key "email_local".
The zone pages do not list the zone's wards in this table, so records have no "wards" key (Surat has 30 four-member wards).
Records: level "zone". Record ids: dept:ward_surat:<zone slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward_surat"
BODY, LGD, STATE, DISTRICT = "Surat Municipal Corporation", "251231", "GJ", "Surat"
BASE = "https://www.suratmunicipal.gov.in/Zones/"
ZONES = {"West Zone": "West/WestZone", "Central Zone": "Central/CentralZone", "North Zone": "North/NorthZone",
         "East Zone A": "East/EastZoneA", "East Zone B": "East/EastZoneB", "South Zone A": "South/SouthZoneA",
         "South Zone B": "South/SouthZoneB", "South West Zone": "SouthWest/SouthWestZone", "South East Zone": "SouthEast/SouthEastZone"}
WINGS = {"administrative": "administration", "engineering": "engineering", "health": "health"}


def items(get=None):
    return [{"key": f"{MODULE}-{_esw.slug(z)}", "payload": {"reader": MODULE, "url": BASE + path, "state": STATE, "zone": z}}
            for z, path in ZONES.items()]


def _people(td):
    """[(name, post, mobile, office, email)] of one cell (one or more officers, each starting with a bold name): the text after
    each bold name up to the next one, in document order (the zonal chief's name and post sit in a div, the phones after it)."""
    bolds = td.find_all("span", class_="text-bold")
    out = []
    for i, b in enumerate(bolds):
        stop = bolds[i + 1] if i + 1 < len(bolds) else None
        texts, mail = [], ""
        for el in b.next_elements:
            if el is stop:
                break
            if not isinstance(el, str) or el.find_parent("td") is not td or el.parent is b:
                continue
            t = _esw.clean(el)
            if not t:
                continue
            if el.parent.name == "div" and "contact-email" in (el.parent.get("class") or []):
                mail = t
            else:
                texts.append(t)
        mob = " ".join(re.sub(r"^\(M\)\s*", "", t) for t in texts if t.startswith("(M)"))
        off = " ".join(re.sub(r"^\(O\)\s*", "", t) for t in texts if t.startswith("(O)"))
        post = " ".join(t for t in texts if not t.startswith("("))
        out.append((_esw.clean(b.get_text()), post, mob, off, mail))
    return out


def parse(html, p):
    zone = p.get("zone") or next((z for z, path in ZONES.items() if p["url"].endswith(path)), "Zone")
    soup = _esw.soup(html)
    seen, recs, address = set(), [], None
    for t in soup.find_all("table"):
        heads = [_esw.clean(th.get_text()).lower() for th in t.find_all("th")]
        if heads and all(h in WINGS for h in heads):
            for tr in t.find_all("tr"):
                for i, td in enumerate(tr.find_all("td")):
                    for name, post, mob, off, mail in _people(td):
                        recs.append(("cell", WINGS[heads[i]] if i < len(heads) else None, name, post, mob, off, mail))
        elif t.find("span", class_="text-bold"):
            rows = t.find_all("tr")
            if len(rows) > 1 and not address:
                address = _esw.clean(rows[1].get_text(" ")).split(" | ")[0]
            for td in t.find_all("td"):
                for name, post, mob, off, mail in _people(td):
                    recs.append(("head", None, name, post, mob, off, mail))
    out = []
    for kind, wing, name, post, mob, off, mail in recs:
        if not (name or mob):
            continue
        out.append(_ward.record(MODULE, f"{_esw.slug(zone)}:{_esw.slug(post) or 'post'}:{_esw.slug(name) or 'n'}", seen, body=BODY,
                                lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone, post=post, name=name,
                                phone=", ".join(x for x in (mob, off) if x), address=address, wing=wing or _ward.wing_of(post),
                                email=_esw.emails(mail) if "[at]" in mail or "@" in mail else "",
                                email_local=None if "[at]" in mail or "@" in mail else mail or None, source=p["url"]))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, _esw.slug(p.get("zone") or p["url"][-30:]), r.content)], "" if recs else "no officer table"
