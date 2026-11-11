"""Bhubaneswar Municipal Corporation (www.bmc.gov.in): the 3 zones, the wards each zone holds, and the zone officers.
Two pages (answers from Germany; saved in archive.s1d.me 2026-11-05):
  /bmc/zones-wards       one tab per zone (#home North, #menu1 South-West, #menu2 South-East): "Deputy Commissioner <name>",
                         "Territorial Wards 1, 2, 3 ..." (the ward-to-zone mapping of all 67 wards), then one row per ward (ward no,
                         localities, corporator). The "Officers's Detail" column is commented out in the page: no ward officers.
  /bmc/officers-profile  <li><h5>name<small>post</small></h5> + phone / mobile / email: the zone Assistant Commissioners
                         ("Asst. Commissioner (North Zone)") and the Executive Engineers of the divisions and drainage zones.
Records: the zone Deputy Commissioners (level "zone", wards = the zone's territorial wards); from the profile page only the posts
that name a zone (wards from the zone page's mapping, written into the reader as ZONE_WARDS) or an engineering division (level
"division", no wards: the site does not say which wards a division holds). Record ids: dept:ward_bhubaneswar:<zone>:<post>:<name>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward_bhubaneswar"
BODY, LGD, STATE, DISTRICT = "Bhubaneswar Municipal Corporation", "250520", "OD", "Khordha"
BASE = "https://www.bmc.gov.in/bmc/"
TABS = {"home": "North Zone", "menu1": "South-West Zone", "menu2": "South-East Zone"}
# the zones-wards page as saved on 2026-11-05 (used by the officers-profile item, which names zones but not wards)
ZONE_WARDS = {
    "North Zone": "1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 26",
    "South-West Zone": "15, 22, 23, 24, 25, 27, 37, 38, 39, 46, 47, 48, 49, 50, 51, 52, 62, 63, 64, 65, 66",
    "South-East Zone": "28, 29, 30, 31, 32, 33, 34, 35, 36, 40, 41, 42, 43, 44, 45, 53, 54, 55, 56, 57, 58, 59, 60, 61 & 67",
}


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": BASE + k, "state": STATE, "kind": k}}
            for k in ("zones-wards", "officers-profile")]


def _zone_of(text):
    t = text.lower().replace(" ", "").replace("-", "")
    for z in ZONE_WARDS:
        if z.lower().replace(" ", "").replace("-", "") in t:
            return z
    return None


def parse_zones(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for tab, zone in TABS.items():
        pane = soup.find("div", id=tab)
        summ = pane.find("ul", class_="wardsummary") if pane else None
        if not summ:
            continue
        dc, wards = "", []
        for li in summ.find_all("li"):
            label = _esw.clean(li.find("label").get_text()) if li.find("label") else ""
            body = _esw.clean(li.get_text(" ").replace(label, "", 1))
            if "deputy commissioner" in label.lower():
                dc = body
            elif "ward" in label.lower():
                wards = _ward.wards_of(body)
        if not wards:
            wards = [_esw.clean(s.get_text()) for s in pane.find_all("span", class_="wardno")]
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:deputy-commissioner:{_esw.slug(dc) or 'post'}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone, post="Deputy Commissioner",
                                 name=dc, wards=wards, wing="administration", source=p["url"]))
    return recs


def parse_officers(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for li in soup.find_all("li"):
        h5 = li.find("h5")
        if not h5 or not h5.find("small"):
            continue
        post = _esw.clean(h5.find("small").get_text())
        name = _esw.clean(h5.get_text(" ").replace(h5.find("small").get_text(), ""))
        zone = _zone_of(post)
        div = re.search(r"(?i)division\s*[-–]?\s*([IVX\d]+)", post)
        if not zone and not div:
            continue
        d = li.find("div", class_="directory")
        phone = " ".join(_esw.clean(x.get_text()) for x in d.find_all("div", class_=["phone-d", "mobile-d"])) if d else ""
        email = " ".join([a.get("href", "").replace("mailto:", "") for a in d.find_all("a")]) if d else ""
        if zone:
            level, area, wards = "zone", zone, _ward.wards_of(ZONE_WARDS[zone])
        else:
            level, area, wards = "division", f"Division {div.group(1)}", None
        recs.append(_ward.record(MODULE, f"{_esw.slug(area)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level=level, area=area, zone=zone, post=post, name=name, phone=phone,
                                 email=email, wards=wards, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    kind = p.get("kind") or p["url"].rstrip("/").rsplit("/", 1)[-1]
    recs = parse_zones(r.text, p) if kind == "zones-wards" else parse_officers(r.text, p)
    return recs, [_esw.keep(MODULE, kind, r.content)], "" if recs else "no zone data"
