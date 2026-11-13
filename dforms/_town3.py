"""Shared parts of the town office staff readers for the towns' own websites (dforms/town3_<template>.py, 2026-11-13).

Most town bodies outside the state platforms (dforms/town2_*.py) have no staff list in DB civic. Many of them have their own
website, made by a local vendor (np<town>.in, npp<town>.com, <town>municipality.in, <town>nac.in, mc<town>.in ...). There is no
statewide list of these websites. dforms/town3_sites.json was made once on dev-vps-3 (2026-11-13):
  1. for each town of LGD with no staff in DB civic (UP, RJ, MH, OD, GJ, PB, HR, MP, HP, BR, JH, UK), the usual host names of
     its state were resolved in DNS (np<name>.in, npp<name>.com, <name>municipality.in, <name>nac.in, mc<name>.in, Odisha
     spellings such as Jeypore for Jayapur ...; 20,579 names, 440 answered);
  2. one GET of each home page (300 hosts), then at most two GETs of its staff / employee / officer / contact pages
     (links found by their text), 2.5 s apart;
  3. a site is kept when one of these pages has a staff table (staff_rows below), the site names the same town and district
     as LGD, and the table is the town's own (a page that copies the staff of another town is left out).
Sites per template: town3_od_aspx (Odisha ASP.NET vendor), town3_od_wp (Odisha WordPress theme), town3_od_cards (Odisha
WordPress theme with "Staff Position" cards: card_rows), town3_own (other own sites: PHP / HTML / ASP.NET pages of single
vendors). seeds/town3_found_sites.json lists every (LGD code, host) that answered in DNS and what became of it ("read: <reader>",
"left out: <why>", "MahaULB town site: no TCP answer ...", "no staff table on the staff pages read", parked, HTTP errors).

staff_rows(html) = _town2.staff_rows with more column words: Hindi (अधिकारी / कर्मचारी का नाम, पद का नाम, पदनाम, मोबाईल,
संपर्क सूत्र, ई.मेल), Gujarati (નામ, હોદ્દો), Odia (ନାମ, ପଦବୀ), "Staff Name", and a section column (Section, Branch,
Department, शाखा) that fills the row's section. Rows named "test" (vendor placeholder rows) are counted as skipped, so are names
of dots ("श्री ......"); a post "-" takes the section (शाखा) as its post. role():
_ulb.role_of, "head" only when the whole post names the head (Executive Officer, E.O, Commissioner, Chief Officer, Secretary,
Administrator, अधिशासी अधिकारी, ચીફ ઓફિસર); Odisha "C.O." (Community Organiser) and "D.E.O." (Data Entry Operator) are staff;
Hindi उपयंत्री (sub-engineer) is staff, not a deputy.

fetch(): the known staff pages of the item first (payload "pages", at most 2). When they give no row, the home page (payload
"url") and up to 3 - (requests made) of its staff links. At most 3 requests per site. The same post + name on two pages of a
site is one record (the second is counted "same row twice").
Records: _town2.record (dept town_body, level body, area = the LGD body name, lgd_code, role, section, phone, email); the id
parts keep Hindi, Gujarati and Odia letters (uslug), so a Hindi row has an id of its own that does not depend on its order.
"""
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse

import provenance
from dforms import _esw, _town2

COLS = {
    "name": re.compile(r"(?i)^(name|officer'?s?\s*name|employee\s*name|staff\s*name|name\s*of\s*(the\s*)?(officers?|employees?|staff|official))\b|"
                       r"^नाम|(अधिकारी|कर्मचारी)\s*(/\s*कर्मचारी\s*)?(का\s*)?नाम|नाम\s*कर्मचारी|નામ|ନାମ|ಹೆಸರು"),
    "post": re.compile(r"(?i)^(designation|post|rank)\b|^पद|हुद्दा|^હોદ્દો|ପଦବୀ|ಹುದ್ದೆ"),
    "phone": re.compile(r"(?i)contact|mobile|phone|cell|मोबा[इई]ल|फोन|संपर्क|सम्पर्क|મોબા[ઇઈ]લ|ફોન|ମୋବାଇଲ"),
    "email": re.compile(r"(?i)e-?\s?mail|ई\s*[-.]?\s*मेल|ઇ-?મેલ"),
    "section": re.compile(r"(?i)^(section|branch|department|dept\.?)\b|शाखा|विभाग|શાખા|ବିଭାଗ"),
}
PLACEHOLDER = re.compile(r"(?i)^(test|demo|abc|xyz)$")
DOTS = re.compile(r"(?i)^\s*(श्री(मती)?|sri|shri|smt|mr|mrs|ms)?\.?\s*[.\-–—_*]{3,}\s*$")
AVATAR = re.compile(r"^[A-Z]\s*\|\s*(?=\S)")        # mcpalwal.in: "M | Manoj Kumar" (the letter of a round avatar, then the name)
HEAD = re.compile(r"ચીફ\s*ઓફ[િી]સર|મુખ્ય\s*અધિકારી|ମୁଖ୍ୟ\s*ଅଧିକାରୀ|ନିର୍ବାହୀ\s*ଅଧିକାରୀ")
HEAD_POST = re.compile(r"(?i)^\s*(executive\s*officer|e\.?\s?o\.?|commissioner|municipal\s*commissioner|chief\s*officer|chief\s*municipal\s*officer|"
                       r"c\.?\s?m\.?\s?o\.?|secretary|administrator|sub-collector.*administrator)\s*$|अधिशासी\s*अधिकारी|मुख्य\s*नगर\s*पालिका\s*अधिकारी")
NOT_DEPUTY = re.compile(r"^उपयंत्री|^उप\s*यंत्री|^उप\s*अभियंता")             # sub-engineer, not a deputy of the head
LINK = re.compile(r"(?i)staff|employee|officers?\b|official|directory|administration|who.?s.?who|section|कर्मचारी|अधिकारी|કર્મચારી|સ્ટાફ|contact|"
                  r"संपर्क|सम्पर्क|સંપર્ક")
NOT_LINK = re.compile(r"(?i)login|tender|holding|incumbency|message|msg|ward|chair|president|\.pdf$|mailto:|tel:|javascript:")
SITES_FILE = Path(__file__).with_name("town3_sites.json")


def uslug(s):
    """A slug that keeps the letters, vowel signs and digits of every script ("अधिशासी अधिकारी" -> "अधिशासी-अधिकारी"), lower case."""
    t = "".join(c if unicodedata.category(c)[0] in "LMN" else "-" for c in _esw.clean(s).lower())
    return re.sub(r"-+", "-", t).strip("-")


def sites(module):
    """The sites of one reader from dforms/town3_sites.json."""
    return [s for s in json.loads(SITES_FILE.read_text(encoding="utf-8")) if s["reader"] == module]


def items(module, SITES):
    out = []
    for s in SITES:
        p = {"reader": module, "url": s["home"], "site": s["site"], "body": s["body"], "lgd_code": s["lgd_code"],
             "district": s["district"], "state": s["state"], "pages": s["pages"], "india_only": True, "route": "direct"}
        out.append({"key": f"{module}-{s['site']}", "payload": p})
    return out


def staff_rows(html):
    out = []
    for r in _town2.staff_rows(html, COLS):
        r["name"] = AVATAR.sub("", r["name"])
        if PLACEHOLDER.match(r["name"]):
            provenance.skipped("placeholder row")
            continue
        if DOTS.match(r["name"]):            # "श्री ................." (a form row left empty)
            provenance.skipped("no name")
            continue
        if _town2.NO_NAME.match(r["post"]):   # "-": the branch is the post, as _town2 does for an empty post
            if not r["section"]:
                provenance.skip_row(r["cells"], "no post")
                continue
            r["post"] = r["section"]
        out.append(r)
    return out


def card_rows(html):
    """[{section, name, post, phone, email, cells, pos}] of the "Staff Position" cards of the Odisha municipal WordPress theme:
    <div class="single-author staff-position"> with <p class="author-name">, <p class="deg"> and <p class="cont">Contact No.:
    ...</p>. pos = {"card": n} (1-based, page order)."""
    out = []
    for i, c in enumerate(_esw.soup(html).select("div.staff-position"), 1):
        f = {k: _esw.clean(x.get_text(" ")) if (x := c.select_one(f"p.{k}")) else "" for k in ("author-name", "deg", "cont")}
        name, post, phone = f["author-name"], f["deg"], re.sub(r"(?i)^contact\s*no\.?\s*:?\s*", "", f["cont"])
        if not post:
            provenance.skip_row([name, post, phone], "no post")
            continue
        if _town2.NO_NAME.match(name) or _town2.VACANT.search(name):
            provenance.skipped("no name" if _town2.NO_NAME.match(name) else "vacant post")
            continue
        out.append({"section": "", "name": name, "post": post, "phone": phone, "email": "", "cells": [name, post, f["cont"]],
                    "pos": {"card": i}})
    return out


def role(post, role, state):
    """_ulb.role_of, with three corrections for these sites: the Gujarati / Odia head posts are head; "head" only when the whole
    post names the head (role_of also takes "C.O." = Community Organiser, "D.E.O." = Data Entry Operator, "Peon to E.O");
    Hindi उपयंत्री (sub-engineer) is staff, not a deputy."""
    if HEAD.search(post):
        return "head"
    if role == "head" and not HEAD_POST.search(post):    # "Lady C.O" (Community Organiser), "D.E.O." (Data Entry Operator),
        return "staff"                                   # "Orderly Peon to E.O", "Project Co-ordinator(MUKTA)"
    if role == "deputy" and NOT_DEPUTY.search(post):
        return "staff"
    return role


def links(html, base):
    """Links of a home page whose text or address names staff, officers or contacts (same host), staff words first."""
    host = urlparse(base).hostname.removeprefix("www.")
    first, rest = [], []
    for a in _esw.soup(html).find_all("a", href=True):
        href, text = a["href"].strip(), _esw.clean(a.get_text(" "))
        u = urljoin(base, href).split("#")[0]
        if (urlparse(u).hostname or "").removeprefix("www.") != host or NOT_LINK.search(u) or NOT_LINK.search(text):
            continue
        if not (LINK.search(text) or LINK.search(urlparse(u).path)):
            continue
        if u in first or u in rest or u.rstrip("/") == base.rstrip("/"):
            continue
        (rest if re.search(r"(?i)contact|संपर्क|सम्पर्क|સંપર્ક", text + u) else first).append(u)
    return first + rest


def fetch(module, p, get, rows=None):
    """rows: the function that reads one page (default staff_rows)."""
    rows = rows or staff_rows
    files, recs, seen, pairs = [], [], set(), set()
    n = [0, 0]                    # requests made, requests answered

    def read(u, staff=True):
        n[0] += 1
        r = get(u)
        if r is None:
            return None
        n[1] += 1
        path = urlparse(u).path.strip("/") + ("-" + urlparse(u).query if urlparse(u).query else "")
        files.append(_esw.keep(module, f"{p['site']}-{_esw.slug(path) or 'home'}", r.content))
        if not staff:
            return r
        for row in rows(r.text):
            k = (uslug(row["post"]), uslug(row["name"]))
            if k in pairs:
                provenance.skipped("same row twice")
                continue
            pairs.add(k)
            rid, d = _town2.record(module, p["state"], p["site"], p["body"], row, seen, district=p.get("district"),
                                   lgd_code=p.get("lgd_code"), source=u, src_url=u, slug=uslug)
            d["role"] = role(d["post"], d["role"], p["state"])
            recs.append((rid, d))
        return r

    for u in p.get("pages", [])[:2]:
        read(u)
    if not recs and n[0] < 3:
        home = read(p["url"], staff=False)
        if home is not None:
            for u in links(home.text, p["url"]):
                if n[0] >= 3:
                    break
                if u not in p.get("pages", []):
                    read(u)
    if not n[1]:
        return [], [], "no answer"
    return recs, files, "" if recs else "no staff rows"
