"""Karnataka: police station officers (SHO: the Police Inspector or Police Sub-Inspector of a station) from the district police
sites of the KSP web platform, <district>police.karnataka.gov.in (35 district and city sites, one server, 103.138.196.129; pages /<id>/<slug>/en; the
railway police site and bangaloreurbanpolice, whose contact page names the Bengaluru commissioner only, are left out).

police_ka reads the KSP station locator (landline, station email, no names, no mobiles). The district sites publish the CUG
mobiles of the posts, and some publish the officers' names. Page kinds seen (2026-11-13):
- "contact" tables (Shivamogga /10/contact-us, Belagavi District /50/police-officers-contacts, Bidar
  /67/police-officers-contact-details): one row per post, the post and its place in one cell ("PSI KATKOL PS", "PI DODDAPETE
  PS", "CPI KARGAL RURAL", "DySP GOKAK", "SP BIDAR/Control Room") | STD code | office number | mobile | e-mail. Sub-division rows
  ("GOKAK SUB-DIVISION", the same text in every cell) head each block. No names.
- "officer" tables (Haveri /392/haveri-district-police-officer-name): Officer Name | Designation (SP, DSP, PI, CPI, PSI) |
  Name of the Station / Unit ("Haveri Town PS", "Haveri Town PS - L&O", "Byadagi Circle"). Names, no phones.
Rank words (first word of the cell, or the Designation column): SP, Addl. SP, ASP, DySP / DSP, CPI (circle inspector), PI
(police inspector), PSI (sub-inspector), RPI. A row is level "police_station" when its place names a station ("... PS", "Police
Station") and its rank is PI or PSI: these are the station officers; "sho_rank" says which (the PI is the SHO where the station
has one; a station with PSIs only is led by its senior PSI; the page does not say which PSI). CPI rows are level "circle", DySP /
ASP rows "subdivision", SP / Addl. SP rows "district"; units (DCRB, DSB, DAR, control room, CEN, traffic circle) keep the rank's
level with office_type "unit".
area of a station row = the station as the page writes it without the rank and the "PS" word ("KATKOL", "Haveri Town"); station
= the place as written. phone = the mobile (the post's CUG number, 9480xxxxxx), telephone = STD + office number.

Items: one per site. payload "pages" = the pages known to hold these tables (from archive.s1d.me captures, 2026-11-05 to
2026-11-07); payload "find" = also read the home page (/en) and follow up to 3 of its links whose text names contacts, officers
or police stations (for sites whose page is not known). Answers from India (dev-vps-3 got Bidar and Belagavi on 2026-11-13; the
same server then did not answer three more requests for 60 s: the hub's delay and retries handle it). route "direct".
Record ids: dept:sho_ka:<site>:<rank>:<place slug>[:<mobile or name slug>].
"""
import re

import provenance
from dforms import _esw, _police

METHOD = "html table (KSP district police site)"

MODULE = "sho_ka"
STATE = "KA"
# site -> (district or commissionerate as LGD / KSP name it, [known pages])
SITES = {
    "bagalkotpolice": ("Bagalkote", []),
    "ballaripolice": ("Ballari", ["/15/police-stations/en"]),
    "bangaloreruralpolice": ("Bengaluru Rural", []),
    "belagavicitypolice": ("Belagavi City", []),
    "belagavidistrictpolice": ("Belagavi", ["/50/police-officers-contacts/en"]),
    "bidarpolice": ("Bidar", ["/67/police-officers-contact-details/en"]),
    "chikkaballapurapolice": ("Chikkaballapura", ["/3/contact-us/en"]),
    "chikkamagalurupolice": ("Chikkamagaluru", ["/4/police-stations/en"]),
    "chitradurgapolice": ("Chitradurga", ["/3/police-stations/en"]),
    "chnpolice": ("Chamarajanagar", []),
    "davangerepolice": ("Davanagere", []),
    "dharwadpolice": ("Dharwad", ["/18/contact-us/en"]),
    "dkpolice": ("Dakshina Kannada", ["/2/police-stations-contact-details/en"]),
    "gadagpolice": ("Gadag", ["/13/police-stations/en"]),
    "hassanpolice": ("Hassan", ["/10/police-station-details/en"]),
    "haveripolice": ("Haveri", ["/392/haveri-district-police-officer-name/en"]),
    "hubballidharwadcitypolice": ("Hubballi-Dharwad City", ["/5/contact-us/en"]),
    "kalaburagicitypolice": ("Kalaburagi City", ["/33/police-officers-contacts/en"]),
    "kalaburagidistrictpolice": ("Kalaburagi", ["/58/police-officers-list/en"]),
    "kgfpolice": ("Kolar Gold Fields", []),
    "kodagupolice": ("Kodagu", []),
    "kolarpolice": ("Kolar", ["/9/contact-us/en"]),
    "koppalpolice": ("Koppal", ["/11/contact-us/en"]),
    "mandyapolice": ("Mandya", ["/2/police-stations/en"]),
    "mangalorecitypolice": ("Mangaluru City", []),
    "mysurucitypolice": ("Mysuru City", ["/18/contact-us/en"]),
    "mysurupolice": ("Mysuru", []),
    "raichurpolice": ("Raichur", []),
    "ramanagarapolice": ("Ramanagara", []),
    "shivamoggapolice": ("Shivamogga", ["/10/contact-us/en"]),
    "tumkurpolice": ("Tumakuru", []),
    "udupipolice": ("Udupi", ["/3/contact-us/en"]),
    "uttarakannadapolice": ("Uttara Kannada", ["/31/contact-us/en"]),
    "vijayapurapolice": ("Vijayapura", []),
    "yadgirpolice": ("Yadgir", []),
}
RANK = re.compile(r"(?i)^\s*(addl\.?\s*s\.?p\.?(?:\s*-?\s*\d)?|add(?:itiona)?l\.?\s*s\.?p|a\.?s\.?p|dy\.?\s*s\.?p|d\.?s\.?p|"
                  r"c\.?p\.?i|r\.?p\.?i|w\.?p\.?s\.?i|p\.?s\.?i|p\.?i|s\.?p)\b\.?\s*[-,:]?\s*")
RANK_POST = {"sp": ("Superintendent of Police", "district"), "addlsp": ("Additional Superintendent of Police", "district"),
             "asp": ("Assistant Superintendent of Police", "subdivision"), "dysp": ("Deputy Superintendent of Police", "subdivision"),
             "dsp": ("Deputy Superintendent of Police", "subdivision"), "cpi": ("Circle Police Inspector", "circle"),
             "rpi": ("Reserve Police Inspector", "district"), "pi": ("Police Inspector", "police_station"),
             "psi": ("Police Sub-Inspector", "police_station"), "wpsi": ("Woman Police Sub-Inspector", "police_station")}
STATION = re.compile(r"(?i)\bP\.?\s?S\.?(?=$|[\s,()–-])|police\s*sta?tion|\bthana\b|ಠಾಣೆ")
UNIT = re.compile(r"(?i)\b(dcrb|dsb|dar|control\s*room|cen\b|c\s*e\s*n|fpb|msu|cyber|special\s*branch|wireless|computer|"
                  r"traffic\s*circle|coastal|highway|office)\b")
COLS = {
    "name": re.compile(r"(?i)officer'?s?\s*name|^name\b"),
    "label": re.compile(r"(?i)^designation|ps\s*/?\s*office|rank\s*/?\s*place|unit\s*/\s*office|^post\b|^office\s*/\s*ps"),
    "unit": re.compile(r"(?i)name\s*of\s*the\s*(station|unit)|station\s*/\s*unit"),
    "mobile": re.compile(r"(?i)mobile|office\s*\|?\s*contact|contact\s*number|^cug"),
    "phone": re.compile(r"(?i)^off(ice)?\.?\s*(no|phone|\|)?|ps\s*phone|telephone|^off$"),
    "std": re.compile(r"(?i)^std"),
    "email": re.compile(r"(?i)e-?\s?mail"),
}
LINK = re.compile(r"(?i)contact|officer|police\s*station|phone|telephone|directory")


def items(get=None):
    out = []
    for site, (district, pages) in SITES.items():
        out.append({"key": f"{MODULE}-{site}", "payload": {
            "reader": MODULE, "url": f"https://{site}.karnataka.gov.in/en", "site": site, "district": district, "pages": pages,
            "find": True, "state": STATE, "india_only": True, "route": "direct"}})
    return out


def header_map(cells):
    h = {}
    for i, c in enumerate(cells):
        t = _esw.clean(c)
        for f in ("unit", "name", "label", "mobile", "std", "email", "phone"):
            if f not in h and COLS[f].search(t):
                h[f] = i
                break
    if "label" in h and ("mobile" in h or "name" in h or "unit" in h):
        return h
    return None


def rank_of(text):
    """(rank key, rest of the text) of "PSI KATKOL PS" -> ("psi", "KATKOL PS"); ("", text) when no rank word leads."""
    m = RANK.match(text or "")
    if not m:
        return "", _esw.clean(text)
    k = re.sub(r"[^a-z]", "", m.group(1).lower())
    k = "addlsp" if k.startswith("add") else k
    return k, _esw.clean(text[m.end():])


def station_name(place):
    """'Haveri Town PS - L&O' -> 'Haveri Town'; 'KATKOL PS' -> 'KATKOL'; 'Sagara Rural Police Station' -> 'Sagara Rural'."""
    s = re.split(r"\s+[–-]\s+", place)[0]
    s = re.sub(r"(?i)\bP\.?\s?S\.?(?=$|[\s,()])|police\s*sta?tion|\bthana\b", " ", s)
    return _esw.clean(s).strip(" ,-")


def rows(html):
    """[dict(label, name, unit, mobile, phone, std, email, section, cells, pos)] of the officer / contact tables of a page."""
    soup = _esw.soup(html)
    out, last = [], None
    for t in soup.find_all("table"):
        pos = []
        grid = _esw.grid(t, pos=pos)
        if grid and re.search(r"(?i)screen\s*reader|document\s*type|ಸ್ಕ್ರೀನ್", " ".join(grid[0])):
            provenance.filtered("site furniture table (screen readers, file viewers)", len(grid))
            continue
        h, section = None, ""
        for cells, where in zip(grid, pos):
            texts = [_esw.clean(c) for c in cells]
            hm = header_map(texts)
            if hm:
                h, last = hm, (hm, len(texts))
                provenance.skipped("header")
                continue
            if h is None and last and len(texts) == last[1] and RANK.match(texts[last[0]["label"]] if len(texts) > last[0]["label"] else ""):
                h = last[0]          # a table without a heading row after a contact table, same columns, a rank in the post cell
            filled = [x for x in texts if x]
            if not filled:
                provenance.skipped("empty")
                continue
            if len(set(filled)) == 1 and not re.search(r"\d{6,}", filled[0]):
                section = filled[0]
                provenance.skipped("header")
                continue
            if h is None:
                provenance.skip_row(texts, "no heading row")
                continue
            g = {f: (texts[i] if i < len(texts) else "") for f, i in h.items()}
            if not g.get("label") and not g.get("unit"):
                provenance.skip_row(texts, "no post")
                continue
            out.append({**g, "section": section, "cells": texts, "pos": where})
    return out


def records(rs, site, district, url, seen):
    recs = []
    for r in rs:
        name = r.get("name", "")
        if r.get("unit"):                        # Officer Name | Designation | Name of the Station / Unit
            rk, _ = rank_of(r.get("label", ""))
            place = r["unit"]
        else:                                    # "PSI KATKOL PS" | STD | OFF | MOBILE
            rk, place = rank_of(r.get("label", ""))
        mobile = _police.phones(r.get("mobile", ""))
        office = _police.phones(" ".join(x for x in (r.get("std", ""), r.get("phone", "")) if x)) if r.get("phone") else None
        email = _esw.emails(r.get("email", ""))
        if not (mobile or name or email):
            provenance.skip_row(r["cells"], "no name, phone or email")
            continue
        post, level = RANK_POST.get(rk, (r.get("label") or "", "district"))
        is_unit, is_circle = bool(UNIT.search(place)), bool(re.search(r"(?i)\bcircle\b", place))
        # a station: the place names one ("KATKOL PS"), or a PI / PSI is posted to a place that is no unit or circle
        # ("Guttal - Senior PSI (L&O & Traffic)": the PSIs of the Haveri list are named by station and duty)
        is_station = not is_unit and not is_circle and (bool(STATION.search(place)) or rk in ("pi", "psi", "wpsi"))
        if rk in ("pi", "psi", "wpsi") and not is_station:
            level = "circle" if is_circle else "district"
        if level != "police_station" and is_station and rk in ("", "pi", "psi", "wpsi"):
            level = "police_station"
        office_type = "unit" if UNIT.search(place) else None
        area = station_name(place) if level == "police_station" else place
        duty = _esw.clean(re.split(r"\s+[–-]\s+", place, maxsplit=1)[1]) if level == "police_station" and re.search(r"\s[–-]\s", place) else None
        if level == "police_station" and not rk:
            post = "Police Station"
        key = _police.slug(f"{site}-{rk or 'post'}-{place}-{mobile.split(',')[0] if mobile else name}")
        if key in seen:
            provenance.skipped("same row twice")
            continue
        seen.add(key)
        provenance.used()
        recs.append(_police.rec(MODULE, key, level=level, office_type=office_type, post=post, rank=rk.upper() or None,
                                office=r.get("label"), station=place if level == "police_station" else None, area=area,
                                name=name or None, phone=mobile or None, telephone=office, email=email or None,
                                sho_rank=rk.upper() if level == "police_station" and rk in ("pi", "psi", "wpsi") else None, duty=duty,
                                subdivision=r.get("section") or None, state=STATE, district=district, site=site, source=url,
                                src_url=url, cells=r["cells"], src_pos=r["pos"]))
    return recs


def links(html, base):
    """Up to 3 links of the home page whose text names contacts, officers or police stations (same host, /en pages)."""
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        href, text = a["href"], _esw.clean(a.get_text(" "))
        if not LINK.search(text) or re.search(r"(?i)\.pdf$|mailto:|tel:", href):
            continue
        if href.startswith("/"):
            href = base + href
        if not href.startswith(base) or href in out:
            continue
        if re.search(r"(?i)/\d+/[a-z0-9-]*(contact|officer|police-station)[a-z0-9-]*/en$", href) and \
                not re.search(r"(?i)/\d+/[a-z0-9-]+-police-station/en$", href):        # one station's own page: no table
            out.append(href)
    return out[:3]


def fetch(p, get):
    base = f"https://{p['site']}.karnataka.gov.in"
    urls = [base + x for x in p.get("pages", [])]
    files, recs, seen, answered = [], [], set(), 0
    if p.get("find") or not urls:
        r = get(p["url"])
        if r is not None:
            answered += 1
            files.append(_police.gz(MODULE, f"{p['site']}-home", r.content))
            urls += [u for u in links(r.text, base) if u not in urls]
    for u in urls:
        r = get(u)
        if r is None:
            continue
        answered += 1
        files.append(_police.gz(MODULE, f"{p['site']}-{_police.slug(u.split('.gov.in', 1)[1])}", r.content))
        recs += records(rows(r.text), p["site"], p["district"], u, seen)
    if not answered:
        return [], [], "no answer"
    return recs, files, "" if recs else "no officer rows"
