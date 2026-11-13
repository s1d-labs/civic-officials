"""Uttar Pradesh: MLAs of the 18th UP Vidhan Sabha (2022-) from the assembly's "Member's Information" page
(upvidhansabhaproceedings.gov.in/web/guest/member-s-information; the old site uplegisassembly.gov.in does not answer from
Germany or India, 2026-11-11). Answers from Germany. One page of about 3.5 MB: the same members three times (grid by district,
list by district, grid by party); the reader reads the list view: per district a table with name, "Constituency - AC no",
party, "Phone no:" and "Address:" (one address: mostly the home in the constituency, some Lucknow addresses).
No email, no office / residence split, no constituency office.

The list holds every member of the 18th assembly (about 418), also members who left after a by-election (Khair 71: Anoop
Pradhan, now MP, and Surendra Diler, by-election 2024). The page does not say who sits now, so a seat with two or more names
is not tied to the seat: each name gets its own record without office_id ("UP-AC-x-<name>") and "seat_note" says so; one
name per seat gets office_id UP-AC-<no>. Some rows give AC number 0 (Kol, Soranv): the name decides the number.
Each member's own page is /web/guest/member?memberId=<id> ("member_page").
The page pairs some AC numbers with a neighbour's name ("Meerut Cantt - 48": ECI 47 is Meerut Cantt, 48 is Meerut; the same for
Meerut South, Fatehpur / Fatehpur Sikri, Katra / Katra Bazar, Bilaspur 38, Dadraul 65; 2026-11-12 list). The name and the member
agree (MyNeta 2022), the number does not: when the name is an exact ECI name (dforms/ac_no.json) with another number, the name's
number is taken and "seat_note" keeps the page's number.
"""
import re
from collections import Counter

from dforms._trail import tr_pos
from dforms import _esw, _leg
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_up"
URL = "https://upvidhansabhaproceedings.gov.in/web/guest/member-s-information"
BASE = "https://upvidhansabhaproceedings.gov.in"
SHARED = "the page lists {n} members for this seat (a by-election); it does not say who sits now"
ALIAS = {"kol": "koil", "soranv": "soraon"}         # the page's spellings -> dforms/ac_no.json
MISPAIRED = "the page prints AC {page} with this name; ECI's number for {cons} is {eci}"


def seat_of(no, cons):
    """(site AC number, note) for the page's AC number and constituency name: an exact ECI name wins over the page's number."""
    name = ALIAS.get(_leg.norm(cons), cons)
    seat, note = _leg.ac_seat("UP", no, name)
    eci = _esw.ac_no("UP", name)
    if seat and eci and eci != seat:
        return eci, MISPAIRED.format(page=seat, cons=cons, eci=eci)
    return seat, note


def items(get=None):
    return [{"key": "leg_up-list", "payload": {"reader": MODULE, "url": URL, "state": "UP", "india_only": False}}]


def rows(html, where=None):
    """[(memberId, district, name, constituency, AC no or None, party, phone, address)] of the list view, each member once.
    where: a dict; when given, it gets {memberId: src_pos of its <tr>}."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for tr in soup.find_all("tr", onclick=re.compile(r"memberId=\d+")):
        mid = re.search(r"memberId=(\d+)", tr["onclick"]).group(1)
        tds = tr.find_all("td", recursive=False)
        if mid in seen or len(tds) < 4:
            provenance.skip_row(tr, 'skip: mid in seen or len(tds) < 4')
            continue
        seen.add(mid)
        if where is not None:
            where[mid] = tr_pos(tr)
        entry = tr.find_parent("div", class_=re.compile(r"districtEntry"))
        leg = entry.find("legend") if entry else None
        name = _leg.clean(tr.find(class_="full-name").get_text(" ")) if tr.find(class_="full-name") else ""
        m = re.match(r"(.+?)\s*-\s*(\d+)\s*$", _leg.clean(tds[1].get_text(" ")))
        cons, no = (m.group(1), int(m.group(2))) if m else (_leg.clean(tds[1].get_text(" ")), None)
        contact = {}
        for div in tds[3].find_all("div"):
            t = _leg.clean(div.get_text(" "))
            k = re.match(r"(Phone no|Address)\s*:\s*", t)
            if k:
                contact[k.group(1)] = t[k.end():].strip(" .") if k.group(1) == "Address" else t[k.end():]
        out.append((mid, _leg.clean(leg.get_text(" ")) if leg else "", name, cons, no or None,
                    _leg.clean(tds[2].get_text(" ")), contact.get("Phone no", ""), contact.get("Address", "")))
    return out


def parse(html, url=URL):
    where = {}
    rs = rows(html.replace("\u200d", "").replace("\u200c", ""), where)
    seats, ids = {}, {}
    for r in rs:                                         # the same person listed twice (two member ids) counts once
        seat, note = seat_of(r[4], r[3])
        k = (seat or r[3], _leg.slug(r[2]))
        if k in seats:
            ids[k].append(r[0])
            continue
        seats[k], ids[k] = (r, seat, note), [r[0]]
    n = Counter(k[0] for k in seats if isinstance(k[0], int))
    recs = []
    for k, ((mid, district, name, cons, no, party, phone, addr), seat, note) in seats.items():
        shared = seat and n[seat] > 1
        rid, d = _leg.member(MODULE, "UP", "AC", None if shared else seat, name, constituency=cons, party=party, source=url,
                             phone=phone, address=addr, district=district, seat_no=seat or no,
                             member_page=f"{BASE}/web/guest/member?memberId={mid}", member_id=", ".join(ids[k]),
                             note="; ".join(x for x in (SHARED.format(n=n[seat]), note) if x) if shared else note, src_pos=where.get(mid))
        recs.append((rid + "-" + _leg.slug(name) if shared else rid, d))      # two names, one seat: the name keeps them apart
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "members", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no members"
