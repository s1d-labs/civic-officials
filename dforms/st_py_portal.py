"""Puducherry: state-level posts from the Government of Puducherry portal (py.gov.in, Drupal) and the Puducherry Police site.

Pages (HTML, checked 2026-11-13 from dev-vps-3, Mumbai; 75-230 KB each):
- py.gov.in/secretaries: one card per Secretary (div.table-bordered: h2 = post, h3 = name with service and batch, then
  "Office :", "Phone :", "Fax :", "Email :" lines and a "Portfolio" list of departments). About 25 cards.
- py.gov.in/secretaries-list, /section-heads-secretariat, /heads-departments-puducherry: one table each,
  Designation | Department | Email Address (Secretaries, Secretariat section heads, Heads of Departments).
- py.gov.in/district-collector-and-heads-branch-offices-karaikal, -mahe, -yanam (regional administrators): the same table for
  the branch offices of the three outlying regions (level district: Karaikal, Mahe, Yanam are LGD districts).
- py.gov.in/department-contacts: Department | Head | Address (the head's post only, no names).
- police.py.gov.in/senior-officer-address.php ("Senior Officers Address, Updated as on ..."): SN | Rank | Name | Phone No |
  E-mail | Addresses, with section rows ("Director General & Deputy Inspectors General of Police", "Senior Superintendents of
  Police (SSP)", ...).
Records: level state unless the payload gives "level"/"district"; name as written (title, service, batch kept).
One queue item = one page. Ids: dept:st_py_portal:<page>:<row n>.
"""
import re

from dforms import _esw, _state
from provenance import at
import provenance

METHOD = "html table (header names the columns) + html cards (secretaries)"

MODULE = "st_py_portal"
PY = "https://www.py.gov.in/"
PAGES = [  # (page key, url, page kind, body, body_kind, level, district)
    ("secretaries", PY + "secretaries", "cards", "Government of Puducherry, Chief Secretariat", "secretariat", "state", ""),
    ("secretaries-list", PY + "secretaries-list", "table", "Government of Puducherry, Chief Secretariat", "secretariat", "state", ""),
    ("section-heads", PY + "section-heads-secretariat", "table", "Government of Puducherry, Secretariat", "secretariat", "state", ""),
    ("hods", PY + "heads-departments-puducherry", "table", "", "directorate", "state", ""),
    ("dept-contacts", PY + "department-contacts", "table", "", "directorate", "state", ""),
    ("karaikal", PY + "district-collector-and-heads-branch-offices-karaikal", "table", "", "department", "district", "Karaikal"),
    ("mahe", PY + "regional-administrator-and-heads-branch-offices-mahe", "table", "", "department", "district", "Mahe"),
    ("yanam", PY + "regional-administrator-and-heads-branch-offices-yanam", "table", "", "department", "district", "Yanam"),
    ("police", "https://police.py.gov.in/senior-officer-address.php", "table", "Puducherry Police", "police", "state", ""),
]
DIST_CODE = {"Karaikal": "598", "Puducherry": "600"}    # LGD (Mahe and Yanam have no LGD district code in lgd.districts)

HEAD = [("sn", r"^s\.?\s*n|^sl\b|^#"), ("post", r"designation|rank|^head$|post"), ("department", r"department|office"),
        ("name", r"name"), ("email", r"e-?mail"), ("phone", r"phone|tel|mobile|contact"), ("address", r"address")]


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": u, "page": kind, "name": k, "body": b,
                                                 "body_kind": bk, "level": lv, "district": d, "state": "PY",
                                                 "india_only": True, "route": "direct"}}
            for k, u, kind, b, bk, lv, d in PAGES]


def lines_of(el):
    return [x for x in (_esw.clean(t) for t in el.get_text("\n").split("\n")) if x]


def parse_cards(html, url, p):
    s = _esw.soup(html)
    recs = []
    for n, card in enumerate((c for c in s.select("div.table-bordered") if c.find("h2") and c.find("h3")), 1):
        post = _esw.clean(card.find("h2").get_text(" "))
        name = _esw.clean(card.find("h3").get_text(" "))
        para = card.find("p")
        txt = " ".join(lines_of(para)) if para else ""
        office = re.search(r"(?i)office[^:]*:\s*(.*?)(?=(?:phone|fax|email|office)[^:]*:|$)", txt)
        phone = re.search(r"(?i)phone[^:]*:\s*(.*?)(?=(?:fax|email|office)[^:]*:|$)", txt)
        fax = re.search(r"(?i)fax[^:]*:\s*(.*?)(?=(?:email|office|phone)[^:]*:|$)", txt)
        portfolio = [_esw.clean(li.get_text(" ")) for li in card.find_all("li")]
        recs.append(_state.rec(
            MODULE, f"secretaries:{n}", state="PY", level="state", post=post, name=name, body=p.get("body") or "",
            body_kind="secretariat", department="; ".join(portfolio), dept="administration", portfolio=portfolio or None,
            phone=_esw.phones(" ".join(m.group(1) for m in re.finditer(r"(?i)(?:office|phone)[^:]*:\s*([^:]*?)(?=[A-Za-z(]+[^:]*:|$)", txt))),
            office_phone=_esw.phones(office.group(1)) if office else None, phone_personal=_esw.phones(phone.group(1)) if phone else None,
            fax=_esw.phones(fax.group(1)) if fax else None, email=_esw.emails(txt), batch=(re.search(r"\(([A-Z]+\s*:\s*\d{4})\)", name) or [None, None])[1],
            list_no=str(n), src_url=url, src_pos={"card": n, "selector": "div.table-bordered"}))
    return recs


def header_map(cells):
    out = {}
    for i, c in enumerate(cells):
        for f, rx in HEAD:
            if f not in out and re.search(rx, c or "", re.I):
                out[f] = i
                break
    return out


def parse_table(html, url, p, module=MODULE):
    """Every table with a header row that names a post or name column; a full-width row is a section heading.
    Shared with st_ld_portal (payload "state", "district_code")."""
    s = _esw.soup(html)
    recs, n = [], 0
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        hm, section = None, ""
        for row, sp in zip(rows, pos):
            if hm is None:
                h = header_map(row)
                if "post" in h or "name" in h or ("department" in h and ("phone" in h or "email" in h)):
                    hm = h
                continue
            if len(set(x for x in row if x)) == 1 and len(row) > 1 and not re.search(r"@|\[at\]|\d{6}", row[0]):
                section = row[0]           # a section row (the whole width: one text repeated by colspan)
                continue
            g = {f: (row[i] if i < len(row) else "") for f, i in hm.items()}
            if not (g.get("post") or g.get("name") or g.get("department")):
                provenance.skip_row(row, 'skip: not (g.get("post") or g.get("name") or g.get("department"))')
                continue
            n += 1
            dept_name = g.get("department", "")
            district = p.get("district") or ""
            post = g.get("post", "")
            recs.append(_state.rec(
                module, f"{p.get('name', 'page')}:{n}", state=p.get("state") or "PY", level=p.get("level") or "state", post=post,
                name=g.get("name", ""), body=dept_name or p.get("body") or "", body_kind=p.get("body_kind") or "other",
                department=dept_name or p.get("body") or "", district=district, district_code=p.get("district_code") or DIST_CODE.get(district),
                phone=_esw.phones(g.get("phone", "")), email=_esw.emails(g.get("email", "")), address=g.get("address", ""),
                section=section or None, cells=row, list_no=g.get("sn") or str(n), src_url=url, src_pos=sp,
                **({"dept": "police"} if p.get("body_kind") == "police" else {})))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.status_code != 200:
        return [], [], f"http {r.status_code}"
    recs = parse_cards(r.text, p["url"], p) if p.get("page") == "cards" else parse_table(r.text, p["url"], p)
    recs = [(k, {**d, **at(r, p["url"])}) for k, d in recs]
    return recs, [_esw.keep(MODULE, p.get("name", "page"), r.content)], "" if recs else "no rows"
