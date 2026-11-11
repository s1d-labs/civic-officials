"""Puducherry: AERO and ERO of all 30 assembly constituencies and the DEOs of Puducherry and Karaikal, from the CEO Puducherry contact
page (ceopuducherry.py.gov.in/contact.php). Answers from Germany and India. One GET.

The AC table has the columns "N.NAME", AERO, ERO / RO, ARO; each officer cell holds name, "Mobile: ...", the designation lines and
"Phone: ...", split by <br>. The ARO column (assistant returning officer, a polling post) is left out. The DEO tables sit under the
headings "Office of the District Election Officer, <district>" (name, post, mobile, email). The page shows "updated date : 5 - Nov -
2026". BLO + ERO per part: blo_details.php, not read here. One queue item.
Record ids: dept:ero_py:PY-AC-<no>:ero, dept:ero_py:PY-AC-<no>:aero:<slug of designation>, dept:ero_py:PY-DEO-<district>.
"""
import re
from datetime import datetime

from dforms import _esw

MODULE = "ero_py"
URL = "https://ceopuducherry.py.gov.in/contact.php"
AC = re.compile(r"^\s*(\d{1,2})\s*\.\s*(.+?)\s*$")
DEO_HEAD = re.compile(r"Office of the District Election Officer,\s*(\w+)", re.I)


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "PY"}}]


def _dash(s):
    return re.sub(r"\s*[–—]\s*", "-", s or "")


def officer(cell):
    """'NAME | Mobile: 94... | Tahsildar, O/o.DCR (South), | Villianur. | Phone: 0413-2667668' -> name, designation, phone."""
    parts = [p.strip(" ,") for p in _dash(cell).split(" | ") if p.strip(" ,")]
    if not parts:
        return None, None, None
    tel, desig = [], []
    for p in parts[1:]:
        m = re.match(r"(?i)(mobile|phone|ph|tel)\s*[:.]?\s*(.*)", p)
        (tel if m else desig).append(m.group(2) if m else p)
    return parts[0].strip(" ,"), ", ".join(desig).replace(",,", ","), _esw.phones(*tel)


def district_of(no):
    """ACs 1-23 Puducherry, 24-28 Karaikal, 29 Mahe, 30 Yanam (Delimitation 2008)."""
    return "Puducherry" if no <= 23 else "Karaikal" if no <= 28 else "Mahe" if no == 29 else "Yanam"


def updated(html):
    m = re.search(r"(?i)updated\s*date\s*:\s*(\d{1,2})\s*-\s*(\w{3})\w*\s*-\s*(\d{4})", html)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse(html, url=URL):
    soup = _esw.soup(html)
    when = updated(html)
    recs, seen = [], set()

    def add(key, **f):
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="elections", state="PY", source=url, last_updated=when, **f))

    for t in soup.find_all("table"):
        head = t.find_previous(string=DEO_HEAD)
        rows = _esw.grid(t)
        if any(AC.match(r[0]) for r in rows[:3] if r):
            for row in rows:
                m = AC.match(row[0]) if row else None
                if not m or len(row) < 3:
                    continue
                no, ac = int(m.group(1)), f"PY-AC-{int(m.group(1))}"
                area = f"{no} - {m.group(2).title()}"
                for col, role in ((2, "ero"), (1, "aero")):
                    name, desig, phone = officer(row[col])
                    if not name:
                        continue
                    key = f"{ac}:ero" if role == "ero" else f"{ac}:aero:{_esw.slug(desig) or _esw.slug(name)}"
                    add(key, level="ac", area=area, office_id=ac, name=name, designation=desig, phone=phone, district=district_of(no),
                        post="Electoral Registration Officer" if role == "ero" else "Assistant Electoral Registration Officer")
        elif head and t.find_previous(string=re.compile("Electoral Registration Officers", re.I)) is None:
            district = DEO_HEAD.search(head).group(1).title()
            for row in rows:
                row = row + [""] * (4 - len(row))
                if re.match(r"(?i)^DEO", row[1]):
                    add(f"PY-DEO-{_esw.slug(district)}", level="district", area=district, district=district,
                        office_id=f"PY-DEO-{_esw.slug(district)}", post="District Election Officer", designation=row[1],
                        name=row[0], phone=_esw.phones(row[2]), email=_esw.emails(row[3]))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contact", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
