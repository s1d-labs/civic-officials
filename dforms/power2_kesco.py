"""KESCO (Kanpur Electricity Supply Company, Kanpur Nagar, UP): the employee directory, kesco.org.in/about/employee-directory.
Works from Germany (live sample 2026-11-11; not in archive.s1d.me). The old name kesco.co.in serves an expired certificate made
for kesco.org.in: use kesco.org.in only. The page shows "Last Updated: 2026-07-27".
One HTML page, one table per department (heading "<department> Department": "Tech.-I" .. "Tech.-IV" = the 11 kV distribution
divisions, "Technical" = the circle with the 33 kV sub-stations, "33 KV & Electrical Safety.", "(Scada Control Center)", "BILLING",
"COMMERCIAL-1st", "METERING-1st", "HQ" ...). Columns: # | Name | Designation | Office | Mobile | Email ("—" = empty). The same rows
repeat as mobile cards below each table: only the tables are read.
Levels from the designation: MD / Director = zone (company head office), Superintending Engineer = circle, Executive Engineer =
division, Assistant Engineer = subdivision, Junior Engineer = section, SSO (33 kV sub-station operator desk, "name" column
"33 KV SUB STATION") = section with no name. Accountants, executive assistants, camp and call desks are left out.
Parents inside one table: an AE row sits under the last EE row, a JE row under the last AE row. About 330 table rows, about
290 records. Record id dept:power2_kesco:<department>:<designation>:<office or name>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, clean, email, phone, raw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power2_kesco"
URL = "https://kesco.org.in/about/employee-directory"
DASH = {"—", "–", "-"}


def level(post):
    p = " " + re.sub(r"[^a-z]+", " ", (post or "").lower()) + " "
    if re.search(r" (md|managing director|director) ", p):
        return "zone"
    if " superintending " in p or p.startswith(" se "):
        return "circle"
    if " executive engineer " in p or re.match(r" (ee|xen) ", p):
        return "division"
    if " assistant engineer " in p or re.match(r" a e ", p) or re.match(r" ae ", p):
        return "subdivision"
    if " junior engineer " in p or re.match(r" (j e|je) ", p) or p.strip() == "sso":
        return "section"
    return None


def _cell(td):
    t = clean(td.get_text(" ", strip=True))
    return None if t in DASH else t


def parse(html, url=URL):
    m = re.search(r"Last\s*Updated\s*:?\s*(\d{4}-\d{2}-\d{2})", html)
    out = Out(MOD, "UP", url, discom="KESCO", last_updated=m.group(1) if m else None)
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        h = t.find_previous(["h2", "h3", "h4"])
        dept = clean(re.sub(r"\s*Department\s*$", "", h.get_text(" ", strip=True))) if h else None
        division = subdivision = None
        circle = "Technical" if dept and dept.lower().startswith("tech.") else None
        for tr in t.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            tds = tr.find_all("td")
            if len(tds) < 6:
                provenance.skip_row(tr, 'skip: len(tds) < 6')
                continue
            name, post, office, mob, mail = (_cell(x) for x in tds[1:6])
            lvl = level(post)
            if not lvl:
                provenance.skip_row(tr, 'skip: not lvl')
                continue
            if (post or "").upper() == "SSO":
                post, name = f"Sub-station Operator ({name})" if name else "Sub-station Operator", None
            area = office or dept
            par = {"circle": circle if lvl in ("division", "subdivision", "section") else None}
            if lvl == "division":
                division, subdivision = area, None
            elif lvl == "subdivision":
                subdivision = area
                par["division"] = division
            elif lvl == "section":
                par.update(division=division, subdivision=subdivision)
            out.add(f"{dept}:{post}:{office or name}", lvl, area, post=post, name=name, phone_=phone(mob), email_=email(mail),
                    district="Kanpur Nagar", parents=par, wing=dept)
    out.src = {}
    return out.recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [raw(MOD, "employee-directory", r.content, "html")], "" if recs else "no rows"
