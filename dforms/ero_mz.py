"""Mizoram: the District Election Officers (11), the EROs of all 40 assembly constituencies and their AEROs, from the CEO's officer
contacts page ceo.mizoram.gov.in/officer-contacts. Answers from Germany and India.

One page holds every tab (DEO, ERO, AERO, BLO) as cards: name (h5), designation (h6), district, "Assembly Constituency: Saiha (ST)".
ERO and AERO tabs have their own pagers (ero_page, aero_page; 15 cards a page): ?ero_page=N&aero_page=N gives page N of both, so
four GETs read the 40 EROs (3 pages) and the AEROs (4 pages). DEO cards are on every page: taken from page 1 only. No phone or email
on the page. AC numbers come from the page's own AC filter dropdown. One queue item = one page number.
Record ids: dept:ero_mz:MZ-AC-<no>:ero, dept:ero_mz:MZ-AC-<no>:aero:<slug of designation>, dept:ero_mz:MZ-DEO-<district>.
"""
import re

from dforms import _esw

MODULE = "ero_mz"
URL = "https://ceo.mizoram.gov.in/officer-contacts"
PAGES = 4
POST = {"ero": "Electoral Registration Officer", "aero": "Assistant Electoral Registration Officer"}
ALIAS = {}   # page spelling -> AC layer spelling, where _esw.ac_no() misses


def items(get=None):
    return [{"key": f"{MODULE}-p{n}", "payload": {"reader": MODULE, "url": f"{URL}?ero_page={n}&aero_page={n}", "state": "MZ", "page": n}}
            for n in range(1, PAGES + 1)]


def cards(pane):
    out = []
    for c in pane.select("div.media.p-3"):
        name = c.find("h5")
        desig = c.find("h6")
        bodies = [_esw.clean(b.get_text(" ")) for b in c.select("div.media.mt-2 div.media-body")]
        ac = next((b.split(":", 1)[1].strip() for b in bodies if b.lower().startswith("assembly constituency")), "")
        dist = next((b for b in bodies if not b.lower().startswith("assembly constituency")), "")
        out.append({"name": _esw.clean(name.get_text(" ")) if name else "", "designation": _esw.clean(desig.get_text(" ")) if desig else "",
                    "district": dist, "ac": ac})
    return out


def ac_numbers(soup):
    """AC name -> number from the page's own AC filter dropdowns ("12 - Aizawl North III (ST)")."""
    out = {}
    for sel in soup.find_all("select", id=re.compile(r"_ac_id$")):
        for o in sel.find_all("option"):
            m = re.match(r"^\s*(\d{1,2})\s*-\s*(.+?)\s*$", _esw.clean(o.get_text(" ")))
            if m:
                out[_esw.norm_ac(m.group(2))] = int(m.group(1))
    return out


def ac_number(name, page_map=None):
    k = _esw.norm_ac(name)
    return (page_map or {}).get(k) or _esw.ac_no("MZ", ALIAS.get(k, name))


def parse(html, page=1, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    nos = ac_numbers(soup)

    def add(key, **f):
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="elections", state="MZ", source=url, **f))

    if int(page) == 1 and soup.find("div", id="deo"):
        for c in cards(soup.find("div", id="deo")):
            if c["name"] and c["district"]:
                key = f"MZ-DEO-{_esw.slug(c['district'])}"
                add(key, level="district", area=c["district"], post="District Election Officer", designation=c["designation"],
                    name=c["name"], district=c["district"], office_id=key)
    for role in ("ero", "aero"):
        pane = soup.find("div", id=role)
        if pane is None:
            continue
        for c in cards(pane):
            if not c["name"] or not c["ac"]:
                continue
            no = ac_number(c["ac"], nos)
            office = f"MZ-AC-{no}" if no else f"MZ-AC-{_esw.slug(c['ac'])}"
            key = f"{office}:ero" if role == "ero" else f"{office}:aero:{_esw.slug(c['designation']) or _esw.slug(c['name'])}"
            add(key, level="ac", area=f"{no} - {c['ac']}" if no else c["ac"], post=POST[role], designation=c["designation"],
                name=c["name"], district=c["district"], office_id=office if no else None)
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("page", 1), p["url"])
    return recs, [_esw.keep(MODULE, f"p{p.get('page', 1)}", r.content)], "" if recs else "no rows"
