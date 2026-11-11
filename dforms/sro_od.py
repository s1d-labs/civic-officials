"""Odisha: "Staff Directory" of the IGR (igrodisha.gov.in/Offices.aspx). Answers from Germany and India. One GET; two ASP.NET
GridViews: grdOffice = 321 registering offices (Serial, District, Location, Officer Name, Mobile No., Email-ID) and gvadm = 30 District
Registrars (ADMs: Serial, District, Officer Name, Mobile, Landline, Email). District names are the Odia spellings (ANUGOLA, KATAKA).
The office is named after its town (tahasil HQ or DSR town). The page shows no date. One queue item.
Record ids: dept:sro_od:OD-SRO-<district>-<location>, OD-DR-<district>.
"""
from dforms import _esw

MODULE = "sro_od"
URL = "https://igrodisha.gov.in/Offices.aspx"
JUNK_MAIL = {"temp@gmail.com"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "OD"}}]


def _mail(s):
    return ", ".join(e for e in _esw.emails(s).split(", ") if e and e not in JUNK_MAIL)


def _rows(soup, tid):
    t = soup.find("table", id=tid)
    if t is None:
        return []
    g = _esw.grid(t)
    head = [h.lower() for h in g[0]] if g else []
    return [dict(zip(head, r)) for r in g[1:] if r and r[0].strip().isdigit()]


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()

    def add(base, **f):
        key, i = base, 2
        while key in seen:
            key, i = f"{base}-{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="registration", state="OD", source=url, office_id=key, **f))
    for c in _rows(soup, "ContentPlaceHolder1_grdOffice"):
        dist, loc = c.get("district", "").title(), c.get("location", "").title()
        add(f"OD-SRO-{_esw.slug(dist)}-{_esw.slug(loc)}", level="office", area=loc, post="Sub Registrar", name=c.get("officer name"),
            phone=_esw.phones(c.get("mobile no.")), email=_mail(c.get("email-id")), district=dist)
    for c in _rows(soup, "ContentPlaceHolder1_gvadm"):
        dist = c.get("district", "").title()
        add(f"OD-DR-{_esw.slug(dist)}", level="district", area=dist, post="District Registrar",
            designation="Additional District Magistrate", name=c.get("officer name"),
            phone=_esw.phones(c.get("mobile no."), c.get("landline no.")), email=_mail(c.get("email-id")), district=dist)
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "offices", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
