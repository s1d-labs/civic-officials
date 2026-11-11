"""Karnataka: CESC Mysore office contacts, cescmysore.karnataka.gov.in/new-page/<office>/en (India only; the link answers 307 to
/<id>/<office>/en, which requests follows). The 25 office pages linked from /2/contact-us/en = 25 queue items: 2 zonal offices,
4 O&M circles, 19 O&M divisions (the corporate office page is left out).

Each page holds one table. A one-cell row is an office heading (the division, then each sub-division: "Central Subdivision"), a
row "Address : ..." gives that office's address, and the other rows are Sl No, Designation, Mobile Number, Landline, Fax, Email Id.
Rows "Section Officer - <section> AE|JE" are section offices (level section) under the sub-division above; "... Service station"
rows are the division's 24x7 service stations (level section, post "Service Station"). No officer names. A division page lists
~8-12 sub-divisions and ~20-40 section officers; all 19 together ~300 sections.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, phone, raw, slug

BASE = "https://cescmysore.karnataka.gov.in/"
SECTION = re.compile(r"^Section\s*Officer\s*-?\s*(.+?)\s*(?:\b(AE|JE|AEE)\b\.?)?\s*$", re.I)
STATION = re.compile(r"^(?:Service\s*Station\s*-\s*(.+)|(.+?)\s*Service\s*station)$", re.I)


def head_level(text, page_level):
    t = text.lower()
    if "sub" in t and "div" in t:
        return "subdivision"
    if "zon" in t:
        return "zone"
    if "circle" in t:
        return "circle"
    if "division" in t:
        return "division"
    return page_level


def bare(text):
    return clean(re.sub(r"\s*(O&M\s*)?(Sub\s*-?\s*division|Division|Circle|Zonal Office|Zone)\s*$|^(Zonal Office|O&M Circle)\s*-\s*", "",
                        text, flags=re.I)) or clean(text)


def parse(html, page_level, url, district=None):
    soup = BeautifulSoup(html, "lxml")
    out = Out("power_cescmysore", "KA", url, discom="CESC Mysore")
    office = {}            # level -> name of the office above the current row
    cur, addr, head = None, None, None
    for tb in soup.find_all("table"):
        t = tb.get_text(" ", strip=True)
        if "Screen Reader" in t or "Document Type" in t:
            continue
        for tr in tb.find_all("tr"):
            c = [x for x in cells(tr)]
            if not any(c):
                continue
            if len(c) == 1 or (len([x for x in c if x]) == 1 and not re.match(r"^\d+$", c[0])):
                txt = next(x for x in c if x)
                if txt.lower().startswith("address"):
                    addr = clean(txt.split(":", 1)[1] if ":" in txt else txt)
                else:
                    cur = head_level(txt, page_level)
                    office = {k: v for k, v in office.items() if LEVELS.index(k) < LEVELS.index(cur)}
                    office[cur] = bare(txt)
                    addr = None
                continue
            low = [x.lower() for x in c]
            if any("designation" in x for x in low):
                head = low
                continue
            if not head or not cur:
                continue
            d = dict(zip(head, c))
            post = clean(d.get("designation"))
            if not post:
                continue
            mob = d.get("mobile number") or d.get("mobile")
            ph = phone(mob, d.get("landline"))
            mail = email(d.get("email id") or d.get("email"))
            par = {k: v for k, v in office.items() if k != cur}
            m, s = SECTION.match(post), STATION.match(post)
            if m:
                area = clean(m.group(1).strip(" -"))
                p = f"Section Officer ({m.group(2).upper()})" if m.group(2) else "Section Officer"
                out.add(f"section:{office.get('division')}:{area}:{p}", "section", area, post=p, phone_=ph, email_=mail,
                        district=district, parents={**par, cur: office[cur]})
            elif s:
                area = clean((s.group(1) or s.group(2)).strip(" -"))
                out.add(f"station:{office.get('division')}:{area}", "section", area, post="Service Station", phone_=ph, email_=mail,
                        district=district, parents={**par, cur: office[cur]})
            else:
                out.add(f"{cur}:{office[cur]}:{post}", cur, office[cur], post=post, phone_=ph, email_=mail, address=addr,
                        district=district, parents=par)
    return out.recs


LEVELS = ("state", "zone", "circle", "division", "subdivision", "section")


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_cescmysore", slug(p.get("office") or url), r.content, "html")]
    recs = parse(r.text, p.get("level", "division"), url, p.get("district"))
    return recs, files, "" if recs else "no rows"
