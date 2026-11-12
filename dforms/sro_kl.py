"""Kerala: "List of Offices in Kerala" of the Registration Department (registration.kerala.gov.in/en/contact/; keralaregistration.gov.in
itself does not answer). Answers from Germany and India. One GET; one table per district (only the first has the header row): Sl No,
Name & Location of Office, District, Address, Designated Officer ("Sub Registrar", "District Registrar General", "District Registrar
Audit", "Deputy Inspector General (South Zone)"), Telephone, e-Mail. About 315 Sub Registrar offices + District Registrar and DIG
offices (345 rows). No officer names, no village jurisdiction: a Sub Registrar office is named after its town. The page shows no date.
Record ids: dept:sro_kl:KL-SRO-<district>-<office>, KL-DR-<district>-<gl|audit>, KL-DIG-<zone>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_kl"
URL = "https://registration.kerala.gov.in/en/contact/"
HEAD = ["sl", "office", "district", "address", "post", "phone", "email"]


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "KL"}}]


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        for row in pgrid(t):
            if len(row) != 7 or not re.fullmatch(r"\d+", row[0].strip()):
                continue
            c = dict(zip(HEAD, row))
            post, office, district = c["post"], c["office"], c["district"]
            pl = post.lower()
            if "inspector general" in pl:
                zone = re.search(r"\(([^)]+)\)", post)
                base, level, area = f"KL-DIG-{_esw.slug(zone.group(1) if zone else district)}", "zone", zone.group(1) if zone else district
            elif "district registrar" in pl:
                kind = "audit" if "audit" in pl else "gl"
                base, level, area = f"KL-DR-{_esw.slug(district)}-{kind}", "district", district
            else:
                base, level, area = f"KL-SRO-{_esw.slug(district)}-{_esw.slug(office)}", "office", office
            key, i = base, 2
            while key in seen:
                key, i = f"{base}-{i}", i + 1
            seen.add(key)
            recs.append(_esw.record(MODULE, key, dept="registration", level=level, area=area, post=post, office=office,
                                    phone=_esw.phones(c["phone"]), email=_esw.emails(c["email"]), address=c["address"], state="KL",
                                    district=district, office_id=key, source=url, src_pos=row.pos))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contact", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
