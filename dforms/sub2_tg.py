"""Telangana: Tahsildar (MRO), MPDO and RDO of every mandal / revenue division, from the "Administrative Setup" pages of the 33
district portals (<district>.telangana.gov.in, S3WaaS). No reachable state-wide list was found: the CEO's RO/ARO lists
(ceotelangana.nic.in, 2019 and 2023) give no answer even from India, CCLA's key contacts are the head office only, and the PR&RD
directory is known only as a Scribd copy (see the report).

Structure: the same S3WaaS menu as Andhra Pradesh: "Tehsil" / "Mandals" / "MROs" / "Tahsildars & MPDOs" (Gadwal /mandals/:
officer, mandal, mobile; Hyderabad /tehsil/: mandal and the Tahsildar's CUG mobile; Khammam /mros/), "MPDOs" (Medak, Nizamabad,
Rajanna Sircilla /mpdos/) and "Revenue Divisions" (RDO name and mobile). The reader is dforms/sub2_ap.py read() with the
Telangana hosts; the /tehsil/ pages of seeds/dept_field_revenue_s3waas.json (Jagtial, Khammam, Medak, Nalgonda, Nirmal, Siddipet,
Rajanna Sircilla) are left out, that reader has them.

One queue item = one district: 1 GET (home page menu) + 1 GET per linked page (2-6). 33 items, about 70-150 requests.
Records: dept revenue / rural_development / administration, level subdistrict / block / subdivision; area = the mandal or division
as the page spells it. Ids: dept:sub2_tg:<host>:<level>:<slug of area>[:n].
"""
from dforms import sub2_ap

METHOD = "html table (district portal pages from its menu)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_tg"
STATE = "TG"
HOSTS = {
    "adilabad.telangana.gov.in": "Adilabad", "asifabad.telangana.gov.in": "Kumuram Bheem Asifabad",
    "bhoopalapally.telangana.gov.in": "Jayashankar Bhupalapally", "gadwal.telangana.gov.in": "Jogulamba Gadwal",
    "hanumakonda.telangana.gov.in": "Hanumakonda", "hyderabad.telangana.gov.in": "Hyderabad", "jagtial.telangana.gov.in": "Jagitial",
    "jangaon.telangana.gov.in": "Jangoan", "kamareddy.telangana.gov.in": "Kamareddy", "karimnagar.telangana.gov.in": "Karimnagar",
    "khammam.telangana.gov.in": "Khammam", "kothagudem.telangana.gov.in": "Bhadradri Kothagudem",
    "mahabubabad.telangana.gov.in": "Mahabubabad", "mahabubnagar.telangana.gov.in": "Mahabubnagar",
    "mancherial.telangana.gov.in": "Mancherial", "medak.telangana.gov.in": "Medak",
    "medchal-malkajgiri.telangana.gov.in": "Medchal Malkajgiri", "mulugu.telangana.gov.in": "Mulugu",
    "nagarkurnool.telangana.gov.in": "Nagarkurnool", "nalgonda.telangana.gov.in": "Nalgonda", "narayanpet.telangana.gov.in": "Narayanpet",
    "nirmal.telangana.gov.in": "Nirmal", "nizamabad.telangana.gov.in": "Nizamabad", "peddapalli.telangana.gov.in": "Peddapalli",
    "rajannasircilla.telangana.gov.in": "Rajanna Sircilla", "rangareddy.telangana.gov.in": "Ranga Reddy",
    "sangareddy.telangana.gov.in": "Sangareddy", "siddipet.telangana.gov.in": "Siddipet", "suryapet.telangana.gov.in": "Suryapet",
    "vikarabad.telangana.gov.in": "Vikarabad", "wanaparthy.telangana.gov.in": "Wanaparthy", "warangal.telangana.gov.in": "Warangal",
    "yadadri.telangana.gov.in": "Yadadri Bhuvanagiri",
}
POSTS = {"subdistrict": "Tahsildar", "block": "Mandal Parishad Development Officer", "subdivision": "Revenue Divisional Officer"}


def items(get=None):
    return sub2_ap.items(get, MODULE, HOSTS, STATE)


def fetch(p, get):
    return sub2_ap.read(p, get, MODULE, STATE, HOSTS, posts=POSTS)
