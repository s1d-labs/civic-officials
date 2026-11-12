"""Odisha: the Collector & District Magistrate and the Superintendent(s) of Police of all 30 districts, from the state portal's
"District Officials" view (odisha.gov.in/en/state-portal-district-officials, Drupal, 30 rows per page, ?page=0..2). Answers only from
India (this box in Germany times out; archive.s1d.me holds page 0 only).

Columns: Sr. No., District (LGD spelling in capitals: ANUGOLA, KATAKA ...), Name, Designation, Mail ID (dm-angul[at]nic[dot]in),
Address, Phone No. The page shows no date. Rows are kept as the page gives them (the Sambalpur SP row carries the designation
"Additional District Magistrate(Revenue)": the post stays as written, the dept follows the e-mail / IPS mark).
One queue item; the reader follows the pager while the page links to the next page (3 GETs today).
Record ids: dept:sub_od_dist:OD-D-<LGD code>:<slug of post>[:n].
"""
import re

from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_od_dist"
URL = "https://odisha.gov.in/en/state-portal-district-officials"
LGD = {"ANUGOLA": "344", "BALANGIR": "345", "BALESHWAR": "346", "BARAGADA": "347", "BHADRAK": "348", "BOUDH": "349", "KATAKA": "350",
       "DEBAGADA": "351", "DHENKANAL": "352", "GAJAPATI": "353", "GANJAM": "354", "JAGATSINGHPUR": "355", "JAJPUR": "356",
       "JHARSUGUDA": "357", "KALAHANDI": "358", "KANDHAMALA": "359", "KENDRAPADA": "360", "KENDUJHAR": "361", "KHORDHA": "362",
       "KORAPUT": "363", "MALKANGIRI": "364", "MAYURBHANJ": "365", "NABARANGPUR": "366", "NAYAGADA": "367", "NUAPADA": "368",
       "PURI": "369", "RAYAGADA": "370", "SAMBALPUR": "371", "SUBARNAPUR": "372", "SUNDARAGADA": "373"}
NAMES = {"JAGATSINGHPUR": "Jagatsinghapur"}         # LGD name where the portal spells it another way
POLICE = re.compile(r"police|\bS\.?\s?P\b", re.I)
MAX_PAGES = 10


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "OD", "india_only": True}}]


def district_name(cap):
    cap = _esw.clean(cap).upper()
    return NAMES.get(cap) or cap.title()


def rows(html, where=None):
    soup = _esw.soup(html)
    out = []
    for t in soup.find_all("table"):
        tp = []
        g = _esw.grid(t, pos=tp)
        if not g or "district" not in " ".join(g[0]).lower():
            continue
        head = [h.lower() for h in g[0]]
        idx = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("district", "name", "designation", "mail", "address", "phone")}
        for r, pos in zip(g[1:], tp[1:]):
            r = r + [""] * (len(head) - len(r))
            out.append({k: (r[i] if i is not None else "") for k, i in idx.items()})
            if where is not None:
                where.append(pos)
    return out


def parse(html, url, seen):
    recs, where = [], []
    for r, pos in zip(rows(html, where), where):
        cap = _esw.clean(r["district"]).upper()
        if cap not in LGD:
            continue
        code, district = LGD[cap], district_name(cap)
        post, mail = _esw.clean(r["designation"]), _esw.emails(r["mail"])
        police = bool(POLICE.search(post)) or mail.startswith("sp") or bool(re.search(r"\bI\.?\s?P\.?\s?S\b", r["name"]))
        base = f"OD-D-{code}:{_esw.slug(re.sub(r'(?i)[, ]+' + re.escape(district) + r'$', '', post)) or 'officer'}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        rec = _esw.record(MODULE, key, dept="police" if police else "administration", level="district", area=district, post=post,
                          name=_esw.clean(r["name"]), phone=_esw.phones(r["phone"], r["address"]), email=mail, address=r["address"],
                          district=district, district_code=code, state="OD", office_id=f"OD-D-{code}", source=url,
                          src_pos=pos)
        if rec[1].get("name"):
            recs.append(rec)
    return recs


def fetch(p, get):
    base = p.get("url", URL)
    recs, files, seen = [], [], set()
    for n in range(MAX_PAGES):
        url = base if n == 0 else f"{base}?page={n}"
        r = get(url)
        if r is None:
            if n == 0:
                return [], [], "no answer"
            break
        files.append(_esw.keep(MODULE, f"page-{n}", r.content))
        got = parse(r.text, url, seen)
        recs += got
        if not got or f"?page={n + 1}" not in r.text:
            break
    return recs, files, "" if recs else "no rows"
