"""Kerala: KSEB section offices, kseb.in/contact "Section Office details" (India only). One queue item = one electrical circle.

fetch() makes two requests on one session: GET /contact (session cookie + the form's hidden _token), then POST /searchsection with
selectcircle=<English circle name> and the other selects empty. The answer lists every section office of the circle as a card and
an off-canvas table: Section Office, Section Code, Phone, Office email, Sub Division (name + email), Division (name, email, phone),
Circle (name, email, phone), Region. The 'Know Your Section' consumer lookup (captcha) is not used.
Records: one per section (level section, office_id = section code), plus one per sub-division, division and circle (the same
id from every section that names it). About 776 sections, ~220 sub-divisions, 75 divisions, 26 circles. The site stores the
landlines as numbers, so the leading 0 of the STD code is lost ("4772245532"): std0() puts it back on a 10-digit number that does
not start with 6-9 (Kerala STD codes are 04xx; mobiles start with 6-9). A sub-division / division / circle that the sections
spell two ways ("North Paravur" / "NorthParavur") keeps one record (the first spelling). No officer names.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, clean, email, phone, raw, slug

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://kseb.in/"
FIELDS = {"Section Office:": "section", "Section Code:": "code", "Phone:": "phone", "Office email:": "email",
          "Sub Division:": "subdivision", "Division:": "division", "Circle:": "circle", "Region:": "region"}


def lines(td):
    return [clean(x) for x in td.get_text("\n", strip=True).split("\n") if clean(x)]


def std0(p):
    """'4772245532, 9496010101' -> '04772245532, 9496010101': a 10-digit landline that lost the leading 0 of its STD code."""
    if not p:
        return p
    return ", ".join("0" + x if re.fullmatch(r"[1-5]\d{9}", x) else x for x in p.split(", "))


def unit(ls):
    """['Alappuzha', 'eealpy@gmail.com', '4772243487'] -> (name, email, phone)."""
    name = next((x for x in ls if "@" not in x and not re.fullmatch(r"[\d\s+-]+", x)), None)
    return name, email(" ".join(x for x in ls if "@" in x)), std0(phone(*[x for x in ls if re.fullmatch(r"[\d\s+-]{6,}", x)]))


def parse(html, circle_asked, url=BASE + "searchsection"):
    soup = BeautifulSoup(html, "lxml")
    out = Out("power_kseb", "KL", url, discom="KSEB")
    for tb in soup.select("table.section-details-table"):
        d = {}
        for tr in tb.find_all("tr"):
            th, td = tr.find("th"), tr.find("td")
            if th and td and th.get_text(strip=True) in FIELDS:
                d[FIELDS[th.get_text(strip=True)]] = lines(td)
        sec = (d.get("section") or [None])[0]
        if not sec:
            continue
        sd, sde, sdp = unit(d.get("subdivision", []))
        dv, dve, dvp = unit(d.get("division", []))
        ci, cie, cip = unit(d.get("circle", []))
        region = (d.get("region") or [None])[0]
        code = (d.get("code") or [None])[0]
        out.add(f"section:{code or sec}", "section", sec, post="Section Office", office_id=code,
                phone_=std0(phone(*d.get("phone", []))), email_=email(" ".join(d.get("email", []))),
                parents={"zone": region, "circle": ci, "division": dv, "subdivision": sd})
        if sd:
            out.add(f"subdivision:{dv}:{sd}", "subdivision", sd, post="Sub Division Office", email_=sde, phone_=sdp,
                    parents={"zone": region, "circle": ci, "division": dv})
        if dv:
            out.add(f"division:{dv}", "division", dv, post="Division Office", email_=dve, phone_=dvp,
                    parents={"zone": region, "circle": ci})
        if ci:
            out.add(f"circle:{ci}", "circle", ci, post="Circle Office", email_=cie, phone_=cip, parents={"zone": region})
    # a sub-division / division / circle named by several sections: keep one record per id (the first)
    # (the same office spelt with or without a blank: the slug without hyphens)
    seen, recs = set(), []
    for rid, dd in out.recs:
        base = rid.split("~")[0]
        key = base.replace("-", "")
        if key in seen and not rid.startswith("dept:power_kseb:section-"):
            continue
        seen.add(key)
        recs.append((base if not rid.startswith("dept:power_kseb:section-") else rid, dd))
    return recs


def fetch(p, get):
    circle = p["circle"]
    r = get(BASE + "contact")
    if r is None:
        return [], [], "contact page did not answer"
    form = BeautifulSoup(r.text, "lxml").find("form", action=re.compile(r"searchsection"))
    tok = form.find("input", attrs={"name": "_token"}) if form else None
    if not tok or not tok.get("value"):
        return [], [], "no form token on the contact page"
    r2 = get(BASE + "searchsection", method="POST",
             data={"_token": tok["value"], "selectcircle": circle, "selectdivision": "", "selectsubdivision": "", "selectsection": ""})
    if r2 is None:
        return [], [], "search did not answer"
    files = [raw("power_kseb", f"searchsection-{slug(circle)}", r2.content, "html")]
    recs = parse(r2.text, circle)
    return recs, files, "" if recs else "no section offices"
