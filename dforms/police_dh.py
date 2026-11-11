"""Dadra and Nagar Haveli and Daman and Diu Police: police.ddd.gov.in/police-station/ (S3WaaS cards, last updated 05.03.2021).
Works from outside India. Each card: station name (link to /division/<slug>/) and one text 'Address – ... Phone – ...'.
7 stations (Daman 3, Diu 2, DNH 2); no officer names or mobiles. District from the address. One queue item = the page.
Record id dept:police_dh:<division slug>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, phones, rec, slug, uniq

M = "police_dh"
URL = "https://police.ddd.gov.in/police-station/"
SPLIT = re.compile(r"\s*(?:Phone|Telephone(?: No\.?| Number)?|Contact(?: No)?)\s*[:–-]?\s*", re.I)


def district(addr):
    a = addr or ""
    if re.search(r"\bDiu\b", a):
        return "Diu"
    if re.search(r"\bDNH\b|Silvassa|Khanvel|Dadra|Naroli", a, re.I):
        return "Dadra and Nagar Haveli"
    if "Daman" in a:
        return "Daman"
    return None


def last_updated(soup):
    m = re.search(r"Last Updated:\s*(\d{2})\.(\d{2})\.(\d{4})", soup.get_text(" ", strip=True))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    lu = last_updated(soup)
    recs = []
    for card in soup.select(".gen-card-content"):
        a = card.select_one("h2 a")
        p = card.find("p")
        if not a or not p:
            continue
        name = clean(a.get_text(" ", strip=True))
        text = clean(p.get_text(" ", strip=True))
        parts = SPLIT.split(text, maxsplit=1)
        addr = re.sub(r"^Address\s*[:–-]?\s*", "", parts[0]).strip(" ,")
        num = parts[1] if len(parts) > 1 else None
        key = (a.get("href") or "").rstrip("/").rsplit("/", 1)[-1] or slug(name)
        recs.append(rec(M, key, area=name, post="Station (landline)", phone=phones(num), address=addr, state="DH",
                        district=district(addr), office_id=key, source=a.get("href") or url, list_url=url, last_updated=lu))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, "police-station.html", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
