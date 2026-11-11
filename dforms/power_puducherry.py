"""Puducherry: Electricity Department area contacts, electricity.py.gov.in (answers from Germany too).

The index /area-contact-information lists 38 sections (Puducherry, Karaikal, Mahe, Yanam) and the localities each serves, with
one "<area> Area Contact Details" page per locality (334). Pages of one section repeat the same officers, so one queue item =
one section: the payload carries the section, its localities and the url of its first area page (items() lists them from the
index). The area page's first two tables give, in cells of lines: the Executive Engineer of the division, the Assistant Executive
Engineer (O&M sub-division) and, in the second row, the Junior Engineer of the section (Phone Office, Mobile). No names.
Records: one division, one sub-division and one section office per item (division / sub-division ids repeat across sections,
so the same office is one record). "Page last updated date" is kept as last_updated.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, clean, phone, raw, slug

BASE = "https://electricity.py.gov.in"
INDEX = BASE + "/area-contact-information"
REGION = {"KARAIKAL": "Karaikal", "THIRUNALLAR": "Karaikal", "NEDUNGADU": "Karaikal", "AMBAGARATHUR": "Karaikal", "T.R.PATTINAM": "Karaikal",
          "MAHE": "Mahe", "PALLOOR": "Mahe", "YANAM": "Yanam"}


def sections(html):
    """{section: {"areas": [...], "url": first area page}} from the index table."""
    soup = BeautifulSoup(html, "lxml")
    out = {}
    for tr in soup.find_all("tr"):
        td = tr.find_all("td")
        if len(td) < 2:
            continue
        sec = clean(td[0].get_text(" ", strip=True))
        if not sec or not sec.upper().endswith("SECTION"):
            continue
        a = tr.find_all("a", href=True)
        name = clean(td[-1].get_text(" ", strip=True))
        d = out.setdefault(sec, {"areas": [], "url": None})
        if name:
            d["areas"].append(re.sub(r"\s*Area Contact Detail\w*$", "", name))
        if a and not d["url"]:
            h = a[-1]["href"]
            d["url"] = h if h.startswith("http") else BASE + h
    return out


def items(get):
    r = get(INDEX)
    if r is None:
        return []
    return [{"key": f"power_puducherry:{slug(s)}", "payload": {"reader": "power_puducherry", "url": d["url"], "section": s,
             "areas": d["areas"], "state": "PY"}} for s, d in sections(r.text).items() if d["url"]]


def cell(td):
    ls = [clean(x) for x in td.get_text("\n", strip=True).split("\n")]
    ls = [x for x in ls if x]
    off = next((x.split(":", 1)[1] for x in ls if x.lower().startswith("phone office")), None)
    mob = next((x.split(":", 1)[1] for x in ls if x.lower().startswith("mobile")), None)
    addr = ", ".join(x for x in ls[1:] if not re.match(r"(phone office|mobile)", x, re.I) and not x.startswith("("))
    unit = next((x.strip("()") for x in ls[1:3] if x.startswith("(")), None)
    return {"post": ls[0] if ls else None, "unit": clean(unit), "phone": phone(mob, off), "address": clean(addr)}


def parse(html, p, url):
    soup = BeautifulSoup(html, "lxml")
    upd = None
    m = re.search(r"Page last updated date\s*:?\s*([0-9]{2}-[0-9]{2}-[0-9]{4}|[0-9]{2}-[A-Za-z]{3}-[0-9]{4})", soup.get_text(" "))
    if m:
        upd = m.group(1)
    sec = p["section"]
    region = next((v for k, v in REGION.items() if sec.upper().startswith(k)), "Puducherry")
    out = Out("power_puducherry", "PY", url, discom="Electricity Department, Puducherry", last_updated=upd)
    rows = [tr.find_all("td") for tb in soup.find_all("table")[:2] for tr in tb.find_all("tr")]
    rows = [r for r in rows if r and re.search(r"phone|mobile", r[0].get_text(" "), re.I)]      # not the heading rows
    if len(rows) < 2:
        return []
    ee, aee = cell(rows[0][0]), cell(rows[0][1]) if len(rows[0]) > 1 else None
    je = cell(rows[1][0])
    div = re.sub(r"^Executive Engineer[-\s]*", "", ee["post"] or "").strip() or None
    div_area = f"Division {div}" if div else None
    sub_area = aee["unit"] if aee else None
    sec_area = re.sub(r"\s*SECTION$", "", sec, flags=re.I).title()
    if ee["post"]:
        out.add(f"division:{div or ee['post']}", "division", div_area, post=ee["post"], phone_=ee["phone"], address=ee["address"],
                district=region)
    if aee and aee["post"]:
        out.add(f"subdivision:{sub_area or aee['post']}", "subdivision", sub_area, post=aee["post"], phone_=aee["phone"],
                address=aee["address"], district=region, parents={"division": div_area})
    if je["post"]:
        out.add(f"section:{sec_area}", "section", sec_area, post=je["post"], phone_=je["phone"], address=je["address"],
                district=region, parents={"division": div_area, "subdivision": sub_area}, areas=p.get("areas"))
    return out.recs


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_puducherry", slug(p["section"]), r.content, "html")]
    recs = parse(r.text, p, url)
    return recs, files, "" if recs else "no contacts"
