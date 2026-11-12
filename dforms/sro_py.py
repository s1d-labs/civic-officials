"""Puducherry: Sub-Registrar offices of the Registration Department (regn.py.gov.in/contact.html). Answers from Germany and India. One
GET; one table (id tbcontact), 12 rows: SRO Region (commune / taluk: "Bahour", "Karaikal Thirunallar", "Mahe"), Sub-Registrar (name),
Office Address, Phone, Mail. The district comes from the region (Karaikal, Mahe, Yanam, else Puducherry). The page shows no date.
One queue item. Record ids: dept:sro_py:PY-SRO-<slug of region>.
"""
from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_py"
URL = "https://regn.py.gov.in/contact.html"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "PY"}}]


def _district(region):
    for d in ("Karaikal", "Mahe", "Yanam"):
        if region.lower().startswith(d.lower()):
            return d
    return "Puducherry"


def parse(html, url=URL):
    soup = _esw.soup(html)
    table = soup.find("table", id="tbcontact") or soup.find("table")
    if table is None:
        return []
    recs, seen = [], set()
    for row in pgrid(table)[1:]:
        if len(row) < 5 or not row[0].strip():
            continue
        region, name, address, phone, mail = row[:5]
        base = f"PY-SRO-{_esw.slug(region)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}-{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="registration", level="subdistrict", area=region, post="Sub Registrar", name=name,
                                phone=_esw.phones(phone), email=_esw.emails(mail), address=address.replace(" | ", ", ").strip(", "),
                                state="PY", district=_district(region), office_id=key, source=url, src_pos=row.pos))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contact", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
