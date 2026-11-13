"""Uttarakhand: officers of the Uttarakhand Secretariat (Secretariat Administration Department, sad.uk.gov.in, 2026-11-13).

Sources (DBIM WordPress, HTML; archive copies of 2026-11-05, live answers from dev-vps-3 Mumbai 2026-11-13):
- https://sad.uk.gov.in/officerss-staff/ (list, 84 rows): SRNo. | Name | Designation | View Details (link to the officer's page).
  Chief Secretary, ACS, Principal Secretaries, Secretaries, Additional / Joint / Deputy / Under Secretaries.
- each officer page (https://sad.uk.gov.in/<shri-name>/, about 89 KB): table Name | Designation | Email ID; the headings
  "Departments :-" with one card (<h2>) per department the officer holds; table "Staff": Sr. No. | Name | Designation |
  Contact No. (private secretaries with office numbers).
One item = the list + one GET per officer page (about 83). One record per officer (level state, body Uttarakhand Secretariat,
departments = the cards, department = the first card, email from the officer page, phone = the contact numbers of the staff
table, which are the officer's office numbers) and one record per staff row (post e.g. "Private Secretary to <officer>").
Route: proxy (India; abroad unchecked).
Ids: dept:st_uk_sad:<SRNo.> ; dept:st_uk_sad:<SRNo.>:staff:<n>.
"""
import re
from urllib.parse import urljoin

from dforms import _esw, _state
import provenance

METHOD = "html table (list) + html table and cards (officer pages)"
MODULE = "st_uk_sad"
URL = "https://sad.uk.gov.in/officerss-staff/"
BODY = "Uttarakhand Secretariat"
MAX_DETAIL = 150


def parse_list(html, url=URL):
    """[(SRNo., name, designation, detail url, src_pos, cells)] of the list page."""
    s = _esw.soup(html)
    out = []
    for t in s.find_all("table"):
        trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or not any(re.search(r"(?i)designation", c) for c in rows[0]):
            continue
        links = {}
        for i, tr in enumerate(trs, 1):
            a = tr.find("a", href=True)
            if a:
                links[i] = urljoin(url, a["href"])
        for row, p in zip(rows, pos):
            if len(row) < 3 or not re.fullmatch(r"\d{1,4}\.?", row[0].strip()):
                provenance.skip_row(row, 'skip: len(row) < 3 or not re.fullmatch(r"\\d{1,4}\\.?", row[0].strip())')
                continue
            out.append((row[0].strip(" ."), _esw.clean(row[1]), _esw.clean(row[2]), links.get(p["row"], ""), p, row))
    return out


def parse_detail(html):
    """{"email", "designation", "departments": [...], "staff": [(name, post, phone, src_pos, cells)]} of an officer page."""
    s = _esw.soup(html)
    d = {"email": "", "designation": "", "departments": [], "staff": []}
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows:
            continue
        head = [c.lower() for c in rows[0]]
        if any("email" in h for h in head):
            for r in rows[1:2]:
                d["designation"] = _esw.clean(r[1]) if len(r) > 1 else ""
                d["email"] = _esw.emails(r[2]) if len(r) > 2 else ""
        elif any("contact" in h for h in head):
            for r, p in zip(rows[1:], pos[1:]):
                if len(r) >= 4 and r[1].strip():
                    d["staff"].append((_esw.clean(r[1]), _esw.clean(r[2]), _esw.phones(r[3]), p, r))
                else:
                    provenance.skip_row(r, 'skip: not (len(r) >= 4 and r[1].strip())')
    h4 = next((h for h in s.find_all("h4") if re.search(r"(?i)departments", h.get_text())), None)
    if h4 is not None:
        for h in h4.find_all_next("h2"):
            if h.find_previous("h4") is not h4:
                break
            t = _esw.clean(h.get_text())
            if t:
                d["departments"].append(t)
    return d


def records(sn, name, post, link, p, cells, det, url=URL):
    det = det or {}
    deps = det.get("departments") or []
    staff = det.get("staff") or []
    phone = ", ".join(dict.fromkeys(x for _, _, ph, _, _ in staff for x in ph.split(", ") if x))
    out = [_state.rec(
        MODULE, sn, state="UK", level="state", post=post, name=name, body=BODY, body_kind="secretariat",
        department=deps[0] if deps else None, departments=deps or None, email=det.get("email", ""), phone=phone,
        phone_via="office numbers of the officer's staff (officer page)" if phone else None, detail_url=link or None,
        list_no=sn, cells=cells, src_url=url, src_pos=p)]
    for i, (sname, spost, sph, sp, scells) in enumerate(staff, 1):
        out.append(_state.rec(
            MODULE, f"{sn}:staff:{i}", state="UK", level="state", post=f"{spost} to {post} ({name})" if spost else "",
            post_kind="personal_staff", name=sname, body=BODY, body_kind="secretariat", department=deps[0] if deps else None,
            phone=sph, officer=name, officer_post=post, cells=scells, src_url=link, src_pos=sp))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:officers", "payload": {"reader": MODULE, "url": URL, "state": "UK", "india_only": True,
                                                      "route": "proxy"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    files, recs = [_esw.keep(MODULE, "officers", r.content)], []
    for n, (sn, name, post, link, pos, cells) in enumerate(parse_list(r.text, p["url"])):
        det = None
        if link and n < MAX_DETAIL:
            rd = get(link)
            if rd is not None and rd.status_code == 200:
                det = parse_detail(rd.text)
                files.append(_esw.keep(MODULE, f"officer-{_esw.slug(sn)}", rd.content))
        recs += records(sn, name, post, link, pos, cells, det, p["url"])
    return recs, files, "" if recs else "no rows"
