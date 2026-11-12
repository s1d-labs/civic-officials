"""Moradabad Nagar Nigam (nagarnigammoradabad.in): the sanitation supervisor (सफाई नायक) of each of the 70 wards, with the zone of
the ward. One PDF, "ulb_ward_detail" (/assets/files/ulb_ward_detail.pdf; Excel print, 5 pages; saved in archive.s1d.me 2026-11-05),
set in Kruti Dev (converted with dforms/_ward_kd.py). Columns: वार्ड संख्या | वार्ड का नाम | मा0 पार्षद का नाम (+ mobile) |
सफाई नायक का नाम (+ mobile) | क्षेत्र (zone letter N / S / E / W) | voters | male / female / total population | households.
The councillors are not read here (the councillors task has them). The PDF shows no date.
Records: one per ward, post "Sanitation Supervisor", level "ward", wards [n], area_regional = the ward name, zone = "North Zone" ...
Names are Hindi: name and name_regional carry the same text. Record ids: dept:ward2n_moradabad:ward-<n>:sanitation-supervisor.
"""
import re

from dforms import _esw, _ward, _ward_kd as kd

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_moradabad"
BODY, LGD, STATE, DISTRICT = "Moradabad Nagar Nigam", "248929", "UP", "Moradabad"
URL = "https://nagarnigammoradabad.in/assets/files/ulb_ward_detail.pdf"
ZONES = {"N": "North Zone", "S": "South Zone", "E": "East Zone", "W": "West Zone"}
MOB = re.compile(r"(?<!\d)([6-9]\d{9})(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-ward-detail", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def rows(pages):
    """[(ward no, ward name kd, supervisor kd, mobile, zone letter)]."""
    out = []
    for pg in pages:
        for ln in pg.splitlines():
            cells = [c for c in re.split(r"\s{2,}", ln.strip()) if c]
            if len(cells) < 5 or not re.fullmatch(r"\d{1,2}", cells[0]):
                continue
            zi = next((i for i, c in enumerate(cells) if c in ZONES), None)
            if zi is None or zi < 4:
                continue
            sup = cells[zi - 1]
            m = MOB.search(sup)
            out.append((str(int(cells[0])), cells[1], _esw.clean(MOB.sub(" ", sup)).strip(" ]"), m.group(1) if m else "",
                        cells[zi]))
    return out


def parse(pages, p):
    seen, recs = set(), []
    for ward, wname, sup, mob, z in rows(pages):
        name = _esw.clean(kd.convert(sup)).strip(" ,")
        recs.append(_ward.record(MODULE, f"ward-{ward}:sanitation-supervisor", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="ward", area=f"Ward {ward}", area_regional=_esw.clean(kd.convert(wname)),
                                 zone=ZONES[z], post="Sanitation Supervisor", post_regional="सफाई नायक", name=name,
                                 name_regional=name or None, phone=mob, wards=[ward], wing="sanitation", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "ward-detail", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no ward rows (pdftotext missing?)"
