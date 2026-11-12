"""Lakshadweep: the ERO (whole UT, one parliamentary constituency, no assembly) and the AEROs of each island, from the CEO page
ceolakshadweep.gov.in/ero-aero-blo (the URL with a final slash answers 301). Answers from Germany and India.

One GET; the table "Details of ERO & AEROs" (Sl.No, Officer Name, Designation, Office Number, Mobile Number, Defining Area: "Whole
Lakshadweep", "Chetlat Only"). The BLO and BLA tables on the same page are left out. The page shows no date. One queue item.
Record ids: dept:ero_ld:LD-PC-1:ero, dept:ero_ld:LD-AERO-<island>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_ld"
URL = "https://ceolakshadweep.gov.in/ero-aero-blo"


def std0(s):
    """An office landline whose leading 0 the source dropped gets it back: "4936229255" -> "04936229255" (STD code + number,
    10 digits, not starting with 6-9 as a mobile number does). Mobile numbers, numbers after "+91" and numbers with their 0
    stay as written."""
    def fix(m):
        before = m.string[:m.start()].rstrip(" -")
        if len(m.group(1) + m.group(3)) != 10 or before.endswith(("+91", "+", "91")):
            return m.group(0)
        return "0" + m.group(0)
    return re.sub(r"(?<![\d+])([1-5]\d{1,4})(\s*-\s*)?(\d{5,8})(?!\d)", fix, s or "")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "LD"}}]


def parse(html, url=URL):
    recs, seen = [], set()
    for t in _esw.soup(html).find_all("table"):
        g = pgrid(t)
        head = [h.lower() for h in g[0]] if g else []
        if not any("defining area" in h for h in head):
            continue
        for r in g[1:]:
            c = dict(zip(head, r))
            name, desig = c.get("officer name", ""), c.get("designation", "")
            area = re.sub(r"(?i)\s*only\s*$", "", c.get("defining area", "")).strip()
            if not name:
                continue
            phone = _esw.phones(std0(c.get("office number")), c.get("mobile number"))
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
                                    district="Lakshadweep", source=url, src_pos=r.pos, **f))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url", URL))
    return recs, [_esw.keep(MODULE, "ero-aero-blo", r.content)], "" if recs else "no rows"
