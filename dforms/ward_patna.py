"""Patna Municipal Corporation (www.pmc.bihar.gov.in): the 6 circle offices (New Capital, Patliputra, Kankarbagh, Bankipur, Patna
City, Azimabad) and the Water Board. One page, /CircleOfficials.aspx (ASP.NET; India only: no answer from Germany on 2026-11-11;
saved in archive.s1d.me 2026-11-05). Each circle: "<Name> Circle [Office]", "Address :...", then "Contact Details" with the posts and their mobile numbers
(Executive Officer; City Manager (sanitation / vehicles); Revenue officer (holding tax); Chief Sanitory Inspector) and the circle
email (written as eo..[at]gmail[dot]com). The page names no officers and does not list the wards of each circle (Patna has 75
wards), so records have a post, a phone, the circle email and no "wards" key.
Records: level "zone" (a circle). Record ids: dept:ward_patna:<circle slug>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_patna"
BODY, LGD, STATE, DISTRICT = "Patna Municipal Corporation", "249650", "BR", "Patna"
URL = "https://www.pmc.bihar.gov.in/CircleOfficials.aspx"
CIRCLE = re.compile(r"((?:New Capital|Patliputra|Kankarbagh|Bankipur|Patna City|Azimabad) Circle(?: Office)?|Water Board)\s+"
                    r"(?:Address\s*:?\s*)?")
POST = re.compile(r"(Executive Officer|City Manager(?: \([^)]*\))?|Revenue officer(?: \([^)]*\))?|"
                  r"Chief Sanitory Inspector(?: \([^)]*\))?)\s*:\s*([\d\s,/-]{10,})", re.I)


def items(get=None):
    return [{"key": f"{MODULE}-circles", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def text_of(html):
    soup = _esw.soup(html)
    for t in soup(["script", "style"]):
        t.decompose()
    return _esw.clean(soup.get_text(" "))


def parse(html, p):
    t = text_of(html)
    i = t.find("Hide this panel")
    t = t[i:] if i >= 0 else t
    t = t[:t.find("Quick Links")] if "Quick Links" in t else t
    marks = list(CIRCLE.finditer(t))
    seen, recs = set(), []
    for k, m in enumerate(marks):
        block = t[m.end():marks[k + 1].start() if k + 1 < len(marks) else len(t)]
        name = m.group(1).replace(" Office", "")
        address = _esw.clean(re.split(r"Contact Details", block)[0]).strip(" :")
        email = _esw.emails(block)
        posts = POST.findall(block)
        if name == "Water Board":
            ph = re.search(r"Contact Details\s*([\d\s,/-]{10,})", block)
            posts = [("Water Board office", ph.group(1))] if ph else []
        for post, phone in posts:
            recs.append(_ward.record(MODULE, f"{_esw.slug(name)}:{_esw.slug(post)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=name, zone=name, post=_esw.clean(post),
                                     phone=phone.strip(), email=email, address=address, source=p["url"],
                                     src_pos={"selector": "page text", "block": m.group(0), "match": f"{post} {phone}".strip()[:200]}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "circles", r.content)], "" if recs else "no circle offices"
