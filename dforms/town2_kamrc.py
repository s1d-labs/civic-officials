"""Karnataka: the office staff of every urban body on the Municipal Reforms Cell platform (www.<site>.mrc.gov.in, one Drupal site per
City Corporation, City / Town Municipal Council and Town Panchayath), from the site's "City Staff" page, /en/city-staff.

The page is one table: Sl No | Name | Designation | Contact No (| Photo), with one-cell section rows: "Municipal Chief Officer
Details" / "Municipal Commissioner Details", "Engineering Section Details", "Health Section Details", "Revenue Section Details",
"Administration Section Details", "Finance Section Details", "Day Nulm Section Details", "Information Technology (I.T) Section
Details". Posts: Chief Officer / Municipal Commissioner (role head), Assistant Executive Engineer, Environment Engineer, Junior
Engineer, Senior / Junior Health Inspector, Revenue Officer, First Grade Revenue Inspector, Bill Collector, Office Manager, First /
Second Division Assistant, Accountant, Community Affairs Officer, Junior Programmer, Attender, Valveman. Every named row is kept
(clerical posts too: the page lists them as the office's staff). Rows "1-Post Vacant" / "Vacant" are counted as vacant posts.
Contact No is a mobile in most rows. The page shows no date.
Samples (live from India over plain http, dev-vps-3 Mumbai, 2026-11-13): Badami TMC (22 rows), Jamkhandi CMC (two "Housing" rows
with no name; a 4-column table without Photo), Kudachi TMC. aminagadtown answered 503 (the site is down: the item fails and the
hub retries it). When /en/city-staff has no staff table, the reader asks /kn/city-staff once (Kannada posts get an English post
from ward3_kamrc_staff.english(); post_regional keeps the Kannada).

Sites: dforms/ulb2_ka_sites.json (319 sites with body name, district and LGD local body code, made for ulb2_ka), minus the three
corporations whose city-staff page ward3_kamrc_staff reads already (Kalaburagi, Mangaluru, Raichur). India only: no answer from
Germany (ulb2_ka, 2026-11-11); the Indian proxies gave up on these hosts (hub, 2026-11-12); the India server answers (route
"direct"). One queue item = one site.
Records: dept town_body, level body, area = the body name of the site list, lgd_code; post as written (the Kannada one in
post_regional); role from _ulb.role_of; section; phone = Contact No. Record ids: dept:town2_kamrc:<site>:<post slug>:<name slug>.
"""
import json
import re
from pathlib import Path

import provenance
from dforms import _esw, _town2
from dforms.ward3_kamrc_staff import KANNADA, english

METHOD = "html table (staff table with section rows)"

MODULE = "town2_kamrc"
STATE = "KA"
SITES = json.loads((Path(__file__).with_name("ulb2_ka_sites.json")).read_text())
DONE = {"kalaburagicity", "mangalurucity", "raichurcity"}          # ward3_kamrc_staff reads their city-staff pages
UPDATED = re.compile(r"(?i)last\s*updated\s*(?:on)?\s*:?\s*([A-Za-z]{3}\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})")


def url_of(site, lang="en"):
    return f"http://www.{site}.mrc.gov.in/{lang}/city-staff"


def items(get=None):
    out = []
    for s in SITES:
        if s["site"] in DONE:
            continue
        p = {"reader": MODULE, "url": url_of(s["site"]), "site": s["site"], "body": s["body"], "state": STATE,
             "india_only": True, "route": "direct"}
        for k in ("lgd_code", "district"):
            if s.get(k):
                p[k] = s[k]
        out.append({"key": f"{MODULE}-{s['site']}", "payload": p})
    return out


def parse(html, p, url, seen=None):
    """Records of one city-staff page."""
    seen = seen if seen is not None else set()
    m = UPDATED.search(_esw.soup(html).get_text(" "))
    extra = {"page_updated": m.group(1)} if m else {}
    recs = []
    for row in _town2.staff_rows(html):
        post_kn = None
        if KANNADA.search(row["post"]):
            en = english(row["post"])
            if en:
                post_kn, row = row["post"], {**row, "post": en}
        recs.append(_town2.record(MODULE, STATE, p["site"], p["body"], row, seen, district=p.get("district"),
                                  lgd_code=p.get("lgd_code"), source=url, src_url=url, post_regional=post_kn,
                                  **extra))
    return recs


def fetch(p, get):
    files, recs, seen = [], [], set()
    for lang in ("en", "kn"):
        url = p["url"] if lang == "en" else url_of(p["site"], "kn")
        r = get(url)
        if r is None:
            if lang == "en":
                return [], [], "no answer"
            break
        files.append(_esw.keep(MODULE, f"{p['site']}-{lang}", r.content))
        recs = parse(r.text, p, url, seen)
        if recs:
            break
    return recs, files, "" if recs else "no staff rows"
