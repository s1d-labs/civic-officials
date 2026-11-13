"""Tripura: senior officers of the state from the state portal tripura.gov.in/senior-officers-administration (HTML table
Name | Present Position | Departments | Contacts | Email, about 20 rows: Chief Secretary, Principal Secretaries, Secretaries
with their departments, office / fax / mobile numbers and e-mails). Checked 2026-11-13 from dev-vps-3 (Mumbai): HTTP 200,
no captcha. One queue item = the page. Record ids: dept:st_tr_portal:<post slug>:<name slug>.
The department telephone lists linked on tripura.gov.in/contact-directory are read by dforms/st_tr_dirs.py.
"""
import re

from dforms import _esw, _state, st_ne

METHOD = "html table (tripura.gov.in senior officers)"
MODULE = "st_tr_portal"
URL = "https://tripura.gov.in/senior-officers-administration"


def parse(html, url=URL):
    out, seen = [], set()
    for r in st_ne.table_rows(html):
        name, post = r.get("name", ""), r.get("post", "")
        k = f"{_esw.slug(post)}:{_esw.slug(re.sub(r',.*$', '', name))}"
        if k in seen:
            k += f":{r['src_pos']['row']}"
        seen.add(k)
        contact = r.get("contact", "") or r.get("phone", "")
        depts = r.get("department", "")
        out.append(_state.rec(MODULE, k, state="TR", level="state", post=post, post_kind=st_ne.post_kind(post), name=name, body="Government of Tripura",
                              body_kind="secretariat", department=depts, phone=_esw.phones(re.sub(r"\+91\s*", "0", contact)),
                              phone_raw=contact, email=_esw.emails(r.get("email", "") + " " + contact),
                              dept=st_ne.dept(depts.split(" | ")[0]) if not re.search(r"(?i)chief secretary", post) else "administration",
                              cells=r["cells"], src_url=url, src_pos=r["src_pos"]))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:senior", "payload": {"reader": MODULE, "url": URL, "state": "TR", "india_only": False, "route": "direct"}}]


def fetch(p, get):
    r = get(p.get("url") or URL)
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url") or URL)
    return recs, [_esw.keep(MODULE, "senior-officers", r.content)], "" if recs else "no rows"
