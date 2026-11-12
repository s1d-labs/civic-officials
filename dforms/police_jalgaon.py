"""Jalgaon district police (Maharashtra, 37 stations): one page per station, jalgaonpolice.gov.in/police-stations?id=N
(ids from the station dropdown #policeStationBox on /police-stations). Page: h2 station name; two cards: officer in charge
(name, rank, mobile, station) and station (landline, email, address, sub-divisional officer); DIGIPIN; Google Maps embed
(!2d lon !3d lat). Text is Marathi. Some mobiles are printed with a digit missing (e.g. "88579 7016"): such a number is kept
only in mobile_as_published. Works from outside India. One queue item = one station page. Record id dept:police_jalgaon:<id>."""
import re

from bs4 import BeautifulSoup

from dforms._police import ascii_digits, clean, email, gz, phones, rec

METHOD = "html cards (fields by icon class)"     # source trail (provenance.py): how this reader reads its sources

M = "police_jalgaon"
LIST = "https://jalgaonpolice.gov.in/police-stations"
URL = LIST + "?id={}"


def items(get):
    r = get(LIST)
    if r is None:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    sel = soup.find("select", id="policeStationBox")
    out = []
    for o in sel.find_all("option") if sel else []:
        v = (o.get("value") or "").strip()
        if v.isdigit():
            out.append({"key": f"{M}:{v}", "payload": {"reader": M, "url": URL.format(v), "id": v, "state": "MH",
                                                       "station": clean(o.get_text(" ", strip=True))}})
    return out


def _info(card):
    """Card fields by icon class: fa-user, fa-graduation-cap, fa-mobile, fa-phone, fa-envelope, fa-map-marker, fa-building."""
    f = {}
    for div in card.select(".stn-prof-info"):
        i = div.find("i")
        cls = [c for c in (i.get("class", []) if i else []) if c.startswith("fa-")]
        a = div.find("a")
        val = clean(a.get("href", "").split(":", 1)[-1] if a else div.get_text(" ", strip=True))
        if cls:
            f[cls[0]] = val
    return f


def parse(html, url, sid):
    soup = BeautifulSoup(html, "lxml")
    first = soup.select_one(".stn-prof-card")
    h2 = first.find_previous("h2", class_="section__titletext") if first else None
    station = clean(h2.get_text(" ", strip=True)) if h2 else None
    cards = [_info(c) for c in soup.select(".stn-prof-card")]
    off = next((c for c in cards if "fa-user" in c), {})
    stn = next((c for c in cards if "fa-envelope" in c or "fa-map-marker" in c), {})
    mob_raw = ascii_digits(off.get("fa-mobile") or "")
    mob = phones(mob_raw) if len(re.sub(r"\D", "", mob_raw)) == 10 else None
    m = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", html)
    dp = re.search(r"DIGIPIN\s*:\s*([0-9A-Z]{3}-[0-9A-Z]{3}-[0-9A-Z]{4})", html)
    if not station and not off:
        return []
    return [rec(M, str(sid), area=station or off.get("fa-building"), post="Police station in-charge", name=off.get("fa-user"),
                rank=off.get("fa-graduation-cap"), phone=phones(mob, stn.get("fa-phone")), mobile=mob,
                mobile_as_published=mob_raw.strip() if mob_raw.strip() and not mob else None, landline=phones(stn.get("fa-phone")),
                email=email(stn.get("fa-envelope") or ""), address=stn.get("fa-map-marker"), subdivision=stn.get("fa-building"),
                digipin=dp.group(1) if dp else None, lat=float(m.group(2)) if m else None, lon=float(m.group(1)) if m else None,
                state="MH", district="Jalgaon", office_id=str(sid), source=url,
                src_pos={"selector": ".stn-prof-card (fields by icon class)"})]


def fetch(p, get):
    sid = p.get("id") or re.search(r"id=(\d+)", p["url"]).group(1)
    url = p.get("url") or URL.format(sid)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url, sid)
    return recs, [gz(M, f"station-{sid}.html", r.content)], "" if recs else "no station block"
