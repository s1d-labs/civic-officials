"""Corporation of the City of Panaji (ccpgoa.com, WordPress + Elementor). Panaji has 30 wards and no zones. Two pages (answer from
Germany; archive.s1d.me copies saved 2026-11-07, live check 2026-11-11):
  /ccp-at-your-disposal/     one table SR NO. | SERVICES | PICTURE | NAME | DESIGNATION | PHONE NO.: the staff who handle each service
                             (Sub Registrar, Head Clerk, Municipal Inspectors, Municipal Engineer Gr.I, Revenue Officer, UDCs), and
                             the works supervisor of "Development works in ward No. 1-15" and "ward No. 16-30". One cell can name
                             several people (lines): names and designations pair from the end (6 names, 5 designations: the first
                             name takes the first designation too).
  /sanitation-related-works/ "Contact Sanitary Inspector", name, mobile (an Elementor icon list).
Records: level "ward" when the service names wards (wards = that range), else level "body" (the officer serves all 30 wards).
area = the service as written. Record ids: dept:ward2n_panaji:<page>:<service slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_panaji"
BODY, LGD, STATE, DISTRICT = "Corporation of the City of Panaji", "252071", "GA", "North Goa"
BASE = "https://ccpgoa.com/"
PAGES = ("ccp-at-your-disposal", "sanitation-related-works")
ADDRESS = "Dr Pandurang Pissurlekar Rd, Altinho, Panaji, Goa 403001"


def items(get=None):
    return [{"key": f"{MODULE}-{p}", "payload": {"reader": MODULE, "url": f"{BASE}{p}/", "state": STATE, "page": p}} for p in PAGES]


def _lines(cell):
    return [x.strip() for x in (cell or "").split("|") if x.strip()]


def parse_disposal(html, p, seen):
    recs = []
    for head, rows in _ward.header_tables(html, "services", "designation"):
        for r in rows:
            service = _esw.clean(_ward.col(r, "services").split("|")[0])
            names, posts = _lines(_ward.col(r, "name")), _lines(_ward.col(r, "designation"))
            if not service or not names or service.lower() == "no result":
                continue
            wards = _ward.wards_of(service) if re.search(r"(?i)\bward", service) else []
            phone = _ward.col(r, "phone").replace("|", " ")
            off = max(0, len(names) - len(posts))
            for i, nm in enumerate(names):
                post = posts[max(0, i - off)] if posts else "Staff"
                post = {"R.O": "Revenue Officer", "R.O.": "Revenue Officer"}.get(post, post)
                nm = re.sub(r"(?i)^(shri|smt|mrs|mr|ms)\.?\s+", "", nm)
                if re.search(r"(?i)section$", nm):
                    recs.append(_ward.record(MODULE, f"disposal:{_esw.slug(service)[:60]}:{_esw.slug(nm)}", seen, body=BODY, lgd=LGD,
                                             state=STATE, district=DISTRICT, level="body", area=service, post=f"{post} ({nm})",
                                             phone=phone, address=ADDRESS, source=p["url"], src_pos=r.pos))
                    continue
                recs.append(_ward.record(MODULE, f"disposal:{_esw.slug(service)[:60]}:{_esw.slug(nm)}", seen, body=BODY, lgd=LGD,
                                         state=STATE, district=DISTRICT, level="ward" if wards else "body", area=service,
                                         post=post, name=nm, phone=phone, address=ADDRESS, wards=wards,
                                         wing="engineering" if re.search(r"(?i)development\s*works", service) else None,
                                         source=p["url"], src_pos=r.pos))
    return recs


def parse_sanitation(html, p, seen):
    recs = []
    for ui, ul in enumerate(_esw.soup(html).find_all("ul", class_="elementor-icon-list-items"), 1):
        items_ = [_esw.clean(li.get_text(" ")) for li in ul.find_all("li")]
        if not items_ or not re.match(r"(?i)contact\s+sanitary\s+inspector", items_[0]):
            continue
        name = next((x for x in items_[1:] if not re.search(r"\d{6}", x)), "")
        phone = " ".join(x for x in items_[1:] if re.search(r"\d{6}", x))
        recs.append(_ward.record(MODULE, f"sanitation:sanitary-inspector:{_esw.slug(name)}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="body", area="Sanitation related works", post="Sanitary Inspector",
                                 name=name, phone=phone, address=ADDRESS, source=p["url"],
                                 src_pos={"selector": "ul.elementor-icon-list-items", "index": ui}))
    return recs


PARSERS = {"ccp-at-your-disposal": parse_disposal, "sanitation-related-works": parse_sanitation}


def fetch(p, get):
    page = p.get("page") or next((k for k in PAGES if k in p["url"]), "")
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = PARSERS[page](r.text, p, set())
    return recs, [_esw.keep(MODULE, page, r.content)], "" if recs else "no staff rows"
