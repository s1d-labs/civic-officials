"""Puducherry: every polling station (part) with its Booth Level Officer and mobile, from the CEO's "BLO Contact Numbers" pages,
ceopuducherry.py.gov.in/blo_ps.php?c=<base64 of the AC number> (30 ACs, about 1,000 parts (AC 2: 40); the page shows "As on 27.04.2026").
One table per AC: PART_NO ("2/1" = AC 2, part 1), POLLING STATION (building and address with PIN), Booth Level Officer Name,
Mobile No. The rows have no closing </tr>, so the parser reads the <td> cells per "<tr>" piece. The page answers from abroad.
The same site lists the same stations with elector counts at ac_wise_polling_station.php?c=...; the BLO page has all we need.
Record ids: dept:civic_pollst_py:PY-<ac>-<part>. Layer "pollst" (polling stations, cityofficials.s1d.me).
"""
import base64
import re

from dforms import _esw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_pollst_py"
BASE = "https://ceopuducherry.py.gov.in/blo_ps.php?c="
# AC number -> district (Puducherry region 1-23, Karaikal 24-28, Mahe 29, Yanam 30)
DISTRICT = {**{n: "Puducherry" for n in range(1, 24)}, **{n: "Karaikal" for n in range(24, 29)}, 29: "Mahe", 30: "Yanam"}


def url_of(ac):
    return BASE + base64.b64encode(str(ac).encode()).decode()


def items(get=None):
    return [{"key": f"{MODULE}-ac{ac}", "payload": {"reader": MODULE, "url": url_of(ac), "state": "PY", "ac_no": ac}}
            for ac in range(1, 31)]


def as_on(html):
    m = re.search(r"As on\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", html)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def parse(html, url, ac=None):
    head = re.search(r"<h5[^>]*>\s*(\d+)\s*\.\s*([^<]+?)\s*</h5>", html)
    ac_name = _esw.clean(head.group(2)) if head else ""
    if head and ac is None:
        ac = int(head.group(1))
    body = html[html.find("<tbody"):] if "<tbody" in html else html
    recs, seen = [], set()
    for trn, piece in enumerate(re.split(r"(?i)<tr[^>]*>", body)[1:], 1):
        cells = [_esw.clean(_esw.soup(c).get_text(" ")) for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", piece)]
        if len(cells) < 2:
            provenance.skip_row(piece, 'skip: len(cells) < 2')
            continue
        m = re.match(r"^(\d+)\s*/\s*(\d+[A-Z]?)$", cells[0])
        if not m:
            provenance.skip_row(piece, 'skip: not m')
            continue
        acn, part = int(m.group(1)), m.group(2)
        if (acn, part) in seen:
            provenance.skip_row(piece, 'skip: (acn, part) in seen')
            continue
        seen.add((acn, part))
        name = cells[2] if len(cells) > 2 else ""
        phone = _esw.phones(cells[3]) if len(cells) > 3 else ""
        key = f"PY-{acn}-{part}"
        recs.append(_esw.record(MODULE, key, dept="elections", level="polling_station", area=cells[1], post="BLO", name=name,
                                phone=phone, state="PY", district=DISTRICT.get(acn), office_id=key, source=url,
                                last_updated=as_on(html), layer="pollst", ac_no=acn, ac_name=ac_name, part_no=part,
                                station=cells[1], src_pos={"after": "<tbody", "row": trn, "cells": cells}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p["url"], p.get("ac_no"))
    return recs, [_esw.keep(MODULE, f"ac{p.get('ac_no', 'x')}", r.content)], "" if recs else "no rows"
