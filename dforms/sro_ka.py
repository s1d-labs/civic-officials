"""Karnataka: Sub-Registrar offices of the Department of Stamps and Registration (igr.karnataka.gov.in/14/sub-registrars/en).
Answers only from India (Germany gets no connection). One GET; one table of about 260 rows: Sl.No., District Registrar Office
(rowspan, carried down), Sub Registrar Office, Name ("Ayeesha Tabassum, Sub Registrar"), Office Address, Phone No., E-mail ID.
No village jurisdiction: the office is named after its town or locality. The page shows no date. One queue item.
Record ids: dept:sro_ka:KA-SRO-<slug of office>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_ka"
URL = "https://igr.karnataka.gov.in/14/sub-registrars/en"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "KA", "india_only": True}}]


def split_name(s):
    """"Prakash Nayak,FDA , Sub registrar (I/C)" -> ("Prakash Nayak", "FDA, Sub registrar (I/C)")."""
    parts = [x.strip() for x in re.split(r"\s*,\s*", s or "") if x.strip()]
    if not parts:
        return "", ""
    return parts[0], ", ".join(parts[1:])


def parse(html, url=URL):
    soup = _esw.soup(html)
    table = next((t for t in soup.find_all("table") if "Sub Registrar Office" in t.get_text(" ")), None)
    if table is None:
        return []
    rows = pgrid(table)
    recs, seen = [], set()
    for row in rows[1:]:
        if len(row) < 7 or not row[0].strip().isdigit():
            continue
        _, dro, office, who, address, phone, email = row[:7]
        name, desig = split_name(who)
        base = f"KA-SRO-{_esw.slug(office)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}-{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="registration", level="office", area=office, post="Sub Registrar",
                                designation=desig if desig.lower() != "sub registrar" else None, name=name, phone=_esw.phones(phone), email=_esw.emails(email), address=address,
                                registration_district=re.sub(r"^DRO\s*", "", dro).strip(), state="KA", office_id=key, source=url, src_pos=row.pos))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "sub-registrars", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
