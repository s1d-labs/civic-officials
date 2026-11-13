"""Jammu and Kashmir: postings of IAS and JKAS officers and the department e-mail directory of the General Administration
Department (jkgad.nic.in, ASP.NET, 2026-11-13).

Sources (HTML; archive copies of 2026-11-05/06; live GET + POST checked from dev-vps-3, Mumbai, 2026-11-13):
- https://jkgad.nic.in/En/CivilList.aspx : "List of IAS" (GridView: S No | Officer Name | Designation | Place Of Posting |
  With Effect From | View Property Statement), 10 rows a page; select ddlout = cadre (A AGMUT, S Erstwhile JK Cadre,
  O Outside, U Inter Cadre Deputation), ddlPageSize (10-100), ddlPageNumb (page). About 90 AGMUT rows (unchecked for S/O/U).
- https://jkgad.nic.in/En/KAS_Officers.aspx : "List of JKAS Officers", same grid; 75 pages of 10 = about 750 rows; with
  page size 100: 8 pages.
- https://jkgad.nic.in/leftMenu/Email_Directory.aspx?depType=D : department, IAS and JKAS e-mail lists (Name | Email ID).
Postbacks: the page's own __doPostBack fields (event target = the select), with the hidden fields of the last answer. One
queue item = one list (IAS: 4 cadres x (1 + pages) POSTs; KAS: 1 + 8 POSTs; e-mail: 1 GET).
Levels from the post: Divisional Commissioner -> division (Jammu / Kashmir, dforms/st_div_jk.json); Deputy Commissioner,
Additional Deputy Commissioner, Assistant Commissioner, District ... -> district (district = place of posting as written);
Sub Divisional Magistrate / Tehsildar -> subdivision / subdistrict; every other post -> state.
Route: direct or proxy (answers from India; abroad unchecked).
Ids: dept:st_jk_gad:<ias|kas>:<cadre>:<S No> ; dept:st_jk_gad:email:<table>:<row>.
"""
import re

from dforms import _esw, _state
from forms import aspnet
import provenance

METHOD = "html table (ASP.NET GridView, postback paging)"
MODULE = "st_jk_gad"
PAGES = {"ias": "https://jkgad.nic.in/En/CivilList.aspx", "kas": "https://jkgad.nic.in/En/KAS_Officers.aspx",
         "email": "https://jkgad.nic.in/leftMenu/Email_Directory.aspx?depType=D"}
CADRES = {"A": "AGMUT", "S": "Erstwhile JK Cadre", "O": "Outside", "U": "Inter Cadre Deputation"}
PFX = "ctl00$conPage$"
MAX_PAGES = 30


def level_of(post, place):
    p = f"{post} {place}"
    if re.search(r"(?i)divisional commissioner", post):
        div = "Jammu" if re.search(r"(?i)jammu", place) else "Kashmir" if re.search(r"(?i)kashmir|srinagar", place) else ""
        return "division", div, ""
    if re.search(r"(?i)sub[- ]?divisional|\bSDM\b", p):
        return "subdivision", "", ""
    if re.search(r"(?i)\btehsildar\b", post):
        return "subdistrict", "", ""
    if re.search(r"(?i)deputy commissioner|\bADC\b|additional district|district development commissioner|assistant commissioner|"
                 r"\bdistrict\b|\bACR\b|\bACD\b", post):
        dist = re.sub(r"(?i)^(district|deputy commissioner|office of the)\s*,?\s*", "", place).strip(" ,")
        return "district", "", dist.title() if dist.isupper() else dist
    return "state", "", ""


def grid_rows(html):
    """[(cells, src_pos)] of the officers grid (the table whose header has "Officer Name")."""
    s = _esw.soup(html)
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if rows and any(re.fullmatch(r"(?i)officer name", c.strip()) for c in rows[0]) and len(rows[0]) >= 6:
            return [(r, p) for r, p in zip(rows, pos) if r and re.fullmatch(r"\d{1,4}", r[0].strip())]
    return []


def n_pages(html):
    s = _esw.soup(html)
    sel = next((x for x in s.find_all("select") if (x.get("name") or "").endswith("ddlPageNumb")), None)
    return len(sel.find_all("option")) if sel else 1


def officer_records(kind, cadre, rows, url):
    out = []
    for cells, p in rows:
        sn, name, post, place, wef = cells[0], cells[2], cells[3], cells[4], cells[5]
        lvl, div, dist = level_of(post, place)
        out.append(_state.rec(
            MODULE, f"{kind}:{cadre}:{_esw.clean(sn)}", state="JK", level=lvl, division=div, district=dist,
            post=_esw.clean(post), name=_esw.clean(name), body=_esw.clean(place), body_kind="secretariat" if lvl == "state" else lvl,
            department=_esw.clean(place) or None, place_of_posting=_esw.clean(place), with_effect_from=_esw.clean(wef),
            service="IAS" if kind == "ias" else "JKAS", cadre=CADRES.get(cadre) if kind == "ias" else None,
            post_kind=_state.post_kind(post) or None, list_no=_esw.clean(sn), cells=cells, src_url=url, src_pos=p))
    return out


def email_records(html, url):
    s = _esw.soup(html)
    out = []
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or [c.strip().lower() for c in rows[0][:2]] != ["name", "email id"]:
            continue
        tno = pos[0]["table"] if pos else 0
        first = rows[1][0] if len(rows) > 1 else ""
        kind = "department" if re.search(r"(?i)department|sectt|secretariat", first) else "officer"
        for row, p in zip(rows[1:], pos[1:]):
            if len(row) < 2 or not row[0].strip():
                provenance.skip_row(row, 'skip: len(row) < 2 or not row[0].strip()')
                continue
            name, mail = _esw.clean(row[0]), _esw.emails(row[1])
            out.append(_state.rec(
                MODULE, f"email:{tno}:{p['row']}", state="JK", level="state",
                post="Department e-mail" if kind == "department" else "Officer e-mail (IAS / JKAS list)",
                name="" if kind == "department" else name, body=name if kind == "department" else "General Administration Department",
                body_kind="department" if kind == "department" else "secretariat", department=name if kind == "department" else None,
                email=mail, list_kind=kind, cells=row, src_url=url, src_pos=p))
    return out


def post_form(html, target, values):
    d = dict(aspnet.hidden(html))
    d["__EVENTTARGET"], d["__EVENTARGUMENT"] = PFX + target, ""
    for k, v in values.items():
        d[PFX + k] = v
    return d


def fetch_list(p, get, kind):
    url = p["url"]
    r = get(url)
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    files, recs = [_esw.keep(MODULE, f"{kind}-get", r.content)], []
    for cadre in (p.get("cadres") or list(CADRES)) if kind == "ias" else [""]:
        html, sel = r.text, {}
        if kind == "ias":
            sel = {"ddlout": cadre}
            r1 = get(url, method="POST", data=post_form(html, "ddlout", {**sel, "ddlPageSize": "10", "ddlPageNumb": "0"}))
            if r1 is None or r1.status_code != 200:
                continue
            html = r1.text
        r2 = get(url, method="POST", data=post_form(html, "ddlPageSize", {**sel, "ddlPageSize": "100", "ddlPageNumb": "0"}))
        if r2 is None or r2.status_code != 200:
            continue
        html = r2.text
        files.append(_esw.keep(MODULE, f"{kind}-{cadre or 'all'}-1", r2.content))
        recs += officer_records(kind, cadre or "all", grid_rows(html), url)
        for pg in range(1, min(n_pages(html), MAX_PAGES)):
            rp = get(url, method="POST", data=post_form(html, "ddlPageNumb", {**sel, "ddlPageSize": "100", "ddlPageNumb": str(pg)}))
            if rp is None or rp.status_code != 200:
                break
            html = rp.text
            files.append(_esw.keep(MODULE, f"{kind}-{cadre or 'all'}-{pg + 1}", rp.content))
            recs += officer_records(kind, cadre or "all", grid_rows(html), url)
    # the same S No on two pages would be the same officer row twice: keep the first
    seen, out = set(), []
    for rid, d in recs:
        if rid not in seen:
            seen.add(rid)
            out.append((rid, d))
    return out, files, "" if out else "no rows"


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": u, "list": k, "state": "JK", "india_only": True,
                                                 "route": "direct"}} for k, u in PAGES.items()]


def fetch(p, get):
    kind = p.get("list", "ias")
    if kind == "email":
        r = get(p["url"])
        if r is None or r.status_code != 200:
            return [], [], "no answer"
        recs = email_records(r.text, p["url"])
        return recs, [_esw.keep(MODULE, "email", r.content)], "" if recs else "no rows"
    return fetch_list(p, get, kind)
