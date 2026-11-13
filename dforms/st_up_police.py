"""Uttar Pradesh Police: officer lists of uppolice.gov.in (ASP.NET), with name, rank, posting, CUG mobile, office phone, e-mail.

Pages (links of the home page menu "Police Units" / "Zones & Ranges" / "Districts", checked 2026-11-13 from dev-vps-3):
- frmUnitOfficials.aspx?<unit>&cd=<code>: 24 units (DGP HQ, PHQ, ATS, STF, CB-CID, EOW, Vigilance, GRP, PAC, Traffic,
  Fire Service, Training, Telecom, Security ...): level state.
- frmOfficials.aspx?zone<x>&cd=<code>: 8 zones (ADG zone): level division, area = the zone (no district list: zones group
  several ranges).
- frmOfficials.aspx?range<x>&cd=<code>: 18 ranges (IG / DIG range): level division; UP ranges have the names and districts
  of the 18 revenue divisions (dforms/st_div_up.json).
- frmOfficials.aspx?comm<x>&cd=<code>: 4 police commissionerates (Lucknow, Gautam Buddh Nagar, Kanpur, Varanasi): level
  district (the commissionerate's district).
- frmOfficials.aspx?<district>&cd=<code>: 75 districts (SP / SSP, Additional SPs, COs): level district.
Each page has GridViews ContentPlaceHolder_Body_grd<X> (grdIPSOfficers, grdPPSOfficers, on district pages also
grdRIOTherOfficer ...): all are read; grade = <X> without "Officers". Columns: S.No | Name of IPS (PPS)
Officer | Rank | Posted as | [District of Posting] | CUG / Mobile No. | Office No. | Email Id.
Record id dept:st_up_police:<page slug>:<ips|pps>:<S.No>. src_pos {"table", "row"}. One item = one page (one GET).
Route: direct or proxy (answers from Mumbai); abroad unchecked. No captcha on these pages.
"""
import re

from dforms import _esw, _state, st_lgd_upbrjh as lgd

METHOD = "html table (ASP.NET GridView)"
MODULE = "st_up_police"
BASE = "https://uppolice.gov.in/"
# range / zone slug -> revenue division name of dforms/st_div_up.json (ranges) or zone name
RANGES = {"agra": "Agra", "algrh": "Aligarh", "allhd": "Prayagraj", "azmh": "Azamgarh", "basti": "Basti", "brly": "Bareilly",
          "cdham": "Chitrakoot", "deviptn": "Devipatan", "fzbad": "Ayodhya", "grkpur": "Gorakhpur", "jhansi": "Jhansi",
          "knp": "Kanpur", "lko": "Lucknow", "mirzapur": "Mirzapur", "mod": "Moradabad", "mrt": "Meerut", "saharan": "Saharanpur",
          "vns": "Varanasi"}
ZONES = {"agra": "Agra Zone", "allhd": "Prayagraj Zone", "brly": "Bareilly Zone", "grk": "Gorakhpur Zone", "knp": "Kanpur Zone",
         "lko": "Lucknow Zone", "mrt": "Meerut Zone", "vns": "Varanasi Zone"}
COMMS = {"lko": "Lucknow", "gbngr": "Gautam Buddha Nagar", "knp": "Kanpur Nagar", "vns": "Varanasi"}


def page_kind(slug):
    """(kind, area): kind unit | zone | range | comm | district."""
    if slug.startswith("zone"):
        return "zone", ZONES.get(slug[4:], slug[4:].title() + " Zone")
    if slug.startswith("range"):
        return "range", RANGES.get(slug[5:], slug[5:].title())
    if slug.startswith("comm"):
        return "comm", COMMS.get(slug[4:], slug[4:].title())
    return "district", slug


def parse(html, url, slug, unit=False):
    s = _esw.soup(html)
    kind, area = ("unit", slug) if unit else page_kind(slug)
    out = []
    for t in s.find_all("table", id=re.compile(r"_grd\w+$")):
        m = re.search(r"_grd(\w+?)(?:Officers?|Officer)?$", t["id"])
        grade = (m.group(1) if m else "other").lower()
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows:
            continue
        head = [h.lower() for h in rows[0]]
        col = {k: next((i for i, h in enumerate(head) if w in h), None) for k, w in
               (("sno", "s.no"), ("name", "name"), ("rank", "rank"), ("posted", "posted"), ("dist", "district"),
                ("mobile", "mobile"), ("office", "office no"), ("email", "email"))}
        for cells, sp in zip(rows[1:], pos[1:]):
            g = lambda k: cells[col[k]] if col[k] is not None and col[k] < len(cells) else ""
            sno, name, rank, posted = g("sno"), g("name"), g("rank"), g("posted")
            if not (name or posted) or not re.search(r"\d", sno or "0"):
                continue
            name = re.sub(r"\s*\(\s*0\s*\)\s*$", "", name)      # "PRAGYA MISHRA ( 0 )": the grid's empty batch field
            post = f"{rank}, {posted}" if rank and posted and rank.lower() not in posted.lower() else (posted or rank)
            level, division, dname, dcode, districts = "state", "", "", "", None
            if kind == "zone":
                level, division, districts = "division", area, []
            elif kind == "range":
                level, division = "division", area
            elif kind == "comm":
                level, dname = "district", area
                dcode = lgd.district("UP", area)[0]
            elif kind == "district":
                dcode, dname = lgd.district("UP", g("dist") or posted or slug)
                if not dcode:
                    dcode, dname = lgd.district("UP", slug)
                level = "district"
            else:
                dist = g("dist")
                if dist and not re.search(r"(?i)lucknow", dist):
                    dcode, dname = lgd.district("UP", dist)
            office = g("office")
            phone = ", ".join(x for x in (g("mobile"), "" if office.strip("- ") == "" else office) if x.strip("- "))
            body = {"unit": f"UP Police: {slug}", "zone": f"UP Police: {area}", "range": f"UP Police: {area} Range",
                    "comm": f"Police Commissionerate {area}", "district": f"UP Police: district {dname or slug}"}[kind]
            pk = _state.post_kind(rank) if rank.upper() not in ("DG", "DGP") else (
                "dgp" if re.search(r"(?i)\bDGP\b", posted) and not re.search(r"(?i)/", posted) else "head_of_department")
            out.append(_state.rec(
                MODULE, f"{slug}:{grade}:{sno}", post_kind=pk or None, state="UP", level=level, post=post, name=name, dept="police", body=body,
                body_kind="police", department="Home Department", division=division, districts=districts,
                district=dname if level == "district" else "", district_code=dcode if level == "district" else "",
                posting_district=g("dist") or None, rank=rank, posted_as=posted, grade=grade, phone=phone,
                email=_esw.emails(g("email")), cells=cells, source=url, src_url=url, src_pos=sp))
    return out


def items_from_home(html):
    """Queue items from the saved home page: every frmOfficials / frmUnitOfficials link with its cd code."""
    out, seen = [], set()
    for m in re.finditer(r'href="(frm(Unit)?Officials\.aspx\?([a-z0-9-]+)&(?:amp;)?cd=([^"]+))"', html):
        href, unit, slug, cd = m.group(1).replace("&amp;", "&"), bool(m.group(2)), m.group(3), m.group(4)
        if slug in seen:
            continue
        seen.add(slug)
        out.append({"key": f"{MODULE}:{slug}", "payload": {"reader": MODULE, "url": BASE + href, "slug": slug, "unit": unit,
                                                          "state": "UP", "india_only": True, "route": "direct"}})
    return out


def items(get):
    r = get(BASE)
    return items_from_home(r.content.decode("utf-8", "replace")) if r is not None else []


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.content.decode("utf-8", "replace"), p["url"], p["slug"], p.get("unit", False))
    return recs, [_esw.keep(MODULE, p["slug"], r.content)], "" if recs else "no rows"
