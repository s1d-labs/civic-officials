"""Sikkim: members of the 11th Legislative Assembly (2024-) from the state portal's who's who
(www.sikkim.gov.in/mygovernment/whos-who/mlas, one table, 32 rows). Saved in archive.s1d.me (2026-11-06).

Columns: Name | Position ("Hon'ble MLA") | Constituency. No AC number (the name decides), no party, phone, email or address.
No assembly site with a member list was found. One queue item = the page. Record ids: dept:leg_sk:SK-AC-<no>.
"""
from dforms import _esw, _leg, _leg_se

MODULE = "leg_sk"
URL = "https://www.sikkim.gov.in/mygovernment/whos-who/mlas"
ALIAS = {"khamdungsingtam": "khamdongsingtam", "daramdimbl": "daramdinbl", "westpandam": "westpendam", "dzongubl": "djongubl",
         "syaribl": "shyaribl", "sorengchakhung": "soreongchakung", "namchisingithang": "namchisinghithang"}
FIXED = {"sangha": 32}            # the Sangha seat (monasteries) is not in the site's AC layer: ECI number 32


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "SK", "india_only": False}}]


def parse(html, url):
    recs = []
    for tr in _esw.soup(html).find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        nm, pos, cons = (_esw.clean(td.get_text(" ")) for td in tds[:3])
        if "MLA" not in pos.upper() or not nm:
            continue
        no, note = _leg_se.seat("SK", FIXED.get(_esw.norm_ac(cons)), cons, alias=ALIAS)
        recs.append(_leg.member(MODULE, "SK", "AC", no, _leg_se.name(nm), constituency=cons, source=url, note=note,
                                house="Sikkim Legislative Assembly (11th)"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "mlas", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no members in the page"
