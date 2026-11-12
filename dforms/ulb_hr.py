"""Haryana: Directorate of Urban Local Bodies, "Nodal Officers (Implementation of Haryana Litigation Policy, 2025)",
https://ulbharyana.gov.in/Home/NodalOfficersLitigationPolicy (server-rendered HTML, one table, about 92 KB). Not India-only
(answered from Germany on 2026-11-11). In archive.s1d.me (saved 2026-11-05). Page date "Last Updated On : 21-08-2025".

Columns: Sr. No., District, Name of Municipality, Name of Nodal Officers, Designation, Email Id (written x[at]y[dot]z). 23 rows,
about 20 bodies of the 87. The nodal officer is the body's own Secretary (Municipal Committee) or Executive Officer (Municipal
Council), so for most rows the record is the head of the body; for corporations it is a Deputy / Joint / Additional Commissioner
(role deputy) or the corporation's law officer. No phones. This is the only DULB page that names officers of the bodies: the PIO
list (Home/PIOList) gives posts only, Home/StateMunicipalities gives names of bodies only, Home/ContactUs gives headquarters only.
A cell that names several bodies ("Kaithal, Cheeka, Kalayat, Pundri, Rajaund,Siwan") is one officer nodal for all of them: the
record goes to the body that the officer's mailbox names (eo-kaithal) or, failing that, the body named like the district; the
others go in the extra key nodal_for. When neither fits ("Ellenabad, Kalanwali, Mandi Dabwali, Rania" with secymc.sirsa) the row
gives no record (those bodies have their own rows). Body names as written ("Rohatak", "MC Bawani Khera").
"""
import re

from dforms import _esw, _ulb

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_hr"
URL = "https://ulbharyana.gov.in/Home/NodalOfficersLitigationPolicy"
COLS = {"district": r"district", "body": r"municipality", "name": r"name of nodal", "post": r"designation", "email": r"e-?mail"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "HR", "india_only": False}}]


def key(s):
    return re.sub(r"[^a-z]", "", re.sub(r"(?i)^mc\s+", "", s or "").lower())


def page_date(soup):
    t = soup.find(string=re.compile(r"Last Updated On"))
    if t:
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})", t.find_next(string=re.compile(r"\d{2}-\d{2}-\d{4}")) or "")
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def pick(bodies, district, email):
    """The body of a multi-body cell that the officer belongs to, or None."""
    if len(bodies) == 1:
        return bodies[0]
    local = key(email.split("@")[0]) if email else ""
    for b in bodies:
        if key(b) and key(b) in local:
            return b
    for b in bodies:
        if key(b) == key(district):
            return b
    return None


def parse(html, url=URL):
    soup = _esw.soup(html)
    date = page_date(soup)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        rows = _esw.grid(t)
        if not rows:
            continue
        col = {}
        for i, h in enumerate(rows[0]):
            for k, rx in COLS.items():
                if k not in col and re.search(rx, h, re.I):
                    col[k] = i
        if not {"body", "post"} <= set(col):
            continue
        for row in rows[1:]:
            c = {k: (_esw.clean(row[i]) if i < len(row) else "") for k, i in col.items()}
            bodies = [b.strip() for b in c["body"].split(",") if b.strip()]
            email = _esw.emails(c.get("email", ""))
            body = pick(bodies, c.get("district", ""), email)
            if not body or not (c.get("name") or email):
                continue
            others = [b for b in bodies if b != body]
            recs.append(_ulb.record(MODULE, "HR", body, c["post"], seen, name=c.get("name", ""), email=email, district=c.get("district"),
                                    source=url, last_updated=date, nodal_for=", ".join(others) or None,
                                    list_post="Nodal Officer (Haryana Litigation Policy, 2025)"))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "nodal-officers", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
