"""Himachal Pradesh: the own sites of town bodies that civic.official has no row for (gap list of 2026-11-11). Most HP bodies run a
site of one web vendor (footer link itacademics.co.in; host 184.168.99.245): mc<town>.in / mc<town>.com for municipal councils and
corporations, np<town>.in / np<town>.com for nagar panchayats. Pages "Officers" / "Officer" / "Employee" / "dir" hold a table
"Sr. No. | Designation | Name | Phone Number | Remark" (Secretary or Executive Officer first), "ElectedOfficers" a table of the
President, Vice President and ward members when the site fills it, "Contact" the office email and phone.

The Directorate of Urban Development (ud.hp.gov.in) gave no answer from Germany or from the India server on 2026-11-11, and its
archive copy (2026-11-05) is cut off in the stylesheet: no list of EOs / secretaries could be read there.
The hosts were found by DNS (mc|np + LGD name + .in/.com/.co.in/.org) and by the search agents (found_sites.csv). Sites of
bodies that the hub read already (mcbilaspur.com, npchopal.in, npkarsog.in, npnirmand.in, npsuni.in, nptahliwal.in, mctheog.in,
shimlamc.hp.gov.in, municipalcorporationmandi.in) are left out: their rows are in civic.official but not tied (found_sites has
no state, see the report). One item per site: _ulb2_nw.crawl() reads the start page, checks that it is the body's site
(refuses parked domains), follows up to 8 officer / contact links and reads every officer table.
Not India-only: mcnadaun.in, mchamirpur.com and npamb.in answered from Germany on 2026-11-11.
"""
from dforms import _esw, _ulb2_nw

MODULE = "ulb2_hp"
STATE = "HP"
# start url | LGD code | district | body (LGD name) | body type | name on the site when it differs ("A|B" = either)
SITES = """https://mcnainadevi.in/|248238|Bilaspur|Naina Devi|Municipal Council|
https://nptalai.com/|248237|Bilaspur|Talai|Nagar Panchayat|
https://mcchamba.in/|248046|Chamba|Chamba|Municipal Council|
https://npchowari.in/|276627|Chamba|Chowari|Nagar Panchayat|
https://npbhota.in/|248230|Hamirpur|Bhota|Nagar Panchayat|
https://mchamirpur.com/|248229|Hamirpur|Hamirpur|Municipal Corporation|
https://mcnadaun.in/|248228|Hamirpur|Nadaun|Municipal Council|
https://npbanjar.in/|248221|Kullu|Banjar|Nagar Panchayat|
https://npchirgaon.in/|297013|Shimla|Chirgaon|Nagar Panchayat|
https://npjubbal.com/|248251|Shimla|Jubbal|Nagar Panchayat|
https://npkotkhai.in/|248252|Shimla|Kotkhai|Nagar Panchayat|
https://npnarkanda.in/|248246|Shimla|Narkanda|Nagar Panchayat|
https://npnerwa.com/|297014|Shimla|Nerwa|Nagar Panchayat|
https://mcrampur.in/|248245|Shimla|Rampur|Municipal Council|
https://mcrohru.in/|248253|Shimla|Rohru|Municipal Council|
https://nprajgarh.in/|248047|Sirmaur|Rajgarh|Nagar Panchayat|
https://nparki.in/|248240|Solan|Arki|Nagar Panchayat|
https://mcbaddi.in/|248242|Solan|Baddi|Municipal Corporation|
https://npamb.in/|297009|Una|Amb|Nagar Panchayat|
https://npjogindernagar.in/|248222|Mandi|Jogindarnagar|Municipal Council|Jogindarnagar|Joginder Nagar|Jogindernagar"""


def site_items(module, state, sites, india_only=False):
    out = []
    for line in sites.splitlines():
        url, lgd, district, body, btype, *match = line.split("|")
        p = {"reader": module, "url": url, "state": state, "body": body, "district": district, "lgd_code": lgd,
             "body_type": btype, "india_only": india_only}
        match = "|".join(m for m in match if m)
        if match:
            p["match"] = match
        out.append({"key": f"{module}-{_esw.slug(body)}-{lgd}", "payload": p})
    return out


def items(get=None):
    return site_items(MODULE, STATE, SITES)


def fetch(p, get):
    return _ulb2_nw.crawl(p, get, MODULE, STATE)
