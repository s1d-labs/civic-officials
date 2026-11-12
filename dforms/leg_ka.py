"""Karnataka: members of the Karnataka Legislative Assembly (16th, 2023-): a save-only item for now.

The Assembly's member list is kla.kar.nic.in/assembly/member/members.htm (linked from assembly/assembly.htm). archive.s1d.me has
no copy of it (it has assembly.htm, lsmembers.htm, rsmembers.htm); kla.kar.nic.in answered GitHub runners abroad (archive pool
copies 2026-11-05..08) but not dev-vps-2 / dev-vps-3, so its format could not be seen from here. The NeVA directory
kla.neva.gov.in lists only 3 members (2026-11-12). This item fetches the list page and the pages and files it links whose
address or link text speaks of members, MLAs, addresses or contacts (at most 15), and keeps them in the bucket
(depts/leg_ka/...). It gives no records ("saved only"): a reader is to be written from the saved copy.
"""
import re
from urllib.parse import urljoin

from dforms import _esw, _leg

MODULE = "leg_ka"
URL = "https://kla.kar.nic.in/assembly/member/members.htm"
WANT = re.compile(r"member|mla|address|contact|phone|directory|ಸದಸ್ಯ|ವಿಳಾಸ|ದೂರವಾಣಿ", re.I)


def items(get=None):
    return [{"key": "leg_ka-save", "payload": {"reader": MODULE, "url": URL, "state": "KA", "kind": "AC", "save_only": True,
                                                "house_name": "Karnataka Legislative Assembly (16th)", "india_only": False}}]


def links(html, base):
    """Links on the page worth keeping: same host, .htm/.html/.pdf, address or text about members / contacts."""
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        u = urljoin(base, a["href"].strip())
        if "kla.kar.nic.in" not in u or not re.search(r"\.(html?|pdf)$", u.split("?")[0], re.I):
            continue
        if WANT.search(u) or WANT.search(a.get_text(" ")):
            if u not in out and u != base:
                out.append(u)
    return out[:15]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (member list)"
    files = [_leg.keep(MODULE, "members", r.content)]
    for i, u in enumerate(links(r.text, p["url"])):
        x = get(u)
        if x is not None:
            ext = "pdf" if x.content[:5] == b"%PDF-" else "html"
            files.append(_leg.keep(MODULE, f"linked-{i:02d}-" + _esw.slug(u.rsplit("/", 1)[-1])[:60], x.content, ext))
    return [], files, f"saved only ({len(files)} files): no reader yet"
