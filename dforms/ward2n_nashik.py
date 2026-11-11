"""Nashik Municipal Corporation (nmc.gov.in): its 6 divisional offices (विभागीय कार्यालय: Satpur, CIDCO / New Nashik, Nashik East,
Nashik West, Nashik Road, Panchavati) and the engineers who serve a group of divisions. Two pages (HTML; nmc.gov.in does not answer
from Germany: india_only; live samples 2026-11-11 via vpsin; the archive has other pages of the site but not these two):
  /home/getfrontpage/2/1000/M ("प्रशासन", Last Updated 08-04-2025): tab "प्रशासन": tables per department (Designation | Department |
  Phone (Off.) | Email); rows whose Department cell names divisions ("Panchavati Division (PWD)", "Nashik Road, New Nashik, Satpur
  Division") are read (Executive Engineers of PWD, water supply distribution, drainage; Deputy Engineers per division where the row has
  a phone or an email). Tab "विभागीय कार्यालय": one cell per division office (name, address, email, phone). The page gives posts, no names.
  /home/getfrontpage/233/11/M ("विभागीय अधिकारी, नाशिक रोड", Last Updated 23-06-2026): the Nashik Road Divisional Officer's name,
  phone and email (the site has such a page for Nashik Road only).
Records: level "zone" (a division is a zone of wards); the page does not list the wards of a division (no "wards" key).
Record ids: dept:ward2n_nashik:<division slug>:division-office, :<post slug>:<divisions slug>, nashik-road:divisional-officer.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_nashik"
BODY, LGD, STATE, DISTRICT = "Nashik Municipal Corporation", "251442", "MH", "Nashik"
URL = "https://nmc.gov.in/home/getfrontpage/2/1000/M"
URL_NR = "https://nmc.gov.in/home/getfrontpage/233/11/M"
DIVISIONS = (("new nashik", "New Nashik (CIDCO)"), ("cidco", "New Nashik (CIDCO)"), ("nashik east", "Nashik East"),
             ("nashik (east)", "Nashik East"), ("nashik west", "Nashik West"), ("nashik (west)", "Nashik West"),
             ("nashik road", "Nashik Road"), ("nashikroad", "Nashik Road"), ("panchavati", "Panchavati"), ("panchvati", "Panchavati"),
             ("satpur", "Satpur"))


def items(get=None):
    return [{"key": f"{MODULE}-administration", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}},
            {"key": f"{MODULE}-nashik-road", "payload": {"reader": MODULE, "url": URL_NR, "state": STATE, "india_only": True}}]


def divisions(text):
    t = re.sub(r"\s+", " ", _esw.clean(text).lower())
    out = []
    for k, v in DIVISIONS:
        if k in t and v not in out:
            out.append(v)
    return out


def last_updated(soup):
    d = soup.select_one("div.last-updated-sec")
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", d.get_text(" ") if d else "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse_admin(html, p):
    soup = _esw.soup(html)
    upd = last_updated(soup)
    seen, recs = set(), []
    for t in soup.find_all("table"):
        section = ""
        for tr in t.find_all("tr"):
            h2 = tr.find("h2")
            tds = tr.find_all("td", recursive=False)
            if h2 and len(tds) == 1:
                section = _esw.clean(h2.get_text())
                continue
            if len(tds) == 4 and not tr.find("h2"):
                post, dept, phone, email = (_esw.cell_text(td) for td in tds)
                divs = divisions(dept)
                if not divs or not (re.search(r"\d{5}", phone) or "@" in email):
                    continue
                post = re.sub(r"\s*\|\s*", " ", post)
                dept_names = [x for x in (s.strip() for s in dept.split("|")) if x]
                key = f"{_esw.slug(post)}:{_esw.slug('-'.join(divs))}"
                recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone",
                                         area=", ".join(divs) + (" Division" if len(divs) == 1 else " Divisions"),
                                         zone=", ".join(divs), post=f"{post} ({section})" if section and section.lower() not in post.lower() else post,
                                         phone=phone, email=email, divisions=divs, department=", ".join(dept_names),
                                         wing=_ward.wing_of(f"{section} {post}"), last_updated=upd, source=p["url"]))
            elif len(tds) == 2 and all(td.find("h2") for td in tds):
                for td in tds:
                    name = _esw.clean(td.find("h2").get_text())
                    divs = divisions(name)
                    body = _esw.cell_text(td.find("p") or td)
                    parts = [x.strip() for x in body.split("|")]
                    addr = ", ".join(x for x in parts if x and not re.match(r"(?i)(email|phone)\b", x))
                    ph = next((x for x in parts if x.lower().startswith("phone")), "")
                    recs.append(_ward.record(MODULE, f"{_esw.slug(divs[0] if divs else name)}:division-office", seen, body=BODY, lgd=LGD,
                                             state=STATE, district=DISTRICT, level="zone",
                                             area=f"{divs[0] if divs else name} Division", zone=divs[0] if divs else name,
                                             post="Divisional Office", address=addr, phone=re.sub(r"(?i)phone\s*:?", "", ph),
                                             email=body, wing="administration", last_updated=upd, source=p["url"]))
    return recs


def parse_officer(html, p):
    """The divisional officer page: "विभागाचे नाव | विभाग प्रमुख / खाते प्रमुख | पद | संपर्क नंबर / मोबाइल नंबर | ई-मेल आयडी" pairs."""
    soup = _esw.soup(html)
    text = _esw.clean(soup.get_text(" "))
    f = {}
    for key, label, nxt in (("office", "विभागाचे नाव", "विभाग प्रमुख"), ("name", "विभाग प्रमुख / खाते प्रमुख", "पद"),
                            ("post", "पद", "संपर्क नंबर"), ("phone", "संपर्क नंबर / मोबाइल नंबर", "ई-मेल आयडी"),
                            ("email", "ई-मेल आयडी", "विभागाचे कामकाज")):
        m = re.search(re.escape(label) + r"\s+(.+?)\s+" + re.escape(nxt), text)
        f[key] = _esw.clean(m.group(1)) if m else ""
    if not (f["name"] or f["phone"] or f["email"]):
        return []
    divs = divisions(f["email"] + " " + f["office"]) or divisions(p["url"])
    div = divs[0] if divs else "Nashik Road"
    post = "Divisional Officer" if "विभागीय अधिकारी" in f["post"] else _ward.hi_post(f["post"])
    return [_ward.record(MODULE, f"{_esw.slug(div)}:divisional-officer", set(), body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                         level="zone", area=f"{div} Division", area_regional=f["office"] or None, zone=div, post=post,
                         post_regional=f["post"] or None, name=f["name"], name_regional=f["name"] or None, phone=f["phone"],
                         email=f["email"], wing="administration", last_updated=last_updated(soup), source=p["url"])]


def parse(html, p):
    if "/2/1000/" in p["url"]:
        return parse_admin(html, p)
    recs = parse_officer(html, p)
    # the officer page names its head only: role "head" comes from the post (Divisional Officer is not in _ward.HEAD)
    return [(r, dict(d, role="head")) for r, d in recs]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (nmc.gov.in answers only from India)"
    recs = parse(r.text, p)
    name = "administration" if "/2/1000/" in p["url"] else "nashik-road"
    return recs, [_esw.keep(MODULE, name, r.content)], "" if recs else "no division rows"
