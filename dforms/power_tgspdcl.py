"""Telangana: TGSPDCL official contacts, tgsouthernpower.org/api/contacts/official-contacts (the JSON the contacts page itself
fetches, with Accept: application/json). Answers from Germany. One GET returns everything (about 2,250 posts, with officer
names and "updateDate"); one queue item.

JSON: circles[] (zones, circles, corporate cells) -> sections[] (circle office, divisions, EROs ...) -> entries[] {unit, postId,
postName, empName, contact, isShow}. Kept: the operation posts CE/<zone>, SE/OP/<circle>, DE/OP/<division>, ADE/OP/<sub-division>,
AE/OP/<section> (about 800). The page displays a contact only when isShow != 0; the API returns all of them, and this reader keeps all
(public data is not masked), with "shown_on_page" telling which ones the page displays.
Record id dept:power_tgspdcl:<postId>.
"""
import json
import re

from dforms._power import Out, clean, raw

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

URL = "https://tgsouthernpower.org/api/contacts/official-contacts"
OP = re.compile(r"^(SE|DE|ADE|AE)\s*/\s*(?:OP|OPN|O)\s*/\s*(.+)$", re.I)
ZONE = re.compile(r"^CE\s*/\s*(.*ZONE.*)$", re.I)
LEVEL = {"SE": "circle", "DE": "division", "ADE": "subdivision", "AE": "section"}


def shown(e):
    """Every contact the public API returns (owner 2026-11-11: public data is never masked); the page itself displays only
    those with isShow != 0, which records keep as "shown_on_page"."""
    c = clean(e.get("contact"))
    return c or None


def on_page(e):
    return e.get("isShow") not in (0, "0", None)


def parse(js, source=URL):
    upd = (js.get("updateDate") or "")[:10] or None
    out = Out("power_tgspdcl", "TG", source, discom="TGSPDCL", last_updated=upd)
    for c in js.get("circles") or []:
        circle = clean(c.get("name"))
        for s in c.get("sections") or []:
            sec = clean(s.get("name")) or ""
            division = sec if re.search(r"DIVISION|^DE ", sec, re.I) else None
            sub = None
            for e in s.get("entries") or []:
                post = clean(e.get("postName")) or ""
                m, z = OP.match(post), ZONE.match(post)
                if z:
                    lvl, area = "zone", clean(z.group(1))
                elif m:
                    lvl, area = LEVEL[m.group(1).upper()], clean(m.group(2))
                else:
                    continue
                if lvl == "division":
                    division, sub = post, None
                elif lvl == "subdivision":
                    sub = post
                par = {"circle": circle if lvl in ("division", "subdivision", "section") else None,
                       "division": division if lvl in ("subdivision", "section") else None,
                       "subdivision": sub if lvl == "section" else None}
                out.add(clean(e.get("postId")) or post, lvl, area, post=post, name=e.get("empName"), phone_=shown(e), shown_on_page=on_page(e),
                        office_id=e.get("postId"), parents=par, unit=clean(e.get("unit")))
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url, headers={"Accept": "application/json"})
    if r is None:
        return [], [], "no answer"
    files = [raw("power_tgspdcl", "official-contacts", r.content, "json")]
    try:
        js = json.loads(r.content)
    except ValueError:
        return [], files, "not json"
    recs = parse(js, url)
    return recs, files, "" if recs else "no offices"
