"""Jharkhand: the Civil Surgeon (the district's chief medical officer) and the NHM District Program Manager of every district, from
the "District Team" page of the Jharkhand Rural Health Mission Society (jrhms.jharkhand.gov.in/Home/DistrictTeam, ASP.NET MVC,
one HTML table, no pager, no key). Columns: District Name ("Bokaro (BOK)") | Designation | District Team Name | District Team
Mobile | District Team Email (written dpm[at]gmail[dot]com). 24 districts x 2 posts = 48 rows (2026-11-12, from Mumbai). The
archive holds copies taken through the Indian proxies (2026-11-05); a fetch from abroad is not checked.

Records (depts.py contract): dept health, level district, area = district, post as written ("Civil Surgeon", "District Program
Manager"), name, phone, email, district (LGD name; the page's district code kept as district_site_code).
One queue item = one GET. Ids: dept:health_jh_jrhms:<site code>:<slug of post>[:n].
"""
import re

from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "health_jh_jrhms"
URL = "https://jrhms.jharkhand.gov.in/Home/DistrictTeam"
# site code -> LGD district name (lgd.districts, state 20)
LGD = {"BOK": "Bokaro", "CTR": "Chatra", "DGH": "Deoghar", "DHN": "Dhanbad", "DMK": "Dumka", "JMS": "East Singhbum",
       "GRW": "Garhwa", "GRD": "Giridih", "GDA": "Godda", "GML": "Gumla", "HZB": "Hazaribagh", "JMT": "Jamtara", "KNT": "Khunti",
       "KDM": "Koderma", "LTR": "Latehar", "LHG": "Lohardaga", "PKR": "Pakur", "PLM": "Palamu", "RMG": "Ramgarh", "RNC": "Ranchi",
       "SBJ": "Sahebganj", "SKM": "Saraikela Kharsawan", "SMD": "Simdega", "WSM": "West Singhbhum"}


def parse(html, url=URL):
    s = _esw.soup(html)
    recs, seen = [], set()
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or not re.search(r"(?i)district", " ".join(rows[0])):
            continue
        head = [c.lower() for c in rows[0]]

        def col(rx, row):
            for i, h in enumerate(head):
                if re.search(rx, h) and i < len(row):
                    return row[i]
            return ""
        for row, sp in zip(rows[1:], pos[1:]):
            dist_site = col(r"district name", row)
            m = re.search(r"\(([A-Z]{3})\)", dist_site)
            code = m.group(1) if m else ""
            post, name = col(r"designation", row), col(r"team name|^name", row)
            phone, email = _esw.phones(col(r"mobile|contact", row)), _esw.emails(col(r"email", row))
            if not (name or phone or email):
                continue
            district = LGD.get(code) or re.sub(r"\s*\([A-Z]{3}\)", "", dist_site).strip()
            key = f"{code or _esw.slug(district)}:{_esw.slug(post)}"
            k, n = key, 2
            while k in seen:
                k, n = f"{key}:{n}", n + 1
            seen.add(k)
            recs.append(_esw.record(MODULE, k, dept="health", level="district", area=district, post=post, name=name, phone=phone,
                                    email=email, district=district, district_site=dist_site, district_site_code=code or None,
                                    state="JH", source=url, page=url, src_url=url, src_pos=sp))
    return recs


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "JH", "expected": 48}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_esw.keep(MODULE, "district-team", r.content)], "" if recs else "no rows"
