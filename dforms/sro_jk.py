"""Jammu and Kashmir: Sub Registrar contacts of the Inspector General of Registration (igr.jk.gov.in/ConUsSubRegistrar.html). Answers
only from India. One GET; two tables (JAMMU DIVISION, KASHMIR DIVISION): S.No, Office ("SR R.S.Pura", "Sub Registrar Budgam"), Name of
Sub Registrar, Location (office address), PIN, Contact No, E-mail. The office is named after its tehsil / sub-division. The footer
"Last Updated: DD-MM-YYYY" is a template, not a date. One queue item.
Record ids: dept:sro_jk:JK-SRO-<slug of office place>.
"""
import re

from dforms import _esw

MODULE = "sro_jk"
URL = "https://igr.jk.gov.in/ConUsSubRegistrar.html"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "JK", "india_only": True}}]


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        division = next((r[0].title() for r in g[:2] if "DIVISION" in r[0].upper()), None)
        for row in g:
            if len(row) < 7 or not row[0].strip().isdigit():
                continue
            _, office, name, loc, pin, phone, mail = row[:7]
            place = re.sub(r"^(SR|Sub[ -]?Re[gq]istrar)\s+", "", office, flags=re.I).strip()
            base = f"JK-SRO-{_esw.slug(place)}"
            key, i = base, 2
            while key in seen:
                key, i = f"{base}-{i}", i + 1
            seen.add(key)
            address = ", ".join(x for x in (loc, pin) if x)
            recs.append(_esw.record(MODULE, key, dept="registration", level="subdistrict", area=place, post="Sub Registrar",
                                    office=office, name=name, phone=_esw.phones(phone), email=_esw.emails(mail), address=address,
                                    division=division, state="JK", office_id=key, source=url))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "con-us-sub-registrar", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
