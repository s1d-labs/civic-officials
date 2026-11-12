"""Puducherry: the commissioners of Yanam and Oulgaret (Ozhukarai in LGD) municipalities, the two bodies that ulb_py does not cover.

Two queue items (payload "kind"):
- "directory": yanam.gov.in/directory/ (S3WaaS "Important Contacts of Yanam": Name, Designation, Email, Mobile No, Landline No,
  Fax No; emails written "x[dot]y[at]py[dot]gov[dot]in"). archive.s1d.me copy saved 2026-11-07 (status 200, fetched from India;
  ulb_py found that the live site did not answer from Germany or from the India server on 2026-11-11), so india_only.
  A row counts when its designation names "<Name> Municipality" ("Commissioner, Yanam Municipality"); area = that name.
  Mobile -> phone, landline -> office_phone, fax -> fax. The page shows no date.
- "home": oulmun.in (Oulgaret Municipality's own site, Drupal). The "Who's who" block has cards (h4 = post, p = name): Lt. Governor,
  Chief Minister, Secretary and Director (Local Administration) are state posts and are left out; the "Commissioner" card is the
  body's head. The footer names the site's web information manager (left out). "last updated: 11-Nov-2026 10:24 AM" -> last_updated.
  Not in archive.s1d.me (2026-11-11); one live request from Germany answered 200.
Puducherry's municipalities have no elected council now (no page names a chairperson), so there are no chair records.
"""
import re
from datetime import datetime

from dforms import _esw, _ulb

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_py"
STATE = "PY"
YANAM = "https://yanam.gov.in/directory/"
OULGARET = "https://oulmun.in/"
BODY = re.compile(r"\b([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)\s+Municipality\b")
# LGD codes (civic.ulb): LGD puts Yanam in district "Puducherry", so a name match in district "Yanam" would fail
CODES = {"yanam": "253092", "oulgaret": "253093"}
STATE_POSTS = re.compile(r"(?i)governor|chief\s*minister|^secretary$|^director$")


def items(get=None):
    return [{"key": "ulb2_py-yanam", "payload": {"reader": MODULE, "kind": "directory", "url": YANAM, "state": STATE,
                                                 "district": "Yanam", "india_only": True}},
            {"key": "ulb2_py-oulgaret", "payload": {"reader": MODULE, "kind": "home", "url": OULGARET, "state": STATE,
                                                    "district": "Puducherry", "body": "Oulgaret", "lgd_code": "253093",
                                                    "india_only": False}}]


def parse_directory(html, district=None, url=YANAM):
    recs, seen = [], set()
    for t in _esw.soup(html).find_all("table"):
        tp = []
        rows = _esw.grid(t, pos=tp)
        if not rows:
            continue
        head = [h.lower() for h in rows[0]]
        if "designation" not in head:
            continue
        ix = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("name", "designation", "email", "mobile", "landline", "fax")}
        for r, pos in zip(rows[1:], tp[1:]):
            def col(k):
                i = ix[k]
                return r[i] if i is not None and i < len(r) else ""
            post = col("designation")
            m = BODY.search(post)
            if not m:
                continue
            body = m.group(1)
            extra = {"lgd_code": CODES[body.lower()]} if body.lower() in CODES else {}
            if _esw.phones(col("landline").replace("+91-", "")):
                extra["office_phone"] = _esw.phones(col("landline"))
            if _esw.phones(col("fax").replace("+91-", "")):
                extra["fax"] = _esw.phones(col("fax"))
            recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=col("name"), phone=col("mobile"), email=col("email"),
                                    district=district, body_type="Municipality", source=url, src_pos=pos, **extra))
    return recs


def last_updated(soup):
    m = re.search(r"(?i)last\s*updated\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", soup.get_text(" "))
    try:
        return datetime.strptime(m.group(1), "%d-%b-%Y").strftime("%Y-%m-%d") if m else None
    except ValueError:
        return None


def parse_home(html, body, district=None, url=OULGARET, lgd_code=None):
    soup = _esw.soup(html)
    recs, seen = [], set()
    extra = {"lgd_code": lgd_code} if lgd_code else {}
    lu = last_updated(soup)
    if lu:
        extra["last_updated"] = lu
    for k, card in enumerate(soup.select("div.who-card"), 1):
        h, p = card.find("h4"), card.find("p")
        post, name = _esw.clean(h.get_text(" ") if h else ""), _esw.clean(p.get_text(" ") if p else "")
        if not post or not name or STATE_POSTS.search(post):
            continue
        recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=name, district=district, body_type="Municipality", source=url,
                                src_pos={"selector": "div.who-card", "card": k}, method="html cards (div.who-card)", **extra))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if p.get("kind") == "home":
        recs = parse_home(r.text, p["body"], p.get("district"), p["url"], p.get("lgd_code"))
        name = _esw.slug(p["body"])
    else:
        recs = parse_directory(r.text, p.get("district"), p["url"])
        name = _esw.slug(p.get("district") or "directory")
    return recs, [_esw.keep(MODULE, name, r.content)], "" if recs else "no rows"
