"""EPFO (Employees' Provident Fund Organisation) offices and officers: the one public page www.epfo.gov.in/directory/ (about
3.5 MB, 300 office tabs: head office, 21 zone offices, about 155 regional offices, about 109 district offices, training institutes,
vigilance and audit). Each tab ("tab-content" with id zoneN / sub_zone-N-N / district-N-N-N ...) has an office card (office name,
address, email, "STD Code: 0877") and a staff table "Name | Designation | Contact" (contact = phone + email).
One record per officer: dept "social_security" (new key), level zone / division (regional office) / district (district office) /
state (head office) / body (training institutes, data centre), area = office name, post = designation, name, phone (the STD code
of the office put before a number that has none), email, address. Plus one record per office (post "Office") with the card's
email and address. Record ids dept:central_social_security:epfo:<tab id>[:<officer slug>]. The page answers only from India
(epfindia.gov.in and epfo.gov.in gave 403 to this box in Germany, 2026-11-11), so the seed item is india_only.
ESIC (esic.gov.in) gave no answer from Germany or India (2026-11-11); not read.
"""
import json
import re
from pathlib import Path

from dforms import _esw

MODULE = "central_social_security"
TITLE = re.compile(r"^(?:(?:shri|smt|sri|sh|mr|mrs|ms|dr|km|kumari)(?:\.\s*|\s+))+", re.I)
LEVEL = (("district-", "district"), ("sub_zone-", "division"), ("zone", "zone"), ("head-office", "state"))


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def level_of(tab):
    for pre, lvl in LEVEL:
        if re.match(rf"^(?:vigilance-|audit-|national-data-centre-)?{pre}", tab):
            return lvl
    return "body"


def phone(v, std):
    v = _esw.clean(v)
    out = []
    for x in re.split(r"[,/]", v):
        x = x.strip()
        d = re.sub(r"\D", "", x)
        if len(d) < 6:
            continue
        out.append(f"{std}-{x}" if std and 6 <= len(d) <= 8 and not d.startswith("0") else x)
    return ", ".join(out) or None


def card_of(tab):
    card = tab.select_one(".office-card-accordion")
    if not card:
        return {}
    st = card.find("strong")
    adr = card.select_one(".office-address")
    txt = _esw.clean(card.get_text(" "))
    std = re.search(r"STD Code:\s*(0\d{2,5})", txt)
    return {"office": _esw.clean(st.get_text(" ")) if st else "", "address": _esw.clean(adr.get_text(" ")) if adr else "",
            "email": _esw.emails(txt), "std": std.group(1) if std else None}


def records(html, url, p):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for tab in soup.select("div.tab-content[id]"):
        tid = tab["id"]
        tables = [t for t in tab.find_all("table") if t.find_parent("div", class_="tab-content") is tab]
        if not tables:
            continue
        c = card_of(tab)
        office = c.get("office") or tid
        lvl = level_of(tid)
        recs.append(_esw.record(MODULE, f"epfo:{tid}", dept="social_security", level=lvl, area=office, post="Office",
                                email=c.get("email"), address=c.get("address"), std_code=c.get("std"), state=p.get("state"),
                                office_id=tid, source=url, agency="EPFO", kind="office"))
        for t in tables:
            for tr in t.select("tbody tr") or t.find_all("tr")[1:]:
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                raw = _esw.clean(tds[0].get_text(" "))
                name = TITLE.sub("", raw).strip()
                charge = None
                m = re.search(r"\(([^)]*charge[^)]*)\)\s*$", name, re.I)
                if m:
                    charge, name = m.group(1), name[:m.start()].strip()
                if not name or name.lower() in ("vacant", "-"):
                    continue
                post = _esw.clean(tds[1].get_text(" "))
                ph, em = None, None
                if len(tds) > 2:
                    em = _esw.emails(tds[2].get_text(" "))
                    tel = " ".join(_esw.clean(x.get_text(" ")) for x in tds[2].select(".contact-row") if not x.select_one(".dir-email"))
                    ph = phone(tel or re.sub(r"\S+@\S+", " ", tds[2].get_text(" ")), c.get("std"))
                k = f"epfo:{tid}:{_esw.slug(name)}"
                n, key = 1, k
                while key in seen:
                    n += 1
                    key = f"{k}-{n}"
                seen.add(key)
                recs.append(_esw.record(
                    MODULE, key, dept="social_security", level=lvl, area=office, post=post, name=name, charge=charge,
                    phone=ph, email=em, address=c.get("address"), state=p.get("state"), office_id=tid, source=url,
                    agency="EPFO", kind="officer"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "epfo-directory", r.content)]
    recs = records(r.text, p["url"], p)
    return recs, files, "" if recs else "no office tabs"
