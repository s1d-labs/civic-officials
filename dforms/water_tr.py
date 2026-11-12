"""Tripura: Drinking Water and Sanitation Department (DWS) contact report, dws.tripura.gov.in/Contact_Report.aspx (ASP.NET, 1.5 MB).
Answers only from India. One GET: one grid per office group (heading th.ContactHeadMain: "Secretary Office", "O/o the Chief Engineer",
"Agartala Circle Office", "Agartala II Division Office", "Sub_Division Office", "Laboratory" ...); every officer card holds spans
<grid>_lblName_<n>, _lblDesignation_<n>, _Label1_<n> (office address), _Label2_<n> (email), _Label3_<n> (fax), _Label4_<n> (office
phone), _Label5_<n> (mobile); "NA" = none. About 294 cards; engineers, the secretary and lab chemists are kept (not clerks or lab
assistants). The page shows no date. One queue item. Record ids: dept:water_tr:<slug of group>:<slug of designation>:<slug of place>[:n].
"""
import re

from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_tr"
URL = "https://dws.tripura.gov.in/Contact_Report.aspx"
KEEP = re.compile(r"engineer|secretary|director|chemist|\bS\.?E\b|\bE\.?E\b|\bA\.?E\b|\bJ\.?E\b", re.I)
FIELDS = {"lblName": "name", "lblDesignation": "designation", "Label1": "address", "Label2": "email", "Label3": "fax",
          "Label4": "phone", "Label5": "mobile"}
SPAN = re.compile(r"^(?P<g>.+)_(?P<f>lblName|lblDesignation|Label[1-5])_(?P<i>\d+)$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "TR", "india_only": True}}]


def _level(group, desig):
    g, d = group.lower(), desig.lower()
    if "sub_division" in g or "sub-division" in g or "sub division" in g:
        return "subdivision" if "junior" not in d else "section"
    if "division" in g:
        return "division" if "executive" in d else ("subdivision" if "assistant" in d else "division")
    if "circle" in g:
        return "circle"
    if "laboratory" in g:
        return "district"
    return "state"


def _place(group, address):
    """The division / circle from the group heading ("Agartala II Division Office" -> "Agartala II Division"); for sub-divisions
    and laboratories, the place after "Sub-Division" in the office address ("DWS Sub-Division, Rupaichari, Sabroom" -> "Rupaichari",
    "Sub-Division No-II, Udaipur Division" -> "No-II, Udaipur"), else the first part of the address that is not the office's name."""
    g = re.sub(r"\s*Office$", "", group).replace("_", "-").strip()
    if not re.search(r"sub-division|laboratory", g, re.I):
        return g
    a = _esw.clean(address)
    m = re.search(r"(?i)\bsub[\s_-]*div[a-z]*\.?(?:\s*office)?[\s,:)-]*((?:(?:No\.?|-)?\s*-?\s*[IVX\d]+\b\s*,?\s*)?)"
                  r"([A-Za-z][A-Za-z .]*)", a)
    if m:
        place = re.sub(r"(?i)\s+division$", "", m.group(2).strip(" .,"))
        no = m.group(1).strip(" ,")
        return f"{no}, {place}" if no else place
    a = re.sub(r"(?i)\b(office of the|o/o( the)?|assistant engineer|junior engineer|executive engineer|pwd\s*\(dws\)|dws|"
               r"district laboratory|laboratory|office)\b", " ", a)
    parts = [p.strip(" .-") for p in a.split(",") if p.strip(" .-")]
    return parts[0] if parts else g


def parse(html, url=URL):
    soup = _esw.soup(html)
    cards, heads = {}, {}
    for sp in soup.find_all("span", id=SPAN):
        m = SPAN.match(sp["id"])
        v = _esw.clean(sp.get_text(" "))
        cards.setdefault((m["g"], int(m["i"])), {})[FIELDS[m["f"]]] = "" if v.upper() in ("NA", "N/A", "-") else v
    for g in {g for g, _ in cards}:
        t = soup.find("table", id=g)
        th = t.find("th", class_="ContactHeadMain") if t else None
        heads[g] = _esw.clean(th.get_text(" ")) if th else g
    recs, seen = [], set()
    for (g, i), c in sorted(cards.items(), key=lambda x: (x[0][0], x[0][1])):
        desig = c.get("designation", "")
        if not KEEP.search(desig) or not (c.get("name") or c.get("mobile") or c.get("phone") or c.get("email")):
            continue
        group = heads[g]
        place = _place(group, c.get("address"))
        key = f"{_esw.slug(group)}:{_esw.slug(desig)}:{_esw.slug(place)}"
        k, n = key, 2
        while k in seen:
            k, n = f"{key}:{n}", n + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="water", level=_level(group, desig), area=place, post=desig, name=c.get("name"),
                                phone=_esw.phones(c.get("mobile"), c.get("phone")), fax=_esw.phones(c.get("fax")),
                                email=_esw.emails(c.get("email")), address=c.get("address"), state="TR",
                                office_id=f"TR-DWS-{_esw.slug(place)}", org="Drinking Water and Sanitation Department, Tripura",
                                group=group, source=url))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contact-report", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
