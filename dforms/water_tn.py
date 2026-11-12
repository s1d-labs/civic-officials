"""Tamil Nadu: Tamil Nadu Water Supply and Drainage Board (TWAD) engineer offices, www.twadboard.tn.gov.in/engineer-details/<rank>
(answers only from India). Drupal view pages: executive-engineer ?page=0..8 (about 85 divisions), superintending-engineer ?page=0..1
(about 15 circles), chief-engineer (4 regions). One queue item per page. Each office is a block: <h3> "Executive Engineer ,Project
Division , Karur", address lines, "Pincode :", "Phone Number :", "City :", "Email :", "Fax Number :". No officer names, no date.
Level from the rank (EE = division, SE = circle, CE = zone). Area = the place part of the post.
Record ids: dept:water_tn:TN-TWAD-<slug of post>.
"""
import re

from dforms import _esw, _water

METHOD = "html cards (div.officer_block)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_tn"
BASE = "https://www.twadboard.tn.gov.in/engineer-details/"
PAGES = {"executive-engineer": 9, "superintending-engineer": 2, "chief-engineer": 1}
LEVEL = {"executive-engineer": "division", "superintending-engineer": "circle", "chief-engineer": "zone"}
ORG = "Tamil Nadu Water Supply and Drainage Board"


def items(get=None):
    out = []
    for rank, n in PAGES.items():
        for i in range(n):
            url = BASE + rank + (f"?page={i}" if n > 1 else "")
            out.append({"key": f"{MODULE}-{rank}-{i}", "payload": {"reader": MODULE, "url": url, "rank": rank, "state": "TN",
                                                                  "india_only": True}})
    return out


def field(body, label):
    for p in body.find_all("p"):
        t = _esw.clean(p.get_text(" "))
        if t.lower().startswith(label.lower()):
            return t.split(":", 1)[1].strip() if ":" in t else ""
    return ""


def parse(html, url, rank="executive-engineer"):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for bn, blk in enumerate(soup.select("div.officer_block"), 1):
        h = blk.find("h3")
        if not h:
            continue
        post = re.sub(r"\s*,\s*", ", ", _esw.clean(h.get_text(" ")))
        addr = blk.select_one(".officer_addres")
        address = re.sub(r"(\s*,)+", ",", _esw.cell_text(addr).replace(" | ", ", ")).strip(" ,") if addr else ""
        pin = field(blk, "Pincode")
        if pin and pin not in address:
            address = f"{address} - {pin}" if address else pin
        city = field(blk, "City")
        area = re.sub(r"(?i)^TWAD Board\s*,\s*", "", _water.area_after(post)) or city
        title = post.split(",")[0].strip()
        key = _water.unique(f"TN-TWAD-{_esw.slug(post)}", seen)
        recs.append(_esw.record(MODULE, key, dept="water", level=LEVEL.get(rank) if _water.level_of(title) == "state" else _water.level_of(title), area=area,
                                post=title, phone=_esw.phones(field(blk, "Phone Number")), email=_esw.emails(field(blk, "Email")),
                                address=address, state="TN", city=city, office_id=key, org=ORG, office=post, source=url,
                                src_pos={"selector": "div.officer_block", "block": bn}))
    return recs


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    m = re.search(r"page=(\d+)", url)
    files = [_esw.keep(MODULE, f"{p.get('rank', 'executive-engineer')}-{m.group(1) if m else 0}", r.content)]
    recs = parse(r.text, url, p.get("rank", "executive-engineer"))
    return recs, files, "" if recs else "no rows"
