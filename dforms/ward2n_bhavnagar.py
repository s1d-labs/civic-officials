"""Bhavnagar Mahanagar Palika (bmcgujarat.com, Umbraco site): the ward offices of its 13 wards and the zone offices of its East /
West / Central zones. Three pages under /en/contact-us/ (answer from Germany; live samples 2026-11-11; archive.s1d.me holds them
only under URLs with trailing spaces, saved as 404):
  swm-ward-offices/      one block per zone ("<h4><span>East</span> J.B.Garchar CSI</h4>": zone + its Chief Sanitary Inspector),
                         then one card per ward: the Sanitary Inspector's name, "Ward No. 10 Kaliyabid - Sidsar - Adhewada", the
                         ward office address (with lat/lon in the map link), mobile, email. The zone blocks give the ward-to-zone map.
  drainage-ward-offices/ one card per ward: "Ward No. 1 Chitra - Fulsar - Nari", the drainage Sub Sanitary Inspector ("(SSI)"),
                         office address + lat/lon, mobile; 9 cards a page, the reader follows ?page=N (2 pages).
  bmc-officials/         every department's officers; only the zone sections are read here: "House Tax Central / East / West"
                         (House Tax Superintendent of each zone, mobile, email).
Records: level "ward" (one per ward and wing) and "zone" (CSI, house tax). Record ids: dept:ward2n_bhavnagar:<page>:<ward or zone>:<n>.
"""
import re

from dforms import _esw, _ward

METHOD = "html cards"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_bhavnagar"
BODY, LGD, STATE, DISTRICT = "Bhavnagar Mahanagar Palika", "251165", "GJ", "Bhavnagar"
BASE = "https://bmcgujarat.com/en/contact-us/"
PAGES = ("swm-ward-offices", "drainage-ward-offices", "bmc-officials")


def items(get=None):
    return [{"key": f"{MODULE}-{p}", "payload": {"reader": MODULE, "url": f"{BASE}{p}/", "state": STATE, "page": p}}
            for p in PAGES]


def _card(card):
    """(lines of the card's own headings, address, lat, lon, phone, email)."""
    addr = lat = lon = ""
    a = card.find("a", href=re.compile(r"maps\.google"))
    if a:
        addr = _esw.clean(a.get_text(" "))
        m = re.search(r"loc:\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", a["href"])
        if m:
            lat, lon = m.group(1), m.group(2)
    tel = card.find("a", href=re.compile(r"^tel:"))
    mail = card.find("a", href=re.compile(r"^mailto:"))
    phone = _esw.clean(tel.get_text(" ")) if tel else ""
    email = _esw.clean(mail.get_text(" ")) if mail else ""
    heads = [_esw.clean(h.get_text(" ")) for h in card.find_all(["h5", "h6"]) if not h.find_parent("a")]
    return heads, addr, lat, lon, "" if phone == "-" else phone, "" if email == "-" else email


def _ward_no(text):
    m = re.match(r"(?i)\s*ward\s*no\.?\s*(\d{1,3})\s*(.*)", text)
    return (str(int(m.group(1))), _esw.clean(m.group(2))) if m else (None, "")


def _name(text):
    """("Shri. Ravaiya Parthkumar (SSI)", ...) -> ("Ravaiya Parthkumar", "SSI"); keeps I/C as a note."""
    t = _esw.clean(text)
    post = None
    m = re.search(r"\(\s*([A-Za-z./ ]{2,12})\s*\)\s*$", t)
    if m:
        post, t = m.group(1).strip(), t[:m.start()].strip()
    ic = bool(re.match(r"(?i)i/?c\.?\s+", t))
    t = re.sub(r"(?i)^(i/?c\.?\s+)?(shree|shri|smt)\.?\s+", "", t)
    return t, post, ic


def parse_swm(html, p, seen):
    recs = []
    soup = _esw.soup(html)
    for h4 in soup.find_all("h4", class_="commntitle"):
        sp = h4.find("span")
        zone = _esw.clean(sp.get_text(" ")) if sp else ""
        head = _esw.clean(h4.get_text(" "))[len(zone):].strip()
        if not zone:
            continue
        zname = f"{zone} Zone"
        box = h4.find_next_sibling("div")
        wards = []
        for card in (box.find_all("div", class_="prof-card") if box else []):
            heads, addr, lat, lon, phone, email = _card(card)
            wline = next((h for h in heads if re.match(r"(?i)ward\s*no", h)), "")
            ward, wname = _ward_no(wline)
            if not ward:
                continue
            wards.append(ward)
            nm, _, ic = _name(heads[0] if heads and heads[0] != wline else "")
            recs.append(_ward.record(MODULE, f"swm:ward-{ward}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="ward",
                                     area=f"Ward {ward} {wname}".strip(), zone=zname, wards=[ward], post="Sanitary Inspector",
                                     name=nm, phone=phone, email=email, address=addr, lat=lat or None, lon=lon or None,
                                     wing="sanitation", in_charge=True if ic else None, source=p["url"], src_pos=_ward.nth(card)))
        m = re.match(r"(.*?)\s*\b(CSI|C\.S\.I\.?)\s*$", head)
        if m:
            nm, _, ic = _name(m.group(1))
            recs.append(_ward.record(MODULE, f"swm:{_esw.slug(zone)}:csi", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                     level="zone", area=zname, zone=zname, wards=wards, post="Chief Sanitary Inspector", name=nm,
                                     wing="sanitation", vacant=None if nm else True, source=p["url"],
                                     src_pos=dict(_ward.nth(h4), text=_esw.clean(h4.get_text(" ")))))
    return recs


def parse_drainage(html, p, seen):
    recs = []
    for card in _esw.soup(html).find_all("div", class_="prof-card"):
        heads, addr, lat, lon, phone, email = _card(card)
        ward, wname = _ward_no(heads[0] if heads else "")
        if not ward:
            continue
        nm, post, ic = _name(heads[1] if len(heads) > 1 else "")
        post = {"SSI": "Sub Sanitary Inspector (Drainage)"}.get((post or "").upper().replace(".", ""), "Drainage Ward In-charge")
        recs.append(_ward.record(MODULE, f"drainage:ward-{ward}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="ward",
                                 area=f"Ward {ward} {wname}".strip(), wards=[ward], post=post, name=nm, phone=phone, email=email,
                                 address=addr, lat=lat or None, lon=lon or None, wing="sewerage", in_charge=True if ic else None,
                                 source=p["url"], src_pos=_ward.nth(card)))
    return recs


def parse_officials(html, p, seen):
    """Only the zone sections of the officials page: 'House Tax Central / East / West'."""
    recs = []
    soup = _esw.soup(html)
    section = None
    for box in soup.find_all("div", class_="tender-box"):
        if "justify-content-center" in (box.get("class") or []):
            section = _esw.clean(box.get_text(" "))
            continue
        m = re.match(r"(?i)house\s*tax\s+(east|west|central|north|south)$", section or "")
        if not m:
            continue
        zone = f"{m.group(1).title()} Zone"
        f = {}
        for st in box.find_all("div", class_="start-time"):
            k, v = st.find("p"), st.find("h5")
            if k and v:
                f[_esw.clean(k.get_text(" ")).rstrip(":").lower()] = _esw.clean(v.get_text(" "))
        nm_tag = box.find("h5", class_="job-tie")
        nm, _, ic = _name(nm_tag.get_text(" ") if nm_tag else "")
        nm = re.sub(r"(?i)^(shree|shri)\s+", "", nm)
        post = f.get("designation", "") or "House Tax Superintendent"
        recs.append(_ward.record(MODULE, f"officials:{_esw.slug(zone)}:{_esw.slug(post)}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=f"House Tax {zone}", zone=zone, post=post, name=nm,
                                 phone=_esw.phones(f.get("land line number", ""), f.get("mobile number", "")),
                                 email=f.get("email", ""), wing="revenue", source=p["url"], src_pos=_ward.nth(box)))
    return recs


PARSERS = {"swm-ward-offices": parse_swm, "drainage-ward-offices": parse_drainage, "bmc-officials": parse_officials}


def fetch(p, get):
    page = p.get("page") or next((k for k in PAGES if k in p["url"]), "")
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    seen, files = set(), [_esw.keep(MODULE, page, r.content)]
    recs = PARSERS[page](r.text, p, seen)
    if page == "drainage-ward-offices":
        more = sorted({int(n) for n in re.findall(r'href="\?page=(\d+)"', r.text)} - {1})
        for n in more[:10]:
            r2 = get(f"{p['url']}?page={n}")
            if r2 is None:
                continue
            files.append(_esw.keep(MODULE, f"{page}-p{n}", r2.content))
            recs += PARSERS[page](r2.text, dict(p, url=f"{p['url']}?page={n}"), seen)
    return recs, files, "" if recs else "no cards"
