"""Rewa Nagar Nigam (rewanagarnigam.org, WordPress + Elementor): the civil engineers of its 4 zones. One page per zone,
/civil-zone-<n>/ (answers from Germany; live sample of zone 1 on 2026-11-11, not in archive.s1d.me). Each officer is an
Elementor image box (h3 "elementor-image-box-title" = name, p "elementor-image-box-description" = post) followed by an icon list
(fa-phone = mobile, fa-home = department, fa-globe = office address, fa-envelope = email). Zone 1 names an Executive Engineer and
an Assistant Engineer. The pages give no ward lists. Records: level "zone". Ids: dept:ward2n_rewa:zone-<n>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html cards"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_rewa"
BODY, LGD, STATE, DISTRICT = "Rewa Nagar Nigam", "250797", "MP", "Rewa"
URL = "https://rewanagarnigam.org/civil-zone-{n}/"
ZONES = (1, 2, 3, 4)


def items(get=None):
    return [{"key": f"{MODULE}-civil-zone-{n}", "payload": {"reader": MODULE, "url": URL.format(n=n), "state": STATE, "zone": n}}
            for n in ZONES]


def parse(html, p):
    soup = _esw.soup(html)
    z = p.get("zone") or int(re.search(r"zone-(\d+)", p["url"]).group(1))
    zone = f"Zone {z}"
    seen, recs = set(), []
    for h in soup.select("h3.elementor-image-box-title"):
        name = _esw.clean(h.get_text(" "))
        d = h.find_next_sibling("p")
        post = _esw.clean(d.get_text(" ")) if d else ""
        if not post or not name:
            continue
        info = {}
        box = h.find_parent(class_="elementor-widget-image-box")
        lst = box.find_next(class_="ova-icon-list") if box else None
        if lst and lst.find_previous(class_="elementor-image-box-title") is h:
            for it in lst.select(".item"):
                i = it.find("i")
                kind = next((c for c in (i.get("class") or []) if c.startswith("fa-") and c != "fa-solid"), "") if i else ""
                info.setdefault(kind, _esw.clean(it.get_text(" ")))
        recs.append(_ward.record(MODULE, f"zone-{z}:{_esw.slug(post)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=f"Civil {zone}", zone=zone, post=post, name=name,
                                 phone=info.get("fa-phone", ""), email=info.get("fa-envelope", ""),
                                 address=info.get("fa-globe"), department=info.get("fa-home"), source=p["url"], src_pos=_ward.nth(h)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    z = p.get("zone") or "x"
    return recs, [_esw.keep(MODULE, f"civil-zone-{z}", r.content)], "" if recs else "no officer boxes"
