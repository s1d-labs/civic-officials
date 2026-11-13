"""Municipal Corporation Ludhiana (mcludhiana.gov.in): the officers of its 4 zones (A, B, C, D) by branch. One page,
/StaffList.aspx (ASP.NET; answers from Germany; live sample 2026-11-11, not in archive.s1d.me):
  1. a table Designation | Name | Contact No. | Landline (Office) with the senior officers; the zonal commissioners are the posts
     that name a zone ("Assistant Commissioner cum Zonal Commissioner Zone C", "Superintendent Engineer (B&R) Zone B").
  2. one table per branch (caption <h3>: Audit, B&R, Building, Health, O&M, Tax ...): Sr. No. | Zone | Officer Name |
     Designation | Contact No.; Zone = "A", "A, (A4)", "A&B", "D (D1)", "A,B,C,D", "HQ", "All Zone".
Records: officers of one zone or a part of the zones at level "zone" (zone = "Zone A" / "Zone A, B"; sub-zone in "subzone");
officers of all four zones, "HQ" or "All Zone" are left out (they are head-office posts). The page does not say which of the 95
wards each zone holds, so records have no "wards" key. Record ids: dept:ward_ludhiana:<zones>:<branch>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_ludhiana"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Ludhiana", "248338", "PB", "Ludhiana"
URL = "https://mcludhiana.gov.in/StaffList.aspx"
BRANCH_WING = (("b&r", "engineering"), ("o&m", "water"), ("health", "sanitation"), ("building", "planning"), ("mtp", "planning"),
               ("tax", "revenue"), ("property", "revenue"), ("light", "electrical"), ("horticulture", "horticulture"),
               ("fire", "other"))


def items(get=None):
    return [{"key": f"{MODULE}-staff", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def zones_of(text):
    """("A, B", "A4") from "A, (A4)" / "A&B" / "D (D1)"; ("", "") for HQ, General, all four zones or none."""
    t = _esw.clean(text).upper()
    sub = ", ".join(re.findall(r"\b([A-D]\d)\b", t))
    z = sorted(set(re.findall(r"\b([A-D])\b", re.sub(r"\b[A-D]\d\b", " ", t))))
    if not z or len(z) == 4 or re.search(r"HQ|ALL|GENERAL", t):
        return "", ""
    return ", ".join(z), sub


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []

    cur = {}     # the src_pos of the row being read (source trail)

    def add(zones, sub, branch, post, name, phone):
        wing = next((w for k, w in BRANCH_WING if k in branch.lower()), None) or _ward.wing_of(post)
        zone = f"Zone {zones}"
        recs.append(_ward.record(MODULE, f"{_esw.slug(zones)}:{_esw.slug(branch) or 'senior'}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}",
                                 seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone,
                                 subzone=sub or None, post=post, name=name, phone=re.sub(r"^0$", "", phone), wing=wing,
                                 section=branch or None, source=p["url"], src_pos=cur.get("pos")))
    for t in soup.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g:
            continue
        head = [c.lower() for c in g[0]]
        cap = _esw.clean(t.find("caption").get_text()) if t.find("caption") else ""
        if "zone" in head and "designation" in head:
            zi, ni, di = head.index("zone"), next(i for i, h in enumerate(head) if "name" in h), head.index("designation")
            ci = next((i for i, h in enumerate(head) if "contact" in h), None)
            for r, rp in zip(g[1:], gp[1:]):
                cur["pos"] = rp
                zones, sub = zones_of(r[zi])
                if zones and (r[ni] or (ci is not None and r[ci])):
                    add(zones, sub, cap, _esw.clean(r[di]).strip(" ,"), _esw.clean(r[ni]), _esw.clean(r[ci]) if ci is not None else "")
        elif head[:2] == ["designation", "name"]:
            for r, rp in zip(g[1:], gp[1:]):
                cur["pos"] = rp
                m = re.search(r"\bZone\s+([A-D](?:\s*(?:,|&|and)\s*[A-D])*)\b", r[0], re.I)
                if m:
                    zones, sub = zones_of(m.group(1))
                    if zones:
                        add(zones, sub, "", _esw.clean(r[0]), _esw.clean(r[1]), _esw.clean(r[2]) if len(r) > 2 else "")
    return recs


def fetch(p, get):
    r = get(p["url"], headers={"Connection": "close"})   # 2026-11-13: with keep-alive, requests times out reading the body (curl does not)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "staff-list", r.content)], "" if recs else "no zone officers"
