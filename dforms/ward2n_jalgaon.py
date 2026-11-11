"""Jalgaon Shahar Mahanagarpalika (jcmc.gov.in): the ward officers (prabhag adhikari) of its 4 prabhag samiti offices. One page per
office, OfficersWardOfficer<n>_M.html (static HTML, Marathi; in archive.s1d.me, saved 2026-11-11). Each page has one two-column
table: नाव (name), कार्यग्रहण दिनांक (date of joining), हुद्दा (post: "प्रभाग अधिकारी (प्रभाग समिती १)" or "सहा -आयुक्त तथा प्रभाग
अधिकारी ..."), कार्यालयीन पत्ता (office address), फोन नंबर (office phone), ईमेल (ward office email), तपशील (duties).
The prabhag samiti pages themselves (prabhag_samiti_<n>_M.html) are empty ("The GAD / EST department is establishing.") and no page
lists the election wards of each office (no "wards" key). Records: level "zone", area "Prabhag Samiti <n>". Record ids:
dept:ward2n_jalgaon:ps<n>:ward-officer.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_jalgaon"
BODY, LGD, STATE, DISTRICT = "Jalgaon Shahar Mahanagarpalika", "276571", "MH", "Jalgaon"
URL = "https://jcmc.gov.in/OfficersWardOfficer{n}_M.html"


def items(get=None):
    return [{"key": f"{MODULE}-ps{n}", "payload": {"reader": MODULE, "url": URL.format(n=n), "state": STATE, "office": n}}
            for n in range(1, 5)]


def parse(html, p):
    soup = _esw.soup(html)
    n = p["office"]
    area = f"Prabhag Samiti {n}"
    seen, recs = set(), []
    for t in soup.find_all("table"):
        kv = {}
        for r in _esw.grid(t):
            if len(r) >= 2:
                kv[_esw.clean(r[0]).rstrip(":- ").strip()] = _esw.clean(r[1])
        name = kv.get("नाव")
        if not name:
            continue
        post_mr = _ward.hi_norm(kv.get("हुद्दा", ""))
        m = re.search(r"प्रभाग\s*समिती\s*(\d)", post_mr)
        if m and int(m.group(1)) != n:
            continue
        post = "Assistant Commissioner and Ward Officer" if re.search(r"सहा\s*-?\s*आयुक्त", post_mr) else "Ward Officer"
        joined = _ward.hi_norm(kv.get("कार्यग्रहण दिनांक (JCMC)", "")) or None
        recs.append(_ward.record(MODULE, f"ps{n}:ward-officer", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=area, zone=area, post=post, post_regional=post_mr, name=name,
                                 name_regional=name, phone=_ward.hi_norm(kv.get("फोन नंबर - एक्स्टेंशन", "")),
                                 email=kv.get("ईमेल", ""), address=_ward.hi_norm(kv.get("कार्यालयीन पत्ता", "")),
                                 joined=joined, wing="administration", source=p["url"]))
        break
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"ps{p['office']}", r.content)], "" if recs else "no officer table"
