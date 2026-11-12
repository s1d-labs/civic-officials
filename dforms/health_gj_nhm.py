"""Gujarat: the District Programme Management Unit of the National Health Mission in every district, from
nhm.gujarat.gov.in/dpmu.htm ("List of Officers" -> "District Program Management Unit"; static HTML, no key). One <h3> with the
district name and one table per district: Sr. No. | Designation | Name of Officers | Contact No. | Email ID (written
dpc[dot]health[dot]x[at]gmail[dot]com). Posts: DPC (District Programme Coordinator, head of the unit, under the Chief District
Health Officer), DFO (District Finance Officer), D M&E, DDM (District Data Manager), Programme Associate (Nutrition), DUPC
(District Urban Programme Coordinator). 32 tables, 192 rows with a name or phone (2026-11-12, from Mumbai). The page names no CDHO.
Not read: bpmu.htm (block finance and M&E assistants, names only).
The archive holds no copy; the GitHub pool got no answer from nhm.gujarat.gov.in/contact-us/ on 2026-11-11 (status 0): treat as
India only (unchecked).

Records (depts.py contract): dept health, level district, area = district (LGD name; the site's spelling kept in district_site),
post as written, name, phone, email. One queue item = one GET. Ids: dept:health_gj_nhm:<slug of district>:<serial>.
"""
import re

from dforms import _esw

METHOD = "html table per district heading"     # source trail (provenance.py): how this reader reads its sources

MODULE = "health_gj_nhm"
URL = "https://nhm.gujarat.gov.in/dpmu.htm"
# site heading -> LGD district name (lgd.districts, state 24) where they differ
LGD = {"banaskantha": "Banas Kantha", "dang": "Dangs", "gir-somnath": "Gir Somnath", "kutch": "Kachchh", "mehsana": "Mahesana",
       "panchamahal": "Panch Mahals", "sabarkantha": "Sabar Kantha", "vadorara": "Vadodara", "devbhoomi dwarka": "Devbhumi Dwarka",
       "chhota udepur": "Chhotaudepur", "aravalli": "Arvalli"}


def parse(html, url=URL):
    s = _esw.soup(html)
    recs, seen = [], set()
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or not re.search(r"(?i)designation", " ".join(rows[0])):
            continue
        h = t.find_previous("h3")
        site = _esw.clean(h.get_text(" ", strip=True)) if h else ""
        district = LGD.get(site.lower(), site)
        head = [c.lower() for c in rows[0]]

        def col(rx, row):
            for i, hd in enumerate(head):
                if re.search(rx, hd) and i < len(row):
                    return row[i]
            return ""
        for row, sp in zip(rows[1:], pos[1:]):
            sn = col(r"sr\.?\s*no", row)
            post, name = col(r"designation", row), col(r"name", row)
            phone, email = _esw.phones(col(r"contact|mobile", row)), _esw.emails(" ".join(row[head.index("email id"):]) if "email id" in head else col(r"email", row))
            if not (name or phone or email):
                continue
            key = f"{_esw.slug(site)}:{sn if re.fullmatch(r'\d{1,3}', sn or '') else _esw.slug(post)}"
            k, n = key, 2
            while k in seen:
                k, n = f"{key}:{n}", n + 1
            seen.add(k)
            recs.append(_esw.record(MODULE, k, dept="health", level="district", area=district, post=post, name=name, phone=phone,
                                    email=email, district=district, district_site=site if site != district else None,
                                    unit="NHM District Programme Management Unit", serial=sn or None, state="GJ", source=url,
                                    page=url, src_url=url, src_pos=sp))
    return recs


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "GJ", "india_only": True, "expected": 192}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_esw.keep(MODULE, "dpmu", r.content)], "" if recs else "no rows"
