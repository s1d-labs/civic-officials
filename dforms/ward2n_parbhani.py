"""Parbhani Shahar Mahanagarpalika (pcmcparbhani.org): the Assistant Commissioners who head its 3 prabhag samiti (ward committee)
offices A, B, C. One page per office, /pcmc/assistant-commissioner-ward-committee-a, -b, -c (Marathi + English names; answers
from Germany; live sample 2026-11-11 of A, not in archive.s1d.me). Each page has one block (div.service-content): the name in
English, the name in Marathi, and the post "सहा आयुक्त प्रभाग समिती ' अ '". No phone, email or ward list is given.
(The site also has /pcmc/ward-office-2 and -3 pages; not read.) Records: level "zone", area "Prabhag Samiti A".
Record ids: dept:ward2n_parbhani:ps-<letter>:assistant-commissioner.
"""
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_parbhani"
BODY, LGD, STATE, DISTRICT = "Parbhani Shahar Mahanagarpalika", "251416", "MH", "Parbhani"
URL = "https://pcmcparbhani.org/pcmc/assistant-commissioner-ward-committee-{x}"
LETTERS = {"a": "अ", "b": "ब", "c": "क"}


def items(get=None):
    return [{"key": f"{MODULE}-ps-{x}", "payload": {"reader": MODULE, "url": URL.format(x=x), "state": STATE, "office": x}}
            for x in LETTERS]


def parse(html, p):
    soup = _esw.soup(html)
    x = p["office"]
    box = soup.select_one("div.service-content") or soup
    lines = [_esw.clean(pp.get_text(" ")) for pp in box.find_all("p")]
    lines = [ln for ln in lines if ln]
    post_mr = next((ln for ln in lines if re.search(r"आयुक्त", ln)), "")
    m = re.search(r"प्रभाग\s*समिती\s*'?\s*(अ|ब|क)\s*'?", post_mr)
    if m and m.group(1) != LETTERS[x]:
        return []
    en = next((ln for ln in lines if re.match(r"(?i)(shri|smt|mr|mrs|ms|dr)\b", ln)), "")
    mr = next((ln for ln in lines if re.match(r"(श्रीमती|श्री|सौ|डॉ|कु)\.?", ln)), "")
    if not (en or mr):
        return []
    area = f"Prabhag Samiti {x.upper()}"
    seen = set()
    return [_ward.record(MODULE, f"ps-{x}:assistant-commissioner", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                         level="zone", area=area, area_regional=f"प्रभाग समिती {LETTERS[x]}", zone=area,
                         post="Assistant Commissioner", post_regional=post_mr or None, name=en or mr, name_regional=mr or None,
                         wing="administration", source=p["url"],
                         src_pos={"selector": "div.service-content p" if soup.select_one("div.service-content") else "p",
                                  "lines": [ln for ln in (post_mr, en, mr) if ln]})]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"ps-{p['office']}", r.content)], "" if recs else "no officer block"
