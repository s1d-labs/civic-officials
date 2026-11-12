"""Kerala: Kerala Water Authority office directory, kwa.kerala.gov.in/en/contact-us/ (answers from Germany and India).

One GET (about 440 KB). The first table ("Office / Designation | Office / Designation | Phone | Mobile | eMail") lists every office of
the KWA in blocks: a heading row (second cell empty: "HEAD OFFICE", "PH Circle, Kottayam", "Project Division, Kottayam") and then
one row per post ("Superintending Engineer,PH Circle, Kottayam", "AEE, PH Sub Dn., Kottayam", "AE,WW Section No.I, Kottayam", "AE - I")
with phone, mobile and email. No officer names. The two other tables (sewerage and section staff mobiles) are left out. The page
shows "Last updated at DD-MM-YYYY". About 900 posts. One queue item.
Level from the post (_water.level_of), else from the block heading. Area = the place part of the post, else the block heading.
Record ids: dept:water_kl:KL-KWA-<slug of block>:<slug of post>.
"""
import re

from dforms import _esw, _water

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water_kl"
URL = "https://kwa.kerala.gov.in/en/contact-us/"
ORG = "Kerala Water Authority"


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "KL"}}]


def updated(html):
    m = re.search(r"Last updated at\s*(\d{2})-(\d{2})-(\d{4})", html)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def parse(html, url=URL):
    soup = _esw.soup(html)
    t = next((t for t in soup.find_all("table") if "Office / Designation" in t.get_text(" ")), None)
    if t is None:
        return []
    last = updated(html)
    recs, seen, block = [], set(), "HEAD OFFICE"
    for row in _esw.grid(t)[1:]:
        if len(row) < 5:
            continue
        head, post, phone, mobile, mail = row[0], row[1].lstrip("• ").strip(), row[2], row[3], row[4]
        if not post:                         # block heading
            block = head
            post = head
        ph = _esw.phones(phone, mobile)
        em = _esw.emails(mail)
        if not (ph or em):
            continue
        area = _water.area_after(post) or block
        level = _water.level_of(post, _water.level_of(block, "state"))
        key = _water.unique(f"KL-KWA-{_esw.slug(block)}:{_esw.slug(post)}", seen)
        recs.append(_esw.record(MODULE, key, dept="water", level=level, area=area, post=post, phone=ph, email=em, state="KL",
                                office_id=f"KL-KWA-{_esw.slug(post if _water.area_after(post) else block)}", org=ORG, block=block if block != area else None,
                                source=url, last_updated=last))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "contact-us", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
