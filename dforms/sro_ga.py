"""Goa: Civil Registrar-cum-Sub Registrar offices, one per taluka (reg.goa.gov.in/contact-us.html, the online marriage portal's contact
page; the numbers are the taluka SR offices). Answers only from India (Germany gets 403). One GET; table "Taluka Office | Contact No"
(12 rows: "Civil Registrar-cum-Sub Registrar, Bardez, Mapusa." = taluka Bardez, office at Mapusa) and the State Registrar row
(Designation, Email, Address, Phone, Fax). No officer names per office, no email per office. The page shows no date. One queue item.
Record ids: dept:sro_ga:GA-SRO-<taluka>, GA-SR-state.
"""
import re

from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_ga"
URL = "https://reg.goa.gov.in/contact-us.html"
TALUKA = {"panaji": "Tiswadi", "mormugao": "Mormugao", "satari": "Sattari"}   # office town -> taluka, where the page names the town


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "GA", "india_only": True}}]


def _mail(s):
    return _esw.emails(re.sub(r"\[\s*@\s*\]", "@", s or ""))


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs = []
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not g:
            continue
        head = [h.lower() for h in g[0]]
        if head[:1] == ["taluka office"]:
            for row in g[1:]:
                if len(row) < 2:
                    continue
                parts = [x.strip(" .") for x in row[0].split(",")[1:] if x.strip(" .")]
                if not parts:
                    continue
                first = parts[0]
                taluka = TALUKA.get(first.lower(), first)
                town = parts[-1]
                key = f"GA-SRO-{_esw.slug(taluka)}"
                recs.append(_esw.record(MODULE, key, dept="registration", level="subdistrict", area=taluka, post="Civil Registrar-cum-Sub Registrar",
                                        office=row[0].strip(" ."), town=town, phone=_esw.phones(row[1]), state="GA", office_id=key,
                                        source=url))
        elif head[:2] == ["designation", "email"]:
            for row in g[1:]:
                if len(row) >= 4 and "state registrar" in row[0].lower():
                    recs.append(_esw.record(MODULE, "GA-SR-state", dept="registration", level="state", area="Goa", post=row[0],
                                            email=_mail(row[1]), address=row[2], phone=_esw.phones(row[3]), state="GA",
                                            office_id="GA-SR-state", source=url))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contact-us", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
