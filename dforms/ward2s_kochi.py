"""Kochi Municipal Corporation (kochicorporation.lsgkerala.gov.in, the LSGD Kerala Drupal platform): its zonal offices, health
circles, zone revenue and section staff, and the engineers. One page, /en/phone-numbers/404 ("Phone Numbers"; answers from
Germany; saved in archive.s1d.me 2026-11-09; the page shows "Last Updated: Thursday, October 22, 2026"). The page has one table
per block; the reader uses these (the other blocks are councillors, standing committees and non-corporation offices):
  ZONAL OFFICES            OFFICE NAME | CONTACT NO: Vyttila, Edapally, Fort Kochi, Mattanchery, Palluruthy, Pachalam
  HEAD OF THE DEPARTMENTS  NAME | DESIGNATION | CONTACT NO (Secretary, Superintending Engineer, Revenue Officers incl. "(WEST
                           ZONE)", Health Officer, Executive Engineers)
  (other important)        NAME | DESIGNATION | PHONE: Assistant Executive Engineers, Assistant Engineers, Clean City Managers
  SUPERINTENDENTS          No. | NAME | SECTION | OFFICE | PHONE (office = MAIN OFFICE or a zonal office)
  HEALTH INSPECTORS        No. | NAME | OFFICE ("HEALTH CIRCLE 1".."22") | PLACE (the circle office's place) | PHONE
  REVENUE INSPECTORS       NO | NAME | OFFICE (MAIN OFFICE or a zonal office) | PHONE
The page does not say which of the 76 divisions (wards) each zone or health circle holds, so records have no "wards" key.
Records: zonal offices and staff posted to a zonal office at level "zone" (area = the zone, e.g. "Fort Kochi Zonal Office");
health inspectors at level "circle" (area "Health Circle 3 (Mattanchery)"); staff of the main office and the body-wide engineers
(Assistant Engineers with no section or ward given) at level "body". Record ids: dept:ward2s_kochi:<area slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_kochi"
BODY, LGD, STATE, DISTRICT = "Kochi Municipal Corporation", "252220", "KL", "Ernakulam"
URL = "https://kochicorporation.lsgkerala.gov.in/en/phone-numbers/404"
# the zonal offices as the page spells them (in its different tables) -> one name
ZONES = {"vyttila": "Vyttila", "vytilla": "Vyttila", "edapally": "Edappally", "edappally": "Edappally", "fortkochi": "Fort Kochi",
         "mattanchery": "Mattancherry", "mattancherry": "Mattancherry", "palluruthy": "Palluruthy", "pachalam": "Pachalam"}


def items(get=None):
    return [{"key": f"{MODULE}-phone-numbers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def zone_of(office):
    """"FORTKOCHI" / "VYTTILA REVENUE" / "EDAPALLY" -> the zone name; "MAIN OFFICE" or anything else -> None."""
    k = re.sub(r"[^a-z]", "", _esw.clean(office).lower().replace("revenue", ""))
    for key, z in ZONES.items():
        if k.startswith(key):
            return z
    return None


def post_of(s):
    p = _esw.clean(s)
    p = re.sub(r"(?i)\bASST\.?\s*", "Assistant ", p)
    p = re.sub(r"(?i)\bEXE\.?\s*", "Executive ", p)
    p = re.sub(r"(?i)\bCCM\b", "Clean City Manager", p)
    p = re.sub(r"(?i)\bAHO\b", "Additional Health Officer", p)
    return re.sub(r"\s+", " ", p).strip().title()


def last_updated(html):
    m = re.search(r"Last Updated:\s*(?:<[^>]+>\s*)*\w+day,\s*(\w+ \d{1,2}, \d{4})", html)
    if not m:
        return None
    import datetime
    try:
        return datetime.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def heading(t):
    """The block heading written just before a table ("ZONAL OFFICES", "OTHER OFFICERS"), lower case; "" when there is none."""
    h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "p", "strong"])
    return _esw.clean(h.get_text()).lower() if h else ""


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    upd = last_updated(html)

    cur = {}     # the src_pos of the row being read (source trail)

    def add(level, area, post, name="", phone="", zone=None, **extra):
        recs.append(_ward.record(MODULE, f"{_esw.slug(area)}:{_esw.slug(post)}:{_esw.slug(name) or 'office'}", seen, body=BODY,
                                 lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area, post=post, name=name,
                                 phone=phone, zone=zone, source=p["url"], last_updated=upd, **extra, src_pos=cur.get("pos")))

    def staff(name, post, office, phone, **extra):
        z = zone_of(office)
        if z:
            add("zone", f"{z} Zonal Office", post, name, phone, zone=z, **extra)
        else:
            add("body", BODY, post, name, phone, office=_esw.clean(office).title() or None, **extra)

    for t in soup.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g:
            continue
        heads = [[c.lower() for c in r] for r in g[:2]]
        top = " ".join(heads[0])
        if heads[0][:2] == ["office name", "contact no"] and heading(t) == "zonal offices":
            for r, rp in zip(g[1:], gp[1:]):
                cur["pos"] = rp
                z = zone_of(r[0])
                if z and len(r) > 1:
                    add("zone", f"{z} Zonal Office", "Zonal Office", phone=r[1], zone=z)
        elif "health inspectors" in top:
            for r, rp in zip(g[2:], gp[2:]):
                cur["pos"] = rp
                if len(r) < 5 or not _esw.clean(r[1]):
                    provenance.skip_row(r, 'skip: len(r) < 5 or not _esw.clean(r[1])')
                    continue
                circle = _esw.clean(r[2]).title()
                place = _esw.clean(r[3]).title()
                area = f"{circle} ({place})" if place else circle
                add("circle", area, "Health Inspector", r[1], r[4], circle=circle, place=place or None)
        elif "revenue inspectors" in top:
            for r, rp in zip(g[2:], gp[2:]):
                cur["pos"] = rp
                if len(r) >= 4 and _esw.clean(r[1]):
                    staff(r[1], "Revenue Inspector", r[2], r[3])
        elif "superintendents" in top:
            for r, rp in zip(g[2:], gp[2:]):
                cur["pos"] = rp
                if len(r) >= 5 and _esw.clean(r[1]):
                    sec = _esw.clean(r[2]).title()
                    staff(r[1], f"Superintendent ({sec})" if sec else "Superintendent", r[3], r[4], section=sec or None)
        elif heads[0][:2] == ["name", "designation"] and heading(t) != "other officers":
            for r, rp in zip(g[1:], gp[1:]):
                cur["pos"] = rp
                if len(r) >= 3 and _esw.clean(r[0]) and _esw.clean(r[1]):
                    post = post_of(r[1])
                    staff(r[0], post, "WEST ZONE" if "west" in post.lower() else "", r[2])
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "phone-numbers", r.content)], "" if recs else "no officer tables"
