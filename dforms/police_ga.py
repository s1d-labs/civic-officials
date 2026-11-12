"""Goa Police: one page per station on the citizen portal, citizen.goapolice.gov.in/web/guest/<name>-police-station (46 links on
the portal home, some with a space in the path, incl. special units: ANC, ATS, cyber, coastal and railway police stations).
The article block holds 'INCHARGE: NAME , RANK', 'Contact No:', 'Mobile No:' (official 7875756xxx CUG), 'Email:' ([at]/[dot]
masked), 'Fax No:'; the map portlet's mapAddress is the address. The 'Last Modified Date' changes every day, so it is not kept.
Works from outside India. One queue item = one station page. Record id dept:police_ga:<page slug>."""
import html as htmlmod
import re
from urllib.parse import quote, unquote, urljoin

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

M = "police_ga"
HOME = "https://citizen.goapolice.gov.in/"


def page_url(href):
    return urljoin(HOME, quote(unquote(href), safe="/:.-_~"))


def page_key(url):
    name = unquote(url.rstrip("/").rsplit("/", 1)[-1])
    return slug(name.replace(" ", ""))


def items(get):
    r = get(HOME)
    if r is None:
        return []
    hrefs = []
    for a in BeautifulSoup(r.text, "lxml").find_all("a", href=re.compile(r"/web/guest/[^\"]*police-station")):
        u = page_url(a["href"])
        if u not in hrefs:
            hrefs.append(u)
    return [{"key": f"{M}:{page_key(u)}", "payload": {"reader": M, "url": u, "state": "GA"}} for u in hrefs]


def parse(html, url):
    soup = BeautifulSoup(html, "lxml")
    art = next((a for a in soup.select(".journal-content-article") if "INCHARGE" in a.get_text().upper()), None)
    if art is None:
        return []
    lines = [clean(x.get_text(" ", strip=True)) for x in art.find_all(["h2", "h3", "h4", "p"])]
    lines = [x for x in lines if x]
    text = "\n".join(lines)
    station = lines[0] if lines and "INCHARGE" not in lines[0].upper() else None

    def field(label):
        m = re.search(rf"{label}\s*:?\s*(.*)", text, re.I)
        return clean(m.group(1)) if m else None

    name = rank = None
    m = re.search(r"IN\s?CHARGE\s*:\s*(.+)", text, re.I)
    if m:
        parts = [clean(x) for x in m.group(1).split(",") if clean(x)]
        name = parts[0] if parts else None
        rank = ", ".join(parts[1:]) or None
    mob, land, fax = phones(field("Mobile No")), phones(field("Contact No")), phones(field("Fax No"))
    mm = re.search(r'mapAddress:"([^"]*)"', html)
    addr = clean(htmlmod.unescape(mm.group(1))) if mm else None
    k = page_key(url)
    return [rec(M, k, area=station or k, post="Police station in-charge", name=name, rank=rank, phone=phones(mob, land),
                mobile=mob, landline=land, fax=fax, email=email(field("Email") or ""), address=addr, state="GA",
                source=url)]


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, f"{page_key(url)}.html", r.content)], "" if recs else "no INCHARGE block"
