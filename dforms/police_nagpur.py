"""Nagpur City Police (commissionerate, 37 stations): nagpurpolice.gov.in/police-stations.php, one page of div.station-card:
h3.station-name, info items by icon (fa-location-dot = place, fa-phone = landline(s) without the 0712 STD code, fa-envelope =
email), div.officer-name (officer in charge, "प्रभारी अधिकारी"; Marathi or English), a Google Maps link. No mobiles, no rank.
Works from outside India. One queue item = the page. Record id dept:police_nagpur:<station>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html cards"     # source trail (provenance.py): how this reader reads its sources

M = "police_nagpur"
URL = "https://nagpurpolice.gov.in/police-stations.php"


def key(s):
    """slug() that keeps Indic vowel signs."""
    return re.sub(r"[^\wऀ-෿]+", "-", (clean(s) or "").lower()).strip("-") or slug(s)


def std(nums, code="0712"):
    if not nums:
        return nums
    return ", ".join(f"{code}-{n}" if re.fullmatch(r"\d{7}", n) else n for n in nums.split(", "))


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ci, card in enumerate(soup.select("div.station-card"), 1):
        h = card.select_one(".station-name")
        station = clean(h.get_text(" ", strip=True)) if h else None
        if not station:
            continue
        f = {}
        for it in card.select(".info-item"):
            i = it.find("i")
            cls = " ".join(i.get("class", [])) if i else ""
            txt = clean(it.get_text(" ", strip=True))
            if "fa-phone" in cls:
                f["landline"] = std(phones(txt))
            elif "fa-envelope" in cls:
                a = it.find("a", href=re.compile("^mailto:", re.I))
                f["email"] = email(a["href"][7:] if a else txt)
            elif "fa-location" in cls:
                f["place"] = txt
        on = card.select_one(".officer-name")
        ot = card.select_one(".officer-title")
        mp = card.find("a", href=re.compile(r"maps\.(app\.goo\.gl|google)"))
        recs.append(rec(M, key(station), area=station, post=clean(ot.get_text(" ", strip=True)) if ot else "Officer in charge",
                        name=clean(on.get_text(" ", strip=True)) if on else None, phone=f.get("landline"),
                        landline=f.get("landline"), email=f.get("email"), address=f.get("place"), map_link=mp["href"] if mp else None,
                        state="MH", district="Nagpur", source=url, src_pos={"selector": "div.station-card", "card": ci}))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, "police-stations.html", r.content)], "" if recs else "no station cards"
