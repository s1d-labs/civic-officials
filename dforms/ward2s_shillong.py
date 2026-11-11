"""Shillong Municipal Board (smb.gov.in, static HTML; a municipal board, not a corporation, the only urban body of Meghalaya's
capital, 27 wards): its zone and ward field staff. India only: no answer from Germany (2026-11-11, connect timeout); all four pages
saved in archive.s1d.me 2026-11-05. The pages show no "Last Updated" date. Four pages, one queue item each:
  /other_menu/whos_who.html        table "SOLID WASTE MANAGEMENT BRANCH": Name | "Asstt. Manager <North/South/East/West> Zone" |
                                   "Ward No. 8,9,10 ..." | phone (the ward-to-zone mapping of the SWM zones); table "WATER WORKS
                                   DEPARTMENT": Incharge | Designation | Contact Number | Area (localities). The first table (CEO,
                                   E.O., heads of sections) is left to the whoswho task.
  /department/public_works.html    Sl. No | Name | Designation | Responsiblitities | Contact No: Executive Engineer, Assistant and
                                   Junior Engineers, with "to assess the building of Ward No. 1, 2, 3,4,5 & 6".
  /department/water_works.html     Sl No | Name | Designation | Contact Number | Area: the water works inspectors and their localities
                                   (the same people as on whos_who.html, some with other phone numbers: both are kept, the record id
                                   carries the page).
  /department/health_sanitation.html  "Field Staff" table: Senior Sanitary Inspectors (SSI), Sanitary Inspectors (SI), Conservancy
                                   Supervisors (C.S.), Water Works Inspector (W.W.I.); no areas.
Records: SWM zone managers level "zone" (wards = the zone's wards); engineers with ward numbers level "ward" (one record with all the
wards that engineer covers); water works inspectors level "division" (area = the localities, extra key "localities"); engineers
without wards and the sanitation field staff level "body" (a body-wide list: the site does not tie them to a ward or zone).
Clerks, peons, tracers and drivers are left out. Record ids: dept:ward2s_shillong:<page>:<area slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2s_shillong"
BODY, LGD, STATE, DISTRICT = "Shillong Municipal Board", "249814", "ML", "East Khasi Hills"
BASE = "https://smb.gov.in"
PAGES = {"whos-who": "/other_menu/whos_who.html", "public-works": "/department/public_works.html",
         "water-works": "/department/water_works.html", "health-sanitation": "/department/health_sanitation.html"}
POSTS = {"SSI": "Senior Sanitary Inspector", "SI": "Sanitary Inspector", "C.S.": "Conservancy Supervisor",
         "W.W.I.": "Water Works Inspector"}
ZONE = re.compile(r"(?i)\b(north|south|east|west|central)\s+zone\b")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": BASE + v, "page": k, "state": STATE, "india_only": True}}
            for k, v in PAGES.items()]


def _name(s):
    return re.sub(r"^(Shri|Smti|Kum|Smt|Sri)\.?\s*", "", _esw.clean(s)).strip()


def parse(html, p):
    page = p.get("page") or next((k for k, v in PAGES.items() if p["url"].endswith(v)), "page")
    soup = _esw.soup(html)
    seen, recs = set(), []

    def add(level, area, post, name, phone="", wards=None, zone=None, **extra):
        name = _name(name)
        if not (name or _esw.clean(phone)):
            return
        recs.append(_ward.record(MODULE, f"{page}:{_esw.slug(area)[:40]}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen,
                                 body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=level, area=area, post=post,
                                 name=name, phone=phone, wards=wards, zone=zone, source=p["url"], **extra))

    for t in soup.find_all("table"):
        g = [[_esw.clean(c) for c in r] for r in _esw.grid(t)]
        if not g:
            continue
        head = [c.lower() for c in g[0]]
        body = g[1:] if any(h in ("name", "incharge", "designation") for h in head) else g
        for r in body:
            r = r + [""] * (5 - len(r))
            if r[0].isdigit():                         # Sl No first
                r = r[1:] + [""]
            if not any(r):
                continue
            zm = ZONE.search(r[1])
            if zm and "ward" in r[2].lower():           # SWM zone manager: name | post + zone | Ward No. .. | phone
                zone = f"{zm.group(1).title()} Zone"
                post = _esw.clean(ZONE.sub("", r[1]).strip(" ,"))
                post = re.sub(r"(?i)^asst\w*\.?", "Assistant", post) + " (Solid Waste Management)"
                add("zone", zone, post, r[0], r[3], wards=_ward.wards_of(r[2]), zone=zone)
            elif re.search(r"(?i)water\s*works?\s*inspector", r[1]) and re.search(r"[A-Za-z]{4}", r[3]):
                area = _esw.clean(r[3])
                add("division", area, "Water Works Inspector", r[0], r[2], localities=area, wing="water")
            elif page == "public-works" and re.search(r"(?i)engineer", r[1]):
                wards = _ward.wards_of(r[2].split("Ward No", 1)[1]) if "ward no" in r[2].lower() else []
                if wards:
                    add("ward", "Ward " + ", ".join(wards), r[1], r[0], r[3], wards=wards, duties=r[2])
                else:
                    add("body", BODY, r[1], r[0], r[3], duties=r[2] or None)
            elif page == "health-sanitation" and r[1] in POSTS:
                add("body", BODY, POSTS[r[1]], r[0], r[2])
            elif page == "water-works" and re.search(r"(?i)superintendent", r[1]):
                add("body", BODY, "Superintendent (Water Works)", r[0], r[2], wing="water")
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("page") or "page", r.content)], "" if recs else "no staff tables"
