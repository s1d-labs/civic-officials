"""Rajasthan: Jodhpur Police Commissionerate (East + West), jodhpurpolice.rajasthan.gov.in/city-zones. One page with an SVG
map: each station area is a <g data-info="...Police Station NAME<br>Tel. : 0291-XXXXXXX..." latitude=".." logitude=".."> (the
site's spelling). No officer names or mobiles. Answers only from India. One queue item = the page.
Record id dept:police_rj:jodhpur:<station>."""
import html as htmlmod
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, phones, rec, slug, uniq

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

M = "police_rj"
URL = "https://jodhpurpolice.rajasthan.gov.in/city-zones"


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs, seen = [], set()
    for g in soup.find_all(attrs={"data-info": True}):
        info = BeautifulSoup(htmlmod.unescape(g["data-info"]).replace("<br>", "\n"), "lxml").get_text("\n")
        lines = [clean(x) for x in info.split("\n") if clean(x)]
        if not lines:
            continue
        name = lines[0]
        tel = " ".join(re.sub(r"(?i)^tel\.?\s*:?", "", x) for x in lines[1:] if re.search(r"(?i)tel|\d{6}", x))
        if name in seen:
            continue
        seen.add(name)
        lat, lon = g.get("latitude"), g.get("logitude") or g.get("longitude")
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            lat = lon = None
        recs.append(rec(M, f"jodhpur:{slug(re.sub(r'(?i)^police station\s+', '', name))}", area=name,
                        office_type="police station", post="SHO", phone=phones(tel), state="RJ", district="Jodhpur",
                        unit="Jodhpur Police Commissionerate", lat=lat, lon=lon, source=url))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, "jodhpur-city-zones.html", r.content)], "" if recs else "no stations"
