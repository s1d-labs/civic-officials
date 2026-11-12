"""Shared reader for the NeVA (National e-Vidhan Application) member directories: <house>.neva.gov.in, one site per house
(jkla, hrla, hpvs, jhla, arla, wbla, uplc ...). The readers dforms/leg_jk, leg_hr, leg_hp, leg_jh, leg_ar, leg_wb and leg_uplc
call this module. Answers from Germany (2026-11-11).

The site keeps the house in the session: the first page of the host sets ASP.NET_SessionId and the "lang" cookie (hi-IN, bn-IN,
en-US ... per house). The members page (/ContactDirectory/MenuContactDirec) then loads the list with its own JavaScript:
FetchMemberList(16, <house no>) = GET /ContactDirectory/FetchMembersList?MLT=16&MSLT=<no>&Assemblyid=<no> (an HTML fragment).
The site's own language switch is GET /Home/ChangeInEngCulture?lang=<GUID>&langCulCode=en-US (the GUID is in every page's
ChangeLangaugeEnglish()). The reader reads the list in the house's default language, then in English when the default is not
English: English names and constituency names decide the seat (dforms/ac_no.json); the regional text goes in name_regional /
area_regional.

One card per member (div.search-item): link /Member/Details/<id>?AssemblyID=<no>, name (with an honorific), party,
"Constituency Name : [<AC no> - ]<constituency> -<district> (<state>)", date of birth (not kept), then icons: location-dot =
address (a residence in the capital or the home address; the card does not say which), fax, phone, envelope = email (written
x[at]y[dot]in). Some houses fill only a few contacts (Haryana: 5 of 90). No constituency office.
"""
import difflib
import json
import re
from pathlib import Path

import provenance
from dforms import _esw, _leg, _leg_se

_AC = None

LANG_EN = "7C4F28F6-02FC-4627-993D-E255037531AD"
SHARED = "the list has {n} members for this seat (a by-election); it does not say who sits now"
HONORIFIC = re.compile(r"^(?:(?:sh|shree|janab|mr|mrs|ms)\.?\s+)+", re.I)
HONORIFIC_REGIONAL = re.compile(r"^(?:(?:श्रीमती|श्रीमति|सुश्री|श्री|कुमारी|डॉ०?|डा0|শ্রীমতী|শ্রীমতি|শ্রী|ಶ್ರೀಮತಿ|ಶ್ರೀ)\.?\s*)+")
# district: one inner bracket allowed ("Nuh -Mewat(Nuh) (Haryana)"); a trailing "*" is dropped ("Kinnaur -KINNAUR (ST)*")
CONS = re.compile(r"^(?:(?P<no>\d{1,3})\s*-\s*)?(?P<cons>.*?)(?:\s+-(?=\S)(?P<district>(?:[^()]|\([^()]*\)(?=\s*\())*?))?"
                  r"\s*(?:\((?P<state>[^()]*)\))?\s*\**$")


def item(module, state, host, house, house_name, kind="AC", india_only=False):
    """The one queue item of a house: the whole member list."""
    return {"key": f"{module}-list", "payload": {"reader": module, "url": list_url(host, house), "host": host, "state": state,
                                                 "house": house, "house_name": house_name, "kind": kind,
                                                 "india_only": india_only}}


def list_url(host, house):
    return f"https://{host}/ContactDirectory/FetchMembersList?MLT=16&MSLT={house}&Assemblyid={house}"


def english(html):
    return "Constituency Name" in html


def name(s):
    s = _leg_se.name(HONORIFIC.sub("", _esw.clean(s)))
    return _esw.clean(HONORIFIC_REGIONAL.sub("", s))


def constituency(text):
    """(AC no or None, constituency, district): '76 - Daltonganj -Palamu (Jharkhand)' -> (76, 'Daltonganj', 'Palamu');
    'Tuting-Yingkiong' -> (None, 'Tuting-Yingkiong', '')."""
    t = _esw.clean(text)
    m = CONS.match(t)
    if not m:
        return None, t, ""
    no = int(m.group("no")) if m.group("no") else None
    return no, _esw.clean(m.group("cons")).strip(" -"), _esw.clean(m.group("district") or "")


def near(state, cons):
    """(AC number, layer name) for a constituency name that is spelled a little differently in dforms/ac_no.json, or (None, "").
    Only a clear best match counts (similarity >= 0.85 and 0.1 above the next name). Not for JK and AS: there the new seats
    after the 2022/2023 delimitation have names close to other old seats."""
    global _AC
    if state in ("JK", "AS") or not cons:
        return None, ""
    if _AC is None:
        _AC = json.loads((Path(__file__).parent / "ac_no.json").read_text())
    names = {k: v for k, v in _AC.get(state, {}).items() if k and "@" not in k}
    k = _esw.norm_ac(re.sub(r"\((sc|st|bl|gen)\)", "", cons, flags=re.I))
    if not k:
        return None, ""
    scores = sorted(((difflib.SequenceMatcher(None, k, n).ratio(), n) for n in names), reverse=True)
    if scores and scores[0][0] >= 0.85 and (len(scores) == 1 or scores[0][0] - scores[1][0] >= 0.1):
        return names[scores[0][1]], scores[0][1]
    return None, ""


def cards(html):
    """[{id, name, party, cons_text, address, phone, fax, email}] in page order."""
    out = []
    for k, it in enumerate(_esw.soup(html).select("div.search-item"), 1):
        a = it.find("a", href=re.compile(r"/Member/Details/\d+"))
        h3 = it.find("h3")
        if not a or not h3:
            continue
        d = {"id": re.search(r"/Member/Details/(\d+)", a["href"]).group(1), "href": a["href"],
             "name": _esw.clean(h3.get_text(" ")),
             "party": _esw.clean(it.find("h6").get_text(" ")) if it.find("h6") else "", "cons_text": "",
             "address": "", "phone": "", "fax": "", "email": "", "card": k}
        for tr in it.select("div.card-body table tr"):
            tds = tr.find_all("td")
            if len(tds) == 2 and not d["cons_text"]:
                d["cons_text"] = _esw.clean(tds[1].get_text(" "))        # the first row: constituency (any language)
        for li in it.select("ul.icon-info li"):
            icon = " ".join(li.find("i").get("class", [])) if li.find("i") else ""
            t = _esw.clean(li.get_text(" ")).strip(' ".')
            t = t if re.search(r"\w", t) else ""                    # "-" and "." stand for nothing
            if "location" in icon or "map-marker" in icon:
                d["address"] = t
            elif "fax" in icon:
                d["fax"] = t
            elif "phone" in icon:
                d["phone"] = t
            elif "envelope" in icon:
                d["email"] = t
        out.append(d)
    return out


def parse(html, url, p, regional_html=None, alias=None, src=None):
    """Records of one house from the English list (html); regional_html = the same list in the house's own language.
    src: provenance.at() of the English answer (the list url is asked twice: in the house's language, then in English)."""
    st, kind, host = p["state"], p.get("kind", "AC"), p["host"]
    regional = {c["id"]: c for c in cards(regional_html)} if regional_html else {}
    rows = []
    for c in cards(html):
        no_text, cons, district = constituency(c["cons_text"])
        no, note, match = None, "", ""
        if kind == "AC":
            no, note = _leg_se.seat(st, no_text, cons, district or None, alias)
            if not no:
                no, match = near(st, cons)
                match = f"near name match: {match}" if no else ""
        rows.append((c, no_text, cons, district, no, note, match))
    per_seat = {}
    for r in rows:
        if r[4]:
            per_seat[r[4]] = per_seat.get(r[4], 0) + 1
    recs = []
    for c, no_text, cons, district, no, note, match in rows:
        if no and per_seat[no] > 1:
            no, note = None, SHARED.format(n=per_seat[no])
        rg = regional.get(c["id"])
        nm = name(c["name"])
        extra = {}
        if rg and rg["name"] != c["name"]:
            extra["name_regional"] = name(rg["name"])
            extra["area_regional"] = constituency(rg["cons_text"])[1]
            extra["party_regional"] = rg["party"] if rg["party"] != c["party"] else ""
        recs.append(_leg.member(p["reader"], st, kind, no, nm, constituency=cons, party=c["party"], source=url,
                                phone=c["phone"], email=c["email"], address=c["address"], note=note,
                                fax=_esw.phones(c["fax"]), district=district, seat_no=no_text,
                                member_page=f"https://{host}{c['href']}", member_id=c["id"], house=p.get("house_name", ""),
                                seat_match=match, src_pos={"selector": "div.search-item", "card": c["card"],
                                                           "member_id": c["id"]}, **(src or {}), **extra))
    count = {}
    for rid, _ in recs:
        count[rid] = count.get(rid, 0) + 1
    out, seen = [], set()
    for rid, d in recs:                    # two names, one seat (or one name twice): the name, then the member id keeps them apart
        if count[rid] > 1 or rid.endswith("-x-"):        # "-x-": a constituency name without Latin letters
            rid = f"{rid}-{_esw.slug(d['name']) or d['member_id']}".replace("-x--", "-x-")
            rid = f"{rid}-{d['member_id']}" if rid in seen else rid
        seen.add(rid)
        out.append((rid, d))
    return out


def fetch(module, p, get, alias=None):
    host = p["host"]
    if get(f"https://{host}/") is None:                       # sets the house and the language in the session
        return [], [], "no answer"
    r = get(p["url"], headers={"X-Requested-With": "XMLHttpRequest"})
    if r is None:
        return [], [], "no answer (member list)"
    files = [_leg.keep(module, "list", r.content)]
    first = r.content.decode("utf-8", "replace")
    if not cards(first):
        return [], files, "no members in the list"
    if english(first):
        return parse(first, p["url"], p, alias=alias, src=provenance.at(r, p["url"])), files, ""
    get(f"https://{host}/Home/ChangeInEngCulture?lang={LANG_EN}&langCulCode=en-US", headers={"X-Requested-With": "XMLHttpRequest"})
    r2 = get(p["url"], headers={"X-Requested-With": "XMLHttpRequest"})
    if r2 is None:
        return [], files, "no answer (English member list)"
    files.append(_leg.keep(module, "list-en", r2.content))
    en = r2.content.decode("utf-8", "replace")
    if not english(en) or not cards(en):
        return [], files, "the English member list did not come"
    recs = parse(en, p["url"], p, regional_html=first, alias=alias, src=provenance.at(r2, p["url"]))
    return recs, files, "" if recs else "no members"
