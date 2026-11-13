"""Goa Police phone directory, citizen.goapolice.gov.in/web/guest/phone (one table "Sr. No. | Name | Phone | Email | Mobile", 240 rows,
posts only, no officer names): DGP .. DySP, SDPOs, the station PIs (PI <name> PS), traffic cells (PI Traffic Cell <town>), special
branch, cyber, women / AHTU units, the outposts ("<name> Outpost (OP) - <station>"), helplines and the North / South district police
control rooms. Landlines are written without the STD code (7 digits; all of Goa is 0832): written here as 0832-<number>; the cell as
published is kept in phone_raw. Emails "x[at]y[dot]z" are made plain. Works from outside India (police_ga's host).
Kept for every row: level police_station for "PI <x> PS" rows and outposts (office_type police station / police post / women /
cyber), subdivision for SDPO, district for SP North / South and the district control rooms, state for the rest (office_type unit,
traffic, cyber, women, control_room). district North Goa / South Goa when the row names it or its station is known to be there.
One queue item = the page. Record id dept:police3_ga:<slug of the post>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police3_ga"
URL = "https://citizen.goapolice.gov.in/web/guest/phone"
SOUTH = re.compile(r"margao|fatorda|colva|cuncolim|curtorim|quepem|curchorem|sanguem|canacona|vasco|mormugao|mormagoa|verna|dabolim|"
                   r"ponda|mardol|collem|betul|talpona|harbour|konkan|south", re.I)
NORTH = re.compile(r"panaji|agacaim|old goa|mapusa|anjuna|colvale|pernem|mandrem|mopa|porvorim|porvorm|calangute|saligao|bicholim|"
                   r"valpoi|chapora|siolim|tiracal|tiracol|north", re.I)


def phone_of(*cells):
    out = []
    for c in cells:
        c = clean(c) or ""
        if not re.search(r"\d", c):
            continue
        c = re.sub(r"\(.*?\)|N/W", " ", c)
        c = re.sub(r"(?<!\d)(\d{7})(?!\d)", r"0832-\1", c)
        out.append(c)
    return phones(*out)


def kind_of(post):
    p = post.lower()
    if "outpost" in p:
        return "police_station", "police post"
    if "control room" in p or "spcr" in p or "helpline" in p or "whatsapp" in p:
        return ("district" if "district" in p else "state"), "control_room"
    if "traffic" in p:
        return "state", "traffic"
    if re.search(r"women|woman|ahtu|pink", p):
        return ("police_station" if re.search(r"\bps\b", p) else "state"), "women"
    if "cyber" in p:
        return ("police_station" if p.startswith("pi ") else "state"), "cyber"
    if re.match(r"^pi\b.*\bps\b", p):
        return "police_station", "police station"
    if p.startswith("sdpo"):
        return "subdivision", "office"
    if re.search(r"superintendent of police,? -?\s*(north|south)", p):
        return "district", "office"
    return "state", "unit"


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for ti, t in enumerate(soup.find_all("table")):
        rows = t.find_all("tr")
        head = [clean(c.get_text(" ", strip=True)) or "" for c in rows[0].find_all(["td", "th"])] if rows else []
        if [h.lower() for h in head[1:3]] != ["name", "phone"]:
            continue
        for ri, tr in enumerate(rows[1:], 1):
            c = [clean(x.get_text(" ", strip=True)) or "" for x in tr.find_all(["td", "th"])]
            if len(c) < 5 or not c[1]:
                provenance.skip_row(tr, 'skip: len(c) < 5 or not c[1]')
                continue
            post = c[1]
            level, otype = kind_of(post)
            m = re.match(r"^(.+?)\s+Outpost\s*\(OP\)\s*-\s*(.+)$", post, re.I)
            area = clean(m.group(1)) + " Outpost" if m else re.sub(r"^(PI|SDPO|DySP)\s+", "", post, flags=re.I)
            district = "South Goa" if SOUTH.search(post) else "North Goa" if NORTH.search(post) else None
            if level == "state" and otype == "traffic" and district:
                level = "district"
            em = [e for e in (email(x) for x in re.split(r",\s*", c[3])) if e]
            out.append(rec(M, slug(post), level=level, office_type=otype, area=area, post=post, parent_station=clean(m.group(2)) if m
                           else None, phone=phone_of(c[4], c[2]), phone_raw=" | ".join(x for x in (c[2], c[4]) if x.strip("- ")) or None,
                           email=", ".join(em) or None, district=district, state="GA", source=url, src_url=url,
                           src_pos={"table": ti, "row": ri}))
    return uniq(out)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, "phone", r.content)], "" if recs else "no rows"
