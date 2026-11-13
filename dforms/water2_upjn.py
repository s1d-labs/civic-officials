"""UP Jal Nigam (Rural), Uttar Pradesh: the staff directory www.upjn.co.in/Contact/StaffDirectory (Hindi). Works from Germany (live
sample 2026-11-11; not in archive.s1d.me). The page footer shows "Last Updated Date : 25 June Wednesday" from a script clock, so
no date is kept. UP Jal Nigam (Urban) has no reachable site (jalnigam.up.gov.in has no DNS, jn.upsdc.gov.in times out from
Germany and India; upjn.org is a squatted domain).
Two tables:
1. Civil cadre: मुख्य अभियंता (क्षेत्र) | मण्डल कार्यालय | S.No | खंड कार्यालय | अधिकारियों का नाम व फोन नं. Zone and circle names
   stand in one row, the zone CE and circle SE ("name, mobile") in the next row (odd rowspans), then one row per division with
   its EE: 81 divisions in about 10 zones and 20 circles.
2. Electrical / mechanical (वि०/यां०) cadre: zone | circle office with its SE ("..., श्री <name>, अधी०अभि०, <mobile>") | division
   office with its EE | n | district: about 15 divisions, each with the districts it covers.
Names, areas and posts are Hindi: name / area carry the Hindi text (name_regional / area_regional the same), post is English,
post_regional as written. Levels: CE = zone, SE = circle, EE = division. About 110 civil and 25 E/M records.
Record ids: dept:water2_upjn:civil:<zone|circle|division>:<area> and dept:water2_upjn:em:<circle|division>:<office>.
"""
import re

from bs4 import BeautifulSoup

from dforms import _esw
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources


def slug(s):
    """Lower-case key that keeps Devanagari letters (the areas are Hindi)."""
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", "-", (s or "").lower()).strip("-")[:120]

MODULE = "water2_upjn"
URL = "https://www.upjn.co.in/Contact/StaffDirectory"
ORG = "UP Jal Nigam (Rural)"
MOB = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
POSTS = {"zone": ("Chief Engineer (Zone)", "मुख्य अभियंता"), "circle": ("Superintending Engineer", "अधीक्षण अभियन्ता"),
         "division": ("Executive Engineer", "अधिशासी अभियन्ता")}


def person(t):
    """'अरविन्द कुमार त्रिपाठी , 9532501599' -> (name, phones)."""
    t = _esw.clean(t) or ""
    phones = MOB.findall(t)
    name = MOB.sub(" ", t)
    name = re.sub(r",\s*(कार्यवाहक)", r" (\1)", name)
    name = _esw.clean(re.sub(r"[\s,]+$", "", re.sub(r"^[\s,]+", "", re.sub(r"\s*,\s*(,\s*)+", ", ", name))))
    return name, ", ".join(dict.fromkeys(phones)) or None


class Recs:
    def __init__(self, url):
        self.url, self.out, self.seen = url, [], {}

    def add(self, key, level, area, name, phones, parents=None, **extra):
        key = slug(key) or "x"
        if key in self.seen:
            d = self.seen[key]
            if extra.get("zones"):
                d["zones"] = sorted(set(d.get("zones", [])) | set(extra["zones"]))
            return
        post, post_hi = POSTS[level]
        district = extra.pop("district", None)
        rid, d = _esw.record(MODULE, key, dept="water", level=level, area=area, area_regional=area, post=post, post_regional=post_hi,
                             name=name, name_regional=name, phone=phones, state="UP", district=district, source=self.url,
                             org=ORG, parents={k: v for k, v in (parents or {}).items() if v} or None, **extra)
        self.seen[key] = d
        self.out.append((rid, d))


def civil(table, R):
    zone = circle = None
    pending = []
    for tr in table.find_all("tr"):
        cells = [_esw.clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]
        idx = next((i for i, c in enumerate(cells) if c.isdigit()), None)
        if idx is None:
            provenance.skip_row(tr, 'skip: idx is None')
            continue
        tp = tr_pos(tr)
        for ci, c in enumerate(cells[:idx], 1):
            if MOB.search(c):
                if pending:
                    lvl = pending.pop(0)
                    name, ph = person(c)
                    area = zone if lvl == "zone" else circle
                    R.add(f"civil:{lvl}:{area}", lvl, area, name, ph, {"zone": zone} if lvl == "circle" else None, cadre="civil",
                          src_pos=dict(tp, col=ci))
            elif c.endswith("क्षेत्र"):
                zone, pending = c, ["zone"]
            elif c.endswith("मण्डल"):
                circle = c
                pending = [p for p in pending if p != "circle"] + ["circle"]
        if len(cells) >= idx + 3:
            area = cells[idx + 1]
            name, ph = person(cells[idx + 2])
            dist = area.split(",")[-1].strip() if "," in area else area
            R.add(f"civil:division:{area}", "division", area, name, ph, {"zone": zone, "circle": circle}, cadre="civil",
                  district=dist, src_pos=dict(tp, col=idx + 3))


def _office(c):
    """'खण्ड कार्यालय (वि०/यां०) लखनऊ,श्री सै० मो० शावाज, अधि०अभि०, 9151919633' -> (office, name, phones)."""
    ph = ", ".join(dict.fromkeys(MOB.findall(c))) or None
    t = re.sub(r"[\s,]*(अधी०\s*अभि०|अधि०\s*अभि०)[\s,]*", ", ", MOB.sub(" ", c[c.find(")") + 1:] if ")" in c else c), count=1)
    m = re.match(r"^\s*([^\s,]+)[\s,]+(.*)$", t)
    head = c[: c.find(")") + 1] if ")" in c else ""
    place, name = (m.group(1), m.group(2)) if m else (t, "")
    return _esw.clean(f"{head} {place}"), _esw.clean(re.sub(r"[\s,]+$", "", name)), ph


def em(table, R):
    zone = circle = division = None
    for tr in table.find_all("tr"):
        cells = [_esw.clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]
        tp = tr_pos(tr)
        for i, c in enumerate(cells):
            if c.endswith("क्षेत्र") and not MOB.search(c):
                zone = c
            elif "मण्डल" in c and MOB.search(c):
                off, name, ph = _office(c)
                circle = off
                R.add(f"em:circle:{off}", "circle", off, name, ph, None, cadre="electrical-mechanical", zones=[zone] if zone else None,
                      src_pos=dict(tp, col=i + 1))
            elif c.startswith("खण्ड") and MOB.search(c):
                off, name, ph = _office(c)
                division = (f"em:division:{off}", off, name, ph)
                R.add(division[0], "division", off, name, ph, {"circle": circle, "zone": zone}, cadre="electrical-mechanical",
                      districts=[], src_pos=dict(tp, col=i + 1))
            elif c.isdigit() and i + 1 < len(cells) and division:
                d = R.seen.get(slug(division[0]))
                if d is not None:
                    d.setdefault("districts", []).append(cells[i + 1].strip("()"))
                break


def parse(html, url=URL):
    R = Recs(url)
    tables = BeautifulSoup(html, "lxml").find_all("table")
    for t in tables:
        head = " ".join(td.get_text(" ", strip=True) for td in (t.find("tr") or t).find_all(["td", "th"]))
        if "खंड कार्यालय" in head and "नाम" in head:
            civil(t, R)
        elif "क्षेत्रीय कार्यालय" in head:
            em(t, R)
    return R.out


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_esw.keep(MODULE, "staff-directory", r.content)], "" if recs else "no rows"
