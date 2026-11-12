"""Goa: Directorate of Fire & Emergency Services, "E-Telephone Directory" on dfes.goa.gov.in/overview-functioning/contact-us/
(saved on archive.s1d.me 2026-11-06). One card per officer or station: the director, deputy directors, divisional and assistant
divisional officers (zone in brackets after the name) and each fire station with its Station Fire Officer (officer in charge),
mobile numbers, landline (the station's own numbers, "/101"), and an email written as per[hyphen]fire[dot]goa[at]nic[dot]in.
Station cards sit under a zone heading (North / Central / South Zone). The page has 21 stations and sections, 9 officer cards.
The page shows no date. Record ids: dept:emerg_fire_ga:<slug of the station or post>-<slug of the name>.
"""
import re

from dforms import _emerg, _esw

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_ga"
URL = "https://dfes.goa.gov.in/overview-functioning/contact-us/"
LEVELS = {"director": "state", "deputy director": "state", "divisional officer": "zone", "asst. div. officer": "zone"}


def items(get=None):
    return _emerg.seed(MODULE)


def is_card(cls):
    return bool(cls) and any(c.endswith("-card") or c.startswith("station-") for c in cls)


def card_parts(card):
    """(badge, name, note in brackets, mobiles, landline, email) of one card."""
    badge = _emerg.clean(card.find("div").get_text(" ")) if card.find("div") else ""
    head = card.find(["h4", "h3"])
    note = ""
    name = ""
    if head:
        sm = head.find("small")
        if sm:
            note = _emerg.clean(sm.get_text(" "))
            sm.extract()
        name = _emerg.clean(head.get_text(" "))
    if not note:
        sm = card.find("small")
        note = _emerg.clean(sm.get_text(" ")) if sm else ""
    text = _esw.cell_text(card)
    email = _emerg.emails(_esw.deob(text))
    rest = text
    for t in (badge, name, note):
        rest = rest.replace(t, " ") if t else rest
    rest = _esw.deob(rest)
    rest = re.sub(r"[\w.+-]+@[\w.-]+", " ", rest)
    mobiles = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", rest)
    rest = re.sub(r"(?<!\d)[6-9]\d{9}(?!\d)", " ", rest)
    land = [m.group(0).strip(" |") for m in re.finditer(r"(?:0832[- ]?)?\d{7}(?:\s*/\s*\d{7})*(?:[ /]+\d{7})*(?:\s*/\s*101)?", rest)
            if m.group(0).strip(" |")]
    return badge, name, note.strip("()"), mobiles, land, email


def records(html, url):
    s = _esw.soup(html)
    recs, seen, zone = [], set(), None
    for el in s.find_all(["h3", "div"]):
        if el.name == "h3" and not el.find_parent(class_=is_card):
            t = _emerg.clean(el.get_text(" "))
            if re.fullmatch(r"(?i)(north|south|central)\s+zone", t):
                zone = t.title()
            continue
        if el.name != "div" or not is_card(el.get("class")):
            continue
        badge, name, note, mobiles, land, email = card_parts(el)
        if not badge:
            continue
        station = "station-" in " ".join(el.get("class"))
        if station:
            post = note or "Station Fire Officer"
            addl = bool(re.search(r"(?i)additional\s+charge", post))
            post = "Station Fire Officer" if addl else post
            area, level = badge, ("facility" if re.match(r"(?i)fire\s+station", badge) else "section")
        else:
            post, area = badge.title(), (note or "Goa")
            addl = bool(re.search(r"(?i)additional\s+charge", note))
            area = re.sub(r"(?i)[-–\s]*additional\s+charge", "", area).strip(" -–") or "Goa"
            level = LEVELS.get(badge.lower(), "state")
        key = _emerg.unique(f"{_emerg.slug(area if station else post + ' ' + area)}-{_emerg.slug(name or 'x')}", seen)
        recs.append(_emerg.record(
            MODULE, key, "fire", dept="fire", level=level, area=area, post=post, name=name,
            phone=", ".join(mobiles + land), mobile=", ".join(mobiles), landline=", ".join(land), email=email,
            additional_charge=True if addl else None, zone=zone if station else None, district=None, state="GA",
            office_id=key, source=url))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = records(r.text, url)
    return recs, [_emerg.keep(MODULE, "contact-us", r.content)], "" if recs else "no cards"
