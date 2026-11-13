"""Ujjain Municipal Corporation (nagarnigamujjain.org/hindi/): its 6 zone offices and the engineers on the "अधिकारी गण" page. Two
pages, one queue item each (payload "kind"); live samples from Mumbai on 2026-11-13, not in archive.s1d.me (the home page also
answers to a US fetch, so the route is probably abroad: unchecked).
- "zones" (/hindi/contact.php): "Our Other Zones", one div.address-card per zone: h5 "Zone - <n>", the address lines, "Phone:".
  A phone of only zeros ("00000000", zones 2 and 5 on 2026-11-13) is a blank: left out. The page names no zone officer and no
  wards (the "झोन/वार्ड" menu links to a Google My Maps map, not read).
- "officers" (/hindi/officer.php): one div.feature-item per officer: h4 = name, p "पद : <post>", a tel: link "मोबाइल : <mobile>"
  (2 executive engineers, 6 assistant engineers, an assistant accounts officer on 2026-11-13). No zone or ward per officer.
  The mobile is the one the card shows; when the card's tel: link dials another number (the last card on 2026-11-13), the
  record says so in "note".
Records: zone offices at level "zone" (post "Zone Office", area "Zone <n>", address, phone; name empty: the office, not a person);
officers at level "body". Hindi names and posts: name without श्री, name_regional as written, post English, post_regional as
written. Record ids: dept:ward3_ujjain:zone-<n>:office, dept:ward3_ujjain:body:<post slug>:<mobile>.
"""
import re

from dforms import _esw, _ward, _ward3_central as c3

METHOD = "html cards"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_ujjain"
BODY, LGD, STATE, DISTRICT = "Ujjain Municipal Corporation", "250851", "MP", "Ujjain"
BASE = "https://nagarnigamujjain.org/hindi"
PAGES = {"zones": f"{BASE}/contact.php", "officers": f"{BASE}/officer.php"}


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "kind": k, "url": u, "state": STATE, "route": "abroad"}}
            for k, u in PAGES.items()]


def parse_zones(html, p):
    seen, recs = set(), []
    for card in _esw.soup(html).select("div.address-card"):
        h = card.find("h5")
        m = re.search(r"(?i)zone\s*-?\s*(\d{1,2})", h.get_text(" ", strip=True) if h else "")
        if not m:
            continue
        z = str(int(m.group(1)))
        lines = [_esw.clean(x.get_text(" ", strip=True)) for x in card.find_all("p")]
        phone = next((re.sub(r"(?i)^phone:\s*", "", x) for x in lines if x.lower().startswith("phone")), "")
        if not re.search(r"[1-9]", phone):
            phone = ""
        addr = ", ".join(x for x in lines if x and not x.lower().startswith(("address", "phone")))
        recs.append(_ward.record(MODULE, f"zone-{z}:office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=f"Zone {z}", zone=f"Zone {z}", post="Zone Office", phone=phone,
                                 address=addr, wing="administration", role="head", source=p["url"],
                                 src_pos=_ward.nth(card, "div.address-card")))
    return recs


def parse_officers(html, p):
    seen, recs = set(), []
    for card in _esw.soup(html).select("div.feature-item"):
        h = card.find("h4")
        post_p = next((x for x in card.find_all("p") if "पद" in x.get_text()), None)
        if not h or not post_p:
            continue
        name = _esw.clean(h.get_text(" ", strip=True))
        post = _esw.clean(re.sub(r"^\s*पद\s*:?", "", post_p.get_text(" ", strip=True)))
        tel = card.find("a", href=re.compile(r"^tel:"))
        mob = c3.phones_in(tel.get_text(" ", strip=True)) if tel else ""
        href = c3.phones_in(tel["href"][-10:]) if tel else ""
        note = f"the tel: link of the card dials {href}" if href and href not in mob else None
        en = c3.post_en(post)
        if re.search(r"प्रभार", post) and "in charge" not in en:
            en += " (in charge)"
        recs.append(_ward.record(MODULE, f"body:{_esw.slug(en)}:{mob.split(',')[0] or len(recs)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="body", area=BODY, post=en, post_regional=post,
                                 name=c3.strip_title(name), name_regional=name, phone=mob, wing=c3.wing(post, en),
                                 note=note, source=p["url"], src_pos=_ward.nth(card, "div.feature-item")))
    return recs


def parse(html, p):
    return parse_officers(html, p) if p.get("kind") == "officers" else parse_zones(html, p)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("kind", "page"), r.content)], "" if recs else "no zone or officer cards"
