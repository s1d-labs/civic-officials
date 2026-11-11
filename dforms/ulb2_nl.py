"""Nagaland: the heads of the town bodies, from district portal tables (dforms/_ulb2_ne.py reads them).

- Mokokchung, https://mokokchung.nic.in/district-administration-contact-details/ (S3WaaS, saved by archive.s1d.me 2026-11-06):
  row "ADC and Administrator MMC" (Atsungba Walling, mobile 8415059304) = the Administrator of Mokokchung Municipal Council.
Other districts: the S3WaaS pages say that a Town Council is "headed by an Administrator in the rank of Additional Deputy
Commissioner" (tseminyu.nic.in/municipal/) or give only "Office of the Administrator, <Town> Town Council" (Shamator, Tseminyu,
Peren disaster-management committee), with no name. The district who's-who pages name the ADCs, but not as administrators of a
council, so they are not read as town officials here. The elected councils of the June 2024 election (first in about 20 years)
and their chairpersons are on no page of the archive (ud.nagaland.gov.in "Urban Local Bodies/ Towns" and "List of Employees" are
empty pages; no State Election Commission site in the archive).
Not India-only.
"""
from dforms import _ulb2_ne

MODULE = "ulb2_nl"
STATE = "NL"
PAGES = [
    {"url": "https://mokokchung.nic.in/district-administration-contact-details/", "district": "Mokokchung", "key": "mokokchung-contacts",
     "rules": [[r"\badministrator\s+(MMC|mokokchung\s+municipal)", "Mokokchung", "249717", "Municipal Council"]]},
]


def items(get=None):
    return [{"key": f"{MODULE}-{p['key']}", "payload": {"reader": MODULE, "url": p["url"], "district": p["district"], "state": STATE,
                                                       "rules": p["rules"], "india_only": False}} for p in PAGES]


def parse(html, rules, district=None, url=""):
    return _ulb2_ne.parse(MODULE, STATE, html, rules, district, url)


def fetch(p, get):
    return _ulb2_ne.fetch(MODULE, STATE, p, get)
