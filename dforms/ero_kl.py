"""Kerala: EROs, AEROs and DEOs of all 140 assembly constituencies, from the CEO's telephone list (www.ceo.kerala.gov.in/telephone-numbers).
Answers from Germany and India. One GET; one hidden table per district (div id=Dist_<District>): #, Location (AC name), Name,
Designation ("ERO & Deputy Collector (LR), Collectorate, Kasaragod", "AERO & Tahsildar, ...", "DEO & DISTRICT COLLECTOR"), Phone, Email,
Mobile. Other rows (Deputy Collector Election, office rows) are not EROs and are left out. The page shows no date. One queue item.
Record ids: dept:ero_kl:KL-AC-<no>:ero, dept:ero_kl:KL-AC-<no>:aero:<slug of designation>, dept:ero_kl:KL-DEO-<district>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_kl"
URL = "https://www.ceo.kerala.gov.in/telephone-numbers"
# spellings on the page -> AC layer names, where ac_no() misses
ALIAS = {"sulthanbathery": "sulthanbatherys", "vatakara": "vadakara", "thiruvambady": "thiruvambadi", "eranad": "ernad",
         "vallikkunnu": "vallikunnu", "mannarkad": "mannarkkad", "nenmara": "nemmara", "irinjalakkuda": "irinjalakuda",
         "chalakkudy": "chalakudy", "ambalapuzha": "ambalappuzha", "kazhakkoottam": "kazhakoottam",
         "thiruvananthapuram": "thiruvananthapura"}
ROLE = re.compile(r"^\s*(A?ERO|DEO)\b\s*(?:&|and|,|-)?\s*(.*)$", re.I)
POST = {"ERO": "Electoral Registration Officer", "AERO": "Assistant Electoral Registration Officer", "DEO": "District Election Officer"}


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
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "KL"}}]


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for div in soup.find_all("div", id=re.compile(r"^Dist_")):
        district = div["id"][5:].replace("_", " ")
        t = div.find("table")
        if not t:
            continue
        rows = pgrid(t)
        head = [h.lower() for h in rows[0]] if rows else []
        for row in rows[1:]:
            c = dict(zip(head, row))
            m = ROLE.match(c.get("designation", ""))
            if not m:
                continue
            role, desig = m.group(1).upper(), m.group(2).strip(" ,&")
            loc = c.get("location", "")
            f = dict(dept="elections", post=POST[role], designation=desig, name=c.get("name"),
                     phone=_esw.phones(std0(c.get("phone number")), c.get("mobile")), email=_esw.emails(c.get("email")),
                     state="KL", district=district, source=url, src_pos=dict(row.pos, div=div["id"]))
            if role == "DEO":
                key = f"KL-DEO-{_esw.slug(district)}"
                f.update(level="district", area=district, office_id=key)
            else:
                no = _esw.ac_no("KL", ALIAS.get(_esw.norm_ac(loc), loc), district)
                ac = f"KL-AC-{no}" if no else f"KL-AC-{_esw.slug(loc)}"
                key = f"{ac}:ero" if role == "ERO" else f"{ac}:aero:{_esw.slug(desig) or _esw.slug(c.get('name'))}"
                f.update(level="ac", area=f"{no} - {loc}" if no else loc, office_id=ac if no else None)
            k, i = key, 2
            while k in seen:
                k, i = f"{key}:{i}", i + 1
            seen.add(k)
            recs.append(_esw.record(MODULE, k, **f))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "telephone-numbers", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
