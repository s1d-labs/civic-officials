"""Andhra Pradesh: health officers from the Health, Medical & Family Welfare Department site hmfw.ap.gov.in. Two pages, one item:

1. https://hmfw.ap.gov.in/contact.aspx: three tables, each under an <h3>:
   "Health Department Officials" (Secretary, Commissioner, Director of Public Health: name | post | e-mail | phone),
   "CHFW Officers Details" (state officers of the Commissionerate: name | post | e-mail | phone) and
   "District Medical & Health Officers" (one DMHO per district of the 2022 map, 28 rows: name | district | e-mail | phone).
   E-mails are written "dmhovzm(at)gmail(dot)com".
2. http://hmfw.ap.gov.in/hsms/CSMSContacts.aspx (Hospital Sanitation Management System, public contact page): Medical
   Superintendents of the APVVP Community Health Centres and Area Hospitals (116 rows: S.No | hospital | superintendent |
   mobile | e-mail), grouped under a row per district of the old 13-district map (tr.RowDistrictStyle, tr.RowDataStyle).

Both pages were saved by the archive from the GitHub runners (vantage pool, 2026-11-05/06): the site answers abroad.
Records (depts.py contract): dept health; DMHO rows level district (post "District Medical & Health Officer", area and district
= the district), state officers level state, hospital superintendents level facility (area = the hospital, district = the
old district the page groups it under). Ids: dept:health_ap_hmfw:<dmho|state|hospital>:<slug>.
"""
import re

from dforms import _esw

MODULE = "health_ap_hmfw"
CONTACT = "https://hmfw.ap.gov.in/contact.aspx"
CSMS = "http://hmfw.ap.gov.in/hsms/CSMSContacts.aspx"
HONOR = re.compile(r"(?i)^(sri|smt|shri)\.?\s+")
HOSP = {"CHC": "Community Health Centre", "AH": "Area Hospital", "DH": "District Hospital"}


def _cells(tr):
    return [_esw.cell_text(c) for c in tr.find_all(["td", "th"], recursive=False)]


def parse_contact(html, url=CONTACT):
    s = _esw.soup(html)
    recs = []
    for h in s.find_all("h3"):
        title = _esw.clean(h.get_text(" "))
        t = h.find_next("table")
        if t is None or not re.search(r"(?i)officials|officers", title):
            continue
        dmho = "District Medical" in title
        for tr in t.find_all("tr"):
            c = _cells(tr)
            if len(c) < 4 or not c[0] or c[0].lower().startswith("name of"):
                continue
            name = HONOR.sub("", re.sub(r"\s+", " ", c[0])).strip()
            if dmho:
                district = c[1]
                recs.append(_esw.record(MODULE, f"dmho:{_esw.slug(district)}", dept="health", level="district", area=district,
                                        district=district, post="District Medical & Health Officer", category=title, name=name,
                                        phone=_esw.phones(c[3]), email=_esw.emails(c[2]), state="AP", source=url, page=url))
            else:
                post = re.sub(r"\s*\|\s*", " ", c[1]).strip(" ,")
                recs.append(_esw.record(MODULE, f"state:{_esw.slug(post)}:{_esw.slug(name)}", dept="health", level="state",
                                        area="Andhra Pradesh", post=post, category=title, name=name, phone=_esw.phones(c[3]),
                                        email=_esw.emails(c[2]), state="AP", source=url, page=url))
    return recs


def parse_csms(html, url=CSMS):
    s = _esw.soup(html)
    recs, district = [], ""
    for tr in s.find_all("tr", class_=["RowDistrictStyle", "RowDataStyle"]):
        c = _cells(tr)
        if "RowDistrictStyle" in tr.get("class", []):
            district = c[0].title() if c else ""
            continue
        if len(c) < 5 or not c[1]:
            continue
        sno, hosp, name, mob, mail = c[:5]
        kind = hosp.split(",")[0].strip().upper()
        place = hosp.split(",", 1)[1].strip() if "," in hosp else hosp
        ic = bool(re.match(r"(?i)i/?c\b", name))
        name = re.sub(r"(?i)^i/?c\s*[,.]?\s*", "", name).strip()
        recs.append(_esw.record(MODULE, f"hospital:{_esw.slug(district)}:{_esw.slug(hosp)}", dept="health", level="facility",
                                area=hosp, place=place, facility_type=HOSP.get(kind, kind), district=district,
                                post="Medical Superintendent" + (" (in charge)" if ic else ""), name=name,
                                phone=_esw.phones(mob), email=_esw.emails(mail), serial=sno.rstrip("."), state="AP",
                                source=url, page=url))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:contacts", "payload": {"reader": MODULE, "url": CONTACT, "csms_url": CSMS, "state": "AP"}}]


def fetch(p, get):
    recs, files, why = [], [], []
    for name, url, parse in (("contact", p.get("url") or CONTACT, parse_contact), ("csms", p.get("csms_url") or CSMS, parse_csms)):
        r = get(url)
        if r is None:
            why.append(f"no answer from {name}")
            continue
        files.append(_esw.keep(MODULE, name, r.content))
        got = parse(r.text, url)
        if not got:
            why.append(f"no rows on {name}")
        recs += got
    return recs, files, "; ".join(why) if not recs else ""
