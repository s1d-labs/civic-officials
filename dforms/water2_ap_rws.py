"""Andhra Pradesh: Rural Water Supply and Sanitation (RWS&S) and Public Health Engineering officers from the district web sites
(<district>.ap.gov.in, S3WaaS / WordPress; answer from Germany and India). No state-wide public directory was found: rws.ap.gov.in,
aprws.ap.gov.in and apphmed.ap.gov.in do not resolve, www.appublichealth.gov.in and phmed.ap.gov.in give no connection.

items(get) asks the search of each of the 28 district sites (/?s=rural+water and /?s=public+health) and queues every page whose
title names the department ("Rural Water Supply and Sanitation(RWSS)", "Rural Water Supply", "Public Health Engineering").
One queue item = one page. Pages seen 2026-11-11:
- SPSR Nellore ?p=31534 and Tirupati /rural-water-supply-and-sanitationrwss/: one table Sl.No | Name of the Officer | Designation |
  Circle / Division / Sub-Division | Phone Number (SE / District RWS Engineering Officer, EEs, DEEs: 12-14 rows each);
- Krishna /rural-water-supply-and-sanitation/: S.NO | Name of the Officer | Division/Mandal Attached | Contact Number (the post is
  in the "attached" cell: "Executive Engineer(P),Vijayawada."; 15 rows);
- Kakinada /departments/rural-water-supply/, Konaseema ?p=27971: one text line "Executive Engineer, RWS & S, Kakinada, Contact
  No.9100121101, Email : eerwskkd[at]ap[dot]gov[dot]in";
- Kadapa ?p=28061 (Public Health wing, payload wing "ph"): Official Designation | E-Mail ID | Contact Number (EE + 3 DEE).
Expected: about 150-300 rows over the state (SE, EE, DEE per district; few pages list the mandal AEs).
Levels: SE / District RWS Engineering Officer = circle, EE = division, DEE = subdivision, AEE / AE = section.
last_updated = the page footer "Last Updated: DD.MM.YYYY". Record ids: dept:water2_ap_rws:<district>:<level>-<area>-<post>[:n].
"""
import re

from dforms import _util2_south_water as sw

MOD = "water2_ap_rws"
HOSTS = [(f"{h}.ap.gov.in", d) for h, d in (
    ("allurisitharamaraju", "Alluri Sitharama Raju"), ("anakapalli", "Anakapalli"), ("ananthapuramu", "Ananthapuramu"),
    ("annamayya", "Annamayya"), ("bapatla", "Bapatla"), ("chittoor", "Chittoor"), ("eastgodavari", "East Godavari"),
    ("eluru", "Eluru"), ("guntur", "Guntur"), ("kadapa", "YSR Kadapa"), ("kakinada", "Kakinada"), ("konaseema", "Konaseema"),
    ("krishna", "Krishna"), ("kurnool", "Kurnool"), ("markapuram", "Markapuram"), ("nandyal", "Nandyal"), ("ntr", "NTR"),
    ("palnadu", "Palnadu"), ("parvathipurammanyam", "Parvathipuram Manyam"), ("polavaram", "Polavaram"), ("prakasam", "Prakasam"),
    ("spsnellore", "SPSR Nellore"), ("srikakulam", "Srikakulam"), ("srisathyasai", "Sri Sathya Sai"), ("tirupati", "Tirupati"),
    ("visakhapatnam", "Visakhapatnam"), ("vizianagaram", "Vizianagaram"), ("westgodavari", "West Godavari"))]
WORDS = ("rural water", "public health")
TITLE = r"rural\s+water|\bRWS|public\s+health\s+eng|public\s+health\s+(and|&)\s+municipal|\bPHMED\b"


def items(get):
    out = sw.search_items(get, MOD, "AP", HOSTS, WORDS[:1], TITLE, "rws")
    for it in sw.search_items(get, MOD, "AP", HOSTS, WORDS[1:], TITLE, "ph"):
        if not any(o["payload"]["url"] == it["payload"]["url"] for o in out):
            out.append(it)
    for it in out:
        if re.search(r"(?i)public\s+health", it["payload"].get("title", "")):
            it["payload"]["wing"] = "ph"
    return out


def fetch(p, get):
    org = "Public Health Engineering" if p.get("wing") == "ph" else "RWS&S"
    return sw.fetch_page(dict(p, org=p.get("org", org)), get, MOD, "AP")
