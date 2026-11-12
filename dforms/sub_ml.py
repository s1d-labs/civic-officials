"""Meghalaya: the Deputy Commissioner and the Superintendent of Police of all 12 districts, from the state portal's key contacts
meghalaya.gov.in/key-contacts/deputy-commissioner and /key-contacts/superintendent-of-police (Drupal views). India only: the portal
timed out from Germany and from the India VPS on 2026-11-11; archive.s1d.me holds copies of both pages from 2026-11-10 (status 200,
captured through the pool), and the test samples are cut from those copies.

The district portals of Eastern West Khasi Hills (no portal yet), East Garo Hills, East Jaintia Hills, South West Garo Hills and
West Garo Hills fail from every route, so this list is their one live public source for the DC (name, office phone, email).
One table per page, one row per officer. Two layouts: DCs = (name in <strong> + designation in <div>, contact cell); SPs = (name,
designation, contact cell). The contact cell holds "Address :", "Phone :", "Fax :", "Email ID :" lines; a number marked "(Fax)" in
the Phone line goes to fax. District = the designation after the post ("Deputy Commissioner, East Garo Hills District,
Williamnagar" -> East Garo Hills). DC -> dept administration, SP -> dept police; level district. No page date (the portal's footer
date is site-wide). Record ids: dept:sub_ml:ML-<district slug>:dc, dept:sub_ml:ML-<district slug>:sp.
"""
import re

from dforms._trail import tr_pos
from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_ml"
BASE = "https://meghalaya.gov.in/key-contacts/"
PAGES = {"dc": BASE + "deputy-commissioner", "sp": BASE + "superintendent-of-police"}


def items(get=None):
    return [{"key": f"{MODULE}-{p}", "payload": {"reader": MODULE, "url": u, "state": "ML", "page": p, "india_only": True}}
            for p, u in PAGES.items()]


def _contact(td):
    """{"address", "phone", "fax", "email"} from a contact cell of "Label : value" lines."""
    for br in td.find_all("br"):
        br.replace_with("\n")
    out = {}
    for line in td.get_text("").split("\n"):
        m = re.match(r"\s*([A-Za-z ]+?)\s*:\s*(.*)$", _esw.clean(line))
        if m:
            out[m.group(1).lower()] = m.group(2).strip()
    phone = out.get("phone", "")
    fax = re.findall(r"([\d\s-]{5,})\s*\(\s*f(?:ax)?\s*\)", phone, flags=re.I)
    phone = re.sub(r"[\d\s-]{5,}\(\s*f(?:ax)?\s*\)", " ", phone, flags=re.I)
    return {"address": out.get("address", ""), "phone": _esw.phones(phone),
            "fax": _esw.phones(out.get("fax", ""), *fax), "email": _esw.emails(out.get("email id", "") or out.get("email", ""))}


def district(desig):
    """"Deputy Commissioner, East Garo Hills District, Williamnagar" -> "East Garo Hills"."""
    parts = [p.strip() for p in desig.split(",")]
    d = parts[1] if len(parts) > 1 else ""
    return re.sub(r"(?i)\s+district$", "", d).strip()


def parse(html, url, page):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue
        first = tds[0]
        strong, div = first.find("strong"), first.find("div")
        if len(tds) >= 3:
            name, desig = _esw.clean(first.get_text(" ")), _esw.clean(tds[1].get_text(" "))
        else:
            name = _esw.clean(strong.get_text(" ")) if strong else _esw.clean(first.get_text(" "))
            desig = _esw.clean(div.get_text(" ")) if div else ""
        c = _contact(tds[-1])
        d = district(desig)
        if not d:
            continue
        base = key = f"ML-{_esw.slug(d)}:{page}"
        n = 2
        while key in seen:
            key, n = f"{base}:{n}", n + 1
        seen.add(key)
        post = "Deputy Commissioner" if page == "dc" else "Superintendent of Police"
        rec = _esw.record(MODULE, key, dept="administration" if page == "dc" else "police", level="district", area=d, post=post,
                          designation=desig, name=name, phone=c["phone"], fax=c["fax"], email=c["email"], address=c["address"],
                          district=d, state="ML", source=url, src_pos=tr_pos(tr))
        if rec[1].get("name") or rec[1].get("phone") or rec[1].get("email"):
            recs.append(rec)
    return recs


def fetch(p, get):
    page = p.get("page", "dc")
    url = p.get("url") or PAGES[page]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, page, r.content)]
    recs = parse(r.text, url, page)
    return recs, files, "" if recs else "no rows"
