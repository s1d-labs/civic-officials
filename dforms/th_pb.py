"""Punjab: the head of each urban body (Executive Officer of a council or nagar panchayat, Commissioner of a corporation) and
its elected head (President / Mayor), from the two "authority" cards at the top of the body's page on the Local Government
Department's e-Nigam platform (NIC Punjab): https://mcpatiala.punjab.gov.in/Home/Index?mcid=<id>&lng= (any platform host answers
for any mcid, see cforms/cr_pb.py). Static HTML, about 330 KB per page; answers from outside India.

Each card: div.massage-card > .name_overlay > h6 (name) + p (post: "President", "Mayor", "Executive Officer", "Commissioner").
The card image's file name often carries its upload time ("20261111_134359_SubHead.jpg") -> photo_uploaded (yyyy-mm-dd).
A card with an empty name (Talwara, 2026-11-13: both cards empty) gives no record. No phones on the cards.
cforms/cr_pb.py reads the member cards (.gallery_card2) of the same page and not these two cards.

One item per body (114 mcids of the platform switcher, cforms/cr_pb.PLATFORM). dforms/th_pb_lgd.json: mcid -> body, LGD code,
district (from the cr_pb seeds; Jalandhar and Amritsar matched by name). Records: dept_office, dept town_body, level body,
role head / chair from _ulb.role_of(post), src_pos {selector, card}.
"""
import json
import re
from pathlib import Path

from dforms import _esw, _ulb
from cforms.cr_pb import PLATFORM
import provenance

METHOD = "html cards (e-Nigam home page, .massage-card .name_overlay)"

MODULE = "th_pb"
STATE = "PB"
HOST = "https://mcpatiala.punjab.gov.in"
LGD = json.loads(Path(__file__).with_name("th_pb_lgd.json").read_text())["mcid"]
POSTWORD = re.compile(r"(?i)^\s*(ex[e]?c?u?tive\s*officer|president|mayor|commissioner|vice\s*president)\s*$")


def items(get=None):
    out = []
    for mcid in sorted(PLATFORM):
        b = LGD.get(str(mcid), {})
        out.append({"key": f"{MODULE}-{mcid}", "payload": {
            "reader": MODULE, "mcid": mcid, "body": b.get("body") or PLATFORM[mcid], "district": b.get("district"),
            "lgd_code": b.get("lgd_code"), "url": f"{HOST}/Home/Index?mcid={mcid}&lng=", "state": STATE, "india_only": False}})
    return out


def cards(html):
    """[(card number, name, post, image url)] of the authority cards."""
    out = []
    for k, c in enumerate(_esw.soup(html).select(".massage-card"), 1):
        ov = c.select_one(".name_overlay")
        if not ov:
            continue
        h, p = ov.find("h6"), ov.find("p")
        img = c.find("img")
        out.append((k, _esw.clean(h.get_text(" ") if h else ""), _esw.clean(p.get_text(" ") if p else ""),
                    img.get("src", "") if img else ""))
    return out


def parse(html, p):
    recs, seen = [], set()
    url = p.get("url") or f"{HOST}/Home/Index?mcid={p['mcid']}&lng="
    b = LGD.get(str(p.get("mcid")), {})
    for k, name, post, img in cards(html):
        if not name or not post or POSTWORD.search(name):     # "Exective Officer" typed as the name (Tapa, 2026-11-13)
            provenance.skipped('skip: not name or not post or POSTWORD.search(name)')
            continue
        m = re.search(r"/(20\d\d)(\d\d)(\d\d)_\d{6}_", img)
        recs.append(_ulb.record(MODULE, STATE, p.get("body") or b.get("body", ""), post, seen, name=name,
                                district=p.get("district") or b.get("district"), source=url, page=url,
                                lgd_code=p.get("lgd_code") or b.get("lgd_code"), area_latin=b.get("lgd_name"),
                                mcid=p.get("mcid"), photo=img or None,
                                photo_uploaded=f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None,
                                src_pos={"selector": ".massage-card .name_overlay", "card": k}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if "name_overlay" not in r.text:
        return [], [], "no authority cards"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"enigam-{p['mcid']}", r.content)], "" if recs else "cards without names"
