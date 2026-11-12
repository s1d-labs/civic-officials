"""Telangana: chairpersons and vice chairpersons (mayors / deputy mayors of the corporations) elected by the councils after the
2026 municipal poll, from each body's own site on the CDMA platform, <town>municipality.telangana.gov.in/pages/chairman-details.
The State Election Commission (tsec.gov.in knowPRUrban.do) lists ward members only ("Know Your": Ward Member).
Page: table "Sno | Name | Designation | Photo | Mobile" (Chairman, Vice Chairman), read with dforms/ulb2_tg.parse_cdma. The page
shows no date; on Adilabad (2026-11-12) both heads are 2026 ward winners (Anusha Bandari, ward 45; Mohammad Rohith, ward 44).
One queue item = one body, made from seeds/councillors_cp_tg.json (same hosts as the council pages): payload
{"kind": "form-tg_heads", "state": "TG", "url" (chairman-details), "body", "lgd_code", "slug"}. The own ward is not on the page:
the loader can find it by name among the body's 2026 ward winners (councillor:TG:<slug>:<ward>).
Record id councillor:TG:head:<slug>:<chair|vice>.
"""
import re

from dforms import ulb2_tg

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

ELECTION = "Telangana 2026 (municipal poll 2026; heads elected by the councils), as listed on the body's website"
POSTS = [(r"deputy\s*mayor", "vice", "Deputy Mayor"), (r"vice\s*-?\s*chair", "vice", "Vice Chairperson"),
         (r"\bmayor\b", "chair", "Mayor"), (r"chair\s*(?:man|person)?", "chair", "Chairperson")]


def post_of(t):
    for rx, key, pos in POSTS:
        if re.search(rx, t or "", re.I):
            return key, pos
    return None


def parse(html, p, url):
    recs = {}
    for _, o in ulb2_tg.parse_cdma(html, dict(p, url=url, page="chairman-details")):
        hit = post_of(o.get("post"))
        if not hit or not o.get("name"):
            continue
        key, pos = hit
        d = {"type": "councillor", "state": "TG", "body": p.get("body"), "lgd_code": p.get("lgd_code"), "ward_no": key,
             "position": pos, "position_local": o.get("post"), "name": o.get("name"), "phone": o.get("phone"),
             "email": o.get("email"), "election": ELECTION, "indirect": True, "url": url, "src_url": url,
             "src_pos": o.get("src_pos"), "own_ward_record_prefix": f"councillor:TG:{p.get('slug')}:" if p.get("slug") else None}
        recs.setdefault(f"councillor:TG:head:{p.get('slug') or p.get('lgd_code')}:{key}",
                        {k: v for k, v in d.items() if v not in (None, "")})
    return list(recs.items())


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p, p["url"])
    return recs, [], "" if recs else "no head on chairman-details"


def items(get=None):
    import json
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    for it in json.load(open(os.path.join(here, "seeds", "councillors_cp_tg.json"), encoding="utf-8")):
        q = it["payload"]
        host = re.match(r"https?://[^/]+", q["url"]).group(0)
        if "municipality.telangana.gov.in" not in host and "corporation.telangana.gov.in" not in host:
            continue
        out.append({"key": "tg-heads-" + (q.get("slug") or q.get("lgd_code")),
                    "payload": {"kind": "form-tg_heads", "state": "TG", "url": host + "/pages/chairman-details",
                                "body": q.get("body"), "lgd_code": q.get("lgd_code"), "slug": q.get("slug"),
                                "guessed": q.get("guessed")}})
    return out
