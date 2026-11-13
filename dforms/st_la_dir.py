"""Ladakh: the UT directory (ladakh.gov.in/directory/, DBIM WordPress theme, 2026-11-13).

Source: https://ladakh.gov.in/directory/ (HTML, 141 KB; archive copy of 2026-11-05). One table per section; each table's
wrapper <div class="taxonomy-section" data-params="<base64 {"term_id": N}>"> names the section, and the page's filter
<select> gives the section name of each term id (249 UT Administration, 559 LAHDC Leh, 770 LAHDC Kargil, 772..953 District
Administration Leh / Kargil / Nubra / Changthang / Zanskar / Sham / Drass, 786 Police Headquarters UT Ladakh, 781 Member of
Parliament, 788 Indo-Tibetan Border Police). Columns: Name | Designation | Email | Mobile | Landline No | Address.
Levels: UT Administration, Police Headquarters, MP -> state; LAHDC <x> and District Administration <x> -> district
(district = <x>; Nubra, Changthang, Zanskar, Sham and Drass are districts created in 2024-25 that LGD may not list yet).
ITBP rows (a central force) are kept with level state, body_kind other.
Route: answered from India in the archive; abroad unchecked -> proxy.
Ids: dept:st_la_dir:<term id>:<row in its table>.
"""
import base64
import json
import re

from dforms import _esw, _state

METHOD = "html table"
MODULE = "st_la_dir"
URL = "https://ladakh.gov.in/directory/"


def sections(soup):
    """{term id: section name} from the filter <select>."""
    out = {}
    for o in soup.select("select option"):
        v = (o.get("value") or "").strip()
        if re.fullmatch(r"\d+", v):
            out[v] = _esw.clean(o.get_text())
    return out


def term_of(table):
    d = table.find_parent(attrs={"data-params": True})
    if d is None:
        return ""
    try:
        return str(json.loads(base64.b64decode(d["data-params"] + "==").decode("utf-8", "replace")).get("term_id", ""))
    except Exception:
        return ""


def level_of(section):
    m = re.search(r"(?i)^(?:LAHDC|District Administration)\s+(.+)$", section)
    if m:
        return "district", m.group(1).strip().title()
    return "state", ""


def parse(html, url=URL):
    s = _esw.soup(html)
    names = sections(s)
    out = []
    for t in s.find_all("table"):
        term = term_of(t)
        section = names.get(term, "")
        level, district = level_of(section)
        pos = []
        n = 0
        for row, p in zip(_esw.grid(t, pos=pos), pos):
            if len(row) < 6 or re.fullmatch(r"(?i)name", row[0].strip()):
                continue
            n += 1
            name, post, mail, mob, land, addr = (_esw.clean(c) for c in row[:6])
            kind = ("police" if re.search(r"(?i)police", section) else "other" if re.search(r"(?i)border|parliament", section)
                    else "district" if level == "district" else "secretariat")
            out.append(_state.rec(
                MODULE, f"{term or 'x'}:{n}", state="LA", level=level, district=district, post=post, name=name,
                body=section or "UT Administration of Ladakh", body_kind=kind, department=section or None,
                dept="police" if kind == "police" else None, email=_esw.emails(mail), phone=_esw.phones(mob, land),
                mobile=mob or None, landline=land or None, address=addr, section=section, term_id=term or None, cells=row,
                src_url=url, src_pos=p))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:directory", "payload": {"reader": MODULE, "url": URL, "state": "LA", "india_only": True,
                                                       "route": "proxy"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "directory", r.content)], "" if recs else "no rows"
