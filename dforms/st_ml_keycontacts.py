"""Meghalaya: "Key Contacts" of the state portal meghalaya.gov.in (Drupal views; checked 2026-11-13 from dev-vps-3, Mumbai:
HTTP 200, no captcha). Every page has tables Name | Designation | Contact Details ("Address : ... Phone : ... Email ID :
a[at]b[dot]in").
- /key-contacts/secretaries: one table per department (about 96, the department name in the heading above each table; about
  340 rows: Commissioner & Secretary, Secretary, Additional / Joint / Deputy / Under Secretary). The /key-contacts/department/<n>
  pages repeat these tables department by department, so they are not read.
- /key-contacts/organisation/<n>: one page per directorate, commission, board or office (about 110: heads of departments;
  "Commissioner of Division, Shillong" and "... Tura" -> level division), the name from the link text of the index.
- /key-contacts/chief-secretary, addl-chief, gov-sect, cm-sect, deputy-commissioner, superintendent-of-police: the Chief
  Secretary, Additional Chief Secretaries, Governor's and Chief Minister's secretariats, district DCs and SPs (level district).
Seed: items(get) reads /key-contacts (one item per page). Record ids: dept:st_ml_keycontacts:<page slug>:<dept slug>:<name slug>.
"""
import re
from urllib.parse import urljoin

from dforms import _esw, _state, st_ne

METHOD = "html table (meghalaya.gov.in key contacts)"
MODULE = "st_ml_keycontacts"
BASE = "https://meghalaya.gov.in"
INDEX = BASE + "/key-contacts"
PAGES = {"secretaries": ("Secretaries to the Government", "secretariat", "state"),
         "chief-secretary": ("Chief Secretary", "secretariat", "state"),
         "addl-chief": ("Additional Chief Secretaries", "secretariat", "state"),
         "gov-sect": ("Governor's Secretariat", "governor", "state"),
         "cm-sect": ("Chief Minister's Secretariat", "cm_office", "state"),
         "deputy-commissioner": ("Deputy Commissioners", "other", "district"),
         "superintendent-of-police": ("Superintendents of Police", "police", "district")}
DISTRICTS = ["Eastern West Khasi Hills", "East Garo Hills", "East Jaintia Hills", "East Khasi Hills", "North Garo Hills", "Ri Bhoi",
             "South Garo Hills", "South West Garo Hills", "South West Khasi Hills", "West Garo Hills", "West Jaintia Hills",
             "West Khasi Hills"]


def index_items(html, url=INDEX):
    s = _esw.soup(html)
    out, seen = [], set()
    for a in s.find_all("a", href=True):
        h = urljoin(url, a["href"])
        m = re.search(r"/key-contacts/(organisation/\d+|[a-z-]+)$", h)
        if not m or m.group(1) not in PAGES and not m.group(1).startswith("organisation/") or h in seen:
            continue
        seen.add(h)
        out.append({"key": f"{MODULE}:{m.group(1).replace('/', '-')}",
                    "payload": {"reader": MODULE, "url": h, "page": m.group(1), "org": _esw.clean(a.get_text(" ")),
                                "state": "ML", "india_only": False, "route": "direct"}})
    return out


def district_of(text):
    t = text.lower()
    for d in sorted(DISTRICTS, key=len, reverse=True):
        if d.lower() in t:
            return d
    return ""


def parse(html, p):
    page = p.get("page", "secretaries")
    title, bk, level = PAGES.get(page, (p.get("org", ""), "", "state"))
    org = p.get("org") or title
    if page.startswith("organisation/"):
        bk = "commission" if re.search(r"(?i)commission(?!er)", org) else "police" if re.search(r"(?i)police", org) else \
            "division" if re.search(r"(?i)commissioner of division", org) else "directorate"
    division = ""
    m = re.search(r"(?i)commissioner of division,?\s*(\w+)", org)
    if m:
        division, level = m.group(1).title(), "division"
    out, seen = [], set()
    for r in st_ne.table_rows(html):
        name, post = r.get("name", ""), r.get("post", "")
        dept = r["section"] if page == "secretaries" else org
        ph, em, addr = st_ne.contact(r.get("contact", "") + " " + r.get("phone", "") + " " + r.get("email", ""))
        dist = district_of(post + " " + addr) if level == "district" else ""
        k = f"{page.replace('/', '-')}:{_esw.slug(dept)[:60]}:{_esw.slug(re.sub(r',.*$', '', name)) or _esw.slug(post)}"
        if k in seen:
            k += f":{r['src_pos']['table']}-{r['src_pos']['row']}"
        seen.add(k)
        out.append(_state.rec(MODULE, k, state="ML", level=level if (level != "district" or dist) else "state", district=dist,
                              division=division, post=post, post_kind=st_ne.post_kind(post), name=name, body=dept, body_kind=bk, department=dept,
                              dept=st_ne.dept(dept, post) if page not in ("chief-secretary", "addl-chief", "gov-sect", "cm-sect")
                              else "administration", phone=ph, email=em, address=addr, section=r["section"] or None,
                              cells=r["cells"], src_url=p["url"], src_pos=r["src_pos"]))
    return out


def items(get):
    r = get(INDEX)
    if r is None or r.status_code != 200:
        return []
    return index_items(r.text, INDEX)


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("page", "page").replace("/", "-"), r.content)], "" if recs else "no rows"
