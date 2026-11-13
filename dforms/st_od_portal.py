"""Odisha: officers of every department from the state portal's Who's Who and the CMO's senior officers (HTML tables, Drupal):

1. https://odisha.gov.in/en/about-us/whos-who/department?page=N (N = 0..78 on 2026-11-06; 20 rows a page, about 1,580 rows):
   "Sr. No. | Name | Designation | Department | Phone Number | Email id | Tel. EPABX": ministers, Principal Secretaries,
   Commissioner-cum-Secretaries, Addl./Joint/Deputy/Under Secretaries, directors and other heads of each department
   (the department's own site feeds the list; filter field_domain_access_target_id = All).
2. https://odisha.gov.in/en/contacts/secretariat : "Departments | Telephone No | EPABX" (39 rows: one office line per
   department of Lok Seva Bhawan; no names: post "Department office").
3. https://cm.odisha.gov.in/en/CMs-office/senior-officers : "Sr. No. | Officer's Name | Designation | E-mail ID | Office
   Number" (16 rows: Advisor, ACS, PS, Addl./Spl./Joint Secretaries, OSDs to the Chief Minister).
Records: level state. One queue item = one page. Ids: dept:st_od_portal:<page>:<table>:<row>.
Route: archive copies of 2026-11-05/06 were taken through the Indian proxy; the hosts answer from Mumbai (direct); abroad unchecked.
"""
import re

from dforms import _esw, _state, _st_ape

METHOD = "html table (header names), Drupal pager ?page=N"
MODULE = "st_od_portal"
WHOSWHO = "https://odisha.gov.in/en/about-us/whos-who/department"
SECRETARIAT = "https://odisha.gov.in/en/contacts/secretariat"
CMO = "https://cm.odisha.gov.in/en/CMs-office/senior-officers"
LAST_PAGE = 78      # "Go to last page" link of 2026-11-06 (?page=78); the reader also reads the last-page link of each page


def last_page(html):
    m = re.search(r'href="\?page=(\d+)"[^>]*title="Go to last page"', html)
    return int(m.group(1)) if m and m.group(1).isdigit() else None


def parse(html, url, page):
    recs = []
    for ti, t in enumerate(_st_ape.tables(html), 1):
        for d, pos, cells in _st_ape.header_rows(t):
            k = f"{page}:{ti}:{pos['row']}"
            common = dict(state="OD", level="state", src_url=url, src_pos=pos, cells=cells, section=page,
                          list_no=d.get("sn") if (d.get("sn") or "").isdigit() else None)
            if page == "secretariat":
                dep = d.get("department", "")
                if not dep:
                    continue
                recs.append(_state.rec(MODULE, k, post="Department office", post_kind="office", body=f"{dep} Department",
                                       body_kind="secretariat", department=dep, phone=_esw.phones(d.get("phone")),
                                       epabx=d.get("epabx"), **common))
                continue
            post, name = d.get("post", ""), d.get("name", "")
            if not (post or name):
                continue
            if page == "cmo":
                body, kind, dep = "Chief Minister's Office, Odisha", "cm_office", "Chief Minister's Office"
            else:
                dep = d.get("department", "")
                body, kind = dep, ("department" if dep else "secretariat")
                if re.search(r"(?i)minister", post) and not re.search(r"(?i)secretar", post):
                    kind = "minister"
            phone = _esw.phones(d.get("phone"))
            recs.append(_state.rec(MODULE, k, post=post, post_kind=_st_ape.post_kind(post), name=name, body=body, body_kind=kind,
                                   department=dep, phone=phone, email=_esw.emails(d.get("email") or ""),
                                   epabx=d.get("epabx"), **common))
    return recs


def items(get=None):
    out = [{"key": f"{MODULE}:whoswho:{n}", "payload": {"reader": MODULE, "url": f"{WHOSWHO}?page={n}", "page": f"whoswho-{n}",
                                                         "state": "OD", "india_only": True, "route": "direct"}}
           for n in range(LAST_PAGE + 1)]
    out += [{"key": f"{MODULE}:{p}", "payload": {"reader": MODULE, "url": u, "page": p, "state": "OD", "india_only": True,
                                                 "route": "direct"}} for p, u in (("secretariat", SECRETARIAT), ("cmo", CMO))]
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    page = p.get("page") or "page"
    recs = parse(r.text, p["url"], page)
    if page.startswith("whoswho"):
        lp = last_page(r.text)
        if lp is not None and lp > LAST_PAGE:     # more pages than the seeds: say so on a record, the parent adds items
            recs.append((f"dept:{MODULE}:pager:{page}", {"type": "seed_note", "module": MODULE, "last_page": lp,
                                                          "seeded_last_page": LAST_PAGE, "src_url": p["url"]}))
    return recs, [_esw.keep(MODULE, re.sub(r"[^a-z0-9-]", "-", page), r.content)], "" if recs else "no rows"
