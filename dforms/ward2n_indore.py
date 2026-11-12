"""Indore Municipal Corporation (imcindore.mp.gov.in): its 22 zonal offices and their staff. One page, /contact (Next.js + Strapi;
answers from Germany; live sample 2026-11-11, not in archive.s1d.me: the archive holds only the home page). The page data sits in
the __NEXT_DATA__ JSON: attributes.zonalOfficersCard = one card per zone ("ZONAL OFFICE 01"), its description holds lines
"Zonal Office Name:- <name> Zone", "Wards Details:- 7,9,10 and16", "Contact - Zonal Office:- <phone>", "Zonal Officer Name:- <name>
- <mobile>", "CSI Health:- <mobile>" (the Chief Sanitary Inspector: the page gives the mobile only), "Asst. Revenue Officer:- <name>
- <mobile>". Records: level "zone", per zone the zone office, the Zonal Officer (head), the CSI Health and the Asst. Revenue Officer,
each with the zone's wards (85 wards in 22 zones). Record ids: dept:ward2n_indore:zone-<nn>:<post slug>.
"""
import json
import re

from dforms import _esw, _ward

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_indore"
BODY, LGD, STATE, DISTRICT = "Indore Municipal Corporation", "250901", "MP", "Indore"
URL = "https://imcindore.mp.gov.in/contact"
LINES = (("zone", r"zonal\s*office(\s*name)?"), ("wards", r"wards?\s*details?"), ("office", r"contact\s*-?\s*zonal\s*office"),
         ("officer", r"zonal\s*officer(\s*name)?"), ("csi", r"c\.?\s?s\.?\s?i\.?\s*health"),
         ("aro", r"asst\.?\s*revenue\s*officer|assistant\s*revenue\s*officer"))
POSTS = {"officer": "Zonal Officer", "csi": "Chief Sanitary Inspector (Health)", "aro": "Assistant Revenue Officer"}


def items(get=None):
    return [{"key": f"{MODULE}-contact", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def fields(desc):
    out = {}
    for ln in (desc or "").splitlines():
        m = re.match(r"\s*(.+?)\s*:\s*-?\s*(.*)$", ln)
        if not m:
            continue
        label = m.group(1).strip(" -")
        for k, rx in LINES:
            if k not in out and re.fullmatch(rf"(?i){rx}", _esw.clean(label)):
                out[k] = _esw.clean(m.group(2)).strip(" -")
                break
    return out


def name_phone(v):
    """"Mr. Vinod Agrawal - 7440443421" -> (name, phone); a value that is only digits is a phone."""
    v = _esw.clean(v)
    if not re.search(r"[A-Za-zऀ-ॿ]", v):
        return "", v
    m = re.match(r"(.*?)\s*-?\s*((?:\+?91[\s-]*)?\d[\d\s/,-]{5,})?$", v)
    return _esw.clean(m.group(1)).strip(" -"), (m.group(2) or "")


def cards(html):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return [], None
    a = json.loads(m.group(1))["props"]["pageProps"]["data"]["data"]["attributes"]
    return a.get("zonalOfficersCard") or [], (a.get("updatedAt") or "")[:10] or None


def parse(html, p):
    seen, recs = set(), []
    cs, updated = cards(html)
    for c in cs:
        mc = c.get("MunicipalContent") or {}
        num = re.search(r"\d+", mc.get("title") or "")
        f = fields(mc.get("description"))
        if not num or not f.get("zone"):
            continue
        nn = f"{int(num.group(0)):02d}"
        zname = f"Zone {nn}: {f['zone']}"
        wards = _ward.wards_of(f.get("wards", ""))
        common = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=zname, zone=zname, wards=wards,
                      source=p["url"], last_updated=updated, office_id=f"zone-{nn}")
        if f.get("office"):
            recs.append(_ward.record(MODULE, f"zone-{nn}:zone-office", seen, post="Zonal Office", phone=f["office"],
                                     wing="administration", **common))
        for k, post in POSTS.items():
            if k not in f:
                continue
            name, phone = name_phone(f[k])
            if not (name or phone):
                continue
            recs.append(_ward.record(MODULE, f"zone-{nn}:{_esw.slug(post)}", seen, post=post, name=name, phone=phone,
                                     wing="health" if k == "csi" else None, **common))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contact", r.content)], "" if recs else "no zonal offices in the page data"
