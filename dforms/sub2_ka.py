"""Karnataka: Tahsildar of every taluk, Executive Officer of every taluk panchayat and Assistant Commissioner of every revenue
sub-division, from the taluk / taluk panchayat / sub-division pages of the 31 district portals (<district>.nic.in, S3WaaS).
No state-wide list with names was found: RDPR (rdpr.karnataka.gov.in) has no officer list, Mahiti Kanaja's "Officials of PRI"
lists gram panchayat staff per GP (and answered an error for a taluk), the ZP portals (zp<district>.karnataka.gov.in) each have
their own page layout, and the CEO's BLO files (dforms/ero_ka.py) name AEROs without post or taluk (see the report).

Structure: the home page is in Kannada; the English menu (start page https://<host>/en/) links pages such as "Taluk Office" / "Tahsildars" / "Taluks" (taluk, Tahsildar, phone, e-mail),
"Taluk Panchayat" (taluk, EO, phone, e-mail) and "Assistant Commissioners" / "Sub Division" (sub-division, AC, phone). The
reader is dforms/sub2_ap.py read() with the Karnataka hosts and posts; the menu words (taluk, taluk panchayat, assistant
commissioner) are in sub2_ap.KINDS. A page that only names the taluks gives no record.

One queue item = one district: 1 GET (home page menu) + 1 GET per linked page (1-6). 33 items (shimoga.nic.in and
shivamogga.nic.in both answer), about 60-150 requests.
Records: dept revenue / rural_development / administration, level subdistrict / block / subdivision; area = the taluk or
sub-division as the page spells it. Ids: dept:sub2_ka:<host>:<level>:<slug of area>[:n].
"""
from dforms import sub2_ap

MODULE = "sub2_ka"
STATE = "KA"
HOSTS = {
    "bagalkot.nic.in": "Bagalkote", "ballari.nic.in": "Ballari", "bangalorerural.nic.in": "Bengaluru Rural",
    "belagavi.nic.in": "Belagavi", "bengalurusouth.nic.in": "Bengaluru South", "bengaluruurban.nic.in": "Bengaluru Urban",
    "bidar.nic.in": "Bidar", "chamrajnagar.nic.in": "Chamarajanagar", "chikkaballapur.nic.in": "Chikkaballapura",
    "chikkamagaluru.nic.in": "Chikkamagaluru", "chitradurga.nic.in": "Chitradurga", "davanagere.nic.in": "Davanagere",
    "dharwad.nic.in": "Dharwad", "dk.nic.in": "Dakshina Kannada", "gadag.nic.in": "Gadag", "hassan.nic.in": "Hassan",
    "haveri.nic.in": "Haveri", "kalaburagi.nic.in": "Kalaburagi", "kodagu.nic.in": "Kodagu", "kolar.nic.in": "Kolar",
    "koppal.nic.in": "Koppal", "mandya.nic.in": "Mandya", "mysore.nic.in": "Mysuru", "raichur.nic.in": "Raichur",
    "ramanagara.nic.in": "Bengaluru South", "shimoga.nic.in": "Shivamogga", "shivamogga.nic.in": "Shivamogga",
    "tumkur.nic.in": "Tumakuru", "udupi.nic.in": "Udupi", "uttarakannada.nic.in": "Uttara Kannada",
    "vijayanagara.nic.in": "Vijayanagara", "vijayapura.nic.in": "Vijayapura", "yadgir.nic.in": "Yadgir",
}
POSTS = {"subdistrict": "Tahsildar", "block": "Executive Officer, Taluk Panchayat", "subdivision": "Assistant Commissioner"}


def items(get=None):
    return sub2_ap.items(get, MODULE, HOSTS, STATE, path="en/")


def fetch(p, get):
    return sub2_ap.read(p, get, MODULE, STATE, HOSTS, posts=POSTS)
