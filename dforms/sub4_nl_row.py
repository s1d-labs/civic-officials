"""Nagaland: Deputy Commissioners and the district Right of Way nodal officers (EACs and SDOs), from the state RoW portal's
"Public Entities for RoW" page (row.nagaland.gov.in/publicEntities). One HTML table, 32 rows on 2026-11-13: Name of Public Entity
(the officer) | Designation | District | Contact (mobile) | Email. The page answered from dev-vps-3 (Mumbai); its certificate
chain is incomplete (TLS check off on failure: records tls_unverified through get()). Route abroad not checked.

Records: Deputy Commissioner -> dept administration, level district, area = district; EAC (Extra Assistant Commissioner) and
SDO (Sub-Divisional Officer (Civil)) -> dept administration, level subdivision, area = the district headquarters sub-division
(the portal names only the district). A row whose name cell repeats the post ("Noklak SDO") keeps no name.
One queue item: 1 GET. Record ids: dept:sub4_nl_row:<post>:<district slug>[:n].
"""
import re

from dforms import _esw
import provenance

METHOD = "html table rows (BeautifulSoup)"     # source trail (provenance.py)

MODULE = "sub4_nl_row"
URL = "https://row.nagaland.gov.in/publicEntities"
LGD = {"chumoukedima": "758", "dimapur": "244", "kiphire": "614", "kohima": "245", "longleng": "615", "meluri": "788",
       "mokokchung": "246", "mon": "247", "niuland": "764", "noklak": "736", "peren": "613", "phek": "248", "shamator": "765",
       "tseminyu": "757", "tuensang": "249", "wokha": "250", "zunheboto": "251"}
POSTS = (("dc", "Deputy Commissioner", "district", r"deputy\s+commissioner"),
         ("eac", "Extra Assistant Commissioner", "subdivision", r"\beac\b|extra\s+assistant"),
         ("sdo", "Sub-Divisional Officer (Civil)", "subdivision", r"\bs\.?d\.?o\b|sub[\s-]*divisional"))
TITLE = re.compile(r"^(?:mr|ms|mrs|shri|smt|dr|er|b)\.?\s+", re.I)


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "NL", "india_only": False}}]


def build(html, source=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for table in soup.find_all("table"):
        pos = []
        rows = _esw.grid(table, pos=pos)
        if not rows or not re.search(r"(?i)designation", " ".join(rows[0])):
            continue
        for row, sp in zip(rows[1:], pos[1:]):
            if len(row) < 4:
                provenance.skip_row(row, 'skip: len(row) < 4')
                continue
            name, desig, district, contact = row[:4]
            email = row[4] if len(row) > 4 else ""
            post = next((p for p in POSTS if re.search(p[3], desig, re.I)), None)
            if not post or not district:
                provenance.skip_row(row, 'skip: not post or not district')
                continue
            dk = re.sub(r"[^a-z]", "", district.lower())
            if re.fullmatch(rf"(?i)\s*{re.escape(district)}\s+{re.escape(desig)}\s*", name):
                name = ""                                   # "Noklak SDO": the post, no person
            person = re.sub(r",?\s*\b(NCS|IAS|lAS)\b\.?", "", name).strip(" ,.")
            cadre = "IAS" if re.search(r"\b[Il]AS\b", name) else ("NCS" if re.search(r"\bNCS\b", name) else "")
            k = f"{post[0]}:{_esw.slug(district)}"
            while k in seen:
                k += ":2"
            seen.add(k)
            recs.append(_esw.record(MODULE, k, dept="administration", level=post[2], post=post[1], designation=desig,
                                    area=district, district=district, district_code=LGD.get(dk, ""), state="NL",
                                    name=TITLE.sub("", person).strip(), cadre=cadre, phone=_esw.phones(contact),
                                    email=_esw.emails(email), source=source, role="Right of Way nodal officer"
                                    if post[0] != "dc" else None, src_pos=sp))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = build(r.text, url)
    return recs, [_esw.keep(MODULE, "public-entities", r.content)], "" if recs else "no rows"
