"""Lakshadweep: the ERO (whole UT, one parliamentary constituency, no assembly) and the AEROs of each island, from the CEO page
ceolakshadweep.gov.in/ero-aero-blo (the URL with a final slash answers 301). Answers from Germany and India.

One GET; the table "Details of ERO & AEROs" (Sl.No, Officer Name, Designation, Office Number, Mobile Number, Defining Area: "Whole
Lakshadweep", "Chetlat Only"). The BLO and BLA tables on the same page are left out. The page shows no date. One queue item.
Record ids: dept:ero_ld:LD-PC-1:ero, dept:ero_ld:LD-AERO-<island>.
"""
import re

from dforms import _esw

MODULE = "ero_ld"
URL = "https://ceolakshadweep.gov.in/ero-aero-blo"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "LD"}}]


def parse(html, url=URL):
    recs, seen = [], set()
    for t in _esw.soup(html).find_all("table"):
        g = _esw.grid(t)
        head = [h.lower() for h in g[0]] if g else []
        if not any("defining area" in h for h in head):
            continue
        for r in g[1:]:
            c = dict(zip(head, r))
            name, desig = c.get("officer name", ""), c.get("designation", "")
            area = re.sub(r"(?i)\s*only\s*$", "", c.get("defining area", "")).strip()
            if not name:
                continue
            phone = _esw.phones(c.get("office number"), c.get("mobile number"))
            if re.match(r"(?i)^electoral registration officer|^ero\b", desig):
                key = "LD-PC-1:ero"
                f = dict(level="pc", area="1 - Lakshadweep", post="Electoral Registration Officer", office_id="LD-PC-1")
            else:
                key = f"LD-AERO-{_esw.slug(area) or _esw.slug(name)}"
                f = dict(level="subdistrict", area=area, post="Assistant Electoral Registration Officer", office_id=key)
            k, i = key, 2
            while k in seen:
                k, i = f"{key}:{i}", i + 1
            seen.add(k)
            recs.append(_esw.record(MODULE, k, dept="elections", designation=desig if not desig.lower().startswith(("electoral",
                                    "assistant electoral", "aero")) else None, name=name, phone=phone, state="LD",
                                    district="Lakshadweep", source=url, **f))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url", URL))
    return recs, [_esw.keep(MODULE, "ero-aero-blo", r.content)], "" if recs else "no rows"
