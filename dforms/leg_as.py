"""Assam: members of the 16th Legislative Assembly (elected 2026-05-04) with phone, email and address, from the assembly site
(assambidhansabha.org/members, "Members of Current Assembly"). Answers from Germany too.

The list has 7 pages of 20 cards (members?page=N): name, party, "23-CHENGA" (the ECI number after the 2023 delimitation), email,
phone. Each card links to members?id=<n>, which adds the present and the permanent address (and repeats the email).
One queue item = one list page; fetch() also reads the detail page of each member on it (20 GETs) for the addresses.
Seat numbers: _leg.ac_seat("AS", ...) maps the name to the site's pre-2023 AC layer. A seat that is not in that layer gets no
number (id AS-AC-x-<constituency>, seat_no = the ECI number, seat_note says why): its ECI number can be an old number of another seat.
Record ids: dept:leg_as:AS-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_se

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_as"
BASE = "https://assambidhansabha.org/members"
PAGES = 7
ALIAS = {"rangia": "Rangiya"}      # site spelling -> the old AC layer's name


def items(get=None):
    return [{"key": f"{MODULE}-page-{n}", "payload": {"reader": MODULE, "url": f"{BASE}?page={n}", "state": "AS", "page": n,
                                                    "details": True, "india_only": False}} for n in range(1, PAGES + 1)]


def parse_list(html):
    """[(detail url, name, party, ECI no, constituency, email, phone)] from one list page."""
    out = []
    for p in _esw.soup(html).select("p.text-light"):
        box = p.find_parent("div")
        a = box.find("a", href=re.compile(r"members\?id=\d+")) if box else None
        strong = p.find("strong")
        spans = [_esw.clean(s.get_text(" ")) for s in p.find_all("span")]
        if not strong or len(spans) < 2:
            continue
        m = re.match(r"(\d+)\s*-\s*(.+)", spans[1])
        no, cons = (int(m.group(1)), _esw.clean(m.group(2))) if m else (None, spans[1])
        email = _esw.emails(" ".join(spans[2:]))
        phone = _esw.phones(" ".join(s for s in spans[2:] if "@" not in s))
        out.append((a["href"] if a else "", _leg_se.name(strong.get_text(" ")), spans[0], no, cons, email, phone))
    return out


def parse_detail(html):
    """{field name: value} from a member's detail page (Present Address & Contact No, Permanent Address & Contact No, ...)."""
    out = {}
    for tr in _esw.soup(html).select("div.member-details tr"):
        k, v = tr.select_one("td.field-name"), tr.select_one("td.field-value")
        if k and v:
            out[_esw.clean(k.get_text(" "))] = _esw.cell_text(v).replace(" | ", ", ")
    return out


def record(row, detail, url):
    durl, nm, party, no, cons, email, phone = row
    present = detail.get("Present Address & Contact No", "")
    perm = detail.get("Permanent Address & Contact No", "")
    seat, note = _leg.ac_seat("AS", no, ALIAS.get(_esw.norm_ac(cons), cons))
    if note:            # a post-2023 seat that the old AC layer does not have: its ECI number may be another seat's old number
        seat = None     # (ECI 5 Parbatjhora vs old 5 Badarpur), so the record is keyed by name: AS-AC-x-<constituency>
    extra_phone = _esw.phones(present, perm)
    return _leg.member(MODULE, "AS", "AC", seat, nm, constituency=_leg_se.title(cons), party=party, source=durl or url,
                       phone=", ".join(x for x in (phone, extra_phone) if x),
                       email=", ".join(x for x in (email, _esw.emails(detail.get("E-mail ID (If Any)", ""))) if x),
                       residence_address=present, permanent_address=perm, seat_no=no, note=note,
                       house="Assam Legislative Assembly (16th)")


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, f"page-{p.get('page', 'x')}", r.content)]
    recs = []
    for row in parse_list(r.text):
        detail = {}
        if p.get("details") and row[0]:
            rd = get(row[0])
            if rd is not None:
                files.append(_leg.keep(MODULE, "member-" + row[0].rsplit("=", 1)[-1], rd.content))
                detail = parse_detail(rd.text)
        recs.append(record(row, detail, p["url"]))
    return recs, files, "" if recs else "no members in the page"
