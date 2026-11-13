"""Kalyan-Dombivli Municipal Corporation (kdmc.gov.in): the 10 ward office pages (प्रभाग कार्यालय 1 अ ... 10 ई,
/kdmc/SectionInformation.html?editForm&rowId=424..433). Each page has one table अ.क्र. | सहाय्यक आयुक्त | संपर्क क्रमांक | तपशिल:
the row of the ward office's assistant commissioner (a name with an honorific, and the office email or phone), and rows of
documents (titles, not people), which are left out.
The server needs TLS unsafe legacy renegotiation (OpenSSL "unsafe legacy renegotiation disabled" otherwise) and sets a session
cookie on a redirect; from dev-vps-3 (Mumbai) it answers with both, 2026-11-13. Not in archive.s1d.me.
Records: one per assistant commissioner, level "zone" (a ward office = prabhag office over several electoral wards; the page
names none: wards_note). depts.py get() retries with LegacyTLS by itself on a renegotiation error. Ids: dept:ward3_kdmc:zone:<rowId>:<n>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"

MODULE = "ward3_kdmc"
BODY, LGD, STATE, DISTRICT = "Kalyan-Dombivli Municipal Corporation", "251483", "MH", "Thane"
BASE = "https://kdmc.gov.in/kdmc/SectionInformation.html?editForm&rowId={}&page="
OFFICES = {424: "1 अ", 425: "2 ब", 426: "3 क", 427: "4 जे", 428: "5 ड", 429: "6 फ", 430: "7 ह", 431: "8 ग", 432: "9 आय", 433: "10 ई"}
PERSON = re.compile(r"^(श्रीमती|श्रीम\.?|श्री\.?|डॉ\.?|कु\.)\s*")


def items(get=None):
    return [{"key": f"{MODULE}-{rid}", "payload": {"reader": MODULE, "url": BASE.format(rid), "office": off, "state": STATE}}
            for rid, off in OFFICES.items()]


def _digits(s):
    return (s or "").translate(str.maketrans("०१२३४५६७८९", "0123456789"))


def parse(html, p):
    seen, recs = set(), []
    rid = re.search(r"rowId=(\d+)", p["url"]).group(1)
    office = p.get("office") or OFFICES.get(int(rid), rid)
    rows = []
    for table in _esw.soup(html).find_all("table"):
        pos = []
        rows += [{"cells": g, "pos": q} for g, q in zip(_esw.grid(table, pos=pos), pos)]
    for d in rows:
        cells = d["cells"]
        if len(cells) < 3:
            continue
        name = _esw.clean(cells[1])
        if not PERSON.match(name):
            continue
        post = "सहाय्यक आयुक्त"
        m = re.search(r"\(([^)]*आयुक्त[^)]*)\)", name)
        if m:
            post, name = _esw.clean(m.group(1)), _esw.clean(name.replace(m.group(0), ""))
        contact = _digits(cells[2])
        email = contact if "@" in contact else ""
        phone = "" if email else contact
        area = f"{office} Ward Office (Prabhag Karyalay)"
        recs.append(_ward.record(MODULE, f"zone:{rid}:{len(recs) + 1}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=area, area_regional=f"{office} प्रभाग कार्यालय", zone=area, post=post,
                                 post_regional=post, name=name, name_regional=name, phone=phone, email=email, role="head",
                                 wing="administration", wards_note="the source names the ward office, not its electoral wards",
                                 source=p["url"], src_pos=d["pos"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (the host needs TLS unsafe legacy renegotiation)"
    files = [_esw.keep(MODULE, f"ward-office-{re.search(r'rowId=(\d+)', p['url']).group(1)}", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p)
    return recs, files, "" if recs else "no assistant commissioner row (the page lists documents only)"
