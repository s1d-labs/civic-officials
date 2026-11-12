"""Andhra Pradesh: IGRS "List of Officers" PDF (registration.ap.gov.in/igrs/pdfs/R&S Department.pdf, 13 pages, dated 2025-09-22 in the
file). Answers only from India. One GET. Pages: IG office, DIGs (12), District Registrars (26), Audit DRs (13), Chit Registrars (left
out: not registration of documents), then every SRO by district ("SRIKAKULAM DISTRICT" headings): Sl.No, SRO name, SRO code, email,
mobile. Read with pypdf layout text. One queue item.
Record ids: dept:sro_ap:AP-SRO-<SRO code>, AP-DR-<slug>, AP-DIG-<slug>.
"""
import re

from dforms import _esw

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_ap"
URL = "https://registration.ap.gov.in/igrs/pdfs/R&S%20Department.pdf"
LAST_UPDATED = "2025-09-22"
SRO = re.compile(r"^\s*(\d+)\s+(.+?)\s{2,}(\d{3,4})\s+(\S+\s?@igrs\.ap\.gov\.in)\s*(\d*)\s*$")
OTHER = re.compile(r"^\s*(\d+)\s+((?:DIG|DR|SR)\b[ .].+?)\s{2,}(\S+\s?@igrs\.ap\.gov\.in)\s*(\d*)\s*$")
DIST = re.compile(r"^\s{10,}([A-Z][A-Z .]+?)\s+DISTRICT\s*$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "AP", "india_only": True}}]


def _mail(s):
    return _esw.emails(re.sub(r"\s+@", "@", s))


def _phone(s):
    return _esw.phones(s) if s and s.strip("0") else ""


def parse(pages, url=URL):
    recs, seen, district = [], set(), None
    for line in "\n".join(pages).splitlines():
        m = DIST.match(line)
        if m:
            district = " ".join(w if w in ("SPS", "YSR", "NTR") else w.title() for w in m.group(1).split())
            continue
        m = SRO.match(line)
        if m:
            _, name, code, mail, mob = m.groups()
            key = f"AP-SRO-{code}"
            area = re.sub(r"\s*\(?R\.?O\.?\)?\.?$", "", name).strip()
            f = dict(level="subdistrict", area=area.title(), post="Sub Registrar", office=name, district=district, office_id=key, sro_code=code)
        else:
            m = OTHER.match(line)
            if not m:
                continue
            _, desig, mail, mob = m.groups()
            kind = desig.split(".")[0].split()[0]
            place = re.sub(r"^(DIG|DR|SR)[ .]+", "", desig).strip()
            audit = "(audit)" in place.lower()
            place = re.sub(r"\s*\(Audit\)", "", place, flags=re.I).strip()
            if kind == "DIG":
                key, f = f"AP-DIG-{_esw.slug(place)}", dict(level="zone", post="Deputy Inspector General")
            else:
                post = ("District Registrar" if kind == "DR" else "Sub Registrar") + (" (Audit)" if audit else "")
                key = f"AP-{kind}{'-AUDIT' if audit else ''}-{_esw.slug(place)}"
                f = dict(level="district", post=post)
            f.update(area=place, office=desig, office_id=key)
        if key in seen:
            continue
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="registration", phone=_phone(mob), email=_mail(mail), state="AP", source=url,
                                last_updated=LAST_UPDATED, **f))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "rs-department", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, url)
    return recs, files, "" if recs else "no rows"
