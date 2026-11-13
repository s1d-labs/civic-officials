"""Karnataka: the Government Contact Directory ("Govt Contact Manual", karnataka.gov.in/gokdirectory/en), whose content is the
page karnataka.gov.in/contactdirectory/public/17/government-contact-directory/en (iframe; HTML, 128 KB, checked 2026-11-13 from
dev-vps-3, Mumbai; www.karnataka.gov.in fails TLS with "unrecognized name", the bare host answers).

One accordion panel per group (a#collapseN heading), one table each: Governor, Chief Minister, Ministers (33), Chief Secretary,
Additional Chief Secretary, ACS-cum-Development Commissioner, Additional Chief Secretaries (11), Principal Secretaries /
Secretaries (43), Head of Departments (64: Ministry | Department Name | Designation, no names), Deputy Commissioners (31),
CEO Zilla Panchayath (31), Commissioner of Police (6), Superintendent of Police (31). Columns differ per table (Name,
Designation, Department, Email, Internal Tel. No., Office, Fax, Address, District / City, Contacts); the header names them.
Records: level state for the state groups; level district for Deputy Commissioners, CEOs of Zilla Panchayats, Superintendents of
Police and Commissioners of Police (area = the district or city as written). post = the Designation cell, else the group's post.
Phones: Office and Contacts as written, intercom (Internal Tel. No.) and fax kept apart. One queue item = the page.
Ids: dept:st_ka_gokdir:<group slug>:<row n>.
"""
import re

from dforms import _esw, _state
from provenance import at
import provenance

METHOD = "html table per accordion panel (header names the columns)"

MODULE = "st_ka_gokdir"
URL = "https://karnataka.gov.in/contactdirectory/public/17/government-contact-directory/en"
BODY = "Government of Karnataka"
# group heading -> (post when the table has no Designation column, level, body_kind)
GROUPS = [(r"governor", ("Governor", "state", "governor")), (r"chief minister", ("Chief Minister", "state", "cm_office")),
          (r"^ministers", ("Minister", "state", "other")), (r"head of department", ("", "state", "directorate")),
          (r"deputy commissioner", ("Deputy Commissioner and District Magistrate", "district", "division")),
          (r"zilla panch", ("Chief Executive Officer, Zilla Panchayat", "district", "department")),
          (r"commissioner of police", ("Commissioner of Police", "district", "police")),
          (r"superintendent of police", ("Superintendent of Police", "district", "police")),
          (r"secretar|development commissioner", ("", "state", "secretariat"))]
HEAD = [("sn", r"^s\.?\s*l\.?\s*no|^sl\.?\s*no|^sl\b"), ("ministry", r"ministry"), ("department", r"department"),
        ("post", r"designation"), ("name", r"^name"), ("email", r"e-?\s?mail"), ("internal", r"internal|extension"),
        ("office", r"office|contacts?$"), ("fax", r"fax"), ("address", r"address"), ("area", r"district|city")]


def items(get=None):
    return [{"key": f"{MODULE}:page", "payload": {"reader": MODULE, "url": URL, "state": "KA", "india_only": True,
                                                  "route": "direct"}}]


def header_map(cells):
    out = {}
    for i, c in enumerate(cells):
        for f, rx in HEAD:
            if f not in out and re.search(rx, (c or "").strip(), re.I):
                out[f] = i
                break
    return out


def group_of(title):
    for rx, g in GROUPS:
        if re.search(rx, title or "", re.I):
            return g
    return ("", "state", "other")


def parse(html, url=URL):
    s = _esw.soup(html)
    recs = []
    for t in s.find_all("table"):
        a = t.find_previous("a", href=re.compile(r"^#collapse"))
        if a is None:
            continue                     # the accessibility tables of the page frame
        title = _esw.clean(a.get_text(" "))
        gpost, level, bkind = group_of(title)
        pos = []
        rows = _esw.grid(t, pos=pos)
        hm, n = None, 0
        for row, sp in zip(rows, pos):
            if hm is None:
                hm = header_map(row)
                continue
            g = {f: (row[i] if i < len(row) else "") for f, i in hm.items()}
            if not any(g.get(k) for k in ("name", "post", "department", "area")):
                provenance.skip_row(row, 'skip: not any(g.get(k) for k in ("name", "post", "department", "area"))')
                continue
            n += 1
            area = g.get("area", "")
            dept_name = g.get("department", "")
            post = g.get("post") or gpost
            if title.lower().startswith("ministers"):
                post = _esw.clean(g.get("department", "").replace("|", " ")) or "Minister"   # "Hon'ble Minister of Revenue ..."
                dept_name = re.sub(r"(?i)^hon'?ble\s+minister\s+(of\s+|for\s+)?", "", post)
            office = g.get("office", "")
            recs.append(_state.rec(
                MODULE, f"{_esw.slug(title)}:{n}", state="KA", level=level, post=post, name=g.get("name", ""),
                body=dept_name or (area if level == "district" else BODY), body_kind=bkind, department=dept_name or None,
                ministry=g.get("ministry") or None, district=area if level == "district" else "",
                phone=_esw.phones(re.sub(r"(?i)\(fax\)", " ", re.sub(r"[\d\s-]+\(fax\)", " ", office))) or office,
                intercom=g.get("internal") or None, fax=_esw.phones(g.get("fax", "")) or g.get("fax") or None,
                email=_esw.emails(g.get("email", "")), address=g.get("address", ""), section=title, cells=row,
                list_no=g.get("sn") or str(n), src_url=url, src_pos=sp,
                **({"dept": "police"} if bkind == "police" else {"dept": "rural_development"} if "zilla" in title.lower()
                   else {"dept": "administration"} if level == "district" else {})))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.status_code != 200:
        return [], [], f"http {r.status_code}"
    recs = [(k, {**d, **at(r, p["url"])}) for k, d in parse(r.text, p["url"])]
    return recs, [_esw.keep(MODULE, "directory", r.content)], "" if recs else "no rows"
