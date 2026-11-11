"""Delhi Cantonment Board (delhi.cantt.gov.in, the DGDE cantonment site template): the board's own staff, from the page
/boardstaff/ ("Board Staff"; in archive.s1d.me, saved 2026-11-06; the page shows "Last updated on: November 4, 2026"). One card per
officer (div.cb-team-member-card: h6.card-title = name, the next div = post, div.card-text = branch: General, IT, Account,
Engineering ...). The board has 8 wards, but the page does not tie any officer to a ward: records are at level "body". The
Chief Executive Officer is on /ceomessage/ (not read here). Record ids: dept:ward2n_delhicantt:<branch slug>:<post slug>:<name slug>.
The same template serves the other cantonment boards (<name>.cantt.gov.in/boardstaff/), so this reader also reads them when the
payload gives body, local_body_code, state and district.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_delhicantt"
BODY, LGD, STATE, DISTRICT = "Delhi Cantonment Board", "X-DL-CANT", "DL", "New Delhi"
URL = "https://delhi.cantt.gov.in/boardstaff/"
BRANCH_WING = (("engineer", "engineering"), ("sanit", "sanitation"), ("health", "health"), ("hospital", "health"), ("revenue", "revenue"),
               ("tax", "revenue"), ("water", "water"), ("street light", "electrical"), ("electric", "electrical"), ("land", "planning"))


def items(get=None):
    return [{"key": f"{MODULE}-boardstaff", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    body, lgd = p.get("body", BODY), p.get("local_body_code", LGD)
    m = re.search(r"Last updated on:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    seen, recs = set(), []
    for card in soup.select(".cb-team-member-card"):
        t = card.select_one(".card-title")
        if not t:
            continue
        name = _esw.clean(t.get_text())
        post_el = t.find_next_sibling("div")
        post = _esw.clean(post_el.get_text()) if post_el else ""
        br = card.select_one(".card-text")
        branch = _esw.clean(br.get_text(" ")) if br else ""
        if not post or not name:
            continue
        wing = next((w for k, w in BRANCH_WING if k in branch.lower()), None) or _ward.wing_of(post)
        recs.append(_ward.record(MODULE, f"{_esw.slug(branch) or 'branch'}:{_esw.slug(post)}:{_esw.slug(name)}", seen, body=body, lgd=lgd,
                                 state=p.get("state", STATE), district=p.get("district", DISTRICT), level="body", area=body, post=post,
                                 name=name, section=branch or None, wing=wing, last_updated=m.group(1) if m else None, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, _esw.slug(p.get("body", BODY)) + "-boardstaff", r.content)], "" if recs else "no staff cards"
