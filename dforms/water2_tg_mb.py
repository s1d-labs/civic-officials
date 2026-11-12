"""Telangana: Mission Bhagiratha (Telangana Drinking Water Supply Corporation) and RWS&S officers from the district web sites
(<district>.telangana.gov.in, S3WaaS / WordPress; answer from Germany and India). The state sites missionbhagiratha.telangana.gov.in
and mbbulk.telangana.gov.in time out from Germany and India (checked 2026-11-11), so the district pages are the public source.

items(get) asks the search of each of the 33 district sites (/?s=bhagiratha and /?s=rws) and queues every page whose title names
the department ("Mission Bhagiratha Grid", "Missionbhagiratha Intradivision", "RWS & Mission Bhagiratha"). One queue item = one page.
Only some pages hold officers: Bhadradri Kothagudem /missionbhagiratha-intradivision/ (?p=39208, "Last Updated" 25.02.2025 in the
page body; footer 09.11.2026) has two tables: Sl.No. | NAME OF THE OFFICER | DESIGNATION | PLACE OF WORK | CONTACT No. | OFFICE
E-MAIL ID (EE Grid Division, EE Intra Division) and S.No | NAME OF THE OFFICER | DESIGNATION | NAME OF THE SUB DIVISION/MANDAL |
CONTACT NUMBER (Dy.E.E per sub-division, AE/AEE per mandal: 27 rows). Other districts (Jangaon, Kamareddy, Nirmal, Gadwal) describe
the department only (fetch() returns no rows and says so). Expected: about 30-150 rows over the state, mostly sub-division and mandal.
Levels: EE = division, Dy.E.E = subdivision, AEE / AE (mandal section officer) = section, SE = circle (see _util2_south_water).
last_updated = the page footer "Last Updated: DD.MM.YYYY". Record ids: dept:water2_tg_mb:<district>:<level>-<area>-<post>[:n].
"""
from dforms import _util2_south_water as sw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "water2_tg_mb"
HOSTS = [(f"{h}.telangana.gov.in", d) for h, d in (
    ("adilabad", "Adilabad"), ("asifabad", "Kumuram Bheem Asifabad"), ("bhoopalapally", "Jayashankar Bhupalpally"),
    ("gadwal", "Jogulamba Gadwal"), ("hanumakonda", "Hanumakonda"), ("hyderabad", "Hyderabad"), ("jagtial", "Jagtial"),
    ("jangaon", "Jangaon"), ("kamareddy", "Kamareddy"), ("karimnagar", "Karimnagar"), ("khammam", "Khammam"),
    ("kothagudem", "Bhadradri Kothagudem"), ("mahabubabad", "Mahabubabad"), ("mahabubnagar", "Mahabubnagar"),
    ("mancherial", "Mancherial"), ("medak", "Medak"), ("medchal-malkajgiri", "Medchal Malkajgiri"), ("mulugu", "Mulugu"),
    ("nagarkurnool", "Nagarkurnool"), ("nalgonda", "Nalgonda"), ("narayanpet", "Narayanpet"), ("nirmal", "Nirmal"),
    ("nizamabad", "Nizamabad"), ("peddapalli", "Peddapalli"), ("rajannasircilla", "Rajanna Sircilla"), ("rangareddy", "Rangareddy"),
    ("sangareddy", "Sangareddy"), ("siddipet", "Siddipet"), ("suryapet", "Suryapet"), ("vikarabad", "Vikarabad"),
    ("wanaparthy", "Wanaparthy"), ("warangal", "Warangal"), ("yadadri", "Yadadri Bhuvanagiri"))]
WORDS = ("bhagiratha", "rws")
TITLE = r"bhagiratha|bhageeratha|\bRWS\b|rural\s+water"


def items(get):
    return sw.search_items(get, MOD, "TG", HOSTS, WORDS, TITLE, "rws")


def fetch(p, get):
    return sw.fetch_page(dict(p, org=p.get("org", "Mission Bhagiratha / RWS&S")), get, MOD, "TG")
