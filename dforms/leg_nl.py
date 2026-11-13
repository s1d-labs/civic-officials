"""Nagaland: members of the 14th Legislative Assembly (2023-) from the state portal (www.nagaland.gov.in/legislatures,
one table). Saved in archive.s1d.me (2026-11-05).

Columns: Sl.No (= the ECI AC number, 1 Dimapur-I ... 60 Pungro-Kiphire) | Elected Member | Assembly Constituency | Social Media
(an X/Twitter link for some). No party, phone, email or address on this page. The assembly site (nagalandassembly.gov.in /
webtest.nagaland.gov.in/nla) is not read. One queue item = the page. Record ids: dept:leg_nl:NL-AC-<no>.
"""
from dforms._trail import tr_pos
from dforms import _esw, _leg, _leg_se
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_nl"
URL = "https://www.nagaland.gov.in/legislatures"
ALIAS = {"tenning": "tening"}


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "NL", "india_only": False}}]


def parse(html, url):
    recs = []
    for tr in _esw.soup(html).find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3 or not _esw.clean(tds[0].get_text()).isdigit():
            provenance.skip_row(tr, 'skip: len(tds) < 3 or not _esw.clean(tds[0].get_text()).isdigit()')
            continue
        sl, nm, cons = (_esw.clean(td.get_text(" ")) for td in tds[:3])
        by_name, note = _leg_se.seat("NL", None, cons, alias=ALIAS)
        links = [a["href"] for a in tds[3].find_all("a", href=True)] if len(tds) > 3 else []
        recs.append(_leg.member(MODULE, "NL", "AC", by_name or int(sl), _leg_se.name(nm), constituency=cons, source=url,
                                website=", ".join(links), seat_no=int(sl), note=note,
                                house="Nagaland Legislative Assembly (14th)", src_pos=tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "legislatures", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no members in the page"
