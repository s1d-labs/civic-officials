"""Andaman & Nicobar Islands: secretaries and senior officers of the UT Administration, from https://andamannicobar.gov.in/contact
(HTML, 296 KB, one table "Secretaries | Departments / Portfolios", 45 officers in the archive copy of 2026-11-13): each row has
span.officer-name, span.officer-designation, div.officer-meta lines (Year in service / cadre, DOJ in UT Admin, phone, e-mail
written "x[at]and[dot]nic[dot]in") and one a.dept-badge per department / portfolio held.
Records: level state; post = the designation, portfolios = the badges (list); a "Deputy Commissioner (<district>)" or
"Assistant Commissioner (<place>)" portfolio adds the district. dept: from the first portfolio when the officer holds
1-3, else administration. Ids: dept:st_an_contact:<row>.
Route: the archive copy came through the Indian proxy; live answer from Mumbai not tried (assume direct); abroad unchecked.
"""
import re

from dforms import _esw, _state, _st_ape
from dforms._trail import tr_pos
import provenance

METHOD = "html table rows (officer-name / officer-designation / officer-meta / dept-badge)"
MODULE = "st_an_contact"
URL = "https://andamannicobar.gov.in/contact"
AN = {"south andaman": ("602", "South Andamans"), "north and middle andaman": ("632", "North And Middle Andaman"),
      "nicobar": ("603", "Nicobars")}


def text(el):
    return _esw.clean(el.get_text(" ")) if el is not None else ""


def parse(html, url=URL):
    recs = []
    soup = _esw.soup(html)
    for n, tr in enumerate(soup.find_all("tr"), 1):
        nm = tr.select_one(".officer-name")
        if nm is None:
            provenance.skip_row(tr, 'skip: nm is None')
            continue
        name = text(nm)
        post = text(tr.select_one(".officer-designation"))
        meta = [text(m) for m in tr.select(".officer-meta")]
        info = {}
        for m in meta:
            if re.match(r"(?i)year in service", m):
                info["service_year"] = re.sub(r"(?i)^year in service\s*:\s*", "", m)
            elif re.match(r"(?i)doj", m):
                info["joined_ut"] = re.sub(r"(?i)^doj in ut admin\s*:\s*", "", m)
            elif re.search(r"(?i)e-?mail", m):
                info["email"] = _esw.emails(m.replace("[in]", "[dot]in"))
            elif re.search(r"\d{3,}", m):
                info["phone"] = _esw.phones(m)
        badges = [text(b) for b in tr.select(".dept-badge")]
        blob = " ".join(badges)
        code, dname = "", ""
        for k, v in AN.items():
            if re.search(r"(?i)deputy commissioner\s*\(\s*" + k, blob):
                code, dname = v
        pos = tr_pos(tr)
        if not post and badges:
            post = badges[0]
        recs.append(_state.rec(
            MODULE, str(pos.get("row") or n), state="AN", level="district" if code else "state", district=dname,
            district_code=code, post=post, post_kind="district_magistrate" if code and re.match(r"(?i)deputy commissioner", post)
            else _st_ape.post_kind(post), name=name,
            body="Andaman and Nicobar Administration", body_kind="secretariat", department=", ".join(badges[:3]),
            portfolios=badges or None, phone=info.get("phone", ""), email=info.get("email", ""),
            service_year=info.get("service_year"), joined_ut=info.get("joined_ut"),
            dept=_state.dept_key(badges[0]) if len(badges) in (1, 2, 3) and not re.search(r"(?i)chief secretary", post)
            else "administration", src_url=url, src_pos=pos,
            section="Secretaries"))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}:contact", "payload": {"reader": MODULE, "url": URL, "state": "AN", "india_only": True,
                                                     "route": "direct"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "contact", r.content)], "" if recs else "no rows"
