"""Arunachal Pradesh: Itanagar Municipal Corporation (imc.arunachal.gov.in), the state's one municipal corporation (Itanagar and
Naharlagun). No state list of urban body officials was found: ud.arunachal.gov.in and udhud.arunachal.gov.in gave no answer from
Germany or from India (2026-11-11), and archive.s1d.me holds no copy of either.

Two server-rendered pages (Bootstrap cards; each card: h5 name, then <span> lines marked by Material icon names: local_offer = post,
device_hub = office or ward, contact_phone = email and mobile). The pages carry the photos inline as base64 (about 0.7-1.1 MB each).
- /Officers.html: Commissioner, Joint Commissioner, Administrative Officer, engineers ... (14 cards, office email on every card,
  mobiles on some). Footer "Last Update: 2023-11-21 15:32:46".
- /committeemember.html: Mayor, Deputy Mayor and corporators with ward numbers (no phones). Only the Mayor and Deputy Mayor are
  kept: corporators are ward councillors (record type "councillor", councillors.py).
They answer from outside India (checked from Germany 2026-11-11). Area "Itanagar Municipal Corporation" (the office line of the
cards); district Papum Pare. Pasighat Municipal Council (the state's other elected body) has no site that answers.
"""
import re

from dforms import _esw, _ulb

METHOD = "html cards (div.card-body)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_ar"
STATE = "AR"
BASE = "https://imc.arunachal.gov.in"
BODY = "Itanagar Municipal Corporation"
DISTRICT = "Papum Pare"
KEEP_MEMBER = re.compile(r"(?i)\b(mayor|chair)")


def items(get=None):
    return [{"key": f"{MODULE}-imc-{kind}", "payload": {"reader": MODULE, "url": f"{BASE}/{page}", "kind": kind, "body": BODY,
                                                       "district": DISTRICT, "state": STATE, "india_only": False}}
            for kind, page in (("officers", "Officers.html"), ("members", "committeemember.html"))]


def cards(html, where=None):
    """[(name, {icon: text})] of the cards: icon = local_offer / device_hub / contact_phone. where: a list; when given, it gets
    {"selector": "div.card-body", "card": n} per card."""
    soup = _esw.soup(html)
    out = []
    for n, body in enumerate(soup.find_all("div", class_="card-body"), 1):
        h = body.find("h5")
        if not h:
            continue
        name = _esw.clean(h.get_text(" ").replace("account_circle", ""))
        f = {}
        for sp in body.find_all("span", recursive=False):
            i = sp.find("i")
            if i:
                icon = _esw.clean(i.get_text())
                i.extract()
                f[icon] = _esw.clean(sp.get_text(" "))
        out.append((name, f))
        if where is not None:
            where.append({"selector": "div.card-body", "card": n})
    return out


def updated(html):
    m = re.search(r"Last Update:\s*(\d{4}-\d{2}-\d{2})", html)
    return m.group(1) if m else None


def parse(html, kind="officers", body=BODY, district=DISTRICT, url=""):
    recs, seen = [], set()
    last = updated(html)
    where = []
    for (name, f), pos in zip(cards(html, where), where):
        post = f.get("local_offer", "")
        if not post or (kind == "members" and not KEEP_MEMBER.search(post)):
            continue
        contact = f.get("contact_phone", "")
        ward = re.sub(r"(?i)^ward\s*no\.?\s*", "", f.get("device_hub", "")) if kind == "members" else None
        recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=name, phone=_esw.phones(contact), email=_esw.emails(contact),
                                district=district, source=url, last_updated=last, ward=ward or None, src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"imc-{p.get('kind', 'officers')}", r.content)]
    recs = parse(r.text, p.get("kind", "officers"), p.get("body", BODY), p.get("district", DISTRICT), p["url"])
    return recs, files, "" if recs else "no rows"
