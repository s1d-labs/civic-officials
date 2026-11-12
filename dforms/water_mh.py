"""Maharashtra: Maharashtra Jeevan Pradhikaran (MJP) who's who, mjp.maharashtra.gov.in/whos-who/ (answers from Germany and India).

One WordPress page, one table per section (heading before the table: "Headquarters - Finance", "Other Offices Region - Amaravati",
"Region - Kokan" ...), columns Name | Designation | Phone | Email. Headquarters, and per region (Amaravati, Chhatrapati Sambhajinagar,
Kokan, Nagpur, Nashik, Pune) the chief engineer, superintending engineers and executive engineers ("Executive Engineer, Ratnagiri").
About 85 posts. No sub-division level, no date. One queue item.
Level: CE of a region = zone, SE = circle, EE = division, the rest = state (headquarters) or zone (a region office).
Area = the place in the post, else the region. Record ids: dept:water_mh:MH-MJP-<slug of section>:<slug of post>.
"""
import re

from dforms import _esw, _water

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_mh"
URL = "https://mjp.maharashtra.gov.in/whos-who/"
ORG = "Maharashtra Jeevan Pradhikaran"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "MH"}}]


def section(t):
    h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
    s = _esw.clean(h.get_text(" ")) if h else ""
    return re.sub(r"(?i)^other offices\s*", "", s)


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        rows = _esw.grid(t)
        if not rows or [h.lower() for h in rows[0][:2]] != ["name", "designation"]:
            continue
        sec = section(t)
        m = re.match(r"(?i)region\s*-\s*(.+)$", sec)
        region = m.group(1).strip() if m else None
        for row in rows[1:]:
            c = dict(zip([h.lower() for h in rows[0]], row))
            post, name = c.get("designation", ""), c.get("name", "")
            if not post:
                continue
            level = _water.level_of(post, "zone" if region else "state")
            if level == "state" and region:
                level = "zone"
            place = re.sub(r"(?i)^circle\s*,\s*", "", _water.area_after(post))
            area = place or region or sec
            title = post.split(",")[0].strip()
            key = _water.unique(f"MH-MJP-{_esw.slug(sec)}:{_esw.slug(post)}", seen)
            recs.append(_esw.record(MODULE, key, dept="water", level=level, area=area, post=title, name=name,
                                    phone=_esw.phones(c.get("phone")), email=_esw.emails(c.get("email")), state="MH",
                                    office_id=f"MH-MJP-{_esw.slug(region or 'hq')}-{_esw.slug(post)}", org=ORG,
                                    region=region, section=sec if not region else None, source=url))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "whos-who", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
