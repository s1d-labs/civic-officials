"""Dadra & Nagar Haveli and Daman & Diu: the DEOs, EROs and AEROs of both parliamentary constituencies (01 Daman & Diu, 02 Dadra &
Nagar Haveli; the UT has no assembly), from the CEO's organisation page ceodaman.nic.in/organization.aspx. Answers from Germany and
India.

One GET; one table per PC. A heading row ("01-Daman & Diu Parliamentary Constituency") and role rows ("District Election Officer
(DEO)", "Electoral Registration Officer (ERO)" ... spanning their columns) are followed by a row of officer cells: name | post |
address | "Phone : ..." | "Cell No : ...". A role row can hold two roles side by side (DEO and ERO of DNH), so each officer cell takes
the role of its column. RO / ARO rows (polling posts) and the CEO table are left out. The page shows no date. One queue item.
Record ids: dept:ero_dh:DH-DEO-<district>, dept:ero_dh:DH-PC-<no>:ero, dept:ero_dh:DH-PC-<no>:aero:<slug of post>.
"""
import re

from dforms import _esw
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_dh"
URL = "https://ceodaman.nic.in/organization.aspx"
PC = re.compile(r"^\s*0?(\d)\s*-\s*(.+?)\s+Parliamentary Constituency", re.I)
ROLES = (("assistant electoral registration", "aero"), ("electoral registration", "ero"), ("district election", "deo"),
         ("returning officer", None), ("assistant returning", None), ("chief electoral", None))


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "DH"}}]


def _role(text):
    t = text.lower()
    if not t.endswith(")") or "|" in t:
        return "none"
    return next((r for w, r in ROLES if t.startswith(w)), "none")


def officer(text):
    parts = [x.strip(" ,") for x in text.split(" | ") if x.strip(" ,")]
    phone = " ".join(re.sub(r"(?i)^(phone|cell no)\s*:\s*", "", x) for x in parts if re.match(r"(?i)^(phone|cell no)\s*:", x))
    mail = " ".join(x for x in parts if re.match(r"(?i)^e-?mail", x))
    rest = [x for x in parts if not re.match(r"(?i)^(phone|cell no|e-?mail)\s*:?", x)]
    phone = re.sub(r"\((O|R)\)", " ", phone)
    return {"name": rest[0] if rest else "", "designation": rest[1] if len(rest) > 1 else "", "address": ", ".join(rest[2:]),
            "phone": _esw.phones(*phone.split(",")), "email": _esw.emails(mail)}


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        pc, cols = None, []
        for tr in t.find_all("tr"):
            if tr.find_parent("table") is not t:
                continue
            cells = tr.find_all(["td", "th"], recursive=False)
            texts = [_esw.cell_text(c) for c in cells]
            spans = [int(re.sub(r"\D", "", c.get("colspan") or "1") or 1) for c in cells]
            m = PC.match(texts[0]) if texts else None
            if m:
                pc = (int(m.group(1)), m.group(2).strip())
                continue
            if pc is None or not texts:
                provenance.skip_row(tr, 'skip: pc is None or not texts')
                continue
            roles = [_role(x) for x in texts]
            if all(r != "none" for r in roles):
                cols = [r for r, n in zip(roles, spans) for _ in range(n)]
                continue
            col, tp = 0, tr_pos(tr)
            for text, n in zip(texts, spans):
                role = cols[col] if col < len(cols) else None
                col += n
                if not role or not text:
                    provenance.skip_line(text, 'skip: not role or not text')
                    continue
                o = officer(text)
                if not o["name"]:
                    provenance.skip_line(text, 'skip: not o["name"]')
                    continue
                f = dict(dept="elections", designation=o["designation"], name=o["name"], phone=o["phone"], email=o["email"],
                         address=o["address"], state="DH", source=url, src_pos=dict(tp, col=col - n + 1))
                if role == "deo":
                    dist = re.sub(r"(?i)^collector\s*,?\s*", "", o["designation"]).strip(" ,")
                    key = f"DH-DEO-{_esw.slug(dist)}"
                    f.update(level="district", area=dist, post="District Election Officer", district=dist, office_id=key)
                else:
                    office = f"DH-PC-{pc[0]}"
                    key = f"{office}:ero" if role == "ero" else f"{office}:aero:{_esw.slug(o['designation']) or _esw.slug(o['name'])}"
                    f.update(level="pc", area=f"{pc[0]} - {pc[1]}", office_id=office,
                             post="Electoral Registration Officer" if role == "ero" else "Assistant Electoral Registration Officer")
                if key in seen:
                    provenance.skip_line(text, 'skip: key in seen')
                    continue
                seen.add(key)
                recs.append(_esw.record(MODULE, key, **f))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url", URL))
    return recs, [_esw.keep(MODULE, "organization", r.content)], "" if recs else "no rows"
