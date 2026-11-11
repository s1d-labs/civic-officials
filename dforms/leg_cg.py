"""Chhattisgarh: members of the 6th Chhattisgarh Vidhan Sabha (2023-) from the assembly's member page in Hindi
(cgvidhansabha.gov.in/hindi_new/mla_current.htm, 2026-11-11). The English page (english_new/mla_current.htm) still lists the 5th
assembly (2018-2023), so the reader reads the Hindi page. Answers from Germany.

One HTML table, one row per seat (90): serial, "01- भरतपुर-सोनहट ( अ.ज.जा.)" (AC number - constituency), name, party,
"स्थायी पता व दूरभाष" (permanent address, then "मोबाइल नं." / "फोन" numbers and "e-mail :"), "स्थानीय पता व दूरभाष" (the Raipur
address, sometimes with a phone), photo. A vacant seat is one row of 3 cells with a note (67 Ahiwara on 2026-11-11: the
member died); the reader leaves it out. The AC number decides the seat. Names, constituencies and addresses are in Hindi
(name = name_regional = the printed name without श्री / श्रीमती). Party: BJP / INC / GGP from the Hindi name (party_regional = as
printed). Fields: permanent_address, residence_address (Raipur), phone (the permanent column: mobiles and landlines),
phone_residence (Raipur), email. No constituency office.
One queue item = the whole page. Record ids: dept:leg_cg:CG-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_neva

MODULE = "leg_cg"
URL = "https://cgvidhansabha.gov.in/hindi_new/mla_current.htm"
PARTY = {"भारतीय जनता पार्टी": "BJP", "इंडियन नेशनल कांग्रेस": "INC", "गोंडवाना गणतंत्र पार्टी": "GGP"}
PHONE = re.compile(r"मोबाइल|फोन|दूरभाष|टेलीफोन|\bमो\.|\bMob", re.I)
EMAIL = re.compile(r"e-?\s?mail|ई-?\s?मेल", re.I)


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "CG", "india_only": False}}]


def split_cell(td):
    """(address, phones, emails) of one address cell: the address is the text before the first phone or e-mail word."""
    t = _esw.cell_text(td)
    email = _esw.emails(t)
    m = EMAIL.search(t)
    body = t[:m.start()] if m else t
    p = PHONE.search(body)
    address = (body[:p.start()] if p else body).strip(" |,")
    phone = _esw.phones(body[p.start():]) if p else ""
    return _esw.clean(address.replace(" | ", ", ")), phone, email


def parse(html, url=URL):
    recs = []
    for tr in _esw.soup(html).find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 6 or not _esw.clean(tds[0].get_text()).strip(".").isdigit():     # "19." too
            continue
        m = re.match(r"(\d{1,3})\s*-\s*(.+)", _esw.clean(tds[1].get_text(" ")))
        if not m:
            continue
        no = int(m.group(1))
        cons = re.sub(r"\(\s*", "(", _esw.clean(m.group(2)))
        name = _leg_neva.name(tds[2].get_text(" "))
        party = _esw.clean(tds[3].get_text(" "))
        perm, mobile, email = split_cell(tds[4])
        local, phone_local, email_local = split_cell(tds[5])
        seat, note = _leg.ac_seat("CG", no, cons)
        recs.append(_leg.member(MODULE, "CG", "AC", seat, name, constituency=cons, party=PARTY.get(party, party), source=url,
                                email=", ".join(x for x in (email, email_local) if x), phone=mobile,
                                phone_residence=phone_local, permanent_address=perm, residence_address=local, seat_no=no,
                                name_regional=name, party_regional=party, note=note,
                                house="Chhattisgarh Vidhan Sabha (6th)"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "mla_current", r.content)]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no members"
