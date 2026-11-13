"""Andhra Pradesh: fire stations and fire officers of the AP State Disaster Response & Fire Services Department, from
fireservices.ap.gov.in/Fire/fire_contact_distofficersingle?distId=<n> (28 districts; the site's index page
/Fire/fire_contact_distofficer names 28). Each district page has:
- the District Disaster Response & Fire Officer (name, mobile, address, office phone, email written x[dot]y[at]gmail[dot]com);
- a table "<district> Fire station list with details": S.No | Name of the Fire Station | Address with PIN | Name of the Station
  Fire Officer | Station phone with STD code | Mobile | E-mail (fire outposts too, under their parent station's officer);
- the map script: locations = [['<station>', lat, lon], ...].
Answers only from India (this box gets no answer; the India VPS and archive.s1d.me copies of 2026-11-06 have it). A distId past
the last district answers HTTP 500. One queue item per district: 28 items, about 200 stations.
Record ids: dept:civic_fire_ap:<district slug>:<station slug>, and dept:civic_fire_ap:<district slug>:dfo for the district officer.
"""
import re

from dforms import _civic, _esw
import provenance

METHOD = "html table + html page (label spans)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fire_ap"
URL = "https://fireservices.ap.gov.in/Fire/fire_contact_distofficersingle?distId={}"
DISTRICTS = 28
LOC = re.compile(r"\[\s*'([^']+)'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]")


def items(get=None):
    return [{"key": f"{MODULE}-{n:02d}", "payload": {"reader": MODULE, "url": URL.format(n), "state": "AP", "india_only": True,
                                                     "dist_id": n}} for n in range(1, DISTRICTS + 1)]


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower().replace("fire outpost", "").replace("fire station", ""))


def officer(soup):
    """The district officer block: {"post", "name", "mobile", "address", "office_phone", "email"}."""
    box = soup.select_one(".address-box")
    if not box:
        return {}
    h = box.find("h3")
    d = {"post": _esw.clean(h.get_text(" ")) if h else "District Fire Officer"}
    spans = box.select(".text-col span")
    if spans and not spans[0].find("b"):
        d["name"] = _esw.clean(spans[0].get_text(" "))
    for s in spans:
        b = s.find("b")
        if not b:
            continue
        lab = _esw.clean(b.get_text(" ")).rstrip(": ").lower()
        val = _esw.clean(s.get_text(" "))[len(_esw.clean(b.get_text(" "))):].strip(" :")
        d[{"mobile": "mobile", "address": "address", "office phone": "office_phone", "e-mail": "email",
           "residence": "residence"}.get(lab, lab)] = val
    return d


def parse(html, url):
    soup = _esw.soup(html)
    h1 = soup.find("h1")
    district = _esw.clean(h1.get_text(" ")).split("-", 1)[-1].strip() if h1 and "-" in h1.get_text() else ""
    if not district:
        return []
    ds = _esw.slug(district)
    points = {norm(n): (_civic.lat(a), _civic.lon(b)) for n, a, b in LOC.findall(html)}
    recs, seen = [], set()
    o = officer(soup)
    if o.get("name") or o.get("mobile"):
        recs.append(_civic.record(
            MODULE, f"{ds}:dfo", "fire", dept="fire", level="district", area=district, post=o.get("post"), name=o.get("name"),
            phone=_esw.phones(o.get("mobile", ""), o.get("office_phone", "")), email=_esw.emails(o.get("email", "")),
            address=o.get("address"), district=district, state="AP", office_id=f"AP-FIRE-{ds}-DFO", source=url,
            src_pos={"selector": "officer block (label spans)"}, method="html page (label spans)"))
    table = soup.find("table")
    if table:
        gp = []
        for gi, row in enumerate(_esw.grid(table, pos=gp)):
            if len(row) < 7 or not re.fullmatch(r"\d+", row[0].strip()):
                provenance.skip_row(row, 'skip: len(row) < 7 or not re.fullmatch(r"\\d+", row[0].strip())')
                continue
            _, station, address, name, phone, mobile, mail = row[:7]
            station = _esw.clean(station)
            key = _civic.unique(f"{ds}:{_esw.slug(station)}", seen)
            pt = points.get(norm(station), (None, None))
            outpost = bool(re.search(r"(?i)out\s*-?\s*post", station + " " + address))
            recs.append(_civic.record(
                MODULE, key, "fire", dept="fire", level="facility", area=station,
                office=station if outpost else f"{station} Fire Station", post="Station Fire Officer", name=name,
                phone=_esw.phones(phone, mobile), email=_esw.emails(mail), address=address, district=district, state="AP",
                station_type="outpost" if outpost else "station", office_id=f"AP-FIRE-{key}", lat=pt[0], lon=pt[1],
                source=url, src_pos=gp[gi], method="html table"))
    return recs


def fetch(p, get):
    url = p.get("url") or URL.format(p.get("dist_id", 1))
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"dist-{p.get('dist_id', 0):02d}", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
