"""Solapur Municipal Corporation (www.solapurcorporation.gov.in): the officers of its 8 divisional (ward) offices. One page,
/smc/divisional_office_english.aspx (ASP.NET; answers from Germany; saved in archive.s1d.me 2026-11-05): one "contact-card" per
office with card-name (officer), designation ("Divisional Officer No.2") and a tel: link. The page does not list the prabhags of
each divisional office (Solapur has 26 prabhags), so records have no "wards" key; area = "Divisional Office No. N".
Records: level "zone". Record ids: dept:ward_solapur:div<N>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_solapur"
BODY, LGD, STATE, DISTRICT = "Solapur Municipal Corporation", "251577", "MH", "Solapur"
URL = "https://www.solapurcorporation.gov.in/smc/divisional_office_english.aspx"


def items(get=None):
    return [{"key": f"{MODULE}-divisional-offices", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    for card in soup.find_all("div", class_="contact-card"):
        name = _esw.clean(card.find(class_="card-name").get_text()) if card.find(class_="card-name") else ""
        post = _esw.clean(card.find(class_="designation").get_text()) if card.find(class_="designation") else ""
        phone = " ".join(a.get("href", "")[4:] for a in card.find_all("a", href=re.compile(r"^tel:")))
        email = " ".join(a.get("href", "")[7:] for a in card.find_all("a", href=re.compile(r"^mailto:")))
        m = re.search(r"No\.?\s*(\d+)", post)
        if not m or not (name or phone):
            provenance.skip_row(card, 'skip: not m or not (name or phone)')
            continue
        charge = re.search(r"\(([^)]*charge[^)]*)\)", name)
        name = re.sub(r"\s*\([^)]*charge[^)]*\)", "", name).strip()
        area = f"Divisional Office No. {m.group(1)}"
        recs.append(_ward.record(MODULE, f"div{m.group(1)}:{_esw.slug(name) or 'post'}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=area, zone=area, post=post, name=name, phone=phone,
                                 email=email, wing="administration", charge=charge.group(1) if charge else None, source=p["url"], src_pos=_ward.nth(card)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "divisional-offices", r.content)], "" if recs else "no office cards"
