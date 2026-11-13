"""Sangli-Miraj-Kupwad Shahar Mahanagarpalika (smkc.gov.in): the heads of its 4 ward committee offices ("Municipal Department
(Regional) Offices - 1..4", the offices of Ward Committees 1-4). One page per office, SMKCSection_new.aspx?deptcode=55..58 (ASP.NET,
English; in archive.s1d.me, saved 2026-11-07). Each page has "Officer Details": cards (contact-name, contact-designation,
contact-info) with the "Department Head" (the officer who runs the ward office; post written "Department Head (Ward Officer)")
and the "Office Head" (office superintendent). Every card carries the headquarters email and board number only
(smkcorporation@gmail.com, 0233-2373721 / 22 /23), no own phone. The pages do not list the election wards of each office.
Records: level "zone", area "Ward Committee <n>". Record ids: dept:ward2n_sangli:wc<n>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html cards"
# reader audit (audit.py): the two officer cards are the page's people; the other blocks are the site's service links
# ("दिव्यांग नोंदणी | NEW", "लोकसेवा हक्क अधिनियम | NEW"), no person
AUDIT_LEAVES_OUT = r"\| NEW$"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_sangli"
BODY, LGD, STATE, DISTRICT = "Sangli-Miraj-Kupwad Shahar Mahanagarpalika", "251639", "MH", "Sangli"
URL = "https://www.smkc.gov.in/SMKCSection_new.aspx?deptcode={code}"
OFFICES = {1: 55, 2: 56, 3: 57, 4: 58}
POSTS = {"department head": "Department Head (Ward Officer)", "office head": "Office Head (Office Superintendent)"}


def items(get=None):
    return [{"key": f"{MODULE}-wc{n}", "payload": {"reader": MODULE, "url": URL.format(code=c), "state": STATE, "office": n}}
            for n, c in OFFICES.items()]


def parse(html, p):
    soup = _esw.soup(html)
    n = p["office"]
    # the page's own heading (h1#..._deptName); the side menu names all 4 offices, so the first match on the page is always "- 1"
    head = soup.find(id=re.compile(r"deptName$")) or soup.find("h1")
    m = re.search(r"Regional\)\s*Offices\s*-\s*(\d)", head.get_text(" ") if head else "")
    if m and int(m.group(1)) != n:
        return []
    area = f"Ward Committee {n}"
    seen, recs = set(), []
    for card in soup.select("div.contact-card"):
        name = _esw.clean(card.select_one(".contact-name").get_text(" ")) if card.select_one(".contact-name") else ""
        des = _esw.clean(card.select_one(".contact-designation").get_text(" ")) if card.select_one(".contact-designation") else ""
        if not des:
            continue
        info = card.select_one(".contact-info")
        spans = [_esw.clean(s.get_text(" ")) for s in info.find_all("span")] if info else []
        email = next((s for s in spans if "@" in s), "")
        board = next((s for s in spans if re.match(r"0\d{3}-", s)), "")
        post = POSTS.get(des.lower(), des)
        recs.append(_ward.record(MODULE, f"wc{n}:{_esw.slug(des)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=area, zone=area, post=post, post_as_written=des, name=name, phone=board,
                                 email=email, wing="administration", source=p["url"], src_pos=_ward.nth(card)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"wc{p['office']}", r.content)], "" if recs else "no officer cards"
