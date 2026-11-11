"""Bihar: the RO/ERO of each of the 243 assembly constituencies, from the CEO Bihar contact page
(ceoelection.bihar.gov.in/RO-ERO_Contact_Details2025.html). Answers only from India (Germany times out). Plain http.

One static page, table id=eroTable: Sl. No., District, Assembly (name only), RO/ERO Name, Office Address, Mobile No. No AERO, no email,
no date. AC numbers come from the AC layer by name (+ district for the two names that two ACs share), with ALIAS for spellings the
layer writes otherwise. One queue item.
Record ids: dept:ero_br:BR-AC-<no>:ero (BR-AC-<slug>:ero when the name stays unmatched).
"""
from dforms import _esw

MODULE = "ero_br"
URL = "http://ceoelection.bihar.gov.in/RO-ERO_Contact_Details2025.html"
ALIAS = {"surajgarha": "suryagarha", "chiraiya": "chiraia"}   # normalised page name -> layer name, where ac_no() misses
DISTRICT = {"purvichamparan": "purbachamparan"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "BR", "india_only": True}}]


def ac_no(name, district):
    n = _esw.norm_ac(name)
    d = _esw.norm_ac(district)
    return _esw.ac_no("BR", ALIAS.get(n, n), DISTRICT.get(d, d))


def parse(html, url=URL):
    soup = _esw.soup(html)
    t = soup.find("table", id="eroTable") or max(soup.find_all("table"), key=lambda x: len(x.find_all("tr")), default=None)
    if t is None:
        return []
    rows = _esw.grid(t)
    head = [h.lower() for h in rows[0]] if rows else []
    recs, seen = [], set()
    for row in rows[1:]:
        c = dict(zip(head, row))
        name, district = c.get("assembly", ""), c.get("district", "").title()
        if not name or not c.get("ro/ero name"):
            continue
        no = ac_no(name, district)
        ac = f"BR-AC-{no}" if no else f"BR-AC-{_esw.slug(name)}"
        key, i = f"{ac}:ero", 2
        while key in seen:
            key, i = f"{ac}:ero:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="elections", level="ac", area=f"{no} - {name}" if no else name,
                                post="Electoral Registration Officer", designation="RO/ERO", name=c.get("ro/ero name"),
                                address=c.get("office address"), phone=_esw.phones(c.get("mobile no.")), state="BR",
                                district=district, office_id=ac if no else None, source=url))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "ro-ero-contact-details-2025", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
