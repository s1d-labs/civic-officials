"""Arunachal Pradesh: the Who's Who of the state portal arunachalpradesh.gov.in/whos-who.php (checked 2026-11-13 from
dev-vps-3, Mumbai: HTTP 200, 170 KB HTML, no captcha). Six tables: the senior officers (Chief Secretary, Principal Secretaries,
Commissioners, Secretaries: Name | Designation/Departments | Block/Room Details | Remarks | Contact Details | Name of the Link
Officer, with PBX / office / residence numbers and e-mails) and the secretariat officers lists (Sl.No. | Name of the Officer |
Post & Deptt | Remarks = service: Additional / Joint / Deputy / Under Secretaries, PPS), about 100 rows.
A post cell can hold several charges ("1. Principal Secretary (i). Political ... 2. Div. Commissioner (West)"): kept whole;
post_kind is the first rank in it. Record ids: dept:st_ar_whoswho:<table>-<row>:<name slug>.
"""
import re

from dforms import _esw, _state, st_ne
import provenance

METHOD = "html table (arunachalpradesh.gov.in Who's Who)"
MODULE = "st_ar_whoswho"
URL = "https://arunachalpradesh.gov.in/whos-who.php"


def parse(html, url=URL):
    out = []
    for r in st_ne.table_rows(html):
        name, post = r.get("name", ""), r.get("post", "")
        if not name or re.fullmatch(r"(?i)name.*", name):
            provenance.skip_row(r, 'skip: not name or re.fullmatch(r"(?i)name.*", name)')
            continue
        ph, em, _ = st_ne.contact(r.get("contact", "") + " " + r.get("phone", "") + " " + r.get("email", ""))
        p = r["src_pos"]
        div = ""
        m = re.search(r"(?i)div(?:\.|isional)?\s*commissioner\s*\(?\s*(east|west|central)\b", post)
        if m:
            div = m.group(1).title()
        out.append(_state.rec(MODULE, f"{p['table']}-{p['row']}:{_esw.slug(re.sub(r',.*$', '', name))[:60]}", state="AR",
                              level="state", post=post, post_kind=st_ne.post_kind(post), name=name, body="Government of Arunachal Pradesh", body_kind="secretariat",
                              department=post, dept=st_ne.dept(re.sub(r"^.*?\(", "", post)) if "(" in post else "administration",
                              service_cell=r.get("remarks"), room=r.get("address"), phone=ph, email=em,
                              also_divisional_commissioner=div or None, link_officer=(r["cells"][-1] if len(r["cells"]) >= 7 else None),
                              cells=r["cells"], src_url=url, src_pos=p))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:page", "payload": {"reader": MODULE, "url": URL, "state": "AR", "india_only": False, "route": "direct"}}]


def fetch(p, get):
    r = get(p.get("url") or URL)
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url") or URL)
    return recs, [_esw.keep(MODULE, "whos-who", r.content)], "" if recs else "no rows"
