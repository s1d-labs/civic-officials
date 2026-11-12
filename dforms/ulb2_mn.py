"""Manipur: the officers of the municipal councils, from district portal tables (dforms/_ulb2_ne.py reads them).

- Bishnupur, https://bishnupur.nic.in/dlos-and-other-officials/ (S3WaaS, saved by archive.s1d.me 2026-11-05): table "CEO's/EO's
  MUNICIPAL OFFICE" (Sl. No., Name of the Officer, Designation/Department, Email ID; no phones, no emails filled): the Executive
  Officer of each of the district's 7 councils ("EO, Oinam & Kwakta" and "EO, Moirang & Kumbi" head two councils each).
  The district's who's-who page (bishnupur.nic.in/whos-who/, paged) names other officers for the same councils ("CEO, Nambol
  Municipal Council ..."): it is read by officials.py; the dlos table is the one list with all 7.
Other districts: Thoubal's /committee/ page names the Executive Officer posts of its 6 councils without names; Imphal West, Imphal
East, Kakching and Jiribam pages name no council officer (archive copies of 2026-11-05/11). The elected councils (elections of
2018) ended their term in 2023; no later council election was found, so there is no chairperson to read.
Not India-only (S3WaaS sites answer from Germany).
"""
from dforms import _ulb2_ne

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_mn"
STATE = "MN"
MC = "Municipal Council"
PAGES = [
    {"url": "https://bishnupur.nic.in/dlos-and-other-officials/", "district": "Bishnupur", "key": "bishnupur-dlos",
     "rules": [[r"^C?EO\b.*\bNambol\b", "Nambol", "276515", MC], [r"^C?EO\b.*\bOinam\b", "Oinam", "276506", MC],
               [r"^C?EO\b.*\bKwakta\b", "Kwakta", "276525", MC], [r"^C?EO\b.*\bBishnupur\b", "Bishnupur", "276501", MC],
               [r"^C?EO\b.*\bNingthoukhong\b", "Ningthoukhong", "276530", MC], [r"^C?EO\b.*\bMoirang\b", "Moirang", "276514", MC],
               [r"^C?EO\b.*\bKumbi\b", "Kumbi", "276505", MC]]},
]


def items(get=None):
    return [{"key": f"{MODULE}-{p['key']}", "payload": {"reader": MODULE, "url": p["url"], "district": p["district"], "state": STATE,
                                                       "rules": p["rules"], "india_only": False}} for p in PAGES]


def parse(html, rules, district=None, url=""):
    return _ulb2_ne.parse(MODULE, STATE, html, rules, district, url)


def fetch(p, get):
    return _ulb2_ne.fetch(MODULE, STATE, p, get)
