"""Malegaon Mahanagarpalika (malegaoncorporation.org): the ward officers of its 4 prabhag (ward) offices. One page per office,
/mmc/ward-office-no-1, -no-2, ward-office-3, -no-4 (Marathi; answers from Germany; live sample 2026-11-11 of no. 1, not in
archive.s1d.me). Each page has one block "नाव: <name> पदनाम: वॉर्ड अधिकारी - १ मोबाईल क्रमांक: +९१ - ... ई-मेल: ..." and two PDF
links (job chart 2025, "प्रभाग 1 माहिती": the RTI 4(1)(b) manual of the office, Unicode text broken; not read). No page lists the
election wards of each office (no "wards" key). Records: level "zone", area "Ward Office <n>". Record ids:
dept:ward2n_malegaon:wo<n>:ward-officer.
"""
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_malegaon"
BODY, LGD, STATE, DISTRICT = "Malegaon Mahanagarpalika", "251438", "MH", "Nashik"
URLS = {1: "https://malegaoncorporation.org/mmc/ward-office-no-1", 2: "https://malegaoncorporation.org/mmc/ward-office-no-2",
        3: "https://malegaoncorporation.org/mmc/ward-office-3", 4: "https://malegaoncorporation.org/mmc/ward-office-no-4"}


def items(get=None):
    return [{"key": f"{MODULE}-wo{n}", "payload": {"reader": MODULE, "url": u, "state": STATE, "office": n}} for n, u in URLS.items()]


def parse(html, p):
    soup = _esw.soup(html)
    n = p["office"]
    t = _ward.hi_norm(soup.get_text(" "))
    m = re.search(r"नाव:\s*(.+?)\s*पदनाम:\s*(.+?)\s*मोबाईल\s*क्रमांक:\s*([+\d\s-]*)\s*ई-मेल:\s*(\S+)", t)
    if not m:
        return []
    name, post_mr, phone, email = (_esw.clean(x) for x in m.groups())
    k = re.search(r"-\s*(\d)", post_mr)
    if k and int(k.group(1)) != n:
        return []
    area = f"Ward Office {n}"
    seen = set()
    phone = re.sub(r"^\+91\s*-\s*", "", phone)
    return [_ward.record(MODULE, f"wo{n}:ward-officer", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone",
                         area=area, zone=area, post="Ward Officer", post_regional=post_mr, name=name, name_regional=name,
                         phone=phone, email=email, wing="administration", source=p["url"])]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"wo{p['office']}", r.content)], "" if recs else "no officer block"
