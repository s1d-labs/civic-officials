"""Odisha: Commissionerate Police Bhubaneswar-Kataka, bhubaneswarcuttackpolice.gov.in/important-contact-number/ (WordPress).
Table 1 "Sl. | Name | Designation | Office Address | Contact Number | e-Mail ID": the CP, Addl. CP, DCPs and Addl. DCPs with office,
fax and mobile numbers ("+91-674-2530035 (O) +91-674-2530001 (F) +91-8280338300 (M)") and e-mails written "x[at]od[dot]gov[dot]in".
Tables 2 and 3 "SUBDIVISION | Zonal Officers Name & Contact Details | Police Station": the six zones of Bhubaneswar UPD (Khordha)
and of Kataka UPD (Cuttack), each with its ACP (name, mobile, e-mail) and the police stations of the zone.
Kept: officers (level district; DCP Traffic office_type traffic), zones (level circle, ACP name + mobile, stations in "stations"),
and one record per station of a zone (level police_station, circle = zone; no IIC names on this page). Numbers marked (F) go to
"fax". The other Odisha sources did not answer: odishapolice.gov.in times out from Mumbai, the Indian proxies and abroad
(2026-11-05 .. 11-13); district portals list station names and addresses only; the CCTNS citizen portal has no station list.
Answers from Mumbai (2026-11-13); police2n_od notes no connection from outside India. One queue item = the page.
Record id dept:police3_od:<upd>:<zone>[:<station>] and dept:police3_od:officer:<row>-<post>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
from dforms._police3e import kind

METHOD = "html table"

M = "police3_od"
URL = "https://bhubaneswarcuttackpolice.gov.in/important-contact-number/"
UPD = [("bhubaneswar", "Khordha"), ("kataka", "Cuttack")]


def numbers(cell):
    """(phones, fax): '+91-674-2530035 (O) +91-674-2530001 (F) +91-8280338300 (M)' -> ('0674-2530035, 8280338300', '0674-2530001')."""
    ph, fx = [], []
    rest = cell or ""
    for m in re.finditer(r"\+?91[-\s]*([6-9]\d{9})(?!\d)\s*(\((?:[A-Z/]+)\))?", rest):
        (fx if m.group(2) == "(F)" else ph).append(m.group(1))
    rest = re.sub(r"\+?91[-\s]*[6-9]\d{9}(?!\d)", " ", rest)
    for m in re.finditer(r"\+?91[-\s]*(\d{3,4})[-\s]+(\d{6,8})\s*(\((?:[A-Z/]+)\))?", rest):
        (fx if m.group(3) == "(F)" else ph).append(f"0{m.group(1)}-{m.group(2)}")
    return phones(*ph), phones(*fx)


def mail(cell):
    t = clean(cell) or ""
    m = re.search(r"[\w.\-]+@\s*[\w.\-]+\.[a-z]{2,}", t)
    if m:
        return email(m.group(0).replace(" ", ""))
    t = re.sub(r"\s*\[\s*at\s*\]\s*", "@", t)
    t = re.sub(r"\s*\[\s*dot\s*\]\s*", ".", t)
    m = re.search(r"[\w.\-]+@[\w.\-]+\.[a-z]{2,}", t)
    return email(m.group(0)) if m else None


def district_of(text):
    t = re.sub(r"bhubaneswar\s*-\s*kataka", " ", (text or "").lower())
    if "kataka" in t or "cuttack" in t:
        return "Cuttack"
    return "Khordha"


def parse(html, url=URL, state="OD"):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    tables = soup.find_all("table")
    zone_tables = []
    for ti, t in enumerate(tables):
        rows = [[clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])] for tr in t.find_all("tr")]
        head = next((r for r in rows if any(re.search(r"designation", c, re.I) for c in r)), None)
        if head:
            for ri, c in enumerate(rows):
                if c is head or len(c) < 5 or not re.match(r"^\d+\.?$", c[0]):
                    continue
                name = c[1].strip(" .") or None
                post = c[2]
                ph, fx = numbers(c[4])
                level, otype, _ = kind(post)
                if level not in ("district", "circle", "subdivision"):
                    level = "district"
                d = dict(level="district", office_type=otype if otype in ("traffic", "cyber", "women", "control room") else "office",
                         area=district_of(post), post=post, name=name, phone=ph, fax=fx, email=mail(c[5] if len(c) > 5 else ""),
                         address=c[3] or None, state=state, district=district_of(post), unit="Commissionerate Police Bhubaneswar-Kataka",
                         list_no=c[0].strip("."), source=url, src_pos={"table": ti, "row": ri})
                recs.append(rec(M, f"officer:{c[0].strip('.')}-{slug(post)[:50]}", **d))
        elif any(any(re.search(r"Zonal Officers", x, re.I) for x in r) for r in rows):
            zone_tables.append((ti, rows))
    for (ti, rows), (upd, district) in zip(zone_tables, UPD):
        for ri, c in enumerate(rows):
            if len(c) < 3 or not re.match(r"^Zone\s+[IVX]+", c[0], re.I):
                continue
            zone = c[0]
            officer = c[1]
            nm = re.match(r"^(?:ACP\s*,?\s*)?(.+?)\s*,\s*(?:IPS|OPS|OAPS)[^,]*", officer)
            name = clean(nm.group(1)) if nm else None
            mobs = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", officer.replace("+91-", " "))
            stations = [clean(s) for s in re.split(r"\s*,\s*", c[2]) if clean(s)]
            area = f"{'Bhubaneswar' if upd == 'bhubaneswar' else 'Kataka'} UPD {zone}"
            recs.append(rec(M, f"{upd}:{slug(zone)}", level="circle", office_type="circle", area=area, post="ACP", name=name,
                            phone=phones(*mobs), email=mail(officer), state=state, district=district, stations=stations,
                            officer_as_published=officer, source=url, src_pos={"table": ti, "row": ri}))
            for si, s in enumerate(stations):
                otype = "women police station" if re.search(r"mahila|women", s, re.I) else "police station"
                recs.append(rec(M, f"{upd}:{slug(zone)}:{slug(s)}", level="police_station", office_type=otype, area=s,
                                circle=area, state=state, district=district, source=url,
                                src_pos={"table": ti, "row": ri, "cells": [2], "index": si}))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url, p.get("state", "OD"))
    return recs, [gz(M, "important-contact-number", r.content)], "" if recs else "no rows"
