"""Maharashtra: the six Divisional Commissioner offices (revenue divisions) on their S3WaaS sites,
divcom<name>.maharashtra.gov.in, pages "Who's Who" (/en/whos-who/) and "Directory" (/en/directory/). Archive copies 2026-11-05..12:
- divcomnashik: /en/directory/ 4 tables: "Divisional Commissioner Nashik - Officers" (22 rows: Name | Designation | Email | Address
  | Phone), then "Collector Office ...", "CEO Zilla Parishad Office ...", "Municipal Commissioner Office Contact Details of Nashik
  Division" (5-6 rows each: the district heads of the division).
- divcompune: /en/whos-who/ 4 tables (the office 12 rows, Collectors 5, ZP CEOs 5, Municipal Commissioners 6), /en/directory/ 1
  table without names (Designation | Email | Mobile).
- divcomcsn (Chhatrapati Sambhajinagar): /whos-who/ 1 table (12 rows).
- divcomnagpur answers (200) from Mumbai; divcomkonkan and divcomamravati did not resolve (2026-11-13; their sites are not found).
Tables are read with officials.tables (header words), every cell kept in "cells".
Records (dforms/_state.py): rows of the commissioner's own office -> level division (division = the payload's division,
districts from dforms/st_div_mh.json); rows of the Collector / ZP CEO / Municipal Commissioner tables -> level district
(district from the designation or address text, LGD code by name in the division), dept administration / rural_development /
town_body. Route: S3WaaS hosts answer from abroad in general (unchecked for these); seeded "abroad" with the archive copy first.
One queue item = one page (1 GET). Record ids: dept:st_mh_divcom:<division slug>:<page slug>:<table>:<row>.
"""
import re

import officials
from dforms import _esw, _state
import provenance

METHOD = "html table (S3WaaS whos-who / directory)"

M = "st_mh_divcom"
PAGES = [("Nashik", "https://divcomnashik.maharashtra.gov.in/en/whos-who/"),
         ("Nashik", "https://divcomnashik.maharashtra.gov.in/en/directory/"),
         ("Pune", "https://divcompune.maharashtra.gov.in/en/whos-who/"),
         ("Pune", "https://divcompune.maharashtra.gov.in/en/directory/"),
         ("Chhatrapati Sambhajinagar", "https://divcomcsn.maharashtra.gov.in/whos-who/"),
         ("Chhatrapati Sambhajinagar", "https://divcomcsn.maharashtra.gov.in/en/directory/"),
         ("Nagpur", "https://divcomnagpur.maharashtra.gov.in/en/whos-who/"),
         ("Nagpur", "https://divcomnagpur.maharashtra.gov.in/en/directory/")]
MH = {"466": "Ahilyanagar", "467": "Akola", "468": "Amravati", "470": "Beed", "471": "Bhandara", "472": "Buldhana",
      "473": "Chandrapur", "469": "Chhatrapati Sambhajinagar", "488": "Dharashiv", "474": "Dhule", "475": "Gadchiroli",
      "476": "Gondia", "477": "Hingoli", "478": "Jalgaon", "479": "Jalna", "480": "Kolhapur", "481": "Latur", "482": "Mumbai",
      "483": "Mumbai Suburban", "484": "Nagpur", "485": "Nanded", "486": "Nandurbar", "487": "Nashik", "665": "Palghar",
      "489": "Parbhani", "490": "Pune", "491": "Raigad", "492": "Ratnagiri", "493": "Sangli", "494": "Satara", "495": "Sindhudurg",
      "496": "Solapur", "497": "Thane", "498": "Wardha", "499": "Washim", "500": "Yavatmal"}
OLD = {"ahmednagar": "466", "aurangabad": "469", "osmanabad": "488", "sambhajinagar": "469", "gondiya": "476", "buldana": "472"}
DISTRICT_TABLE = [(r"collector", "Collector", "administration"), (r"zilla parishad|\bceo\b|chief executive", "Chief Executive Officer, Zilla Parishad", "rural_development"),
                  (r"municipal", "Municipal Commissioner", "town_body")]


def _k(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def district_in(text, codes):
    """LGD code of the district a text names, among the division's districts (codes) first, then the state; ''."""
    t = _k(text)
    pool = [c for c in codes if c in MH] + [c for c in MH if c not in codes]
    for c in sorted(pool, key=lambda c: (c not in codes, -len(MH[c]))):
        if _k(MH[c]) in t:
            return c
    for old, c in OLD.items():
        if old in t:
            return c
    return ""


def parse(html, division, url):
    div_name, codes = _state.districts_of("MH", division)
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    page = _esw.slug(url.split(host, 1)[-1]) or "home"
    recs = []
    for t in officials.tables(html):
        cap = t.get("caption") or ""
        kind = next(((post, dept) for rx, post, dept in DISTRICT_TABLE if re.search(rx, cap, re.I)), None)
        for row, pos in zip(t["rows"], t["pos"]):
            f = officials.normalise(row)
            desig = f.get("designation", "")
            if not (f.get("name") or desig):
                provenance.skip_row(row, 'skip: not (f.get("name") or desig)')
                continue
            phone = _esw.phones(*[v for h, v in row.items() if re.search(r"(?i)phone|mobile|landline|contact|tel", h)])
            email = _esw.emails(" ".join(v for h, v in row.items() if re.search(r"(?i)e-?mail", h)))
            common = dict(state="MH", post=desig, name=f.get("name", ""), phone=phone, email=email, address=f.get("address", ""),
                          section=cap, cells=row, src_url=url, src_pos=pos, host=host)
            rid = f"{_esw.slug(division)}:{page}:{pos['table']}:{pos['row']}"
            if kind:
                code = district_in(" ".join([desig, f.get("address", ""), email]), codes)
                recs.append(_state.rec(M, rid, level="district", district=MH.get(code, ""), district_code=code,
                                       division=division, districts=[], body=f"{kind[0]}, {MH.get(code, '')}".strip(", "),
                                       body_kind="department", department=kind[0], dept=kind[1], **common))
            else:
                recs.append(_state.rec(M, rid, level="division", division=division, districts=codes,
                                       body=f"Office of the Divisional Commissioner, {division} Division", body_kind="division",
                                       department="Revenue and Forest Department", dept="revenue", **common))
    return recs


def items(get=None):
    return [{"key": f"{M}:{_esw.slug(re.sub(r'^https?://', '', u))}",
             "payload": {"reader": M, "url": u, "division": d, "state": "MH", "india_only": False, "route": "abroad"}}
            for d, u in PAGES]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(M, _esw.slug(re.sub(r"^https?://", "", p["url"])), r.content)]
    recs = parse(r.text, p["division"], p["url"])
    return recs, files, "" if recs else "no tables"
