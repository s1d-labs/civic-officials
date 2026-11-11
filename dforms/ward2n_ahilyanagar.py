"""Ahilyanagar (Ahmednagar) Mahanagarpalika (amc.gov.in): the head of each of its 4 prabhag samiti (zone) offices. One page per
office, /zone-1/ .. /zone-4/ (WordPress, Marathi; answers from Germany; live sample 2026-11-11 of zone 1; the archive holds only
the home page). Each page has a table "dept_table": विभाग प्रमुखाचे नाव : <name> | पदनाम : <post> ("प्रभारी प्रभाग अधिकारी") |
ई – मेल | मोबाईल क्रं., and an introduction that names the office's areas (zone 1: Savedi and Nagapur). The pages do not list
election wards per office (no "wards" key). Records: level "zone", area "Prabhag Samiti <n>". Record ids:
dept:ward2n_ahilyanagar:ps<n>:ward-officer.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2n_ahilyanagar"
BODY, LGD, STATE, DISTRICT = "Ahilyanagar Mahanagarpalika", "251548", "MH", "Ahilyanagar"
URL = "https://amc.gov.in/zone-{n}/"


def items(get=None):
    return [{"key": f"{MODULE}-zone{n}", "payload": {"reader": MODULE, "url": URL.format(n=n), "state": STATE, "office": n}}
            for n in range(1, 5)]


def parse(html, p):
    soup = _esw.soup(html)
    n = p["office"]
    seen, recs = set(), []
    for t in soup.find_all("table"):
        kv = {}
        for r in _esw.grid(t):
            r = [c for c in r if _esw.clean(c) not in (":", "")]
            if len(r) >= 2:
                kv[_esw.clean(r[0])] = _esw.clean(r[1])
        name = kv.get("विभाग प्रमुखाचे नाव")
        if name is None:
            continue
        post_mr = kv.get("पदनाम", "")
        post = "Ward Officer" + (" (in charge)" if "प्रभारी" in post_mr else "")
        if re.search(r"सहा\w*\s*आयुक्त", post_mr):
            post = "Assistant Commissioner"
        area = f"Prabhag Samiti {n}"
        recs.append(_ward.record(MODULE, f"ps{n}:ward-officer", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=area, zone=area, post=post, post_regional=post_mr, name=name,
                                 name_regional=name or None, phone=_ward.col(kv, "मोबाईल"), email=_ward.col(kv, "मेल"),
                                 vacant=None if name else True, wing="administration", source=p["url"]))
        break
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"zone{p['office']}", r.content)], "" if recs else "no head table"
