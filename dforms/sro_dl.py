"""Delhi: Sub-Registrar offices of the Revenue Department (revenue.delhi.gov.in/revenue/sub-registar-offices). Answers from Germany and
India. One GET; one table, 39 rows: District (rowspan, carried down), Sub-Registrar Office, Address. This is the 2026 structure: 13
registration districts, 39 sub-divisions; each SRO's jurisdiction is the revenue sub-division of the same name. No officer name, phone or
email on the page. The page shows no date. One queue item.
Record ids: dept:sro_dl:DL-SRO-<slug of office>.
"""
from dforms import _esw

MODULE = "sro_dl"
URL = "https://revenue.delhi.gov.in/revenue/sub-registar-offices"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "DL"}}]


def parse(html, url=URL):
    soup = _esw.soup(html)
    table = next((t for t in soup.find_all("table") if "SUB-REGISTRAR" in t.get_text(" ").upper()), None)
    if table is None:
        return []
    recs, seen = [], set()
    for row in _esw.grid(table):
        if len(row) < 3 or row[0].strip().upper() == "DISTRICT" or not row[1].strip():
            continue
        district, office, address = row[:3]
        base = f"DL-SRO-{_esw.slug(office)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}-{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="registration", level="subdistrict", area=office, post="Sub Registrar",
                                address=address, state="DL", district=district, office_id=key, source=url))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "sub-registar-offices", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
