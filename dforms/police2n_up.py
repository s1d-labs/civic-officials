"""Uttar Pradesh Police: uppolice.gov.in/frmOfficials.aspx?<unit>&cd=<unit id>, one page per district and per commissionerate.
The cd value is the unit id written as base64 of UTF-16LE text ("MwAwADkA" = "309"); it is not a session token. Each page has
up to three tables "S.No | Name of IPS Officer / Name of PPS Officer / Name Of Officer | Rank | Posted as | CUG / Mobile No. |
Office No. | Email Id": the SSP / SP / Addl. SPs, the circle officers (CO <circle>) and, in the commissionerates (comm*), the
CP, DCPs, ADCPs and ACPs (ACP <circle>). Works from outside India. No station (SHO) rows on this site.

Kept: CO / ACP rows of a territorial circle (level circle, area = the circle: "CO Gabhan" -> Gabhan; "CO I" -> City I;
"ACP Colonelganj/ Lines/ Crime" -> Colonelganj) and the district heads (SSP, SP, Addl. SP, ASP, CP, JCP, DCP, ADCP: level
district). COs and ACPs with a function only (traffic, office, crime, cyber, lines, 112, accounts ...) are level district,
office_type unit. Reserve inspectors and rows with neither a posting nor a phone are left out. Range and zone pages (DIG, IG,
ADG) are not queue items.
items(get) reads the unit menu of one officials page. One queue item = one district or commissionerate page.
Record id dept:police2n_up:<district>:<post slug>."""
import re
from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police2n_up"
BASE = "https://uppolice.gov.in/"
MENU = BASE + "frmOfficials.aspx?aligarh&cd=MwAwADkA"

DISTRICT = {   # the site's unit slug -> district name (LGD spelling); others: the slug in title case
    "ambedkarngr": "Ambedkar Nagar", "bagpat": "Baghpat", "bhadoi": "Bhadohi", "faizabad": "Ayodhya", "fatehgarh": "Farrukhabad",
    "kabirngr": "Sant Kabir Nagar", "kheri": "Lakhimpur Kheri", "muzaffarngr": "Muzaffarnagar", "padrona": "Kushinagar",
    "ramabaingr": "Kanpur Dehat", "sidharthngr": "Siddharthnagar", "budaun": "Budaun", "raebareli": "Rae Bareli",
    "commagr": "Agra", "commgbngr": "Gautam Buddh Nagar", "commgzb": "Ghaziabad", "commknp": "Kanpur Nagar", "commlko": "Lucknow",
    "commprg": "Prayagraj", "commvns": "Varanasi", "amroha": "Amroha", "shravasti": "Shrawasti", "chitrakoot": "Chitrakoot",
}
FUNCTION = re.compile(r"traffic|office|crime|cyber|account|lekha|\bline|highway|\b112\b|writ|court|security|women|mahila|\bmission\b|"
                      r"\brtc\b|vip|\bliu\b|protocol|\bhq\b|hqrs|social media|\bcaw\b|building|bhawan|bhavan|nodal|leave|"
                      r"complaint|jansunwai|staff officer|refinary|refinery|\bkjs\b|vidhan|sachivalay|high court|election", re.I)
CIRCLE = re.compile(r"^\(?\s*(?:CO|C\.O\.?|ACP|A\.C\.P\.?)(?:[\s.\-:]+|$)(.*)$", re.I)
HEAD = re.compile(r"\b(SSP|S\.?S\.?P|SP|S\.P|ADDL\.?\s*S\.?P|ASP|SPRA|CP|JCP|DCP|ADCP|ADDL\.?\s*D\.?C\.?P|ADD\.?\s*CP|ADDL\.?\s*CP|"
                  r"COMMISSIONER|DEPUTY COMMISSIONER|SUPERINTENDENT)\b", re.I)
SKIP = re.compile(r"reserve inspector|\bR\.?\s?I\b|प्रतिसार", re.I)


def district_of(unit):
    return DISTRICT.get(unit) or unit.replace("-", " ").title()


def units(html):
    """[(unit slug, url)] for the district and commissionerate pages in the menu of one officials page."""
    out, seen = [], set()
    for href in re.findall(r'href="((?:https?://uppolice\.gov\.in/)?frmOfficials\.aspx\?([a-z0-9]+)(?:&amp;|&)cd=([^"&]+))"', html):
        url, unit, cd = href
        if unit.startswith(("range", "zone")) or (unit, cd) in seen:
            continue
        seen.add((unit, cd))
        out.append((unit, f"{BASE}frmOfficials.aspx?{unit}&cd={cd}"))
    return out


def items(get):
    r = get(MENU)
    if r is None:
        return []
    out, seen = [], set()
    for unit, url in units(r.text):
        if unit in seen:          # Lucknow and Gautam Buddh Nagar have two ids that show the same page
            continue
        seen.add(unit)
        out.append({"key": f"{M}:{unit}", "payload": {"reader": M, "url": url, "state": "UP", "unit": unit,
                                                      "district": district_of(unit)}})
    return out


def circle_area(posted):
    """'CO Gabhan' -> 'Gabhan'; 'CO I' -> 'City I'; 'ASP (CO CITY)' -> 'City'; 'ACP Colonelganj/ Lines/ Crime' -> 'Colonelganj';
    'CO Traffic/ CO Cyber Crime' -> None (a function, not a circle)."""
    p = clean(posted) or ""
    m = re.search(r"\(\s*((?:CO|ACP)\b[^)]*)\)", p, re.I)          # 'ASP (CO CITY)', 'ASP (Co Sadar/Line)'
    if m:
        p = m.group(1)
    if re.match(r"^(?:ASP|ADDL)", p, re.I) and "/" in p:            # 'ASP/CO LINE/CRIME'
        p = p.split("/", 1)[1]
    m = CIRCLE.match(p.strip())
    if not m:
        return None
    first = re.split(r"\s*[/+,]\s*", m.group(1).strip(" -"))[0].strip(" -.")
    if not first or FUNCTION.search(first):
        return None
    if re.fullmatch(r"(?:[IVX]+|\d+(?:st|nd|rd|th)?)", first, re.I):
        first = "City " + first.upper()
    if (first.isupper() and len(first.replace(" ", "")) > 4) or first.islower():
        first = first.title()
    return first


def officers(html):
    """Rows of the officer tables: dict(name, rank, posted, cug, office, email)."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.find_all("table"):
        head = [clean(x.get_text(" ", strip=True)) or "" for x in t.find("tr").find_all(["th", "td"])] if t.find("tr") else []
        if not any(re.search(r"posted as", h, re.I) for h in head):
            continue
        for tr in t.find_all("tr")[1:]:
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
            if len(c) < 7:
                continue
            out.append({"name": re.sub(r"\s*\(\s*0\s*\)\s*$", "", c[1]).strip(), "rank": c[2], "posted": c[3], "cug": c[4],
                        "office": c[5], "email": c[6]})
    return out


def parse(html, url, district, state="UP"):
    recs = []
    d = slug(district)
    for o in officers(html):
        posted = o["posted"] if o["posted"] not in ("", "-") and not re.fullmatch(r"leave", o["posted"], re.I) else ""
        if not o["name"] or SKIP.search(posted) or (not posted and not o["cug"].strip("- ")):
            continue
        if posted and posted.upper() == district.upper():
            posted = ""
        ph = phones(*(x for x in (o["cug"], o["office"]) if x and x.strip("- ")))
        area = circle_area(posted) if posted else None
        common = dict(name=o["name"], rank=o["rank"] or None, phone=ph, email=email(o["email"]), state=state, district=district,
                      source=url)
        if area:
            post = "ACP" if re.match(r"\(?\s*A\.?C\.?P", posted, re.I) or "(ACP" in posted.upper() else "CO"
            recs.append(rec(M, f"{d}:{post.lower()}-{slug(area)}", level="circle", office_type="circle", area=area,
                            post=f"{post} {area}", **common))
            continue
        post = posted or o["rank"]
        if not post:
            continue
        unit = bool(re.match(r"\(?\s*(?:CO|ACP)\b", posted, re.I)) or not HEAD.search(post) or FUNCTION.search(post)
        recs.append(rec(M, f"{d}:{slug(post)}", level="district", office_type="unit" if unit else "office", area=district,
                        post=post, **common))
    return uniq(recs)


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    unit = p.get("unit") or re.search(r"\?([a-z0-9]+)", url).group(1)
    district = p.get("district") or district_of(unit)
    recs = parse(r.text, url, district, p.get("state", "UP"))
    return recs, [gz(M, unit, r.content)], "" if recs else "no rows"
