"""Karnataka: MESCOM (Mangaluru) office contacts, mescom.karnataka.gov.in (India only). Three pages = three queue items:
- /17/zonal-and-circle-offices/en: one table per zone (2) and circle (4): Sl. No., Officer Name, Designation, E-Mail, Contact No,
  Address. Level zone / circle from the table title.
- /14/divisional-offices/en: one table per O&M division (14): Officer Name, Designation, E-Mail, Contact No, Address.
- /15/subdivision-and-sections/en: one table per sub-division (64): the first row (rowspan) is the sub-division office (AEE and
  staff), then one row per section office (AE / JE (O&M)). Office Name, Designation, E-Mail, Contact No, Address. No names.
A one-cell row with only digits continues the phone cell of the row above. About 243 sections, 64 sub-divisions, 14 divisions.
Records: one per row (office + post); sections and sub-divisions carry the sub-division as parent.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, cells, email, phone, raw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://mescom.karnataka.gov.in/"
PAGES = {"zones": "17/zonal-and-circle-offices/en", "divisions": "14/divisional-offices/en", "sections": "15/subdivision-and-sections/en"}


MOBILE = re.compile(r"\s+(?=[6-9]\d{9}\b)")
CLASS = {"email": lambda x: "@" in x,
         "phone": lambda x: bool(re.fullmatch(r"[\d\s/,-]{6,}", x)),
         "office": lambda x: bool(re.search(r"(sub[- ]?division|section)$", x, re.I)) and "MESCOM" not in x,
         "post": lambda x: bool(re.search(r"(engineer|officer|\bAEE\b|\bJE\b|\bAE\b)", x, re.I)) and "MESCOM" not in x,
         "address": lambda x: "MESCOM" in x or x.startswith("O&M")}


def split_phone(s):
    """'0824-2421833 9448289430' -> ['0824-2421833', '9448289430'] (a landline and a mobile in one cell)."""
    return MOBILE.split(s.strip()) if s else []


def tables(soup):
    for tb in soup.find_all("table"):
        t = tb.get_text(" ", strip=True)
        if "Screen Reader" in t or "Document Type" in t:
            continue
        yield tb


def parse(html, page, url):
    soup = BeautifulSoup(html, "lxml")
    out = Out("power_mescom", "KA", url, discom="MESCOM")
    for tb in tables(soup):
        title, head, last = None, None, None
        for tr in tb.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = cells(tr)
            if len(c) == 1:
                if re.fullmatch(r"[\d\s/-]{6,}", c[0]) and last is not None:
                    last["phone"] = phone(last.get("phone"), *split_phone(c[0]))
                elif "reserved" not in c[0].lower():
                    title = c[0]
                continue
            if any(x.lower() in ("designation", "e-mail") for x in c):
                head = [x.lower() for x in c]
                continue
            if not head or not title:
                provenance.skip_row(tr, 'skip: not head or not title')
                continue
            if page == "sections":
                kind = {k: next((x for x in c if f(x)), None) for k, f in CLASS.items()}
                if len(c) >= 6:                                    # a full row: the first cell is the office, the second the post
                    kind["office"], kind["post"] = c[0], c[1]
                if not kind["office"] and not kind["post"]:
                    if kind["phone"] and last is not None:          # the phone cell of a rowspan row, on its own row
                        last["phone"] = phone(last.get("phone"), *split_phone(kind["phone"]))
                    continue
                if kind["office"]:
                    office = kind["office"]
                elif last is None or last.get("_office") is None:
                    office = title
                else:
                    office = last["_office"]
                same = last is not None and last.get("_office") == office
                is_sub = office == title or re.search(r"sub[- ]?division$", office, re.I)
                lvl = "subdivision" if is_sub else "section"
                area = re.sub(r"\s*(Sub[- ]?division|Section)$", "", office, flags=re.I)
                par = {"subdivision": re.sub(r"\s*Sub[- ]?division$", "", title, flags=re.I)} if lvl == "section" else None
                mail = email(kind["email"]) or (last.get("email") if same else None)
                addr = kind["address"] or (last.get("address") if same else None)
                if last is not None:
                    last.pop("_office", None)
                last = out.add(f"{lvl}:{area}:{kind['post']}", lvl, area, post=kind["post"], phone_=phone(*split_phone(kind["phone"])),
                               email_=mail, address=addr, parents=par)
                last["_office"] = office
            else:
                d = dict(zip(head, c))
                lvl = "division" if page == "divisions" else ("zone" if "zone" in title.lower() else "circle")
                area = re.sub(r"\s*(Zone|Circle|Division)$", "", title, flags=re.I)
                post = d.get("designation")
                last = out.add(f"{lvl}:{area}:{post}:{d.get('officer name')}", lvl, area, post=post, name=d.get("officer name"),
                               phone_=phone(*split_phone(d.get("contact no"))), email_=email(d.get("e-mail")), address=d.get("address"))
    for _, d in out.recs:
        d.pop("_office", None)
    out.src = {}
    return out.recs


def fetch(p, get):
    page = p["page"]
    url = p.get("url") or BASE + PAGES[page]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_mescom", page, r.content, "html")]
    recs = parse(r.text, page, url)
    return recs, files, "" if recs else "no rows"
