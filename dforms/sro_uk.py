"""Uttarakhand: directory of the Stamp and Registration Department (registration.uk.gov.in/directory/). Answers from Germany and India.
One GET; one table (data-table-1), about 75 rows: Name, Designation, Email ([at]/[dot]), Mobile, Landline, Address (= the office's
town: "Dehradun (I)", "Kapkot", "(HQ)"). 51 Sub Registrar rows (in hill tehsils the Tehsildar is in-charge Sub Registrar), District
Registrars (ADMs), AIGs, DIGs and HQ. /directory/page/2 lists no rows. The page shows no date. One queue item.
Record ids: dept:sro_uk:UK-SRO-<town>, UK-DR-<town>, UK-AIG-<town>, UK-DIG-<town>, UK-HQ-<slug of designation>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_uk"
URL = "https://registration.uk.gov.in/directory/"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "UK"}}]


def _kind(desig, town):
    d = desig.lower()
    if "(hq)" in town.lower() or "head of department" in d or "(hq)" in d:
        return "HQ", "state", "Inspector General of Registration office"
    if "deputy inspector general" in d:
        return "DIG", "zone", "Deputy Inspector General"
    if "inspector general" in d or re.match(r"aig\b", d):
        return "AIG", "district", "Assistant Inspector General"
    if "district registrar" in d:
        return "DR", "district", "District Registrar"
    return "SRO", "subdistrict", "Sub Registrar"


def parse(html, url=URL):
    soup = _esw.soup(html)
    table = soup.find("table", class_="data-table-1") or soup.find("table")
    if table is None:
        return []
    rows = pgrid(table)
    recs, seen = [], set()
    for row in rows[1:]:
        if len(row) < 6:
            continue
        name, desig, mail, mobile, land, town = row[:6]
        if not re.search(r"[A-Za-z]", name):
            name = ""
        if not re.search(r"[A-Za-z]", desig):
            desig = "Sub Registrar" if re.match(r"sr\d?[a-z]", mail) else ""
        kind, level, post = _kind(desig, town)
        area = re.sub(r"\s*\(", " (", town).strip()
        place = _esw.slug(desig)[:40].strip("-") if kind == "HQ" else _esw.slug(area)
        base = f"UK-{kind}-{place}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}-{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="registration", level=level, area=area, post=post,
                                designation=desig if desig.lower() != post.lower() else None, name=name,
                                phone=_esw.phones(mobile, land), email=_esw.emails(mail), state="UK", office_id=key, source=url, src_pos=row.pos))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "directory", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
