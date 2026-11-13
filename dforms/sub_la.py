"""Ladakh: the Deputy Commissioner and the other officers of each district, including the five districts made in 2024 (Nubra,
Changthang, Zanskar, Sham, Drass), from the UT portal's directory ladakh.gov.in/directory/ (S3WaaS). Answers from Germany and India.

One GET (about 140 KB). Each category is a <table class="data-table-1"> with a <caption>: "UT Administration", "LAHDC Leh",
"LAHDC Kargil", "District Administration Leh" ... "District Administration Drass", "Police Headquarters UT Ladakh", "Indo-Tibetan
Border Police". Columns: Name, Designation, Email, Mobile, Landline No, Address. Only the "District Administration <district>"
tables are read: Deputy Commissioner and other civil officers -> dept administration; "Superintendent of Police" -> dept police;
level district. The new districts list the DC and SP only (names, DC email; no phones on 2026-11-11). Sankoo, a district in LGD
since 2024, has no table: the UT has not published its administration. The page's "Last Updated" date goes into last_updated
(the archive copy of 2026-11-05 shows it; the live answer of 2026-11-11 did not).
Record ids: dept:sub_la:LA-<district slug>:<designation slug>[:<n>].
"""
import re

from dforms import _esw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_la"
URL = "https://ladakh.gov.in/directory/"
CAPTION = re.compile(r"(?i)^\s*district administration\s+(.+?)\s*$")
POLICE = re.compile(r"(?i)\b(superintendent of police|sp\b|police)")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "LA"}}]


def _date(html):
    m = re.search(r"Last Updated:\s*(?:<[^>]+>\s*)*(\d{2})\.(\d{2})\.(\d{4})", html)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def parse(html, url=URL):
    soup = _esw.soup(html)
    updated = _date(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        cap = t.find("caption")
        m = CAPTION.match(_esw.clean(cap.get_text(" ")) if cap else "")
        if not m:
            continue
        district = m.group(1).title()
        tp = []
        rows = _esw.grid(t, pos=tp)
        if not rows:
            continue
        head = [h.lower() for h in rows[0]]

        def col(row, name):
            i = next((k for k, h in enumerate(head) if h.startswith(name)), None)
            return row[i] if i is not None and i < len(row) else ""

        for row, pos in zip(rows[1:], tp[1:]):
            name, desig = col(row, "name"), col(row, "designation")
            if not (name or desig):
                provenance.skip_row(row, 'skip: not (name or desig)')
                continue
            base = key = f"LA-{_esw.slug(district)}:{_esw.slug(desig) or _esw.slug(name)}"
            n = 2
            while key in seen:
                key, n = f"{base}:{n}", n + 1
            seen.add(key)
            rec = _esw.record(MODULE, key, dept="police" if POLICE.search(desig) else "administration", level="district",
                              area=district, post=desig, designation=desig, name=name,
                              phone=_esw.phones(col(row, "mobile"), col(row, "landline")), email=_esw.emails(col(row, "email")),
                              address=col(row, "address"), district=district, state="LA", source=url, last_updated=updated,
                              src_pos=pos)
            if rec[1].get("name") or rec[1].get("phone") or rec[1].get("email"):
                recs.append(rec)
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "directory", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
