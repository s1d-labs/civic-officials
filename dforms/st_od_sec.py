"""Odisha State Election Commission: its own officers, from https://sec.odisha.gov.in/Landing/AUWhoIsWho (HTML, 46 KB, archive
copy of 2026-11-06 taken through the Indian proxy): one table "Name | Image | Phone (Office) | Address", 5 rows; the name cell
holds "<name>, <service> | <post>" (a vacant post shows "—").
Records: level state, body_kind commission, dept elections. Ids: dept:st_od_sec:<row>. Route: India (direct or proxy); abroad
unchecked.
"""
from dforms import _esw, _state, _st_ape

METHOD = "html table (name cell = name | post)"
MODULE = "st_od_sec"
URL = "https://sec.odisha.gov.in/Landing/AUWhoIsWho"


def parse(html, url=URL):
    recs = []
    for t in _st_ape.tables(html):
        for d, pos, cells in _st_ape.header_rows(t):
            parts = [x.strip() for x in d.get("name", "").split(" | ")]
            name, post = (parts[0], parts[-1]) if len(parts) > 1 else ("", parts[0])
            if not post:
                continue
            recs.append(_state.rec(MODULE, str(pos["row"]), state="OD", level="state", post=post,
                                   post_kind=_st_ape.post_kind(post), name="" if name in ("—", "-") else name,
                                   vacant=True if name in ("—", "-") else None, body="State Election Commission, Odisha",
                                   body_kind="commission", department="State Election Commission", dept="elections",
                                   phone=_esw.phones(d.get("phone")), address=d.get("address", ""), src_url=url, src_pos=pos,
                                   cells=cells, section="Who is Who"))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:whoiswho", "payload": {"reader": MODULE, "url": URL, "state": "OD", "india_only": True,
                                                      "route": "direct"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "whoiswho", r.content)], "" if recs else "no rows"
