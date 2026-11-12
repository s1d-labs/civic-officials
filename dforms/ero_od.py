"""Odisha: the ERO and every AERO (Tahasildars, BDOs, Executive Officers of NACs and municipalities) of all 147 assembly constituencies,
from the CEO Odisha page ceoodisha.nic.in/en/contact/eroaero/ (the URL without the final slash answers 301). Answers only from India.

One GET (about 420 KB); two tables (ACs 1-99, 100-147) with the AC label "N – Name" and the role (ERO / AEROS) repeated by rowspan:
No. & Name of AC, role, designation, name, STD code, landline, mobile, official email, personal email. A cell sometimes holds two
officers ("Tahasildar, Jharbandh | Tahasildar, Padampur"): they become two records when name and designation split alike. Each AERO
area is the tahasil, block or urban body in the designation. The page shows no date. One queue item.
Record ids: dept:ero_od:OD-AC-<no>:ero, dept:ero_od:OD-AC-<no>:aero:<slug of designation>.
"""
import re

from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_od"
URL = "https://ceoodisha.nic.in/en/contact/eroaero/"
AC = re.compile(r"^\s*(\d{1,3})\s*[–—\-.:]+\s*(.+?)\s*$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "OD", "india_only": True}}]


def _parts(s):
    return [x.strip(" ,") for x in (s or "").split(" | ")]


def _flat(s):
    return _esw.clean((s or "").replace(" | ", " ")).strip(" ,")


def _landline(std, num):
    std, num = re.sub(r"[^\d]", "", std or ""), re.sub(r"[^\d]", "", num or "")
    if len(num) < 5:
        return ""
    return f"{std}-{num}" if std and not num.startswith("0") else num


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        rows = pgrid(t)
        last = None
        for row in rows:
            rp, row = row.pos, row + [""] * (9 - len(row))
            m = AC.match(row[0])
            role = row[1].strip().upper()
            if m and not role and last == m.group(1):     # a blank role cell under the AC's AEROs (6 - Brajarajnagar)
                role = "AEROS"
            if not m or role not in ("ERO", "AERO", "AEROS"):
                continue
            last = m.group(1)
            no, acname = int(m.group(1)), m.group(2)
            names, desigs = _parts(row[3]), _parts(row[2])
            if len(names) > 1 and len(names) == len(desigs):
                mobiles, mails = _parts(row[6]), _parts(row[7])
                people = [(names[i], desigs[i], mobiles[i] if len(mobiles) == len(names) else row[6],
                           mails[i] if len(mails) == len(names) else row[7]) for i in range(len(names))]
            else:
                people = [(_flat(row[3]), _flat(row[2]), row[6], row[7])]
            for name, desig, mobile, mail in people:
                desig = _flat(desig)
                ac = f"OD-AC-{no}"
                if role == "ERO":
                    base, post = f"{ac}:ero", "Electoral Registration Officer"
                else:
                    base, post = f"{ac}:aero:{_esw.slug(desig) or _esw.slug(name)}", "Assistant Electoral Registration Officer"
                key, i = base, 2
                while key in seen:
                    key, i = f"{base}:{i}", i + 1
                seen.add(key)
                rec = _esw.record(MODULE, key, dept="elections", level="ac", area=f"{no} - {acname}", post=post, designation=desig,
                                  name=_flat(name), phone=_esw.phones(_landline(row[4], row[5]), mobile),
                                  email=_esw.emails(" ".join((mail, row[8]))), state="OD", office_id=ac, source=url,
                                  src_pos=rp)
                if rec[1].get("name") or rec[1].get("phone") or rec[1].get("email"):
                    recs.append(rec)
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "eroaero", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
