"""Goa: South Goa district site, southgoa.nic.in/municipalities/ (S3WAAS page, "Last Updated: 22.03.2021").

One table: Name ("Municipal Council Canacona"), Address ("Chief Officer, Canacona Municipal Council"), Phone No (office landline).
7 municipal councils of South Goa (Canacona, Cuncolim, Sanguem, Curchorem-Cacora, Quepem, Mormugao, Margao). The address cell names the
post, not the person, so each record is the Chief Officer's post (role head) with the office phone and no name. A row whose address
does not name a chief officer gives no record. Answers from outside India (checked 2026-11-11 from Germany: 200).
Goa has no statewide list in reach: dma.goa.gov.in has no DNS record (2026-11-11, also from India); northgoa.gov.in's municipality
cards give address and website only; goaulbservice.gov.in shows staff and elected members only inside a per-town session (the archive
copies of AbtStaff.aspx and ElectedMembers.aspx are an error page). District: the South Goa site lists bodies that LGD now puts in
South Goa or Kushavati, so the record gives no district (civic-india sql/87 ties by the name in the state).
"""
import re

from dforms import _esw, _ulb

MODULE = "ulb_ga"
URL = "https://southgoa.nic.in/municipalities/"
CO = re.compile(r"(?i)\bchief\s*officer\b")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "GA", "india_only": False}}]


def updated(html):
    m = re.search(r"Last\s*Updated\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", _esw.clean(_esw.soup(html).get_text(" ")))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def parse(html, url=URL):
    recs, seen = [], set()
    up = updated(html)
    for t in _esw.soup(html).find_all("table"):
        rows = _esw.grid(t)
        if not rows or not any(re.search(r"(?i)phone", h) for h in rows[0]):
            continue
        head = [h.lower() for h in rows[0]]
        ix = {k: next((i for i, h in enumerate(head) if re.search(rx, h)), None)
              for k, rx in (("name", r"name"), ("addr", r"address"), ("phone", r"phone"))}
        for row in rows[1:]:
            cell = lambda k: _esw.clean(row[ix[k]]) if ix[k] is not None and ix[k] < len(row) else ""   # noqa: E731
            body, addr, phone = cell("name"), cell("addr"), cell("phone")
            if not body or not CO.search(addr) or not phone:
                continue
            recs.append(_ulb.record(MODULE, "GA", body, "Chief Officer", seen, phone=phone, body_type="Municipal Council", source=url,
                                    last_updated=up, address=addr))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "municipalities", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
