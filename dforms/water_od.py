"""Odisha: urban water supply offices of the Public Health Engineering Organisation (PHEO) and of WATCO. Both answer from Germany and
India.
- page "pheo": www.pheoodisha.gov.in/view-portal-emp-dir/<portal id>, one Employee Directory per portal (1 = Engineer-in-Chief,
  2-5 and 19, 22 = circles, 8-18, 20-21, 23-26 = PH divisions; ids from the home page menu). Table: SL. No., Name, Designation,
  Place Of Posting, Phone Number. Only engineer posts are kept (not clerks, drivers, peons); the footer "Contact Us" block (office,
  phone, fax, e-mail) gives one office record. One queue item = one portal (24 items).
- page "watco": api.watcoodisha.in/watcocms/getAllActiveWhosewhosub (JSON: 21 WATCO groups, ~199 staff with designation, place of
  posting, contact no.) and page "watco-main": /getAllActiveWhoseWhoMain (chairperson, MD, directors). One queue item each.
Record ids: dept:water_od:pheo-<portal>:<slug of place>:<slug of designation>[:n], dept:water_od:pheo-<portal>:office,
dept:water_od:watco:<slug of group>:<slug of place>:<slug of designation>[:n], dept:water_od:watco-main:<slug of post>.
"""
import html as htmlmod
import json
import re

from dforms import _esw

MODULE = "water_od"
PHEO = "https://www.pheoodisha.gov.in/view-portal-emp-dir/{}"
WATCO = "https://api.watcoodisha.in/watcocms/getAllActiveWhosewhosub"
WATCO_MAIN = "https://api.watcoodisha.in/watcocms/getAllActiveWhoseWhoMain"
PORTALS = {1: "Engineer-in-Chief, Public Health, Odisha", 2: "Bhubaneswar Circle", 3: "Cuttack Circle", 4: "Sambalpur Circle",
           5: "Berhampur Circle", 8: "PH Division, BBSR", 9: "PH Division, Puri", 10: "PH Division-I, Cuttack",
           11: "PH Division, Cuttack", 12: "PH Division, Baripada", 13: "PH Division, Sambalpur", 14: "PH Division, Rourkela",
           15: "PH Division, Balangir", 16: "PH Division, Berhampur", 17: "PH Division, Koraput",
           18: "PH Division, Bhanjanagar at chatrapur", 19: "Balasore Circle", 20: "PH Division, Balasore",
           21: "PH Division, Keonjhar", 22: "Bhawanipatna Circle", 23: "PH Division, Bhawanipatna", 24: "PH Division, Rayagada",
           25: "PH Division, Angul", 26: "PH Division, Jharsuguda"}
ENGINEER = re.compile(r"engineer|estimator", re.I)


def items(get=None):
    out = [{"key": f"{MODULE}-pheo-{n}", "payload": {"reader": MODULE, "url": PHEO.format(n), "state": "OD", "page": "pheo",
                                                     "portal": n, "office": name}} for n, name in PORTALS.items()]
    out.append({"key": f"{MODULE}-watco", "payload": {"reader": MODULE, "url": WATCO, "state": "OD", "page": "watco"}})
    out.append({"key": f"{MODULE}-watco-main", "payload": {"reader": MODULE, "url": WATCO_MAIN, "state": "OD", "page": "watco-main"}})
    return out


def _level(desig, place):
    d, p = desig.lower(), place.lower()
    if "section" in p:
        return "section"
    if re.search(r"sub[\s.-]*division", p):
        return "subdivision"
    if "engineer-in-chief" in d or "chief engineer" in d:
        return "state"
    if "superintending" in d or "circle" in p:
        return "circle"
    if "junior engineer" in d:
        return "section"
    return "division"


def _place(s):
    """"P.H.Sub-.Division,No-III, Berhampur" -> "Sub-Division No-III, Berhampur"."""
    s = re.sub(r"^(O/o\.?\s*|Office of (the)?\s*)", "", _esw.clean(s), flags=re.I)
    s = re.sub(r"\s*\(\s*P\.?\s*H\.?\s*\)|\bP\.\s*H\.?\s*", "", s)
    s = re.sub(r"^(EE|SE|EIC)\s*,\s*", "", s)
    s = re.sub(r"Sub[\s.-]*Division", "Sub-Division", s, flags=re.I)
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"^(Sub-Division|Section|Division)\s*,\s*", r"\1 ", s)
    return s.strip(" ,")


def parse_pheo(html, p):
    soup = _esw.soup(html)
    portal = p.get("portal")
    office = p.get("office") or PORTALS.get(portal, "")
    recs, seen = [], set()
    for t in soup.find_all("table"):
        rows = _esw.grid(t)
        if not rows or "designation" not in [h.lower() for h in rows[0]]:
            continue
        head = [h.lower() for h in rows[0]]
        for row in rows[1:]:
            c = dict(zip(head, row))
            name, desig = c.get("name", ""), c.get("designation", "")
            if not ENGINEER.search(desig) or not name or name.lower().startswith("vacant"):
                continue
            place = _place(c.get("place of posting", "")) or office
            key = f"pheo-{portal}:{_esw.slug(place)}:{_esw.slug(desig)}"
            k, i = key, 2
            while k in seen:
                k, i = f"{key}:{i}", i + 1
            seen.add(k)
            recs.append(_esw.record(MODULE, k, dept="water", level=_level(desig, place), area=place, post=desig, name=name,
                                    phone=_esw.phones(c.get("phone number")), state="OD",
                                    office_id=f"OD-PHEO-{_esw.slug(place)}", org="Public Health Engineering Organisation, Odisha",
                                    office=office, source=p["url"]))
    # the footer block: "Contact Us Office of the Executive Engineer, P.H. Division, Berhampur Phone: ... Fax : ... E-Mail: ..."
    h2 = next((h for h in soup.find_all("h2") if _esw.clean(h.get_text()) == "Contact Us"), None)
    box = h2.find_parent(["div", "section"]) if h2 else None
    text = _esw.clean(box.get_text(" ")) if box else ""
    m = re.search(r"Contact Us\s+(.*?)\s+Phone\s*:?\s*(.*?)\s+Fax\s*:?\s*(.*?)\s+E-?Mail\s*:?\s*(\S*)", text)
    if m and (m.group(2) or m.group(4)):
        recs.append(_esw.record(MODULE, f"pheo-{portal}:office", dept="water",
                                level="state" if portal == 1 else ("circle" if "circle" in office.lower() else "division"),
                                area=_place(office), post="Office", address=m.group(1), phone=_esw.phones(m.group(2)),
                                fax=_esw.phones(m.group(3)), email=_esw.emails(m.group(4)), state="OD",
                                office_id=f"OD-PHEO-portal-{portal}", org="Public Health Engineering Organisation, Odisha",
                                office=office, source=p["url"]))
    return recs


def _wlevel(desig, place, group):
    d, p = desig.lower(), place.lower()
    if "section" in p:
        return "section"
    if re.search(r"sub[\s.-]*division", p):
        return "subdivision"
    if "corporate" in group.lower():
        return "state"
    return "division"


def parse_watco(js, url=WATCO):
    recs, seen = [], set()
    for g in js.get("data") or []:
        group = _esw.clean(g.get("name"))
        gmail = _esw.emails(g.get("title"))
        for x in g.get("whosWhoSubContents") or []:
            desig, place = _esw.clean(x.get("designation")), _esw.clean(x.get("placeOfPosting"))
            name = re.sub(r"\(\s*contractual\s*\)", "", _esw.clean(x.get("nameOfTheStaff")), flags=re.I).strip()
            if not name and not x.get("contactNo"):
                continue
            key = f"watco:{_esw.slug(group)}:{_esw.slug(place)}:{_esw.slug(desig)}"
            k, i = key, 2
            while k in seen:
                k, i = f"{key}:{i}", i + 1
            seen.add(k)
            gm = "general manager" in desig.lower()
            recs.append(_esw.record(MODULE, k, dept="water", level=_wlevel(desig, place, group), area=place or group, post=desig,
                                    name=name, phone=_esw.phones(x.get("contactNo")), email=gmail if gm else None, state="OD",
                                    office_id=f"OD-WATCO-{_esw.slug(place or group)}", org="WATCO (Water Corporation of Odisha)",
                                    group=group, source=url))
    return recs


def _nopin(s):
    """Drops PIN codes ("Bhubaneswar 751001", "- 751007") and EPABX extensions, which _esw.phones() would read as numbers."""
    s = re.sub(r"\d{4}\s*\(EPABX\)", " ", s or "")
    return re.sub(r"(?<=[A-Za-z,])\s*-?\s*[1-8]\d{5}\b(?!\d)", " ", s)


def parse_watco_main(js, url=WATCO_MAIN):
    recs = []
    for x in js.get("data") or []:
        lines = [_esw.clean(htmlmod.unescape(s)) for s in re.split(r"<br\s*/?>|</p>", x.get("name") or "")]
        lines = [re.sub(r"<[^>]+>", "", s).strip() for s in lines if re.sub(r"<[^>]+>", "", s).strip()]
        if not lines:
            continue
        if len(lines) >= 2:
            name, post = lines[0], " ".join(lines[1:])
        else:
            m = re.match(r"(.*?)\s+((?:Managing |Executive )?Director.*|Chairperson.*|Chief .*)$", lines[0])
            name, post = (m.group(1), m.group(2)) if m else (lines[0], "")
        addr = _esw.clean(x.get("contactAddress"))
        recs.append(_esw.record(MODULE, f"watco-main:{_esw.slug(post or name)}", dept="water", level="state", area="Odisha",
                                post=post, name=name, phone=_esw.phones(_nopin(addr)),
                                email=_esw.emails(addr), address=re.split(r"\s+(?:Contact|Mobile) No", addr)[0], state="OD",
                                office_id="OD-WATCO-head-office", org="WATCO (Water Corporation of Odisha)", source=url))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    page = p.get("page", "pheo")
    if page == "pheo":
        files = [_esw.keep(MODULE, f"pheo-emp-dir-{p.get('portal')}", r.content)]
        recs = parse_pheo(r.text, p)
    else:
        files = [_esw.keep(MODULE, page, r.content, "json")]
        try:
            js = json.loads(r.content)
        except ValueError:
            return [], files, "not json"
        recs = parse_watco(js, p["url"]) if page == "watco" else parse_watco_main(js, p["url"])
    return recs, files, "" if recs else "no rows"
