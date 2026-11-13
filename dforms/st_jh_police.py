"""Jharkhand Police: "Important Contacts" of jhpolice.gov.in (Drupal view /imp-contacts), the state police officers with
office, residence, fax, mobile and e-mail: DGP and Police Headquarters, Special Branch, ACB, Jharkhand Jaguar, Home Guard & Fire,
JAP, Home Department (Chief Secretary, Home Secretary), Railways, Training, ATS, Wireless, Police Housing Corporation, CID, SCRB,
and the zones (South Chotanagpur, Bokaro, Palamu, Dumka): zonal IG, range DIGs and the SSPs/SPs of each district.

Page: /imp-contacts?field_spcon_location_nid=<location id> (18 locations, the view's own filter <select>; checked
2026-11-13 from dev-vps-3: Bokaro Zone = 14 rows, no pager; the unfiltered page lists only the first groups). One table per
group under <div class="view-grouping-header">. Columns: Name | Rank/ Designation | Code (STD) | Office No. | Residence No. |
Fax No. | Mobile No. | Email. "--" = empty. A post without a holder has name "--" (kept, vacant / not named).
Levels: zone rows with IG -> division (the zone); range DIG -> division (the range, else the zone); SSP / SP / SRP of a district
-> district (district from the post text, LGD); the rest -> state. Phones: office with STD code, residence and fax labelled.
Record id dept:st_jh_police:<location id>:<table n>:<row n>:<post slug>. src_pos {"table", "row"}.
Route: direct or proxy (answers from Mumbai); abroad unchecked. One item = one location page (one GET).
"""
from dforms import _esw, _state, st_lgd_upbrjh as lgd
import provenance

METHOD = "html table (Drupal view, grouped)"
MODULE = "st_jh_police"
URL = "https://www.jhpolice.gov.in/imp-contacts?field_spcon_location_nid={}"
LOCATIONS = {"915": "Police Headquarter", "1480": "Special Branch", "1485": "Anti Corruption Bureau (A.C.B.)",
             "1483": "Jharkhand Jaguar", "1487": "Home Guard", "1488": "JAP", "1572": "Home Department", "1486": "Railways",
             "1484": "Training", "32500": "Anti-Terrorist Squad", "1482": "Wireless", "1489": "Jharkhand Police Housing Corporation",
             "916": "CID", "1481": "SCRB", "68943": "South Chotanagpur Zone", "56780": "Bokaro Zone", "63270": "Palamu Zone",
             "56782": "Dumka Zone"}


def blank(s):
    s = _esw.clean(s)
    return "" if not s.strip("-– ,") else s


def level_of(post, group):
    p = post.lower()
    zone = "zone" in group.lower()
    if zone and ("ig" in p.replace(".", "").split() or "zonal" in p or "inspector general" in p):
        return "division"
    if zone and ("dig" in p.replace(".", "") or "range" in p):
        return "division"
    if any(w in p.replace(".", "") for w in ("ssp", "sp,", "sp ", "srp")) and lgd.district("JH", post)[0]:
        return "district"
    return "state"


def parse(html, url, loc=""):
    s = _esw.soup(html)
    out = []
    for g in s.find_all("div", class_="view-grouping"):
        head = g.find("div", class_="view-grouping-header")
        group = _esw.clean(head.get_text(" ")) if head else LOCATIONS.get(loc, "")
        for t in g.find_all("table"):
            pos = []
            rows = _esw.grid(t, pos=pos)
            for i, (cells, sp) in enumerate(zip(rows, pos)):
                if not cells or cells[0].lower() == "name":
                    provenance.skipped('skip: not cells or cells[0].lower() == "name"')
                    continue
                c = (cells + [""] * 8)[:8]
                name, post, std = blank(c[0]), blank(c[1]), blank(c[2])
                if not post and not name:
                    provenance.skipped('skip: not post and not name')
                    continue
                std_p = (lambda x: f"{std}-{x}" if x and std and not x.startswith("0") and len(x) < 9 else x)
                office = ", ".join(std_p(x.strip()) for x in blank(c[3]).split(",") if x.strip("- "))
                parts = [office, blank(c[6])]
                if blank(c[4]):
                    parts.append(f"{std_p(blank(c[4]))} (residence)")
                if blank(c[5]):
                    parts.append(f"{std_p(blank(c[5]))} (fax)")
                level = level_of(post, group)
                dcode, dname = lgd.district("JH", post) if level == "district" else ("", "")
                division = ""
                if level == "division":
                    division = group if "zone" in group.lower() else ""
                    if "range" in post.lower():
                        dc, dn = lgd.district("JH", post)
                        division = f"{dn} Range" if dn else group
                out.append(_state.rec(
                    MODULE, f"{loc or _esw.slug(group)}:{sp['table']}:{sp['row']}:{_esw.slug(post)[:40]}", state="JH", level=level, post=post,
                    name=name, dept="police", body=f"Jharkhand Police: {group}" if group != "Home Department" else "Home Department",
                    body_kind="police" if group != "Home Department" else "department", department="Home Department",
                    division=division, districts=[] if level == "division" else None, district=dname, district_code=dcode,
                    phone=", ".join(x for x in parts if x), email=_esw.emails(c[7]), section=group, cells=cells,
                    source=url, src_url=url, src_pos=sp))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": URL.format(k), "location": k, "label": v,
                                                 "state": "JH", "india_only": True, "route": "direct"}}
            for k, v in LOCATIONS.items()]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.content.decode("utf-8", "replace"), p["url"], p.get("location", ""))
    return recs, [_esw.keep(MODULE, f"loc-{p.get('location', 'all')}", r.content)], "" if recs else "no rows"
