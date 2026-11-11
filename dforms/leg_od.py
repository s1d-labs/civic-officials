"""Odisha: members of the 17th Legislative Assembly (2024-) with address, phone and email, from the assembly's member cards
(assembly.odisha.gov.in/MemberofAssembly.aspx; odishaassembly.nic.in redirects there). 16 cards per page, 147 members, so about
10 pages; the next page is an ASP.NET postback ("Next" button) with the form state of the page before it, in the same session.
Answers only from India (from Germany the redirect to the new host ends without a page).

Card: name, party, "Constituency Name: Bargarh - ( Bargarh , Odisha )" (constituency - (district, state)), date of birth, one
address (the member's home address: written "At/Po ..."), phone(s), email(s) (written x[dot]y[at]gov[dot]in). No AC number: the
name and district decide. No office address, no constituency office. One queue item = the whole list (all pages).
Record ids: dept:leg_od:OD-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_se

MODULE = "leg_od"
URL = "https://assembly.odisha.gov.in/MemberofAssembly.aspx"
MAX_PAGES = 20
# site spellings -> the names of ac_no.json (normalised)
ALIAS = {"bhubaneswarcentralmadhya": "bhubaneswarmadhya", "bhubaneswarnorthuttar": "bhubaneswaruttar",
         "ekamrabhubaneswar": "ekamrabhubaneshwar", "laxmipur": "lakshmipur", "mahakalapara": "mahakalapada",
         "nabarangapur": "nabarangpur", "nimapada": "nimapara", "padmapur": "padampur", "sarashkana": "saraskana",
         "talasara": "talsara"}


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "OD", "india_only": True}}]


def _seat(constituency, district):
    k = _esw.norm_ac(constituency)
    n, note = _leg_se.seat("OD", None, constituency, district)
    if not n and k in ALIAS:
        n, note = _leg_se.seat("OD", None, ALIAS[k], district)
    return n, note


def parse(html, url):
    recs = []
    for card in _esw.soup(html).select("div.memeber-item"):
        h3 = card.find("h3")
        nm = _leg_se.name(h3.get_text(" ") if h3 else "")
        if not nm:
            continue
        party = _esw.clean(card.find("h6").get_text(" ")) if card.find("h6") else ""
        cons_raw, dob = "", ""
        for tr in card.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 2 and "Constituency" in tds[0].get_text():
                cons_raw = _esw.clean(tds[1].get_text(" "))
            elif len(tds) == 2 and "Birth" in tds[0].get_text():
                dob = _esw.clean(tds[1].get_text(" "))
        m = re.match(r"(.*?)\s+-\s+\(\s*([^,()]+?)\s*,\s*[^()]*\)\s*$", cons_raw)
        constituency, district = (_esw.clean(m.group(1)), _esw.clean(m.group(2)).title()) if m else (cons_raw, "")
        constituency = re.sub(r"\s*\(\s*", " (", constituency).replace(" )", ")")
        address = phone = email = ""
        for li in card.select("ul.icon-info-memeber li"):
            icon = " ".join(li.find("i").get("class", [])) if li.find("i") else ""
            t = _esw.clean(li.get_text(" "))
            if "map-marker" in icon:
                address = t
            elif "phone" in icon:
                phone = t
            elif "envelope" in icon:
                email = t
        no, note = _seat(constituency, district)
        recs.append(_leg.member(MODULE, "OD", "AC", no, nm, constituency=constituency, party=party, source=url, phone=phone,
                                email=email, residence_address=address, district=district, note=note,
                                house="Odisha Legislative Assembly (17th)"))
    return recs


def _form(html, button):
    """The page's form fields (hidden state + filters as they are) and the pressed button, for the next postback."""
    s = _esw.soup(html)
    data = {}
    for inp in s.find_all("input"):
        n, t = inp.get("name"), (inp.get("type") or "text").lower()
        if n and t not in ("submit", "button", "image", "checkbox", "radio"):
            data[n] = inp.get("value", "")
    nxt = s.find("input", {"name": button})
    if nxt is None or nxt.has_attr("disabled"):
        return None
    data[button] = nxt.get("value", "Next")
    return data


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files, recs, seen = [], [], set()
    for page in range(1, MAX_PAGES + 1):
        files.append(_leg.keep(MODULE, f"page-{page}", r.content))
        new = [x for x in parse(r.text, p["url"]) if x[0] not in seen]
        if not new:
            break
        seen.update(x[0] for x in new)
        recs += new
        data = _form(r.text, "ctl00$ContentPlaceHolder1$btnNext")
        if data is None:
            break
        r = get(p["url"], method="POST", data=data)
        if r is None:
            return recs, files, "" if recs else "no answer to the next page"
    return recs, files, "" if recs else "no members in the page"
