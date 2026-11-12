"""Gujarat: UGVCL (Uttar Gujarat Vij Company, Mehsana) field officers by circle, division and sub-division, www.ugvcl.com/contact
(India only: no answer from Germany; sample fetched from India 2026-11-11; the page footer says "Last updated on: 05-11-2026").
The server does not send its intermediate certificate (Sectigo Public Server Authentication CA OV R36: scrape_hub_client/certs/
sectigo_public_server_ov_r36.pem). Page structure: tabs CORPORATE OFFICE (empty table) | MEHSANA | SABARMATI | HIMATNAGAR | PALANPUR
CIRCLE, one table each (class "employee"): Circle | Division | Sub-Division | Name | Designation, ~660 rows. Rows with a
sub-division = the sub-division office (Deputy Engineer, Junior Engineers, Dy. S.A.); rows with only a division = the division
office (Executive Engineer, Deputy Engineers, accounts staff); rows with neither = the circle office (Superintending Engineer).
Names yes, phones and e-mails no (the page shows none). About 100 sub-divisions, 30 divisions, 4 circles.
Not covered: MGVCL /contact-us.php (no answer from the India servers), DGVCL and PGVCL (TLS closed from Germany and India on
2026-11-11); the MGVCL / UGVCL senior officers are in power2_gujarat.
Records: dept:power2_gj_subdiv:ugvcl:<circle>:<division>:<sub-division>:<post>:<name>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, clean, raw

MODULE = "power2_gj_subdiv"
URLS = {"ugvcl": "https://www.ugvcl.com/contact"}
DISCOM = {"ugvcl": "UGVCL"}


def _strip(s, word):
    return clean(re.sub(rf"\s*\b{word}\b\s*$", "", s or "", flags=re.I)) or clean(s)


def parse(html, discom="ugvcl", url=URLS["ugvcl"]):
    out = Out(MODULE, "GJ", url, discom=DISCOM[discom])
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr"):
            c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(c) != 5 or (c[0] or "").lower() == "circle":
                continue
            circle, div, sub, name, post = c
            if not circle or not (name or post) or tuple(c) in seen:
                continue
            seen.add(tuple(c))  # the page repeats some rows word for word
            post = (post or "").strip('"')
            ca, da, sa = _strip(circle, "circle"), _strip(div, "division"), clean(sub)
            if sa:
                lvl, area, par = "subdivision", sa, {"circle": ca, "division": da}
            elif da:
                lvl, area, par = "division", da, {"circle": ca}
            else:
                lvl, area, par = "circle", ca, None
            out.add(f"{discom}:{ca}:{da or ''}:{sa or ''}:{post}:{name or ''}", lvl, area, post=post, name=name, parents=par)
    return out.recs


def fetch(p, get):
    discom = p.get("discom", "ugvcl")
    url = p.get("url") or URLS[discom]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MODULE, f"{discom}-contact", r.content, "html")]
    recs = parse(r.text, discom, url)
    return recs, files, "" if recs else "no rows"
