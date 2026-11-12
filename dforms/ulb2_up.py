"""Uttar Pradesh: the head of the Yamuna Expressway Industrial Development Authority, which LGD lists as the urban body "Yeida"
(Notified Area Council, Gautam Buddha Nagar, local body code 274822). The authority runs the notified area; its Chief Executive
Officer is the head of the body. ulb_up (localbodies.up.nic.in) lists only the elected nagar nigams, nagar palika parishads and
nagar panchayats, so the industrial-area councils have no official in DB civic.

Source: yamunaexpresswayauthority.com home page: "<p class="ceo-desig-block"><strong>Shri ... (IAS)</strong>Chief Executive
Officer</p>"; the header link "tel:0120-..." gives the office phones (office_phone). The page shows "Last Updated :" without a
value. Not in archive.s1d.me (2026-11-11); one live request from Germany answered 200, so not India-only.

Not covered (no answer from Germany or from the India server, 2026-11-11): noidaauthorityonline.in (Noida, 301210) and
greaternoidaauthority.in (Gnida, 274823). No source names a head for the township councils of Grasim Industries (301249),
Hindalco Renukoot (301244) and the Jhansi Railway Settlement (301241).
"""
import re

from dforms import _esw, _ulb

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_up"
STATE = "UP"
YEIDA = "https://yamunaexpresswayauthority.com/"


def items(get=None):
    return [{"key": "ulb2_up-yeida", "payload": {"reader": MODULE, "kind": "authority", "url": YEIDA, "state": STATE,
                                                 "body": "Yeida", "district": "Gautam Buddha Nagar", "lgd_code": "274822",
                                                 "body_type": "Notified Area Council", "india_only": False}}]


def parse(html, body, district=None, url=YEIDA, lgd_code=None, body_type=None):
    soup = _esw.soup(html)
    recs, seen = [], set()
    tel = soup.find("a", href=re.compile(r"^tel:"))
    office = _esw.phones(tel.get_text(" ")) if tel else ""
    for p in soup.select("p.ceo-desig-block"):
        s = p.find("strong")
        name = _esw.clean(s.get_text(" ") if s else "")
        if s:
            s.extract()
        post = _esw.clean(p.get_text(" "))
        if not name or not post:
            continue
        extra = {k: v for k, v in (("lgd_code", lgd_code), ("office_phone", office)) if v}
        recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=name, district=district, body_type=body_type, source=url, **extra))
        break                   # the block stands twice (once in an HTML comment); the first is the live one
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p["body"], p.get("district"), p["url"], p.get("lgd_code"), p.get("body_type"))
    return recs, [_esw.keep(MODULE, _esw.slug(p["body"]), r.content)], "" if recs else "no rows"
