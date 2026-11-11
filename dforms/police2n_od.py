"""Odisha: Commissionerate Police Bhubaneswar-Cuttack, bhubaneswarcuttackpolice.gov.in/organizational-structure/ (WordPress,
"Last Updated on" in the footer). For each urban police district (Bhubaneswar UPD, Kataka UPD) the page shows the DCP (name
and post in <div class="name"> / <div class="designation">) and six zones, each with its police stations
(<div class="..._zone_head">Zone 1</div> then <div class="..._station">Capital</div> ...). A zone is the area of an ACP (level
circle). Kept: the CP, Addl. CP and DCPs (level district, names, no phones), one record per zone (level circle, no officer on
the page) and one per station (level police_station, circle = the zone; no IIC names or phones on the page). Answers only
from India (no connection from outside, 2026-11-11). One queue item = the page. Record id dept:police2n_od:<upd>:<zone>[:<station>]."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, rec, slug, uniq

M = "police2n_od"
URL = "https://bhubaneswarcuttackpolice.gov.in/organizational-structure/"
DISTRICT = {"bhubaneswar": "Khordha", "kataka": "Cuttack", "cuttack": "Cuttack"}


def parse(html, url=URL, state="OD"):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    m = re.search(r"Last Updated on\s*:?\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", soup.get_text(" "))
    months = "january february march april may june july august september october november december".split()
    lu = f"{m.group(3)}-{months.index(m.group(2).lower()) + 1:02d}-{int(m.group(1)):02d}" if m and m.group(2).lower() in months else None
    for nm in soup.select("div.name"):
        des = nm.find_next_sibling("div", class_="designation")
        name, post = clean(nm.get_text(" ", strip=True)), clean(des.get_text(" ", strip=True)) if des else None
        mm = re.match(r"^(.+?)\s*\(([^()]*(?:COMMISSIONER|DCP)[^()]*)\)\s*$", name or "", re.I)
        if mm:                                    # top block: 'DR. SURESH DEV DATTA SINGH, IPS (COMMISSIONER OF POLICE)'
            name, post = mm.group(1), mm.group(2)
        name = re.sub(r"\s*,?\s*\b(?:IPS|OPS|OAPS-I)\b.*$", "", name or "").strip(" ,")
        if not name or not post:
            continue
        upd = nm.find_previous("h3")
        upd_name = clean(upd.get_text(" ", strip=True)) if upd and "Police District" in upd.get_text() else None
        dist = DISTRICT.get(slug(upd_name or "").split("-")[0]) if upd_name else None
        recs.append(rec(M, f"{slug(upd_name or 'commissionerate')}:{slug(post)}", level="district", office_type="office",
                        area=upd_name or "Bhubaneswar-Cuttack Commissionerate", post=post, name=name or None,
                        state=state, district=dist, source=url, last_updated=lu))
    for head in soup.find_all("div", class_=lambda c: c and any(x.endswith("_zone_head") for x in c.split())):
        zone = clean(head.get_text(" ", strip=True))
        upd = head.find_previous("h3")
        upd_name = re.sub(r"\s+", " ", clean(upd.get_text(" ", strip=True)) if upd else "").strip()
        dist = DISTRICT.get(slug(upd_name).split("-")[0])
        u = slug(upd_name or "upd")
        recs.append(rec(M, f"{u}:{slug(zone)}", level="circle", office_type="circle", area=f"{upd_name} {zone}", post="ACP",
                        state=state, district=dist, source=url, last_updated=lu))
        box = head.find_next_sibling("div") or head.parent
        for st in box.find_all("div", class_=lambda c: c and any(x.endswith("_station") for x in c.split())):
            name = clean(st.get_text(" ", strip=True))
            if not name:
                continue
            recs.append(rec(M, f"{u}:{slug(zone)}:{slug(name)}", office_type="police station", area=name, post="IIC",
                            circle=f"{upd_name} {zone}", state=state, district=dist, source=url, last_updated=lu))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, "organizational-structure", r.content)], "" if recs else "no rows"
