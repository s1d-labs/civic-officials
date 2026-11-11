"""Sikkim Police: police.sikkim.gov.in/visitor/telephonepolice. India only. The server omits its intermediate certificate
(GlobalSign GCC R6 AlphaSSL CA 2025, now in certs/). One table: Sl.No | Rank | Official Mobile Number | Official Email ID,
with a row per district ("PAKYONG DISTRICT" ...) before its officers. Kept: SHO/<station> rows (27 police stations), SDPO/<place>
(subdivisions) and SP, SSP, ASP of each district. Headquarters posts above the first district row are left out. No names.
Record id dept:police_sk:<district>:<post>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

M = "police_sk"
URL = "https://police.sikkim.gov.in/visitor/telephonepolice"


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs, district = [], None
    for tr in soup.find_all("tr"):
        c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) == 1 and c[0] and c[0].upper().endswith("DISTRICT"):
            district = c[0].title().replace(" District", "")
            continue
        if district is None or len(c) < 3:
            continue
        post = c[1] or ""
        m = re.match(r"^(SHO|SDPO|SSP|SP|ASP)\s*/\s*(.+)$", post.replace(" / ", "/").replace(" /", "/"))
        if not m:
            continue
        kind, place = m.group(1), m.group(2).title()
        level = {"SHO": "police_station", "SDPO": "subdivision"}.get(kind, "district")
        num = re.sub(r"\((?:M|O|FAX)\)", " ", c[2] or "")
        recs.append(rec(M, f"{slug(district)}:{slug(post)}", level=level, area=place if level != "district" else district,
                        post=kind, phone=phones(num), email=email(c[3] if len(c) > 3 else None), state="SK",
                        district=district, source=url))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, "telephonepolice.html", r.content)]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
