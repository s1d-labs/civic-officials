"""Assam: the list of Secretaries of the state portal assam.gov.in/list-of-secretaries (checked 2026-11-13 from dev-vps-3,
Mumbai: HTTP 200, 200 KB HTML, no captcha). Table 1: officers serving the state (about 100: Chief Secretary, Special Chief
Secretaries, ACS, Principal Secretaries, Commissioners & Secretaries, Secretaries; columns Name | Source of Recruitment
(RR-1993 ...) | Domicile | Educational Qualification | Present Post). Table 2: Assam cadre officers on central deputation
(posts in the Government of India): kept with on_central_deputation true and body "Government of India".
The page gives no phones or e-mails. Commissioners of the five divisions (Lower / North / Central / Upper Assam, Barak Valley)
get level division and their districts from dforms/st_div_as.json. Record ids: dept:st_as_secretaries:<table>:<name slug>.
"""
import re

from dforms import _esw, _state, st_ne

METHOD = "html table (assam.gov.in list of secretaries)"
MODULE = "st_as_secretaries"
URL = "https://assam.gov.in/list-of-secretaries"
DIV = re.compile(r"(?i)commissioner,?\s+(lower assam|north assam|central assam|upper assam|barak valley)")


def parse(html, url=URL):
    out = []
    for r in st_ne.table_rows(html):
        name, post = r.get("name", ""), r.get("post", "")
        if not name:
            continue
        dep = r["src_pos"]["table"] > 1 or bool(re.search(r"(?i)govt\.? of india|central deputation", post))
        m = DIV.search(post)
        div = m.group(1).title() if m and not dep else ""
        out.append(_state.rec(MODULE, f"{r['src_pos']['table']}:{_esw.slug(re.sub(r',.*$', '', name))[:60]}", state="AS",
                              level="division" if div else "state", division=div, post=post, post_kind=st_ne.post_kind(post), name=name,
                              body="Government of India" if dep else "Government of Assam", body_kind="other" if dep else "secretariat",
                              department=post, dept=st_ne.dept(re.sub(r"^[^,]*,", "", post)) if "," in post else "administration",
                              on_central_deputation=True if dep else None, recruitment=r.get("remarks"),
                              cells=r["cells"], src_url=url, src_pos=r["src_pos"]))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:page", "payload": {"reader": MODULE, "url": URL, "state": "AS", "india_only": False, "route": "direct"}}]


def fetch(p, get):
    r = get(p.get("url") or URL)
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url") or URL)
    return recs, [_esw.keep(MODULE, "list-of-secretaries", r.content)], "" if recs else "no rows"
