"""Mizoram: members of the 9th Legislative Assembly (2023-) with party and present / permanent address, from the member
profiles of the assembly site (mizoramassembly.in/members/details/<id>; the list mizoramassembly.in/members names the 40 ids).
Answers from Germany too.

Profile: name (h4), "3-Mamit" (ECI AC number - constituency), a table: Father's Name, Date of Birth, Place of Birth, Present
Address, Permanent Address, Educational Qualification, Political Party Affilication, Date of Election ... No phone, no email.
The site's "Who's Who" PDF (storage/downloads-forms/July2024/vJtaahmm0J07CdUfkNkK.pdf, 2024) has the same fields, its
"Address & Contact No." column is empty. One queue item = one member profile. items(get) reads the list page for the ids; without
get it uses IDS (the list as read on 2026-11-11). Record ids: dept:leg_mz:MZ-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_se

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_mz"
LIST = "https://mizoramassembly.in/members"
DETAIL = "https://mizoramassembly.in/members/details/{}"
IDS = [51, 15, 16, 76, 70, 19, 20, 68, 74, 58, 77, 64, 61, 59, 78, 71, 66, 79, 80, 56, 81, 82, 67, 73, 43, 24, 60, 83, 84, 57,
       69, 72, 85, 86, 75, 87, 30, 65, 62, 63]


def list_ids(html):
    out = []
    for m in re.finditer(r'<h3>\s*<a href="(?:https?://[^"/]+)?/members/details/(\d+)"', html):
        if int(m.group(1)) not in out:
            out.append(int(m.group(1)))
    return out


def items(get=None):
    ids = IDS
    if get is not None:
        r = get(LIST)
        ids = (list_ids(r.text) if r is not None else []) or IDS
    return [{"key": f"{MODULE}-member-{i}", "payload": {"reader": MODULE, "url": DETAIL.format(i), "state": "MZ", "member_id": i,
                                                      "india_only": False}} for i in ids]


def parse(html, url):
    s = _esw.soup(html)
    box = s.select_one("div.profile-page")
    if not box or not box.find("h4"):
        return []
    nm = _leg_se.name(box.find("h4").get_text(" "))
    a = box.find("a")
    m = re.match(r"\s*(\d+)\s*-\s*(.+)", _esw.clean(a.get_text(" ")) if a else "")
    no, cons = (int(m.group(1)), _esw.clean(m.group(2))) if m else (None, "")
    f = {}
    for tr in box.find_all("tr"):
        th, tds = tr.find("th"), tr.find_all("td")
        if th and tds:
            f[_esw.clean(th.get_text(" ")).lower()] = _esw.cell_text(tds[-1]).replace(" | ", ", ")
    party = next((v for k, v in f.items() if k.startswith("political party")), "")
    seat, note = _leg_se.seat("MZ", no, cons)
    present, perm = f.get("present address", ""), f.get("permanent address", "")
    return [_leg.member(MODULE, "MZ", "AC", seat, nm, constituency=cons, party=party, source=url, residence_address=present,
                        permanent_address=perm if perm and perm != present else "", elected_on=f.get("date of election", ""),
                        note=note, house="Mizoram Legislative Assembly (9th)")]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, f"member-{p.get('member_id', 'x')}", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no profile in the page"
