"""Andhra Pradesh: members of the 16th Legislative Assembly (2024-) with email, communication address and permanent address,
from the legislature's member report (www.aplegislature.org, Liferay portlet "AssemblyMemberInformation"). Answers only from India
(Germany gets 403).

The portlet shows one view at a time (GET parameters term_id=16, order_by=N):
  order_by=1 "District": cards with name, ECI AC number ("1. ICHCHAPURAM"), party, by district;
  order_by=6 "Address List": table Sl No | name, (constituency), email | communication address | permanent address.
fetch() reads both (two GETs) and joins them on the constituency name. No phone numbers on either view. The site gives ECI
numbers 1-175; _leg.ac_seat turns them into the site layer's united-AP numbers (+119).
One queue item = the whole assembly. Record ids: dept:leg_ap:AP-AC-<site no>.
The MLA "Who is Who" PDF (legislation.aplegislature.org, Portlets/LatestNews/1786621611527_...MLA-WhoisWho.pdf) is not read.
"""
import re

import provenance
from dforms._trail import tr_pos
from dforms import _esw, _leg, _leg_se

METHOD = "html cards (district view) + html table (address view)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_ap"
PAGE = "https://www.aplegislature.org/web/legislative-assembly/legislative-assembly/member-s-information"
PORTLET = "AssemblyMemberInformation_APPortlet_INSTANCE_u0YprwIEdWmS"
TERM = 16


def view_url(order_by, term=TERM):
    ns = "_" + PORTLET + "_"
    return (f"{PAGE}?p_p_id={PORTLET}&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
            f"&{ns}term_id={term}&{ns}order_by={order_by}")


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": view_url(1), "address_url": view_url(6), "state": "AP",
                                                  "term": TERM, "india_only": True}}]


def parse_district(html, where=None):
    """{normalised constituency: (ECI no, constituency, name, party, district)} from the district view. where: a dict; when
    given, it gets {normalised constituency: {"selector": "li", "li": n}} (n = the member's <li> among the page's <li>)."""
    out, district = {}, ""
    s = _esw.soup(html)
    nli = 0
    for el in s.find_all(["h4", "li"]):
        nli += el.name == "li"
        if el.name == "h4":
            district = _esw.clean(el.get_text(" ")).title()
            continue
        nm = el.select_one("font.mem_name")
        cn = el.select_one("div.const_name")
        if not nm or not cn:
            continue
        no_el = cn.select_one("span.const_id")
        no = re.sub(r"\D", "", no_el.get_text()) if no_el else ""
        cons = _esw.clean(cn.get_text(" ").replace(no_el.get_text() if no_el else "", "", 1))
        party_el = el.select_one("div.cbp-vm-details div.cbp-vm-icon") or el.select_one("div.cbp-vm-icon")
        out[_esw.norm_ac(cons)] = (int(no) if no else None, cons, _leg_se.name(nm.get_text(" ")),
                                   _esw.clean(party_el.get_text(" ")) if party_el else "", district)
        if where is not None:
            where[_esw.norm_ac(cons)] = {"selector": "li", "li": nli}
    return out


def _addr(td):
    return re.sub(r"(,\s*)+", ", ", _esw.cell_text(td).replace(" | ", ", ")).strip(" ,")


def parse_address(html, where=None):
    """{normalised constituency: (name, constituency, email, communication address, permanent address)} from the address view."""
    out = {}
    for tr in _esw.soup(html).find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 4 or not _esw.clean(tds[0].get_text()).isdigit():
            continue
        parts = [x for x in _esw.cell_text(tds[1]).split(" | ") if x]
        nm = _leg_se.name(parts[0]) if parts else ""
        cons = next((re.sub(r"^\(\s*|\s*\)$", "", x) for x in parts[1:] if x.startswith("(")), "")
        email = _esw.emails(" ".join(parts[1:]))
        out[_esw.norm_ac(cons)] = (nm, _esw.clean(cons), email, _addr(tds[2]), _addr(tds[3]))
        if where is not None:
            where[_esw.norm_ac(cons)] = tr_pos(tr)
    return out


def merge(dist, addr, url, pos=None):
    """pos: {"dist", "addr": {constituency key: src_pos}, "dist_src", "addr_src": provenance.at() of each view}. A member in
    the district view gets its src (and src_pos) from there, with the address view's row in src_pos "address_row"."""
    pos = pos or {}
    recs = []
    for k in list(dist) + [k for k in addr if k not in dist]:
        no, cons, nm, party, district = dist.get(k, (None, "", "", "", ""))
        a = addr.get(k)
        if a:
            nm = nm or a[0]
            cons = cons or a[1]
        seat, note = _leg_se.seat("AP", no, cons, district)
        comm = a[3] if a else ""
        perm = a[4] if a else ""
        sp = dict(pos.get("dist", {}).get(k) or {})
        if k in pos.get("addr", {}):
            sp["address_row"] = {**pos["addr"][k], "url": (pos.get("addr_src") or {}).get("src_url", "")}
        src = pos.get("dist_src") if k in dist else pos.get("addr_src")
        recs.append(_leg.member(MODULE, "AP", "AC", seat, nm, constituency=cons, party=party, source=url, src_pos=sp or None,
                                **(src or {}),
                                email=a[2] if a else "", address=comm or perm, communication_address=comm,
                                permanent_address=perm if perm != comm else "", district=district, seat_no=no, note=note,
                                house="Andhra Pradesh Legislative Assembly (16th)"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "district", r.content)]
    pos = {"dist": {}, "addr": {}, "dist_src": provenance.at(r, p["url"])}
    dist = parse_district(r.text, pos["dist"])
    addr = {}
    ra = get(p["address_url"]) if p.get("address_url") else None
    if ra is not None:
        files.append(_leg.keep(MODULE, "address", ra.content))
        addr = parse_address(ra.text, pos["addr"])
        pos["addr_src"] = provenance.at(ra, p["address_url"])
    recs = merge(dist, addr, p["url"], pos)
    return recs, files, "" if recs else "no members in the page"
