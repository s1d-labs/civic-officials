"""Odisha: the Chief District Medical & Public Health Officers (CDMO) and the other Chief Medical Officers (CMO) of the state, from the
Health & Family Welfare Department's "Telephone Directory" (health.odisha.gov.in/en/health/citizen-information/telephone-directory,
Drupal view, 20 rows per page, ?page=0..1). First table "Telephone Numbers of CDMOs/ CMOs": Sr. No. | District | Name of the
CDMO/ CMO | Mobile | Office | Fax; 33 rows (2026-11-12, from Mumbai). Districts are written as LGD spells them (Anugola, Kataka,
Sundaragada). Rows 19, 31, 32 have no district (CMOs of other offices: the page does not say which); row 33 repeats Anugola. The
page shows no date, and some names may be old (unchecked). The second table on the page (district | telephone number, no name)
is not read. The pool (GitHub, abroad) got no answer from this host on 2026-11-11 (archive, status 0): India only.

Records (depts.py contract): dept health, level district (state when the row has no district), area = district, post "CDMO/CMO"
(the column title), name, phone (mobile, office), fax, district. Odia digits in phone cells (୦୬୭୬୨) are written as ASCII digits.
One queue item = the pages of the view (2 GETs today; follows "Go to next page" up to 6 pages).
Ids: dept:health_od_cdmo:<serial>.
"""
import re

from dforms import _esw
import provenance

METHOD = "html table (Drupal view pages)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "health_od_cdmo"
URL = "https://health.odisha.gov.in/en/health/citizen-information/telephone-directory"
ODIA = str.maketrans("୦୧୨୩୪୫୬୭୮୯", "0123456789")


def parse(html, url=URL, page=0):
    s = _esw.soup(html)
    recs = []
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or not re.search(r"(?i)cdmo|cmo", " ".join(rows[0])):
            continue
        head = [c.lower() for c in rows[0]]

        def col(rx, row):
            for i, h in enumerate(head):
                if re.search(rx, h) and i < len(row):
                    return row[i]
            return ""
        for row, sp in zip(rows[1:], pos[1:]):
            sn = col(r"sr\.?\s*no", row)
            if not re.fullmatch(r"\d{1,3}", sn or ""):
                continue
            district, name = col(r"^district", row), col(r"name", row)
            mobile, office, fax = (col(rx, row).translate(ODIA) for rx in (r"mobile", r"office", r"fax"))
            phone = _esw.phones(mobile, office)
            if not (name or phone):
                continue
            recs.append(_esw.record(MODULE, sn, dept="health", level="district" if district else "state",
                                    area=district or "Odisha", post="CDMO/CMO", name=name, phone=phone,
                                    fax=_esw.phones(fax) or None, district=district or None, state="OD", serial=sn,
                                    source=URL, page=url, src_url=url, src_pos={"view_page": page, **sp}))
    return recs


def next_page(html):
    m = re.search(r'<a[^>]+href="\?page=(\d{1,2})"[^>]*title="Go to next page"', html or "") or \
        re.search(r'<a[^>]+title="Go to next page"[^>]*href="\?page=(\d{1,2})"', html or "")
    return int(m.group(1)) if m else None


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "OD", "india_only": True, "expected": 33}}]


def fetch(p, get):
    base = p.get("url") or URL
    recs, files, page, why = [], [], 0, ""
    while page is not None and page < 6:
        url = base if page == 0 else f"{base}?page={page}"
        r = get(url)
        if r is None:
            why = f"page {page}: no answer"
            break
        files.append(_esw.keep(MODULE, f"telephone-directory-{page}", r.content))
        got = parse(r.text, url, page)
        for _, d in got:
            d.update(provenance.at(r, url))
        recs += got
        nxt = next_page(r.text)
        page = nxt if nxt is not None and nxt > page else None
    seen, out = set(), []
    for rid, d in recs:
        if rid not in seen:
            seen.add(rid)
            out.append((rid, d))
    return out, files, "" if out else (why or "no rows")
