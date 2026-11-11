"""Puducherry: commissioners of the municipalities, from the regional who's who pages (S3WaaS template).

Puducherry has no statewide list of municipal heads: the Local Administration Department (lad.py.gov.in) pages of each
municipality give history and wards only, and py.gov.in/department-contacts names no municipal commissioner. The regional
who's who page names the commissioner with office phone and email:
- karaikal.gov.in/about-district/who-s-who/ (one table: name, designation, address, phone, email; emails written
  "x[dot]y[at]py[dot]gov[dot]in"; answers from outside India). The row "Commissioner | Karaikal Municipality, Duplex street ..."
  gives one record for Karaikal.
The page shows no date. A row counts when its post or address names a municipality ("<Name> Municipality"); area = that name.
Not covered: Yanam (yanam.gov.in/directory/ names the commissioner, but the site did not answer from this box or from the
India server on 2026-11-11), Oulgaret (Ozhukarai in LGD; no page found that names its commissioner).
"""
import re

from dforms import _esw, _ulb

MODULE = "ulb_py"
KARAIKAL = "https://karaikal.gov.in/about-district/who-s-who/"
BODY = re.compile(r"\b([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)\s+Municipality\b")


def items(get=None):
    return [{"key": "ulb_py-karaikal", "payload": {"reader": MODULE, "url": KARAIKAL, "state": "PY", "district": "Karaikal",
                                                   "india_only": False}}]


def parse(html, url=KARAIKAL, district=None):
    recs, seen = [], set()
    for t in _esw.soup(html).find_all("table"):
        for row in _esw.grid(t):
            if len(row) < 4:
                continue
            name, post, address = row[0], row[1], row[2]
            m = BODY.search(post) or BODY.search(address)
            if not m or not re.search(r"(?i)commissioner|chairman|chairperson|special officer", post):
                continue
            phone, email = row[3], _esw.emails(row[4]) if len(row) > 4 else ""
            post = re.sub(r"(?i),?\s*\b" + re.escape(m.group(0)) + r"\b", "", post).strip(" ,") or post
            recs.append(_ulb.record(MODULE, "PY", m.group(1), post, seen, name=name, phone=phone, email=email, district=district,
                                    body_type="Municipality", source=url, address=address))
    return recs


def fetch(p, get):
    url = p.get("url", KARAIKAL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, _esw.slug(p.get("district") or "page"), r.content)]
    recs = parse(r.text, url, p.get("district"))
    return recs, files, "" if recs else "no rows"
